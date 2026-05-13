import React, { memo, useEffect, useRef } from "react";
import { Animated, StyleSheet, Text, View, ViewStyle } from "react-native";
import { ArrowDownRight, ArrowUpRight, LucideIcon } from "lucide-react-native";
import { tokens } from "@/constants/tokens";

export type MetricChipVariant = "default" | "positive" | "negative" | "loading" | "manual";

export interface MetricChipProps {
  label: string;
  value?: string | number;
  delta?: string;
  variant?: MetricChipVariant;
  icon?: LucideIcon;
  style?: ViewStyle;
  testID?: string;
}

function MetricChipComponent({ label, value, delta, variant = "default", icon: Icon, style, testID }: MetricChipProps) {
  const shimmer = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (variant !== "loading") return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(shimmer, { toValue: 1, duration: tokens.motion.duration.deliberate, useNativeDriver: true }),
        Animated.timing(shimmer, { toValue: 0, duration: tokens.motion.duration.deliberate, useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [variant, shimmer]);

  const valueColor =
    variant === "positive"
      ? tokens.color.semantic.metric.positive
      : variant === "negative"
      ? tokens.color.semantic.metric.negative
      : tokens.color.text.primary;

  const DeltaIcon = variant === "positive" ? ArrowUpRight : variant === "negative" ? ArrowDownRight : null;

  return (
    <View style={[styles.container, style]} testID={testID}>
      <View style={styles.labelRow}>
        {Icon ? <Icon size={tokens.icon.size.xs} color={tokens.color.text.tertiary} strokeWidth={tokens.icon.stroke.default} /> : null}
        <Text style={styles.label} numberOfLines={1}>
          {label.toUpperCase()}
        </Text>
        {variant === "manual" ? (
          <View style={styles.manualBadge}>
            <Text style={styles.manualText}>M</Text>
          </View>
        ) : null}
      </View>
      {variant === "loading" ? (
        <Animated.View style={[styles.shimmer, { opacity: shimmer.interpolate({ inputRange: [0, 1], outputRange: [0.3, 0.8] }) }]} />
      ) : (
        <View style={styles.valueRow}>
          {DeltaIcon ? <DeltaIcon size={tokens.icon.size.xs} color={valueColor} strokeWidth={tokens.icon.stroke.bold} /> : null}
          <Text style={[styles.value, { color: valueColor }]} numberOfLines={1}>
            {value ?? "—"}
          </Text>
          {delta ? <Text style={[styles.delta, { color: valueColor }]}>{delta}</Text> : null}
        </View>
      )}
    </View>
  );
}

export const MetricChip = memo(MetricChipComponent);

const styles = StyleSheet.create({
  container: {
    paddingVertical: tokens.spacing.xs,
    paddingHorizontal: tokens.spacing.sm,
    borderRadius: tokens.radius.sm,
    backgroundColor: tokens.color.bg.raised,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    minWidth: 72,
    gap: 2,
  },
  labelRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.xs,
  },
  label: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    lineHeight: tokens.type.scale.overline.lineHeight,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  valueRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.xs,
  },
  value: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    lineHeight: tokens.type.scale.bodyMedium.lineHeight,
  },
  delta: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
  },
  manualBadge: {
    paddingHorizontal: 4,
    borderRadius: tokens.radius.sm,
    backgroundColor: tokens.color.brand.indigo[800],
  },
  manualText: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: 9,
    lineHeight: 12,
    color: tokens.color.text.primary,
    letterSpacing: 0.5,
  },
  shimmer: {
    height: tokens.type.scale.bodyMedium.lineHeight,
    width: "60%",
    borderRadius: tokens.radius.sm,
    backgroundColor: tokens.color.border.default,
  },
});

export default MetricChip;
