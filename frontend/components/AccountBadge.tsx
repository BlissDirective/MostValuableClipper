import React, { memo } from "react";
import { StyleSheet, Text, View, ViewStyle } from "react-native";
import { AlertCircle, LucideIcon, Music2, Youtube, Instagram, Facebook, Globe } from "lucide-react-native";
import { tokens } from "@/constants/tokens";

export type Platform = "tiktok" | "youtube" | "instagram" | "facebook" | "default";
export type AccountState = "connected" | "expired-token" | "not-eligible";
export type AccountBadgeVariant = "dot" | "pill" | "rich";

export interface AccountBadgeProps {
  platform: Platform;
  handle?: string;
  followers?: number;
  eligible?: boolean;
  state?: AccountState;
  variant?: AccountBadgeVariant;
  style?: ViewStyle;
  testID?: string;
}

const PLATFORM_ICON: Record<Platform, LucideIcon> = {
  tiktok: Music2,
  youtube: Youtube,
  instagram: Instagram,
  facebook: Facebook,
  default: Globe,
};

const PLATFORM_NAME: Record<Platform, string> = {
  tiktok: "TikTok",
  youtube: "YouTube",
  instagram: "Instagram",
  facebook: "Facebook",
  default: "Platform",
};

function formatFollowers(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function AccountBadgeComponent({
  platform,
  handle,
  followers,
  eligible,
  state = "connected",
  variant = "pill",
  style,
  testID,
}: AccountBadgeProps) {
  const Icon = PLATFORM_ICON[platform];
  const color = tokens.color.semantic.platform[platform];
  const subdued = state === "not-eligible";
  const expired = state === "expired-token";
  const iconColor = subdued ? tokens.color.text.tertiary : color;

  if (variant === "dot") {
    return (
      <View style={[styles.dot, { opacity: subdued ? 0.5 : 1 }, style]} testID={testID}>
        <Icon size={tokens.icon.size.sm} color={iconColor} strokeWidth={tokens.icon.stroke.default} />
        {expired ? (
          <View style={styles.dotWarn}>
            <AlertCircle size={10} color={tokens.color.status.warning} strokeWidth={tokens.icon.stroke.bold} />
          </View>
        ) : null}
      </View>
    );
  }

  const handleText = handle ?? PLATFORM_NAME[platform];

  if (variant === "pill") {
    return (
      <View style={[styles.pill, { opacity: subdued ? 0.6 : 1 }, style]} testID={testID}>
        <Icon size={tokens.icon.size.sm} color={iconColor} strokeWidth={tokens.icon.stroke.default} />
        <Text style={styles.handle} numberOfLines={1}>{handleText}</Text>
        {expired ? <AlertCircle size={tokens.icon.size.xs} color={tokens.color.status.warning} strokeWidth={tokens.icon.stroke.bold} /> : null}
      </View>
    );
  }

  return (
    <View style={[styles.rich, { opacity: subdued ? 0.6 : 1 }, style]} testID={testID}>
      <View style={[styles.richIcon, { backgroundColor: `${color}22`, borderColor: `${color}55` }]}>
        <Icon size={tokens.icon.size.md} color={iconColor} strokeWidth={tokens.icon.stroke.default} />
      </View>
      <View style={styles.richBody}>
        <Text style={styles.richHandle} numberOfLines={1}>{handleText}</Text>
        <View style={styles.richMeta}>
          {typeof followers === "number" ? (
            <Text style={styles.richMetaText}>{formatFollowers(followers)} followers</Text>
          ) : null}
          {eligible === false ? (
            <Text style={[styles.richMetaText, { color: tokens.color.status.warning }]}>Sub-1K — manual entry</Text>
          ) : null}
          {expired ? (
            <Text style={[styles.richMetaText, { color: tokens.color.status.warning }]}>Token expired</Text>
          ) : null}
        </View>
      </View>
    </View>
  );
}

export const AccountBadge = memo(AccountBadgeComponent);

const styles = StyleSheet.create({
  dot: {
    width: 28,
    height: 28,
    borderRadius: tokens.radius.pill,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: tokens.color.bg.raised,
  },
  dotWarn: {
    position: "absolute",
    top: -2,
    right: -2,
    backgroundColor: tokens.color.bg.base,
    borderRadius: tokens.radius.pill,
  },
  pill: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.xs,
    paddingVertical: 4,
    paddingHorizontal: tokens.spacing.sm,
    borderRadius: tokens.radius.pill,
    backgroundColor: tokens.color.bg.raised,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    alignSelf: "flex-start",
  },
  handle: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.primary,
    maxWidth: 140,
  },
  rich: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    paddingHorizontal: tokens.spacing.md,
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.bg.raised,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
  },
  richIcon: {
    width: 44,
    height: 44,
    borderRadius: tokens.radius.md,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
  },
  richBody: {
    flex: 1,
    gap: 2,
  },
  richHandle: {
    fontFamily: tokens.type.scale.h3.family,
    fontSize: tokens.type.scale.h3.size,
    lineHeight: tokens.type.scale.h3.lineHeight,
    color: tokens.color.text.primary,
  },
  richMeta: {
    flexDirection: "row",
    gap: tokens.spacing.sm,
    flexWrap: "wrap",
  },
  richMetaText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
  },
});

export default AccountBadge;
