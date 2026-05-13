import React, { memo } from "react";
import { ScrollView, StyleSheet, Text, View, ViewStyle } from "react-native";
import { Edit3, Film, Sparkles, X, Check, Radio, TrendingUp } from "lucide-react-native";
import { tokens } from "@/constants/tokens";
import { AccountBadge, Platform } from "./AccountBadge";
import { SafetyFlag, SafetyVariant } from "./SafetyFlag";
import { MetricChip } from "./MetricChip";
import { ActionButton } from "./ActionButton";

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
  style,
  testID,
}: SwipeDeckCardProps) {
  const topFlag = safetyFlags?.[0];
  const scale = stackPosition === 0 ? 1 : stackPosition === 1 ? 0.96 : 0.92;
  const offset = stackPosition * 8;
  const opacity = stackPosition === 0 ? 1 : stackPosition === 1 ? 0.7 : 0.4;

  return (
    <View
      testID={testID}
      style={[
        styles.card,
        { transform: [{ scale }, { translateY: offset }], opacity, zIndex: 10 - stackPosition },
        style,
      ]}
    >
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

      <View style={styles.preview}>
        <Film size={tokens.icon.size.xl} color={tokens.color.text.tertiary} strokeWidth={tokens.icon.stroke.thin} />
        <Text style={styles.previewLabel}>Clip preview</Text>
      </View>

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

        {stackPosition === 0 ? (
          <View style={styles.remixHint}>
            <Sparkles size={tokens.icon.size.xs} color={tokens.color.text.tertiary} strokeWidth={tokens.icon.stroke.default} />
            <Text style={styles.remixHintText} onPress={onRemix}>Hold to remix</Text>
          </View>
        ) : null}
      </View>
    </View>
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
  remixHint: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: tokens.spacing.xs,
    paddingTop: tokens.spacing.xs,
  },
  remixHintText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
  },
});

export default SwipeDeckCard;
