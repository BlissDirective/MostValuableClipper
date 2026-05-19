import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Pressable, StyleSheet, Text, View } from "react-native";
import { Stack, useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { Check, ChevronLeft, Edit3, Sparkles, X, Bot, Shield, Scissors, Image, Layers } from "lucide-react-native";

import { tokens } from "@/constants/tokens";
import { ActionButton } from "@/components/ActionButton";
import { SafetyFlag, SafetyVariant } from "@/components/SafetyFlag";
import { SwipeDeckCard, SwipeDeckClip } from "@/components/SwipeDeckCard";
import { triggerHaptic } from "@/utils/haptics";
import { clipsApi, Clip } from "@/lib/api";

interface QueueItem {
  clip: SwipeDeckClip;
  safetyFlags?: { variant: SafetyVariant; categories?: string[]; actionTaken?: string }[];
}

function mapClipToQueueItem(clip: Clip): QueueItem {
  return {
    clip: {
      id: clip.id,
      sourceName: clip.title || "Untitled clip",
      caption: clip.caption || "No caption.",
      targets: [],
    },
    safetyFlags: clip.safety_flags?.length
      ? [{
          variant: "warn" as SafetyVariant,
          categories: clip.safety_flags,
          actionTaken: "Review before posting.",
        }]
      : undefined,
  };
}

export default function ApprovalScreen() {
  const router = useRouter();
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [index, setIndex] = useState<number>(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    clipsApi.list({ status: "ready_for_review", limit: 20 })
      .then((res) => {
        if (cancelled) return;
        const items = (res.data.items || []).map(mapClipToQueueItem);
        setQueue(items);
      })
      .catch((err) => {
        console.warn("[approval] fetch failed:", err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const total = queue.length;
  const current = queue[index];
  const next = queue[index + 1];

  const advance = useCallback(
    async (verdict: "approve" | "reject") => {
      if (!current) return;
      triggerHaptic(verdict === "approve" ? "approve" : "reject");
      try {
        if (verdict === "approve") {
          await clipsApi.approve(current.clip.id);
        } else {
          await clipsApi.reject(current.clip.id);
        }
      } catch (err: any) {
        console.warn(`[approval] ${verdict} failed:`, err.message);
      }
      setIndex((i) => Math.min(i + 1, total));
    },
    [current, total]
  );

  const onEdit = useCallback(() => {
    if (!current) return;
    router.push(`/(app)/clip/${current.clip.id}/edit`);
  }, [current, router]);

  const handleRemix = useCallback(async () => {
    if (!current) return;
    triggerHaptic("light");
    try {
      const result = await clipsApi.remix(current.clip.id, {
        num_variants: 3,
        target_duration: 20,
        include_music: true,
        include_captions: true,
        output_format: "9:16",
      });
      
      if (result.success) {
        Alert.alert(
          "Remix Queued",
          `We're generating ${result.total_variants || 3} AI-powered remixes. Check your clip library in a few minutes.`,
          [{ text: "OK", style: "default" }]
        );
      } else {
        Alert.alert("Remix Failed", result.error || "Could not queue remix.");
      }
    } catch (err: any) {
      console.warn("[approval] remix failed:", err.message);
      Alert.alert("Remix Failed", err?.detail || "Something went wrong.");
    }
  }, [current]);

  const topBanner = useMemo(() => current?.safetyFlags?.[0], [current]);
  const done = index >= total || (!loading && total === 0);

  return (
    <View style={styles.root}>
      <Stack.Screen options={{ headerShown: false }} />
      <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
        <View style={styles.header}>
          <Pressable
            onPress={() => router.back()}
            hitSlop={12}
            style={styles.backBtn}
            accessibilityLabel="Close approval queue"
          >
            <ChevronLeft
              size={tokens.icon.size.md}
              color={tokens.color.text.primary}
              strokeWidth={tokens.icon.stroke.default}
            />
          </Pressable>
          <Text style={styles.title}>Approval Queue</Text>
          <View style={styles.counter}>
            <Text style={styles.counterText}>
              {Math.min(index + 1, total)} of {total}
            </Text>
          </View>
        </View>

        {topBanner ? (
          <View style={styles.bannerWrap}>
            <SafetyFlag
              variant={topBanner.variant}
              categories={topBanner.categories}
              actionTaken={topBanner.actionTaken}
              size="banner"
            />
          </View>
        ) : null}

        <View style={styles.deck}>
          {done ? (
            <EmptyDeck onBack={() => router.back()} />
          ) : (
            <View style={styles.stack}>
              {next ? (
                <View style={[styles.cardSlot, styles.cardBehind]} pointerEvents="none">
                  <SwipeDeckCard clip={next.clip} safetyFlags={next.safetyFlags} stackPosition={1} />
                </View>
              ) : null}
              {current ? (
                <View style={styles.cardSlot}>
                  <SwipeDeckCard
                    clip={current.clip}
                    safetyFlags={current.safetyFlags}
                    stackPosition={0}
                    onApprove={() => advance("approve")}
                    onReject={() => advance("reject")}
                    onEdit={onEdit}
                    onRemix={handleRemix}
                    onLongPressRemix={handleRemix}
                  />
                </View>
              ) : null}
            </View>
          )}
        </View>

        {!done ? (
          <View style={styles.actionBar}>
            <ActionButton
              label="Reject"
              variant="ghost"
              size="lg"
              iconLeft={X}
              onPress={() => advance("reject")}
            />
            <ActionButton
              label="Edit"
              variant="secondary"
              size="lg"
              iconLeft={Edit3}
              onPress={onEdit}
            />
            <ActionButton
              label="Approve"
              variant="primary"
              size="lg"
              iconLeft={Check}
              onPress={() => advance("approve")}
            />
          </View>
        ) : null}

        {!done ? (
          <View style={styles.swarmBar}>
            <ActionButton
              label="Safety"
              variant="ghost"
              size="sm"
              iconLeft={Shield}
              onPress={() => Alert.alert("Safety Swarm", "Run multi-level safety screening on this clip.")}
            />
            <ActionButton
              label="Segments"
              variant="ghost"
              size="sm"
              iconLeft={Layers}
              onPress={() => Alert.alert("Segment Swarm", "Find best moments with parallel analysis strategies.")}
            />
            <ActionButton
              label="Edit"
              variant="ghost"
              size="sm"
              iconLeft={Scissors}
              onPress={() => Alert.alert("Edit Swarm", "Apply automated edit recipes in parallel.")}
            />
            <ActionButton
              label="Thumb"
              variant="ghost"
              size="sm"
              iconLeft={Image}
              onPress={() => Alert.alert("Thumbnail Swarm", "Generate thumbnails with different style strategies.")}
            />
          </View>
        ) : null}

        {!done ? (
          <View style={styles.hintRow}>
            <Sparkles
              size={tokens.icon.size.xs}
              color={tokens.color.text.tertiary}
              strokeWidth={tokens.icon.stroke.default}
            />
            <Text style={styles.hintText}>Hold the card to remix</Text>
          </View>
        ) : null}
      </SafeAreaView>
    </View>
  );
}

function EmptyDeck({ onBack }: { onBack: () => void }) {
  return (
    <View style={styles.empty}>
      <Text style={styles.emptyTitle}>Queue clear.</Text>
      <Text style={styles.emptyBody}>
        Next batch lands after the Strategy Agent finishes its window.
      </Text>
      <View style={{ height: tokens.spacing.md }} />
      <ActionButton label="Back to feed" variant="primary" size="lg" onPress={onBack} />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg.base },
  safe: { flex: 1 },
  header: {
    height: tokens.layout.headerHeight,
    paddingHorizontal: tokens.layout.screenPadding,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: tokens.spacing.sm,
  },
  backBtn: {
    width: tokens.layout.minTouchTarget,
    height: tokens.layout.minTouchTarget,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: tokens.radius.pill,
    backgroundColor: tokens.color.bg.raised,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
  },
  title: {
    flex: 1,
    textAlign: "center",
    fontFamily: tokens.type.scale.h2.family,
    fontSize: tokens.type.scale.h2.size,
    lineHeight: tokens.type.scale.h2.lineHeight,
    letterSpacing: tokens.type.scale.h2.letterSpacing,
    color: tokens.color.text.primary,
  },
  counter: {
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: 4,
    borderRadius: tokens.radius.pill,
    backgroundColor: tokens.color.bg.raised,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    minWidth: tokens.layout.minTouchTarget,
    alignItems: "center",
  },
  counterText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.secondary,
  },
  bannerWrap: {
    paddingHorizontal: tokens.layout.screenPadding,
    paddingBottom: tokens.spacing.sm,
  },
  deck: {
    flex: 1,
    paddingHorizontal: tokens.layout.screenPadding,
    paddingTop: tokens.spacing.sm,
    justifyContent: "center",
  },
  stack: {
    position: "relative",
    width: "100%",
  },
  cardSlot: {
    width: "100%",
  },
  cardBehind: {
    position: "absolute",
    left: 0,
    right: 0,
    top: 0,
  },
  actionBar: {
    flexDirection: "row",
    gap: tokens.spacing.sm,
    paddingHorizontal: tokens.layout.screenPadding,
    paddingTop: tokens.spacing.md,
  },
  swarmBar: {
    flexDirection: "row",
    gap: tokens.spacing.sm,
    paddingHorizontal: tokens.layout.screenPadding,
    paddingTop: tokens.spacing.sm,
    justifyContent: "center",
  },
  hintRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: tokens.spacing.xs,
    paddingVertical: tokens.spacing.sm,
  },
  hintText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  empty: {
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: tokens.spacing.xxxl,
    gap: tokens.spacing.sm,
  },
  emptyTitle: {
    fontFamily: tokens.type.scale.h1.family,
    fontSize: tokens.type.scale.h1.size,
    lineHeight: tokens.type.scale.h1.lineHeight,
    letterSpacing: tokens.type.scale.h1.letterSpacing,
    color: tokens.color.text.primary,
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
