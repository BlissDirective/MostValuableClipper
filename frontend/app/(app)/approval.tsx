// CLAUDE_CODE TODO: implement pan gesture handlers via react-native-gesture-handler + react-native-reanimated.
// Right swipe (>40% width) → approve, haptics.approve.
// Left swipe (>40% width) → reject, haptics.reject + 5s undo toast.
// Long-press 500ms → confirmation overlay "Remix this clip?" → confirm/cancel.
// See component-spec.md §8 SwipeDeckCard for full behavior.
//
// Rork phase ships the visual stack + bottom action bar ONLY. Tapping
// Approve / Reject advances the deck and console.logs; no gestures, no
// reanimated worklets, no swipe haptics here.

import React, { useCallback, useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { Stack, useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { Check, ChevronLeft, Edit3, Sparkles, X } from "lucide-react-native";

import { tokens } from "@/constants/tokens";
import { ActionButton } from "@/components/ActionButton";
import { SafetyFlag, SafetyVariant } from "@/components/SafetyFlag";
import { SwipeDeckCard, SwipeDeckClip } from "@/components/SwipeDeckCard";
import { triggerHaptic } from "@/utils/haptics";

interface QueueItem {
  clip: SwipeDeckClip;
  safetyFlags?: { variant: SafetyVariant; categories?: string[]; actionTaken?: string }[];
}

const QUEUE: QueueItem[] = [
  {
    clip: {
      id: "approval-1",
      sourceName: "Design Details · Ep 412",
      caption:
        "Question-led hook: \"What's the hidden tax on every productivity app you open?\" Cut at 0:47 with on-screen pull-quote.",
      targets: [
        { platform: "tiktok", handle: "@studio" },
        { platform: "instagram", handle: "@studio" },
      ],
      predictedReach: "18-24K",
      predictedRetention: "+14%",
    },
  },
  {
    clip: {
      id: "approval-2",
      sourceName: "F1 Race Recap · Imola",
      caption:
        "Lap 38 undercut reconstruction. Three-angle composite. Caption length 78 chars — within best-performing range.",
      targets: [
        { platform: "tiktok" },
        { platform: "youtube" },
      ],
      predictedReach: "9-12K",
      predictedRetention: "+8%",
    },
    safetyFlags: [
      {
        variant: "warn",
        categories: ["Identifiable individual"],
        actionTaken: "Disclosure recommended in caption.",
      },
    ],
  },
  {
    clip: {
      id: "approval-3",
      sourceName: "Health & Wellness Daily",
      caption:
        "Cohort study on intermittent fasting. Pull-quote: \"Markers, not headlines.\" Health disclosure auto-appended.",
      targets: [{ platform: "tiktok" }, { platform: "instagram" }],
      predictedReach: "6-8K",
      predictedRetention: "+5%",
    },
    safetyFlags: [
      {
        variant: "warn",
        categories: ["Health"],
        actionTaken: "Source citation auto-appended.",
      },
    ],
  },
];

export default function ApprovalScreen() {
  const router = useRouter();
  const [index, setIndex] = useState<number>(0);

  const total = QUEUE.length;
  const current = QUEUE[index];
  const next = QUEUE[index + 1];

  const advance = useCallback(
    (verdict: "approve" | "reject") => {
      console.log("[approval] verdict", { id: current?.clip.id, verdict });
      // CLAUDE_CODE: wire to ApprovalService.submit({clipId, verdict})
      triggerHaptic(verdict === "approve" ? "approve" : "reject");
      setIndex((i) => Math.min(i + 1, total));
    },
    [current, total]
  );

  const onEdit = useCallback(() => {
    console.log("[approval] open editor", { id: current?.clip.id });
    // CLAUDE_CODE: navigate to clip editor (post-MVP)
  }, [current]);

  const onRemix = useCallback(() => {
    console.log("[approval] remix tapped", { id: current?.clip.id });
    // CLAUDE_CODE: long-press gesture confirms remix; see top-of-file note.
  }, [current]);

  const topBanner = useMemo(() => current?.safetyFlags?.[0], [current]);
  const done = index >= total;

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
                    onRemix={onRemix}
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
