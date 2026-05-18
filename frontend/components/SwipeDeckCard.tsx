import React, { memo, useCallback, useRef } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View, ViewStyle, Animated, Alert } from "react-native";
import { Edit3, Film, Sparkles, X, Check, Radio, TrendingUp } from "lucide-react-native";
import { tokens } from "@/constants/tokens";
import { AccountBadge, Platform } from "./AccountBadge";
import { SafetyFlag, SafetyVariant } from "./SafetyFlag";
import { MetricChip } from "./MetricChip";
import { ActionButton } from "./ActionButton";
import { triggerHaptic } from "@/utils/haptics";

export interface SwipeDeckClip {
  id: string;
  sourceName: string;
  caption: string;
  targets: { platform: Platform; handle?: string }[];
  predictedReach?: string;
  predictedRetention?: string;
}

export interface SwipeDeckCardProps {
  clip: SwipeDeckClip;
  safetyFlags?: { variant: SafetyVariant; categories?: string[]; actionTaken?: string }[];
  stackPosition?: 0 | 1 | 2;
  onApprove?: () => void;
  onReject?: () => void;
  onEdit?: () => void;
  onRemix?: () => void;
  onLongPressRemix?: () => void;
  style?: ViewStyle;
  testID?: string;
}

function SwipeDeckCardComponent({
  clip,
  safetyFlags,
  stackPosition = 0,
  onApprove,
  onReject,
  onEdit,
  onRemix,
  onLongPressRemix,
  style,
  testID,
}: SwipeDeckCardProps) {
  const topFlag = safetyFlags?.[0];
  const scale = stackPosition === 0 ? 1 : stackPosition === 1 ? 0.96 : 0.92;
  const offset = stackPosition * 8;
  const opacity = stackPosition === 0 ? 1 : stackPosition === 1 ? 0.7 : 0.4;

  // Long press animation
  const longPressRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const scaleAnim = useRef(new Animated.Value(1)).current;
  const [remixConfirm, setRemixConfirm] = React.useState(false);

  const handleLongPressStart = useCallback(() => {
    if (stackPosition !== 0 || !onLongPressRemix) return;
    triggerHaptic("light");
    
    Animated.timing(scaleAnim, {
      toValue: 0.97,
      duration: 200,
      useNativeDriver: true,
    }).start();

    longPressRef.current = setTimeout(() => {
      triggerHaptic("heavy");
      setRemixConfirm(true);
    }, 500);
  }, [stackPosition, onLongPressRemix, scaleAnim]);

  const handleLongPressEnd = useCallback(() => {
    if (longPressRef.current) {
      clearTimeout(longPressRef.current);
      longPressRef.current = null;
    }
    Animated.timing(scaleAnim, {
      toValue: 1,
      duration: 200,
      useNativeDriver: true,
    }).start();
  }, [scaleAnim]);

  const confirmRemix = useCallback(() => {
    setRemixConfirm(false);
    onLongPressRemix?.();
  }, [onLongPressRemix]);

  const cancelRemix = useCallback(() => {
    setRemixConfirm(false);
  }, []);

  return (
    <Animated.View
      testID={testID}
      style={[
        styles.card,
        { 
          transform: [{ scale: Animated.multiply(scaleAnim, scale) }, { translateY: offset }], 
          opacity, 
          zIndex: 10 - stackPosition 
        },
        style,
      ]}
    >
      {/* Remix Confirmation Overlay */}
      {remixConfirm && stackPosition === 0 && (
        <View style={styles.remixOverlay}>
          <View style={styles.remixOverlayContent}>
            <Sparkles size={tokens.icon.size.lg} color={tokens.color.accent.primary} strokeWidth={tokens.icon.stroke.default} />
            <Text style={styles.remixOverlayTitle}>Remix this clip?</Text>
            <Text style={styles.remixOverlayBody}>
              We'll use AI to generate 2-3 new versions with optimized hooks, fresh captions, and vertical format.
            </Text>
            <View style={styles.remixOverlayActions}>
              <ActionButton label="Cancel" variant="ghost" size="md" onPress={cancelRemix} />
              <ActionButton label="Remix" variant="primary" size="md" iconLeft={Sparkles} onPress={confirmRemix} />
            </View>
          </View>
        </View>
      )}

      {topFlag ? (
        <View style={styles.banner}>
          <SafetyFlag
            variant={topFlag.variant}
            categories={topFlag.categories}
            actionTaken={topFlag.actionTaken}
            size="banner"
          />
        </View>
      ) : null}

      <Pressable
        onPressIn={handleLongPressStart}
        onPressOut={handleLongPressEnd}
        onPress={onRemix}
        delayLongPress={500}
        style={styles.preview}
      >
        <Film size={tokens.icon.size.xl} color={tokens.color.text.tertiary} strokeWidth={tokens.icon.stroke.thin} />
        <Text style={styles.previewLabel}>Clip preview</Text>
        <Text style={styles.remixHintText}>Hold to remix</Text>
      </Pressable>

      <View style={styles.sheet}>
        <View style={styles.sourceRow}>
          <Film size={tokens.icon.size.sm} color={tokens.color.text.secondary} strokeWidth={tokens.icon.stroke.default} />
          <Text style={styles.sourceName} numberOfLines={1}>{clip.sourceName}</Text>
        </View>

        <ScrollView style={styles.captionScroll} contentContainerStyle={styles.captionContent} showsVerticalScrollIndicator={false}>
          <Text style={styles.caption}>{clip.caption}</Text>
        </ScrollView>

        <View style={styles.targetsRow}>
          {clip.targets.map((t, i) => (
            <AccountBadge key={`${t.platform}-${i}`} platform={t.platform} handle={t.handle} variant="pill" />
          ))}
        </View>

        <View style={styles.metricsRow}>
          <MetricChip label="Predicted reach" value={clip.predictedReach ?? "—"} icon={Radio} />
          <MetricChip label="Retention est." value={clip.predictedRetention ?? "—"} variant="positive" icon={TrendingUp} />
        </View>

        {stackPosition === 0 ? (
          <View style={styles.actionBar}>
            <ActionButton label="Reject" variant="ghost" size="lg" iconLeft={X} onPress={onReject} />
            <ActionButton label="Edit" variant="secondary" size="lg" iconLeft={Edit3} onPress={onEdit} />
            <ActionButton label="Approve" variant="primary" size="lg" iconLeft={Check} onPress={onApprove} />
          </View>
        ) : null}
      </View>
    </Animated.View>
  );
}

export const SwipeDeckCard = memo(SwipeDeckCardComponent);

const styles = StyleSheet.create({
  card: {
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.xl,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    overflow: "hidden",
    width: "100%",
    ...tokens.elevation["3"],
  },
  remixOverlay: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "rgba(0,0,0,0.7)",
    zIndex: 100,
    alignItems: "center",
    justifyContent: "center",
    padding: tokens.spacing.lg,
  },
  remixOverlayContent: {
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.xl,
    padding: tokens.spacing.lg,
    gap: tokens.spacing.sm,
    alignItems: "center",
    maxWidth: 300,
    ...tokens.elevation["4"],
  },
  remixOverlayTitle: {
    fontFamily: tokens.type.scale.h3.family,
    fontSize: tokens.type.scale.h3.size,
    lineHeight: tokens.type.scale.h3.lineHeight,
    color: tokens.color.text.primary,
    textAlign: "center",
  },
  remixOverlayBody: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    lineHeight: tokens.type.scale.bodySmall.lineHeight,
    color: tokens.color.text.secondary,
    textAlign: "center",
  },
  remixOverlayActions: {
    flexDirection: "row",
    gap: tokens.spacing.sm,
    marginTop: tokens.spacing.sm,
  },
  banner: {
    padding: tokens.spacing.sm,
    backgroundColor: tokens.color.bg.raised,
    borderBottomWidth: 1,
    borderBottomColor: tokens.color.border.subtle,
  },
  preview: {
    aspectRatio: 9 / 16,
    width: "100%",
    maxHeight: 420,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: tokens.color.bg.raised,
    gap: tokens.spacing.sm,
  },
  previewLabel: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  remixHintText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
    marginTop: tokens.spacing.xs,
  },
  sheet: {
    padding: tokens.spacing.md,
    gap: tokens.spacing.sm,
    backgroundColor: tokens.color.bg.surface,
  },
  sourceRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.xs,
  },
  sourceName: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.secondary,
  },
  captionScroll: {
    maxHeight: 80,
  },
  captionContent: {
    paddingVertical: tokens.spacing.xs,
  },
  caption: {
    fontFamily: tokens.type.scale.body.family,
    fontSize: tokens.type.scale.body.size,
    lineHeight: tokens.type.scale.body.lineHeight,
    color: tokens.color.text.primary,
  },
  targetsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: tokens.spacing.xs,
  },
  metricsRow: {
    flexDirection: "row",
    gap: tokens.spacing.xs,
    flexWrap: "wrap",
  },
  actionBar: {
    flexDirection: "row",
    gap: tokens.spacing.sm,
    marginTop: tokens.spacing.sm,
  },
});

export default SwipeDeckCard;