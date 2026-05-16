import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  FlatList,
  ListRenderItem,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useRouter } from "expo-router";
import { CheckCircle2, ChevronRight, Eye, Plus, UserRound, VideoOff } from "lucide-react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { tokens } from "@/constants/tokens";
import { useAuthStore } from "@/lib/store";
import { ActionButton } from "@/components/ActionButton";
import { ClipCard, ClipCardData } from "@/components/ClipCard";
import { MetricChip } from "@/components/MetricChip";

const PLACEHOLDER_CLIPS: ClipCardData[] = [
  {
    id: "clip-1",
    sourceName: "Design Details · Ep 412",
    caption:
      "The hidden cost of skeuomorphism in modern productivity apps and why nobody talks about it.",
    platforms: [
      { platform: "tiktok", handle: "@studio" },
      { platform: "instagram", handle: "@studio" },
      { platform: "youtube", handle: "@studio" },
    ],
    metrics: { views: "24.1K", retention: "+18%", earnings: "$3.40", retentionVariant: "positive" },
    state: "posted",
    safety: null,
  },
  {
    id: "clip-2",
    sourceName: "F1 Race Recap · Imola",
    caption:
      "Lap 38 — the undercut that decided the podium. Three-camera angle reconstruction inside.",
    platforms: [
      { platform: "tiktok" },
      { platform: "instagram" },
    ],
    state: "queued",
    queuedFor: "8m",
    safety: null,
  },
  {
    id: "clip-3",
    sourceName: "Health & Wellness Daily",
    caption:
      "New cohort study on intermittent fasting metabolic markers — what the headlines miss.",
    platforms: [{ platform: "tiktok" }, { platform: "youtube" }],
    metrics: { views: "—", retention: "—", earnings: "—" },
    state: "held-safety-warn",
    safety: { variant: "warn", categories: ["Health · disclosure recommended"] },
  },
  {
    id: "clip-4",
    sourceName: "Live Stream Highlight",
    caption:
      "Crowd reaction sync from a copyrighted broadcast — held pending rights review.",
    platforms: [{ platform: "tiktok" }, { platform: "instagram" }, { platform: "youtube" }],
    state: "held-safety-block",
    safety: { variant: "block", categories: ["Copyrighted material risk"] },
  },
];

export default function HomeScreen() {
  const router = useRouter();
  const clips = useAuthStore((s) => s.clips);
  const clipsLoading = useAuthStore((s) => s.clipsLoading);
  const fetchClips = useAuthStore((s) => s.fetchClips);
  const approveClip = useAuthStore((s) => s.approveClip);
  const rejectClip = useAuthStore((s) => s.rejectClip);
  const deleteClip = useAuthStore((s) => s.deleteClip);
  const pipelines = useAuthStore((s) => s.pipelines);
  const [refreshing, setRefreshing] = useState<boolean>(false);

  const activePipelineCount = useMemo(
    () => pipelines.filter((p) => p.status === "running").length,
    [pipelines]
  );

  const pendingCount = useMemo(
    () => clips.filter((c) => c.state === "queued" || c.state === "held-safety-warn").length,
    [clips]
  );

  const queuedCount = useMemo(
    () => clips.filter((c) => c.state === "queued").length,
    [clips]
  );

  const postedToday = useMemo(
    () => clips.filter((c) => c.state === "posted").length,
    [clips]
  );

  useEffect(() => {
    fetchClips();
  }, [fetchClips]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchClips().finally(() => setRefreshing(false));
  }, [fetchClips]);

  const renderItem: ListRenderItem<ClipCardData> = useCallback(
    ({ item }) => (
      <ClipCard
        clip={item}
        variant="feed"
        onPress={() => router.push(`/clip/${item.id}`)}
        onAction={(actionId) => {
          if (actionId === "approve") {
            approveClip(item.id);
          } else if (actionId === "reject") {
            rejectClip(item.id);
          } else if (actionId === "delete") {
            deleteClip(item.id);
          } else {
            console.log("[home] clip action", { id: item.id, actionId });
          }
        }}
      />
    ),
    [router, approveClip, rejectClip, deleteClip]
  );

  return (
    <SafeAreaView edges={["top"]} style={styles.safe}>
      <View style={styles.header}>
        <View>
          <Text style={styles.headerOverline}>TODAY</Text>
          <Text style={styles.headerTitle}>Live feed</Text>
        </View>
        <Pressable
          onPress={() => router.push("/(app)/profile")}
          hitSlop={12}
          style={styles.profileBtn}
          accessibilityLabel="Open profile"
        >
          <UserRound
            size={tokens.icon.size.md}
            color={tokens.color.text.secondary}
            strokeWidth={tokens.icon.stroke.default}
          />
        </Pressable>
      </View>

      <FlatList
        data={clips}
        keyExtractor={(c) => c.id}
        renderItem={renderItem}
        contentContainerStyle={styles.listContent}
        ItemSeparatorComponent={Separator}
        ListHeaderComponent={
          <View>
            <ApprovalBanner
              pendingCount={pendingCount}
              onPress={() => router.push("/(app)/approval")}
            />
            <StatusStrip
              activePipelineCount={activePipelineCount}
              queuedCount={queuedCount}
              postedToday={postedToday}
              onNewPipeline={() => {
                router.push("/(app)/pipelines");
              }}
            />
          </View>
        }
        ListEmptyComponent={<EmptyFeed onOpenPipelines={() => router.push("/(app)/pipelines")} />}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={tokens.color.text.tertiary}
            colors={[tokens.color.brand.indigo[400]]}
            progressBackgroundColor={tokens.color.bg.raised}
          />
        }
        showsVerticalScrollIndicator={false}
      />
    </SafeAreaView>
  );
}

function Separator() {
  return <View style={{ height: tokens.layout.feedCardGap }} />;
}

function ApprovalBanner({ pendingCount, onPress }: { pendingCount: number; onPress: () => void }) {
  if (pendingCount <= 0) return null;
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.approvalBanner,
        pressed ? { backgroundColor: tokens.color.brand.indigo[800] } : null,
      ]}
      accessibilityRole="button"
      accessibilityLabel="Open approval queue"
    >
      <View style={styles.approvalIconWrap}>
        <CheckCircle2
          size={tokens.icon.size.md}
          color={tokens.color.brand.indigo[200]}
          strokeWidth={tokens.icon.stroke.default}
        />
      </View>
      <View style={styles.approvalBody}>
        <Text style={styles.approvalTitle}>{pendingCount} clips awaiting approval</Text>
        <Text style={styles.approvalCaption}>Tap to review the queue.</Text>
      </View>
      <ChevronRight
        size={tokens.icon.size.sm}
        color={tokens.color.brand.indigo[200]}
        strokeWidth={tokens.icon.stroke.default}
      />
    </Pressable>
  );
}

interface StatusStripProps {
  activePipelineCount: number;
  queuedCount: number;
  postedToday: number;
  onNewPipeline: () => void;
}

function StatusStrip({ activePipelineCount, queuedCount, postedToday, onNewPipeline }: StatusStripProps) {
  return (
    <View style={styles.stripWrap}>
      <View style={styles.strip}>
        <MetricChip label="Queued" value={String(queuedCount)} delta="clips" style={styles.stripChip} icon={Eye} />
        <MetricChip
          label="Posted today"
          value={String(postedToday)}
          delta="+0"
          variant="positive"
          style={styles.stripChip}
        />
        <MetricChip
          label="Earnings · 7d"
          value="$48.20"
          delta="+12%"
          variant="positive"
          style={styles.stripChip}
        />
      </View>

      <View style={styles.pipelineRow}>
        <Text style={styles.pipelineRowText}>
          {activePipelineCount} active pipeline{activePipelineCount === 1 ? "" : "s"}
        </Text>
        <ActionButton
          label="New"
          variant="ghost"
          size="sm"
          iconLeft={Plus}
          onPress={onNewPipeline}
        />
      </View>
    </View>
  );
}

interface EmptyFeedProps {
  onOpenPipelines: () => void;
}

function EmptyFeed({ onOpenPipelines }: EmptyFeedProps) {
  return (
    <View style={styles.empty}>
      <View style={styles.emptyIconWrap}>
        <VideoOff
          size={tokens.icon.size.xl * 2.5}
          color={tokens.color.text.tertiary}
          strokeWidth={tokens.icon.stroke.thin}
        />
      </View>
      <Text style={styles.emptyTitle}>No clips yet.</Text>
      <Text style={styles.emptyBody}>
        Once your pipeline starts producing, clips show up here.
      </Text>
      <View style={{ height: tokens.spacing.md }} />
      <ActionButton label="Open pipelines" variant="primary" size="lg" onPress={onOpenPipelines} />
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: tokens.color.bg.base },
  header: {
    height: tokens.layout.headerHeight,
    paddingHorizontal: tokens.layout.screenPadding,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  headerOverline: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    lineHeight: tokens.type.scale.overline.lineHeight,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  headerTitle: {
    fontFamily: tokens.type.scale.h2.family,
    fontSize: tokens.type.scale.h2.size,
    lineHeight: tokens.type.scale.h2.lineHeight,
    letterSpacing: tokens.type.scale.h2.letterSpacing,
    color: tokens.color.text.primary,
  },
  profileBtn: {
    width: tokens.layout.minTouchTarget,
    height: tokens.layout.minTouchTarget,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: tokens.radius.pill,
    backgroundColor: tokens.color.bg.raised,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
  },
  listContent: {
    paddingHorizontal: tokens.layout.screenPadding,
    paddingBottom: tokens.spacing.xxl,
    flexGrow: 1,
  },
  approvalBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    backgroundColor: tokens.color.brand.indigo[900],
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.color.brand.indigo[700],
    marginBottom: tokens.spacing.md,
  },
  approvalIconWrap: {
    width: 36,
    height: 36,
    borderRadius: tokens.radius.pill,
    backgroundColor: tokens.color.brand.indigo[800],
    alignItems: "center",
    justifyContent: "center",
  },
  approvalBody: { flex: 1, gap: 2 },
  approvalTitle: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.primary,
  },
  approvalCaption: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.brand.indigo[200],
  },
  stripWrap: {
    marginBottom: tokens.layout.sectionGap,
    gap: tokens.spacing.sm,
  },
  strip: {
    flexDirection: "row",
    gap: tokens.spacing.sm,
    backgroundColor: tokens.color.bg.raised,
    padding: tokens.spacing.md,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    ...tokens.elevation[1],
  },
  stripChip: {
    flex: 1,
    minWidth: 0,
  },
  pipelineRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: tokens.spacing.xs,
  },
  pipelineRowText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  empty: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: tokens.spacing.xxxl,
    paddingHorizontal: tokens.spacing.lg,
    gap: tokens.spacing.sm,
  },
  emptyIconWrap: {
    marginBottom: tokens.spacing.md,
    opacity: 0.6,
  },
  emptyTitle: {
    fontFamily: tokens.type.scale.h1.family,
    fontSize: tokens.type.scale.h1.size,
    lineHeight: tokens.type.scale.h1.lineHeight,
    letterSpacing: tokens.type.scale.h1.letterSpacing,
    color: tokens.color.text.primary,
    textAlign: "center",
  },
  emptyBody: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    lineHeight: tokens.type.scale.bodySmall.lineHeight,
    color: tokens.color.text.secondary,
    textAlign: "center",
    maxWidth: 280,
  },
});
