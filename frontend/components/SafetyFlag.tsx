import React, { memo } from "react";
import { Pressable, StyleSheet, Text, View, ViewStyle } from "react-native";
import { Shield, ShieldAlert, ShieldX, EyeOff, LucideIcon } from "lucide-react-native";
import { tokens } from "@/constants/tokens";
import { triggerHaptic } from "@/utils/haptics";

export type SafetyVariant = "general" | "warn" | "block" | "review";

export interface SafetyFlagProps {
  variant: SafetyVariant;
  categories?: string[];
  actionTaken?: string;
  onTap?: () => void;
  size?: "sm" | "md" | "banner";
  style?: ViewStyle;
  testID?: string;
}

const ICON_MAP: Record<SafetyVariant, LucideIcon> = {
  general: Shield,
  warn: ShieldAlert,
  block: ShieldX,
  review: EyeOff,
};

const LABEL_MAP: Record<SafetyVariant, string> = {
  general: "General",
  warn: "Caution",
  block: "Blocked",
  review: "Held for review",
};

function SafetyFlagComponent({ variant, categories, actionTaken, onTap, size = "sm", style, testID }: SafetyFlagProps) {
  const Icon = ICON_MAP[variant];
  const palette = tokens.color.semantic.safety[variant];
  const isBanner = size === "banner";

  const labelText = categories && categories.length > 0 ? categories.join(" · ") : LABEL_MAP[variant];

  const handlePress = () => {
    if (!onTap) return;
    triggerHaptic("selection");
    onTap();
  };

  const Container = onTap ? Pressable : View;

  return (
    <Container
      onPress={handlePress as () => void}
      hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
      testID={testID}
      style={[
        styles.base,
        isBanner ? styles.banner : styles.pill,
        { backgroundColor: palette.bg, borderColor: palette.border },
        style,
      ]}
    >
      <Icon size={isBanner ? tokens.icon.size.md : tokens.icon.size.xs} color={palette.fg} strokeWidth={tokens.icon.stroke.default} />
      <View style={styles.textCol}>
        <Text style={[styles.label, { color: palette.fg, fontSize: isBanner ? tokens.type.scale.bodySmall.size : tokens.type.scale.caption.size }]} numberOfLines={1}>
          {labelText}
        </Text>
        {isBanner && actionTaken ? (
          <Text style={[styles.subLabel, { color: palette.fg }]} numberOfLines={1}>
            {actionTaken}
          </Text>
        ) : null}
      </View>
    </Container>
  );
}

export const SafetyFlag = memo(SafetyFlagComponent);

const styles = StyleSheet.create({
  base: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.xs,
    borderWidth: 1,
  },
  pill: {
    paddingVertical: 4,
    paddingHorizontal: tokens.spacing.sm,
    borderRadius: tokens.radius.pill,
    alignSelf: "flex-start",
  },
  banner: {
    paddingVertical: tokens.spacing.sm,
    paddingHorizontal: tokens.spacing.md,
    borderRadius: tokens.radius.md,
    minHeight: 56,
    gap: tokens.spacing.sm,
  },
  textCol: {
    flexShrink: 1,
    gap: 2,
  },
  label: {
    fontFamily: tokens.type.scale.caption.family,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
  },
  subLabel: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    opacity: 0.85,
  },
});

export default SafetyFlag;
