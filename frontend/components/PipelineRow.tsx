import React, { memo } from "react";
import { Pressable, StyleSheet, Text, View, ViewStyle } from "react-native";
import { ChevronRight } from "lucide-react-native";
import { tokens } from "@/constants/tokens";
import { triggerHaptic } from "@/utils/haptics";
import { MetricChip } from "./MetricChip";

export type PipelineStatus = "running" | "paused" | "errored" | "setup-incomplete";

export interface PipelineRowProps {
  themeName: string;
  niche: string;
  status: PipelineStatus;
  clipsThisWeek?: number;
  viewDelta?: string;
  deltaVariant?: "positive" | "negative" | "default";
  onTap?: () => void;
  onLongPress?: () => void;
  style?: ViewStyle;
  testID?: string;
}

const STATUS_COLOR: Record<PipelineStatus, string> = {
  running: tokens.color.status.success,
  paused: tokens.color.status.warning,
  errored: tokens.color.status.danger,
  "setup-incomplete": tokens.color.text.tertiary,
};

const STATUS_LABEL: Record<PipelineStatus, string> = {
  running: "Running",
  paused: "Paused",
  errored: "Error",
  "setup-incomplete": "Setup incomplete",
};

function PipelineRowComponent({
  themeName,
  niche,
  status,
  clipsThisWeek,
  viewDelta,
  deltaVariant = "default",
  onTap,
  onLongPress,
  style,
  testID,
}: PipelineRowProps) {
  const handlePress = () => {
    triggerHaptic("selection");
    onTap?.();
  };
  const handleLongPress = () => {
    triggerHaptic("selection");
    onLongPress?.();
  };

  return (
    <Pressable
      onPress={handlePress}
      onLongPress={handleLongPress}
      delayLongPress={400}
      testID={testID}
      style={({ pressed }) => [styles.container, pressed ? styles.pressed : null, style]}
    >
      <View style={[styles.statusDot, { backgroundColor: STATUS_COLOR[status] }]} />
      <View style={styles.body}>
        <Text style={styles.themeName} numberOfLines={1}>{themeName}</Text>
        <Text style={styles.niche} numberOfLines={1}>
          {niche} · {STATUS_LABEL[status]}
        </Text>
      </View>
      <View style={styles.stats}>
        {typeof clipsThisWeek === "number" ? (
          <MetricChip label="This week" value={`${clipsThisWeek} clips`} variant="default" />
        ) : null}
        {viewDelta ? (
          <MetricChip label="7d views" value={viewDelta} variant={deltaVariant === "default" ? "default" : deltaVariant} />
        ) : null}
      </View>
      <ChevronRight size={tokens.icon.size.md} color={tokens.color.text.tertiary} strokeWidth={tokens.icon.stroke.default} />
    </Pressable>
  );
}

export const PipelineRow = memo(PipelineRowComponent);

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
    paddingVertical: tokens.spacing.md,
    paddingHorizontal: tokens.spacing.md,
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    minHeight: 72,
  },
  pressed: {
    backgroundColor: tokens.color.bg.elevated,
  },
  statusDot: {
    width: 10,
    height: 10,
    borderRadius: tokens.radius.pill,
  },
  body: {
    flex: 1,
    gap: 2,
  },
  themeName: {
    fontFamily: tokens.type.scale.h3.family,
    fontSize: tokens.type.scale.h3.size,
    lineHeight: tokens.type.scale.h3.lineHeight,
    color: tokens.color.text.primary,
  },
  niche: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  stats: {
    gap: tokens.spacing.xs,
    alignItems: "flex-end",
  },
});

export default PipelineRow;
