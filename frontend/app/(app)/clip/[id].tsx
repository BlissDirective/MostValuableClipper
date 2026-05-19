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

import { tokens } from "@/constants/tokens";
import { ActionButton } from "@/components/ActionButton";
import { AccountBadge, Platform } from "@/components/AccountBadge";
import { MetricChip } from "@/components/MetricChip";
import { SafetyFlag, SafetyVariant } from "@/components/SafetyFlag";
import { clipsApi, Clip } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { useSwarmExecution } from "@/lib/api-hooks";
import { triggerHaptic } from "@/utils/haptics";

interface DetailData {
  id: string;
  sourceName: string;
  sourceUrl: string;
  caption: string;
  platforms: { platform: Platform; handle: string; views: string; watchTime: string; earnings: string }[];
  safety?: { variant: SafetyVariant; categories: string[]; reasoning: string; actionTaken: string } | null;
}

const PLACEHOLDER: DetailData = {
  id: "clip-1",
  sourceName: "Design Details · Ep 412",
  sourceUrl: "designdetails.fm/412 · 14:22–14:58",
  caption:
    "The hidden cost of skeuomorphism in modern productivity apps and why nobody talks about it. Three examples, one fix.",
  platforms: [
    { platform: "tiktok", handle: "@studio", views: "12.4K", watchTime: "0:21 avg", earnings: "$1.80" },
    { platform: "instagram", handle: "@studio", views: "8.2K", watchTime: "0:18 avg", earnings: "$0.90" },
    { platform: "youtube", handle: "@studio", views: "3.5K", watchTime: "0:34 avg", earnings: "$0.70" },
  ],
  safety: null,
};

export default function ClipDetailScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ id: string }>();
  const [clipData, setClipData] = useState<Clip | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const doSignOut = useAuthStore((s) => s.doSignOut);
  const { isRunning: swarmRunning, runHookSwarm, runRemixSwarm, runPostSwarm } = useSwarmExecution();

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
      return {
        id: clipData.id,
        sourceName: clipData.title || "Untitled clip",
        sourceUrl: clipData.video_url || `Clip · ${clipData.id.slice(0, 8)}`,
        caption: clipData.caption || "No caption provided.",
        platforms: [],
        safety,
      };
    }
    return { ...PLACEHOLDER, id: params.id ?? PLACEHOLDER.id };
  }, [clipData, params.id]);

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
          triggerHaptic("heavy");
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
                  triggerHaptic("heavy");
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
      } else if (action === "swarm-hooks") {
        try {
          triggerHaptic("heavy");
          const result = await runHookSwarm(clip.id, "tiktok");
          Alert.alert(
            "Swarm Hooks Queued",
            `${result.agents} hook agents dispatched. Job ID: ${result.job_id.slice(0, 8)}...`
          );
        } catch (err: any) {
          console.warn("[clip-detail] swarm hooks failed:", err.message);
          Alert.alert("Swarm Failed", err?.detail || "Could not dispatch hook swarm.");
        }
      } else if (action === "swarm-remix") {
        try {
          triggerHaptic("heavy");
          const result = await runRemixSwarm(clip.id);
          Alert.alert(
            "Swarm Remix Queued",
            `${result.agents} remix agents dispatched. Job ID: ${result.job_id.slice(0, 8)}...`
          );
        } catch (err: any) {
          console.warn("[clip-detail] swarm remix failed:", err.message);
          Alert.alert("Swarm Failed", err?.detail || "Could not dispatch remix swarm.");
        }
      } else if (action === "swarm-post") {
        // Swarm post requires connected accounts
        Alert.alert(
          "Swarm Post",
          "Multi-account posting swarm will be available once social accounts are connected."
        );
      } else {
        // Post-MVP: repost actions require AI generation pipeline
        Alert.alert("Coming soon", "Reposting will be available in a future update.");
      }
    },
    [clip.id, router]
  );

  return (
    <>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.root}>
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          <View style={styles.thumb}>
            <Film
              size={tokens.icon.size.xl * 1.5}
              color={tokens.color.text.tertiary}
              strokeWidth={tokens.icon.stroke.thin}
            />
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

            <View style={styles.metricsBlock}>
              <MetricChip label="Total views" value="24.1K" variant="positive" delta="+18%" style={styles.flex1} />
              <MetricChip label="Retention" value="62%" variant="positive" style={styles.flex1} />
              <MetricChip label="Earnings" value="$3.40" style={styles.flex1} />
            </View>

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
              onPress={() => handleAction("swarm-hooks")}
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
