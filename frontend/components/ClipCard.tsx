import React, { memo, useEffect, useRef } from "react";
import { Animated, Pressable, StyleSheet, Text, View, ViewStyle } from "react-native";
import { AlertTriangle, CheckCircle2, Film, Radio, RefreshCw, Repeat, Trash2, TrendingUp, LucideIcon } from "lucide-react-native";
import { tokens } from "@/constants/tokens";
import { triggerHaptic } from "@/utils/haptics";
import { AccountBadge, Platform } from "./AccountBadge";
import { MetricChip } from "./MetricChip";
import { SafetyFlag } from "./SafetyFlag";
import type { SafetyVariant } from "./SafetyFlag";
import { ActionButton } from "./ActionButton";

export type ClipState = "posted" | "queued" | "held-safety-block" | "held-safety-warn" | "processing" | "failed";
export type ClipVariant = "feed" | "detail" | "queue";

export interface ClipCardData {
  id: string;
  sourceName: string;
  sourceIcon?: LucideIcon;
  caption: string;
  platforms: { platform: Platform; handle?: string }[];
  metrics?: {
    views?: string;
    retention?: string;
    earnings?: string;
    retentionVariant?: "positive" | "negative" | "default";
  };
  safety?: { variant: SafetyVariant; categories?: string[] } | null;
  state: ClipState;
  queuedFor?: string;
}

export interface ClipCardProps {
  clip: ClipCardData;
  variant?: ClipVariant;
  onAction?: (actionId: string) => void;
  onPress?: () => void;
  onLongPress?: () => void;
  selected?: boolean;
  selectionMode?: boolean;
  style?: ViewStyle;
  testID?: string;
}

function ClipCardComponent({ clip, variant = "feed", onAction, onPress, onLongPress, selected, selectionMode, style, testID }: ClipCardProps) {
  const shimmer = useRef(new Animated.Value(0)).current;
  const isProcessing = clip.state === "processing";
  const isQueued = clip.state === "queued";
  const isBlock = clip.state === "held-safety-block";
  const isWarn = clip.state === "held-safety-warn";
  const isFailed = clip.state === "failed";

  useEffect(() => {
    if (!isProcessing) return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(shimmer, { toValue: 1, duration: tokens.motion.duration.deliberate, useNativeDriver: true }),
        Animated.timing(shimmer, { toValue: 0, duration: tokens.motion.duration.deliberate, useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [isProcessing, shimmer]);

  const borderColor = isBlock
    ? tokens.color.semantic.safety.block.border
    : isWarn
    ? tokens.color.semantic.safety.warn.border
    : isFailed
    ? tokens.color.status.danger
    : tokens.color.border.subtle;

  const SourceIcon = clip.sourceIcon ?? Film;

  const fire = (id: string) => {
    triggerHaptic("selection");
    onAction?.(id);
  };

  const selectionOverlay = selectionMode ? (
    <View style={[styles.selectionOverlay, selected && styles.selectionOverlayActive]}>
      <View style={[styles.selectionCheck, selected && styles.selectionCheckActive]}>
        {selected && <CheckCircle2 size={20} color={tokens.color.text.inverse} strokeWidth={2} />}
      </View>
    </View>
  ) : null;

  return (
    <Pressable
      onPress={() => {
        if (isProcessing) return;
        triggerHaptic("selection");
        if (selectionMode) {
          onAction?.(selected ? "deselect" : "select");
        } else {
          onPress?.();
        }
      }}
      onLongPress={onLongPress}
      delayLongPress={400}
      testID={testID}
      style={({ pressed }) => [
        styles.card,
        { borderColor },
        pressed && !isProcessing ? styles.pressed : null,
        selected ? styles.cardSelected : null,
        style,
      ]}
    >
      <View style={[styles.thumb, { opacity: isQueued ? 0.6 : 1 }]}>
        {isProcessing ? (
          <Animated.View
            style={[styles.shimmer, { opacity: shimmer.interpolate({ inputRange: [0, 1], outputRange: [0.25, 0.6] }) }]}
          />
        ) : (
          <View style={styles.thumbInner}>
            <Film size={tokens.icon.size.xl} color={tokens.color.text.tertiary} strokeWidth={tokens.icon.stroke.thin} />
          </View>
        )}
        {(isBlock || isWarn) && clip.safety ? (
          <View style={styles.thumbBanner}>
            <SafetyFlag
              variant={clip.safety.variant}
              categories={clip.safety.categories}
              actionTaken={isBlock ? "Tap to review" : "Advisory · Tap to review"}
              size="banner"
              onTap={() => onAction?.("review-safety")}
            />
          </View>
        ) : null}
        {selectionOverlay}
        {isFailed ? (
          <View style={styles.failedOverlay}>
            <AlertTriangle size={tokens.icon.size.lg} color={tokens.color.status.danger} strokeWidth={tokens.icon.stroke.bold} />
            <Text style={styles.failedText}>Generation failed</Text>
          </View>
        ) : null}
      </View>

      <View style={styles.row}>
        <View style={styles.sourceRow}>
          <SourceIcon size={tokens.icon.size.sm} color={tokens.color.text.secondary} strokeWidth={tokens.icon.stroke.default} />
          <Text style={styles.sourceName} numberOfLines={1}>{clip.sourceName}</Text>
        </View>
        {clip.safety && !isBlock && !isWarn ? (
          <SafetyFlag variant={clip.safety.variant} categories={clip.safety.categories} />
        ) : null}
      </View>

      {!isProcessing ? (
        <Text style={styles.caption} numberOfLines={2}>
          {clip.caption}
        </Text>
      ) : (
        <View style={styles.captionSkeleton} />
      )}

      <View style={styles.platformRow}>
        {isQueued ? (
          <Text style={styles.queuedText}>Queued for {clip.queuedFor ?? "later"}</Text>
        ) : (
          clip.platforms.map((p, i) => (
            <AccountBadge key={`${p.platform}-${i}`} platform={p.platform} handle={p.handle} variant="dot" />
          ))
        )}
      </View>

      {!isProcessing && clip.metrics ? (
        <View style={styles.metricsRow}>
          <MetricChip label="Views" value={clip.metrics.views ?? "—"} icon={Radio} />
          <MetricChip
            label="Retention"
            value={clip.metrics.retention ?? "—"}
            variant={clip.metrics.retentionVariant ?? "default"}
            icon={TrendingUp}
          />
          <MetricChip label="Earnings" value={clip.metrics.earnings ?? "—"} />
        </View>
      ) : null}

      <View style={styles.actionsRow}>
        {isBlock ? (
          <>
            <ActionButton label="Override" variant="secondary" size="sm" disabled onPress={() => fire("override")} />
            <ActionButton label="Discard" variant="danger" size="sm" onPress={() => fire("discard")} />
          </>
        ) : isFailed ? (
          <ActionButton label="Retry" variant="secondary" size="sm" iconLeft={RefreshCw} onPress={() => fire("retry")} />
        ) : isProcessing ? (
          <Text style={styles.processingText}>Processing…</Text>
        ) : (
          <>
            <ActionButton label="Boost" variant="ghost" size="sm" iconLeft={TrendingUp} onPress={() => fire("boost")} />
            <ActionButton label="Replicate" variant="ghost" size="sm" iconLeft={Repeat} onPress={() => fire("replicate")} />
            <ActionButton label="Kill" variant="ghost" size="sm" iconLeft={Trash2} onPress={() => fire("kill")} />
          </>
        )}
      </View>
    </Pressable>
  );
}

export const ClipCard = memo(ClipCardComponent);

const styles = StyleSheet.create({
  card: {
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    padding: tokens.spacing.md,
    gap: tokens.spacing.sm,
  },
  pressed: {
    backgroundColor: tokens.color.bg.elevated,
  },
  thumb: {
    aspectRatio: 9 / 16,
    width: "100%",
    maxHeight: 360,
    alignSelf: "center",
    borderRadius: tokens.radius.md,
    overflow: "hidden",
    backgroundColor: tokens.color.bg.raised,
    position: "relative",
  },
  thumbInner: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  shimmer: {
    flex: 1,
    backgroundColor: tokens.color.border.default,
  },
  thumbBanner: {
    position: "absolute",
    left: tokens.spacing.sm,
    right: tokens.spacing.sm,
    top: tokens.spacing.sm,
  },
  failedOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: tokens.color.status.dangerBg,
    alignItems: "center",
    justifyContent: "center",
    gap: tokens.spacing.sm,
  },
  failedText: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    color: tokens.color.status.danger,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: tokens.spacing.sm,
  },
  sourceRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.xs,
    flex: 1,
  },
  sourceName: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.secondary,
    flex: 1,
  },
  caption: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    lineHeight: tokens.type.scale.bodySmall.lineHeight,
    color: tokens.color.text.secondary,
  },
  captionSkeleton: {
    height: tokens.type.scale.bodySmall.lineHeight * 2,
    borderRadius: tokens.radius.sm,
    backgroundColor: tokens.color.border.subtle,
  },
  platformRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.xs,
    flexWrap: "wrap",
  },
  queuedText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.status.warning,
  },
  metricsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: tokens.spacing.xs,
  },
  actionsRow: {
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: tokens.spacing.xs,
    flexWrap: "wrap",
  },
  processingText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  cardSelected: {
    borderColor: tokens.color.accent.primary,
    borderWidth: 2,
  },
  selectionOverlay: {
    position: "absolute",
    top: 8,
    right: 8,
    zIndex: 10,
  },
  selectionOverlayActive: {
    top: 8,
    right: 8,
  },
  selectionCheck: {
    width: 28,
    height: 28,
    borderRadius: 14,
    borderWidth: 2,
    borderColor: tokens.color.text.inverse,
    backgroundColor: "rgba(0,0,0,0.3)",
    alignItems: "center",
    justifyContent: "center",
  },
  selectionCheckActive: {
    backgroundColor: tokens.color.accent.primary,
    borderColor: tokens.color.accent.primary,
  },
});
