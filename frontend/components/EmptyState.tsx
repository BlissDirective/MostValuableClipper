import React from "react";
import { StyleSheet, Text, View, Pressable } from "react-native";
import { LucideIcon } from "lucide-react-native";

import { tokens } from "@/constants/tokens";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  subtitle?: string;
  actionLabel?: string;
  onAction?: () => void;
  size?: "sm" | "md" | "lg";
}

export function EmptyState({
  icon: Icon,
  title,
  subtitle,
  actionLabel,
  onAction,
  size = "md",
}: EmptyStateProps) {
  const sizeMap = {
    sm: { icon: 28, title: tokens.type.scale.bodyMedium.size, subtitle: tokens.type.scale.caption.size, padding: tokens.spacing.lg },
    md: { icon: 40, title: tokens.type.scale.h3.size, subtitle: tokens.type.scale.bodySmall.size, padding: tokens.spacing.xl },
    lg: { icon: 56, title: tokens.type.scale.h2.size, subtitle: tokens.type.scale.body.size, padding: tokens.spacing.xxl },
  };
  const s = sizeMap[size];

  return (
    <View style={[styles.container, { padding: s.padding }]}>
      {Icon && (
        <View style={styles.iconWrap}>
          <Icon size={s.icon} color={tokens.color.brand.indigo[500]} strokeWidth={1.5} />
        </View>
      )}
      <Text style={[styles.title, { fontSize: s.title }]}>{title}</Text>
      {subtitle ? (
        <Text style={[styles.subtitle, { fontSize: s.subtitle }]}>{subtitle}</Text>
      ) : null}
      {actionLabel && onAction ? (
        <Pressable style={styles.action} onPress={onAction}>
          <Text style={styles.actionText}>{actionLabel}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: "center",
    justifyContent: "center",
    gap: tokens.spacing.sm,
  },
  iconWrap: {
    width: 80,
    height: 80,
    borderRadius: tokens.radius.lg,
    backgroundColor: tokens.color.bg.surface,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: tokens.spacing.sm,
  },
  title: {
    fontFamily: tokens.type.fontFamily.primarySemibold,
    color: tokens.color.text.primary,
    textAlign: "center",
  },
  subtitle: {
    fontFamily: tokens.type.fontFamily.primary,
    color: tokens.color.text.secondary,
    textAlign: "center",
    lineHeight: tokens.type.scale.bodySmall.lineHeight,
    maxWidth: 280,
  },
  action: {
    marginTop: tokens.spacing.sm,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    backgroundColor: tokens.color.brand.indigo[500],
    borderRadius: tokens.radius.md,
  },
  actionText: {
    fontFamily: tokens.type.fontFamily.primaryMedium,
    fontSize: tokens.type.scale.bodySmall.size,
    color: tokens.color.text.onAccent,
  },
});