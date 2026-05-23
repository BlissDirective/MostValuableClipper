import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useLocalSearchParams, useRouter, Stack } from "expo-router";
import {
  ChevronLeft,
  Download,
  Film,
  Pencil,
  Repeat,
  Sparkles,
  Trash2,
  Bot,
  Zap,
  Share2,
} from "lucide-react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Video, ResizeMode } from "expo-av";

import { tokens } from "@/constants/tokens";
import { ActionButton } from "@/components/ActionButton";
import SwarmActionSheet from "@/components/SwarmActionSheet";
import SwarmConfigModal, { SwarmExecutionConfig, SwarmPoolType } from "@/components/SwarmConfigModal";
import { AccountBadge, Platform } from "@/components/AccountBadge";
import { MetricChip } from "@/components/MetricChip";
import { SafetyFlag, SafetyVariant } from "@/components/SafetyFlag";
import { clipsApi, Clip } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { useSwarmExecution, useSwarmAllocation } from "@/lib/api-hooks";
import { triggerHaptic } from "@/utils/haptics";

interface DetailData {
  id: string;
  sourceName: string;
  sourceUrl: string;
  caption: string;
  platforms: { platform: Platform; handle: string; views: string; watchTime: string; earnings: string }[];
  safety?: { variant: SafetyVariant; categories: string[]; reasoning: string; actionTaken: string; } | null;
  videoUrl?: string;
  hasMetrics?: boolean;
  views?: number;
  likes?: number;
  shares?: number;
  comments?: number;
  watchTimeSeconds?: number;
  retentionPct?: number;
  earningsCents?: number;
  metricsSyncedAt?: string;
}

export default function ClipDetailScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ id: string }>();
  const [clipData, setClipData] = useState<Clip | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const doSignOut = useAuthStore((s) => s.doSignOut);

  // Video player state
  const [videoStatus, setVideoStatus] = useState<{ isPlaying: boolean }>({ isPlaying: false });

  // Swarm action sheet + config modal state
  const [swarmSheetOpen, setSwarmSheetOpen] = useState(false);
  const [configuringSwarm, setConfiguringSwarm] = useState<string | null>(null);

  // Swarm allocation data
  const { allocation, tier, isLoading: allocationLoading } = useSwarmAllocation();

  const {
    isRunning: swarmRunning,
    runHookSwarm,
    runRemixSwarm,
    runPostSwarm,
    runABTestSwarm,
    runMusicMatchSwarm,
    runThumbnailSwarm,
    runSafetySwarm,
    runHooksAnalysisSwarm,
    runSegmentAnalyzeSwarm,
    runEditSwarm,
  } = useSwarmExecution();

  // Pool metadata for config modal
  const poolMeta = useMemo(() => {
    const meta: Record<string, { label: string; color: string; desc: string; category: string }> = {
      hook: { label: 'Hook Generation', color: '#6366f1', desc: 'Generate multiple hook variations with different personas', category: 'Generate' },
      thumbnail: { label: 'Thumbnail Generation', color: '#8b5cf6', desc: 'Create thumbnails with different style strategies', category: 'Generate' },
      remix: { label: 'Remix Clip', color: '#10b981', desc: 'Generate AI-powered remix variants', category: 'Edit' },
      edit: { label: 'Edit Recipe', color: '#06b6d4', desc: 'Apply automated edit recipes (cuts, captions, zoom)', category: 'Edit' },
      segment_analyze: { label: 'Segment Analysis', color: '#0ea5e9', desc: 'Find best moments: energy peaks, faces, questions', category: 'Edit' },
      safety: { label: 'Safety Check', color: '#f59e0b', desc: 'Run multi-level safety screening (strict to permissive)', category: 'Analyze' },
      hooks_analysis: { label: 'Hooks Analysis', color: '#ec4899', desc: 'Analyze historical hook performance patterns', category: 'Analyze' },
      ab_test: { label: 'A/B Test Analysis', color: '#f97316', desc: 'Compare variants with different winner strategies', category: 'Analyze' },
      music_match: { label: 'Music Match', color: '#14b8a6', desc: 'Match music tracks by energy, tempo, mood, or contrast', category: 'Enhance' },
      post: { label: 'Multi-Account Post', color: '#eab308', desc: 'Post to all connected accounts simultaneously', category: 'Post' },
    };
    return meta;
  }, []);

  const getPoolAllocation = useCallback((poolType: string) => {
    return (allocation && allocation[poolType]) || 1;
  }, [allocation]);

  const getTierLimit = useCallback(() => {
    switch (tier) {
      case 'enterprise': return 10;
      case 'pro': return 5;
      case 'basic': return 2;
      default: return 1;
    }
  }, [tier]);

  useEffect(() => {
    if (!params.id) return;
    let cancelled = false;
    setLoading(true);
    clipsApi.getById(params.id)
      .then((res) => {
        if (!cancelled) setClipData(res.data);
      })
      .catch((err) => {
        console.warn("[clip-detail] fetch failed:", err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [params.id]);

  // Number formatting helpers
  const formatNumber = useCallback((n?: number): string => {
    if (n === undefined || n === null) return "—";
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
    return String(n);
  }, []);

  const formatDuration = useCallback((seconds?: number): string => {
    if (!seconds) return "—";
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    return `${m}m ${s}s`;
  }, []);

  const formatCurrency = useCallback((cents?: number): string => {
    if (cents === undefined || cents === null) return "—";
    return `$${(cents / 100).toFixed(2)}`;
  }, []);

  // Map backend Clip to DetailData for rendering
  const clip = useMemo<DetailData>(() => {
    if (clipData) {
      const safety = clipData.safety_flags?.length
        ? {
            variant: "warn" as SafetyVariant,
            categories: clipData.safety_flags,
            reasoning: "Automated safety screening flagged this clip.",
            actionTaken: "Review before posting.",
          }
        : null;

      // Build platform rows from platform_metrics or platform_posts
      const platforms: DetailData["platforms"] = [];
      const pm = clipData.platform_metrics || {};
      const pp = clipData.platform_posts || {};

      for (const [platform, metrics] of Object.entries(pm)) {
        const post = pp[platform] || {};
        const views = (metrics as any)?.views ?? 0;
        const watchTime = clipData.watch_time_seconds
          ? formatDuration((clipData.watch_time_seconds * (views / (clipData.views || 1))))
          : "—";
        const earnings = clipData.earnings_cents
          ? formatCurrency(Math.round((clipData.earnings_cents * (views / (clipData.views || 1)))))
          : "—";

        platforms.push({
          platform: platform as Platform,
          handle: post.handle || post.post_id || platform,
          views: formatNumber(views),
          watchTime,
          earnings,
        });
      }

      // Also include posted platforms without metrics yet
      for (const [platform, post] of Object.entries(pp)) {
        if (!pm[platform]) {
          platforms.push({
            platform: platform as Platform,
            handle: (post as any)?.handle || (post as any)?.post_id || platform,
            views: "—",
            watchTime: "—",
            earnings: "—",
          });
        }
      }

      const hasMetrics = !!clipData.metrics_synced_at && (clipData.views !== undefined || clipData.views !== null);

      return {
        id: clipData.id,
        sourceName: clipData.title || "Untitled clip",
        sourceUrl: clipData.video_url || `Clip · ${clipData.id.slice(0, 8)}`,
        caption: clipData.caption || "No caption provided.",
        platforms,
        safety,
        videoUrl: clipData.video_url,
        hasMetrics,
        views: clipData.views,
        likes: clipData.likes,
        shares: clipData.shares,
        comments: clipData.comments,
        watchTimeSeconds: clipData.watch_time_seconds,
        retentionPct: clipData.retention_pct,
        earningsCents: clipData.earnings_cents,
        metricsSyncedAt: clipData.metrics_synced_at,
      };
    }
    return {
      id: params.id ?? "clip-1",
      sourceName: "Untitled clip",
      sourceUrl: `Clip · ${(params.id ?? "").slice(0, 8)}`,
      caption: "No caption provided.",
      platforms: [],
      safety: null,
      videoUrl: undefined,
      hasMetrics: false,
    };
  }, [clipData, params.id, formatNumber, formatDuration, formatCurrency]);

  const handleAction = useCallback(
    async (action: string) => {
      if (action === "delete") {
        try {
          await clipsApi.delete(clip.id);
          router.back();
        } catch (err: any) {
          console.warn("[clip-detail] delete failed:", err.message);
        }
      } else if (action === "post") {
        // Posting requires social API keys — BYOK now, premium auto-posting coming soon
        Alert.alert(
          "Auto-Posting",
          "You can bring your own API keys for auto-posting to your social platforms. Integrated auto-posting with managed API keys will be a premium feature coming soon.",
          [
            { text: "OK", style: "default" },
            {
              text: "Download Clip",
              onPress: () => handleAction("download"),
            },
          ]
        );
      } else if (action === "download") {
        try {
          triggerHaptic("blockTriggered");
          const result = await clipsApi.downloadUrl(clip.id);
          if (result?.url) {
            const supported = await Linking.canOpenURL(result.url);
            if (supported) {
              await Linking.openURL(result.url);
            } else {
              Alert.alert("Download Ready", result.url);
            }
          } else {
            Alert.alert("Download Unavailable", "No download URL found for this clip.");
          }
        } catch (err: any) {
          console.warn("[clip-detail] download failed:", err.message);
          Alert.alert("Download Failed", err?.detail || "Could not generate download link.");
        }
      } else if (action === "edit") {
        // Navigate to edit screen
        router.push(`/(app)/clip/${clip.id}/edit`);
      } else if (action === "remix") {
        // AI-powered remix
        Alert.alert(
          "AI Remix",
          "Generate 2-3 new versions with optimized hooks, fresh captions, and vertical format?",
          [
            { text: "Cancel", style: "cancel" },
            {
              text: "Remix",
              onPress: async () => {
                try {
                  triggerHaptic("blockTriggered");
                  const result = await clipsApi.remix(clip.id, {
                    num_variants: 3,
                    target_duration: 20,
                    include_music: true,
                    include_captions: true,
                    output_format: "9:16",
                  });
                  if (result.success) {
                    Alert.alert(
                      "Remix Queued",
                      "We're cooking up 3 AI-powered variants. Check your library in a few minutes."
                    );
                  } else {
                    Alert.alert("Remix Failed", result.error || "Could not queue remix.");
                  }
                } catch (err: any) {
                  console.warn("[clip-detail] remix failed:", err.message);
                  Alert.alert("Remix Failed", err?.detail || "Something went wrong.");
                }
              }
            }
          ]
        );
      } else if (action.startsWith("swarm-quick-")) {
        // Quick-run with defaults (from action sheet play button)
        const swarmType = action.replace("swarm-quick-", "");
        handleSwarmQuickRun(swarmType as SwarmPoolType);
      } else if (action.startsWith("swarm-")) {
        // Legacy handlers - convert to new config flow
        const swarmType = action.replace("swarm-", "");
        setConfiguringSwarm(swarmType);
      }
    },
    [clip.id, router]
  );

  const handleSwarmQuickRun = useCallback(
    async (poolType: SwarmPoolType) => {
      try {
        triggerHaptic("blockTriggered");
        let result;
        switch (poolType) {
          case "hook":
            result = await runHookSwarm(clip.id, "tiktok");
            break;
          case "remix":
            result = await runRemixSwarm(clip.id);
            break;
          case "thumbnail":
            result = await runThumbnailSwarm(clip.id);
            break;
          case "safety":
            result = await runSafetySwarm(clip.id);
            break;
          case "segment_analyze":
            result = await runSegmentAnalyzeSwarm(clip.id);
            break;
          case "edit":
            result = await runEditSwarm(clip.id);
            break;
          case "music_match":
            result = await runMusicMatchSwarm(clip.id);
            break;
          case "ab_test":
            result = await runABTestSwarm(clip.id, clip.id);
            break;
          case "hooks_analysis":
            result = await runHooksAnalysisSwarm(clip.id, "tiktok");
            break;
          case "post":
            Alert.alert("Swarm Post", "Multi-account posting swarm will be available once social accounts are connected.");
            return;
          default:
            return;
        }
        Alert.alert(
          `${poolMeta[poolType]?.label || poolType} Swarm Queued`,
          `${result.agents} agents dispatched. Job ID: ${result.job_id.slice(0, 8)}...`
        );
      } catch (err: any) {
        console.warn(`[clip-detail] swarm ${poolType} failed:`, err.message);
        Alert.alert("Swarm Failed", err?.detail || `Could not dispatch ${poolType} swarm.`);
      }
    },
    [clip.id, poolMeta, runHookSwarm, runRemixSwarm, runThumbnailSwarm, runSafetySwarm, runSegmentAnalyzeSwarm, runEditSwarm, runMusicMatchSwarm, runABTestSwarm, runHooksAnalysisSwarm]
  );

  const handleSwarmConfigure = useCallback((actionId: string) => {
    setSwarmSheetOpen(false);
    setConfiguringSwarm(actionId);
  }, []);

  const handleSwarmExecute = useCallback(
    async (config: SwarmExecutionConfig) => {
      try {
        triggerHaptic("blockTriggered");
        const poolType = config.poolType;
        let result;

        // Build execution params based on config
        const params: Record<string, any> = {
          agent_count: config.agentCount,
          strategies: config.strategyFilter,
          ...(config.customOptions || {}),
        };

        switch (poolType) {
          case "hook":
            result = await runHookSwarm(clip.id, params.platform || "tiktok", params);
            break;
          case "remix":
            result = await runRemixSwarm(clip.id, params);
            break;
          case "thumbnail":
            result = await runThumbnailSwarm(clip.id, params);
            break;
          case "safety":
            result = await runSafetySwarm(clip.id, params);
            break;
          case "segment_analyze":
            result = await runSegmentAnalyzeSwarm(clip.id, params);
            break;
          case "edit":
            result = await runEditSwarm(clip.id, params);
            break;
          case "music_match":
            result = await runMusicMatchSwarm(clip.id, params);
            break;
          case "ab_test":
            result = await runABTestSwarm(clip.id, clip.id, params);
            break;
          case "hooks_analysis":
            result = await runHooksAnalysisSwarm(clip.id, params.platform || "tiktok", params);
            break;
          case "post":
            Alert.alert("Swarm Post", "Multi-account posting swarm will be available once social accounts are connected.");
            return;
          default:
            return;
        }

        setConfiguringSwarm(null);
        Alert.alert(
          `${poolMeta[poolType]?.label || poolType} Swarm Dispatched`,
          `${result.agents} ${config.agentCount > 1 ? 'agents' : 'agent'} dispatched with ${config.strategyFilter.length} strateg${config.strategyFilter.length === 1 ? 'y' : 'ies'}. Job ID: ${result.job_id.slice(0, 8)}...`
        );
      } catch (err: any) {
        console.warn(`[clip-detail] configured swarm failed:`, err.message);
        Alert.alert("Swarm Failed", err?.detail || "Could not dispatch swarm with custom configuration.");
      }
    },
    [clip.id, poolMeta, runHookSwarm, runRemixSwarm, runThumbnailSwarm, runSafetySwarm, runSegmentAnalyzeSwarm, runEditSwarm, runMusicMatchSwarm, runABTestSwarm, runHooksAnalysisSwarm]
  );

  return (
    <>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.root}>
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          <View style={styles.thumb}>
            {clip.videoUrl ? (
              <Video
                source={{ uri: clip.videoUrl }}
                style={styles.videoPlayer}
                resizeMode={ResizeMode.CONTAIN}
                useNativeControls
                isLooping
                onPlaybackStatusUpdate={(status) => {
                  if (status.isLoaded) {
                    setVideoStatus({ isPlaying: status.isPlaying });
                  }
                }}
                accessibilityLabel="Clip preview video"
              />
            ) : (
              <>
                <Film
                  size={tokens.icon.size.xl * 1.5}
                  color={tokens.color.text.tertiary}
                  strokeWidth={tokens.icon.stroke.thin}
                />
                <Text style={styles.noVideoText}>No preview available</Text>
              </>
            )}
            <SafeAreaView edges={["top"]} style={styles.thumbOverlay} pointerEvents="box-none">
              <Pressable
                onPress={() => router.back()}
                hitSlop={12}
                style={styles.backBtn}
                accessibilityLabel="Back"
              >
                <ChevronLeft
                  size={tokens.icon.size.lg}
                  color={tokens.color.text.primary}
                  strokeWidth={tokens.icon.stroke.default}
                />
              </Pressable>
            </SafeAreaView>
          </View>

          <View style={styles.body}>
            <View style={styles.sourceBlock}>
              <Text style={styles.overline}>SOURCE</Text>
              <Text style={styles.sourceName}>{clip.sourceName}</Text>
              <Text style={styles.sourceUrl}>{clip.sourceUrl}</Text>
            </View>

            <View style={styles.captionBlock}>
              <Text style={styles.overline}>CAPTION</Text>
              <Text style={styles.caption}>{clip.caption}</Text>
            </View>

            {clip.safety ? (
              <View style={styles.safetyBlock}>
                <SafetyFlag
                  variant={clip.safety.variant}
                  categories={clip.safety.categories}
                  actionTaken={clip.safety.actionTaken}
                  size="banner"
                />
                <Text style={styles.safetyBody}>{clip.safety.reasoning}</Text>
              </View>
            ) : null}

            {clip.platforms.length > 0 || clip.hasMetrics ? (
              <View style={styles.platformBlock}>
                <Text style={styles.overline}>PER PLATFORM</Text>
                <View style={styles.platformHeader}>
                  <Text style={[styles.colLabel, styles.colPlatform]}>Platform</Text>
                  <Text style={[styles.colLabel, styles.colMetric]}>Views</Text>
                  <Text style={[styles.colLabel, styles.colMetric]}>Watch</Text>
                  <Text style={[styles.colLabel, styles.colMetric]}>Earnings</Text>
                </View>
                {clip.platforms.map((p) => (
                  <View key={p.platform} style={styles.platformRow}>
                    <View style={styles.colPlatform}>
                      <AccountBadge platform={p.platform} handle={p.handle} variant="pill" />
                    </View>
                    <Text style={[styles.colValue, styles.colMetric]}>{p.views}</Text>
                    <Text style={[styles.colValue, styles.colMetric]}>{p.watchTime}</Text>
                    <Text style={[styles.colValue, styles.colMetric]}>{p.earnings}</Text>
                  </View>
                ))}
              </View>
            ) : (
              <View style={styles.platformBlockEmpty}>
                <Text style={styles.overline}>PER PLATFORM</Text>
                <Text style={styles.emptyStateText}>
                  Post this clip to see platform metrics here. Connect your social accounts and tap "Post" to get started.
                </Text>
              </View>
            )}

            {clip.hasMetrics ? (
              <View style={styles.metricsBlock}>
                <MetricChip label="Total views" value={formatNumber(clip.views)} variant="positive" style={styles.flex1} />
                <MetricChip label="Retention" value={clip.retentionPct ? `${Math.round(clip.retentionPct * 100)}%` : "—"} variant="positive" style={styles.flex1} />
                <MetricChip label="Earnings" value={formatCurrency(clip.earningsCents)} style={styles.flex1} />
              </View>
            ) : null}

            <View style={styles.attribution}>
              <Text style={styles.overline}>ATTRIBUTION</Text>
              <Text style={styles.attributionText}>
                Source clipped under fair-use review. Original creator credited in caption per pipeline policy.
              </Text>
            </View>

            {/* BYOK / Premium Banner */}
            <View style={styles.byokBanner}>
              <Text style={styles.byokTitle}>🔑 Bring Your Own API Keys</Text>
              <Text style={styles.byokBody}>
                You can bring your own API keys for auto posting capabilities. Connect your social media accounts using your own developer credentials for full control.
              </Text>
              <View style={styles.byokDivider} />
              <Text style={styles.byokPremiumLabel}>PREMIUM COMING SOON</Text>
              <Text style={styles.byokBody}>
                Integrated API keys for auto posting will be a premium feature — managed keys, zero setup, one-tap posting across all platforms.
              </Text>
            </View>
          </View>
        </ScrollView>

        <SafeAreaView edges={["bottom"]} style={styles.footer}>
          <View style={styles.footerRow}>
            <ActionButton
              label="Post"
              variant="primary"
              size="md"
              iconLeft={Repeat}
              onPress={() => handleAction("post")}
            />
            <ActionButton
              label="Swarm"
              variant="primary"
              size="md"
              iconLeft={Bot}
              onPress={() => setSwarmSheetOpen(true)}
              disabled={swarmRunning}
            />
            <ActionButton
              label="Download"
              variant="secondary"
              size="md"
              iconLeft={Download}
              onPress={() => handleAction("download")}
            />
            <ActionButton
              label="Remix"
              variant="secondary"
              size="md"
              iconLeft={Sparkles}
              onPress={() => handleAction("remix")}
            />
            <ActionButton
              label="Edit"
              variant="ghost"
              size="md"
              iconLeft={Pencil}
              onPress={() => handleAction("edit")}
            />
            <ActionButton
              label="Kill"
              variant="danger"
              size="md"
              iconLeft={Trash2}
              onPress={() => handleAction("delete")}
            />
          </View>
        </SafeAreaView>
      </View>

      <SwarmActionSheet
        visible={swarmSheetOpen}
        onClose={() => setSwarmSheetOpen(false)}
        onConfigure={handleSwarmConfigure}
        onQuickRun={(id) => handleAction(`swarm-quick-${id}`)}
        disabled={swarmRunning}
      />

      {configuringSwarm && poolMeta[configuringSwarm] && (
        <SwarmConfigModal
          visible={!!configuringSwarm}
          onClose={() => setConfiguringSwarm(null)}
          onExecute={handleSwarmExecute}
          poolType={configuringSwarm as SwarmPoolType}
          poolLabel={poolMeta[configuringSwarm].label}
          poolColor={poolMeta[configuringSwarm].color}
          poolDescription={poolMeta[configuringSwarm].desc}
          category={poolMeta[configuringSwarm].category}
          userAllocation={getPoolAllocation(configuringSwarm)}
          tierLimit={getTierLimit()}
          availableAgents={getPoolAllocation(configuringSwarm)}
          availableStrategies={[]}
          strategyLabels={{}}
          strategyDescriptions={{}}
          costPerAgent={0}
          isExecuting={swarmRunning}
        />
      )}
    </>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg.base },
  scroll: { paddingBottom: tokens.spacing.xxxl + tokens.layout.tabBarHeight },
  thumb: {
    aspectRatio: 9 / 16,
    maxHeight: 480,
    width: "100%",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: tokens.color.bg.surface,
    position: "relative",
  },
  videoPlayer: {
    width: "100%",
    height: "100%",
    backgroundColor: tokens.color.bg.base,
  },
  noVideoText: {
    marginTop: tokens.spacing.sm,
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.tertiary,
  },
  thumbOverlay: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
  },
  backBtn: {
    margin: tokens.spacing.md,
    width: tokens.layout.minTouchTarget,
    height: tokens.layout.minTouchTarget,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: tokens.radius.pill,
    backgroundColor: tokens.color.bg.overlay,
  },
  body: {
    padding: tokens.layout.screenPadding,
    gap: tokens.layout.sectionGap,
  },
  overline: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    lineHeight: tokens.type.scale.overline.lineHeight,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.text.tertiary,
    marginBottom: tokens.spacing.xs,
  },
  sourceBlock: { gap: 2 },
  sourceName: {
    fontFamily: tokens.type.scale.h2.family,
    fontSize: tokens.type.scale.h2.size,
    lineHeight: tokens.type.scale.h2.lineHeight,
    letterSpacing: tokens.type.scale.h2.letterSpacing,
    color: tokens.color.text.primary,
  },
  sourceUrl: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  captionBlock: {},
  caption: {
    fontFamily: tokens.type.scale.body.family,
    fontSize: tokens.type.scale.body.size,
    lineHeight: tokens.type.scale.body.lineHeight,
    color: tokens.color.text.primary,
  },
  safetyBlock: {
    gap: tokens.spacing.sm,
  },
  safetyBody: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    lineHeight: tokens.type.scale.bodySmall.lineHeight,
    color: tokens.color.text.secondary,
  },
  platformBlock: {
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    padding: tokens.spacing.md,
  },
  platformBlockEmpty: {
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    padding: tokens.spacing.md,
    gap: tokens.spacing.sm,
  },
  emptyStateText: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    lineHeight: tokens.type.scale.bodySmall.lineHeight,
    color: tokens.color.text.secondary,
  },
  platformHeader: {
    flexDirection: "row",
    paddingBottom: tokens.spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: tokens.color.border.subtle,
  },
  platformRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: tokens.spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: tokens.color.border.subtle,
  },
  colLabel: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  colValue: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    color: tokens.color.text.primary,
  },
  colPlatform: { flex: 1.4 },
  colMetric: { flex: 1, textAlign: "right" },
  metricsBlock: {
    flexDirection: "row",
    gap: tokens.spacing.sm,
  },
  flex1: { flex: 1, minWidth: 0 },
  attribution: {},
  attributionText: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    lineHeight: tokens.type.scale.bodySmall.lineHeight,
    color: tokens.color.text.secondary,
  },
  footer: {
    borderTopWidth: 1,
    borderTopColor: tokens.color.border.subtle,
    backgroundColor: tokens.color.bg.raised,
  },
  footerRow: {
    flexDirection: "row",
    gap: tokens.spacing.sm,
    padding: tokens.layout.screenPadding,
  },
  byokBanner: {
    backgroundColor: tokens.color.brand.indigo[900],
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.color.brand.indigo[700],
    padding: tokens.spacing.md,
    gap: tokens.spacing.sm,
  },
  byokTitle: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.brand.indigo[200],
    fontWeight: "700",
  },
  byokBody: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    lineHeight: tokens.type.scale.bodySmall.lineHeight,
    color: tokens.color.brand.indigo[100],
  },
  byokDivider: {
    height: 1,
    backgroundColor: tokens.color.brand.indigo[700],
    marginVertical: tokens.spacing.xs,
  },
  byokPremiumLabel: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.brand.indigo[300],
    fontWeight: "700",
  },
});
