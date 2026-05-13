import React, { memo, useCallback, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View, ViewStyle } from "react-native";
import { LucideIcon } from "lucide-react-native";
import { tokens } from "@/constants/tokens";
import { triggerHaptic } from "@/utils/haptics";

export type ActionButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ActionButtonSize = "sm" | "md" | "lg";

export interface ActionButtonProps {
  label: string;
  variant?: ActionButtonVariant;
  size?: ActionButtonSize;
  iconLeft?: LucideIcon;
  iconRight?: LucideIcon;
  loading?: boolean;
  disabled?: boolean;
  onPress?: () => void;
  fullWidth?: boolean;
  testID?: string;
}

const SIZE_HEIGHT: Record<ActionButtonSize, number> = { sm: 32, md: 44, lg: 56 };
const SIZE_PADDING: Record<ActionButtonSize, number> = { sm: tokens.spacing.sm, md: tokens.spacing.md, lg: tokens.spacing.lg };
const SIZE_FONT: Record<ActionButtonSize, typeof tokens.type.scale.body> = {
  sm: tokens.type.scale.caption as never,
  md: tokens.type.scale.bodyMedium,
  lg: tokens.type.scale.h3,
};

function ActionButtonComponent({
  label,
  variant = "primary",
  size = "md",
  iconLeft: IconLeft,
  iconRight: IconRight,
  loading = false,
  disabled = false,
  onPress,
  fullWidth = false,
  testID,
}: ActionButtonProps) {
  const [pressed, setPressed] = useState<boolean>(false);

  const handlePress = useCallback(() => {
    if (disabled || loading) return;
    if (variant === "danger") {
      triggerHaptic("blockTriggered");
    } else {
      triggerHaptic("selection");
    }
    onPress?.();
  }, [disabled, loading, variant, onPress]);

  const bg = (() => {
    if (variant === "primary") return pressed ? tokens.color.accent.primaryPressed : tokens.color.accent.primary;
    if (variant === "danger") return pressed ? tokens.color.status.dangerBg : tokens.color.status.danger;
    if (variant === "secondary") return "transparent";
    return "transparent";
  })();

  const fg = (() => {
    if (variant === "primary" || variant === "danger") return tokens.color.text.onAccent;
    if (variant === "secondary") return tokens.color.text.primary;
    return tokens.color.text.secondary;
  })();

  const border = variant === "secondary" ? tokens.color.border.strong : "transparent";

  const font = SIZE_FONT[size];
  const containerStyle: ViewStyle = {
    height: SIZE_HEIGHT[size],
    paddingHorizontal: SIZE_PADDING[size],
    backgroundColor: bg,
    borderColor: border,
    borderWidth: variant === "secondary" ? 1 : 0,
    opacity: disabled ? 0.5 : 1,
    alignSelf: fullWidth ? "stretch" : "auto",
  };

  return (
    <Pressable
      onPress={handlePress}
      onPressIn={() => setPressed(true)}
      onPressOut={() => setPressed(false)}
      disabled={disabled || loading}
      hitSlop={size === "sm" ? { top: 8, bottom: 8, left: 4, right: 4 } : undefined}
      testID={testID}
      accessibilityRole="button"
      accessibilityState={{ disabled: disabled || loading, busy: loading }}
      style={[styles.base, containerStyle]}
    >
      {loading ? (
        <ActivityIndicator color={fg} size="small" />
      ) : (
        <View style={styles.row}>
          {IconLeft ? <IconLeft size={tokens.icon.size.sm} color={fg} strokeWidth={tokens.icon.stroke.default} /> : null}
          <Text
            style={[
              styles.label,
              {
                color: fg,
                fontFamily: font.family,
                fontSize: font.size,
                lineHeight: font.lineHeight,
                letterSpacing: font.letterSpacing,
              },
            ]}
            numberOfLines={1}
          >
            {label}
          </Text>
          {IconRight ? <IconRight size={tokens.icon.size.sm} color={fg} strokeWidth={tokens.icon.stroke.default} /> : null}
        </View>
      )}
    </Pressable>
  );
}

export const ActionButton = memo(ActionButtonComponent);

const styles = StyleSheet.create({
  base: {
    borderRadius: tokens.radius.md,
    alignItems: "center",
    justifyContent: "center",
    minWidth: tokens.layout.minTouchTarget,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.sm,
  },
  label: {},
});

export default ActionButton;
