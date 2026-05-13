import React, { memo } from "react";
import { StyleSheet, Text, View, ViewStyle } from "react-native";
import { ArrowDownRight, ArrowUpRight } from "lucide-react-native";
import { tokens } from "@/constants/tokens";
import { ActionButton } from "./ActionButton";

export type InsightVariant = "positive" | "negative" | "neutral";

export interface InsightTileProps {
  overline: string;
  headline: string;
  body: string;
  variant?: InsightVariant;
  ctaLabel?: string;
  onApply?: () => void;
  style?: ViewStyle;
  testID?: string;
}

function InsightTileComponent({ overline, headline, body, variant = "neutral", ctaLabel, onApply, style, testID }: InsightTileProps) {
  const accent =
    variant === "positive"
      ? tokens.color.semantic.metric.positive
      : variant === "negative"
      ? tokens.color.semantic.metric.negative
      : tokens.color.text.secondary;

  const borderColor =
    variant === "positive"
      ? tokens.color.semantic.metric.positive
      : variant === "negative"
      ? tokens.color.semantic.metric.negative
      : tokens.color.border.default;

  const TrendIcon = variant === "positive" ? ArrowUpRight : variant === "negative" ? ArrowDownRight : null;

  return (
    <View style={[styles.container, { borderColor }, style]} testID={testID}>
      <Text style={styles.overline} numberOfLines={1}>{overline.toUpperCase()}</Text>
      <View style={styles.headlineRow}>
        {TrendIcon ? <TrendIcon size={tokens.icon.size.lg} color={accent} strokeWidth={tokens.icon.stroke.bold} /> : null}
        <Text style={[styles.headline, { color: accent }]} numberOfLines={1}>{headline}</Text>
      </View>
      <Text style={styles.body}>{body}</Text>
      {ctaLabel ? (
        <View style={styles.cta}>
          <ActionButton label={ctaLabel} variant="ghost" size="sm" onPress={onApply} />
        </View>
      ) : null}
    </View>
  );
}

export const InsightTile = memo(InsightTileComponent);

const styles = StyleSheet.create({
  container: {
    padding: tokens.spacing.md,
    borderRadius: tokens.radius.lg,
    backgroundColor: tokens.color.bg.surface,
    borderWidth: 1,
    gap: tokens.spacing.sm,
  },
  overline: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    lineHeight: tokens.type.scale.overline.lineHeight,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  headlineRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.xs,
  },
  headline: {
    fontFamily: tokens.type.scale.h1.family,
    fontSize: tokens.type.scale.h1.size,
    lineHeight: tokens.type.scale.h1.lineHeight,
    letterSpacing: tokens.type.scale.h1.letterSpacing,
  },
  body: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    lineHeight: tokens.type.scale.bodySmall.lineHeight,
    color: tokens.color.text.secondary,
  },
  cta: {
    marginTop: tokens.spacing.xs,
    alignSelf: "flex-start",
  },
});

export default InsightTile;
