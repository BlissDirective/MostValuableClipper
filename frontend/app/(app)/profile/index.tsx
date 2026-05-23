import React, { useCallback, useEffect, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Switch, Text, View, Linking, Alert } from "react-native";
import { useRouter } from "expo-router";
import { useFocusEffect } from "@react-navigation/native";
import { SafeAreaView } from "react-native-safe-area-context";
import {
  ChevronRight,
  CircleHelp,
  CreditCard,
  FileText,
  Link2,
  LucideIcon,
  Settings as SettingsIcon,
  UserRound,
  Bot,
} from "lucide-react-native";

import { tokens } from "@/constants/tokens";
import { ActionButton } from "@/components/ActionButton";
import { AccountBadge, Platform } from "@/components/AccountBadge";
import { useAuthStore, PlatformKey } from "@/lib/store";
import { triggerHaptic } from "@/utils/haptics";

const PLATFORMS: { key: PlatformKey; label: string }[] = [
  { key: "tiktok", label: "TikTok" },
  { key: "instagram", label: "Instagram" },
  { key: "youtube", label: "YouTube" },
];

export default function ProfileScreen() {
  const router = useRouter();
  const doSignOut = useAuthStore((s) => s.doSignOut);
  const user = useAuthStore((s) => s.user);
  const connected = useAuthStore((s) => s.draft.connected);
  const subscriptionTier = useAuthStore((s) => s.subscriptionTier);
  const fetchSubscription = useAuthStore((s) => s.fetchSubscription);
  const fetchSocialAccounts = useAuthStore((s) => s.fetchSocialAccounts);
  const connectPlatform = useAuthStore((s) => s.connectPlatform);
  const disconnectPlatform = useAuthStore((s) => s.disconnectPlatform);
  const socialAccounts = useAuthStore((s) => s.socialAccounts);
  const startOAuth = useAuthStore((s) => s.startOAuth);
  const [showAccounts, setShowAccounts] = useState<boolean>(false);
  const [connecting, setConnecting] = useState<PlatformKey | null>(null);

  useEffect(() => {
    fetchSubscription();
    fetchSocialAccounts();
  }, [fetchSubscription, fetchSocialAccounts]);

  // Refresh social accounts when screen comes into focus
  // (user may have completed OAuth in browser)
  useFocusEffect(
    useCallback(() => {
      fetchSocialAccounts();
    }, [fetchSocialAccounts])
  );

  const onSignOut = useCallback(async () => {
    try {
      await doSignOut();
      router.replace("/(auth)/welcome");
    } catch (err: any) {
      console.error("[profile] sign out error:", err.message);
    }
  }, [doSignOut, router]);

  const handleConnect = useCallback(async (platform: PlatformKey) => {
    if (connected[platform]) {
      // Disconnect
      try {
        triggerHaptic("blockTriggered");
        await disconnectPlatform(platform);
        Alert.alert("Disconnected", `${platform} account has been disconnected.`);
      } catch (err: any) {
        Alert.alert("Error", err.message || `Failed to disconnect ${platform}.`);
      }
      return;
    }

    // Show options: OAuth or Manual
    Alert.alert(
      `Connect ${platform}`,
      "Choose how to connect your account:",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "OAuth (Recommended)",
          onPress: async () => {
            try {
              setConnecting(platform);
              triggerHaptic("blockTriggered");
              const { auth_url } = await startOAuth(platform);
              // User is now in browser — app will refresh accounts when they return
              Alert.alert(
                "Browser Opened",
                `Complete ${platform} authorization in your browser. When you're done, return to this app.`,
                [{ text: "OK", onPress: () => {
                  // Refresh accounts after a delay to catch completed auth
                  setTimeout(() => fetchSocialAccounts(), 3000);
                }}]
              );
            } catch (err: any) {
              Alert.alert("OAuth Failed", err.message || `Could not start ${platform} OAuth.`);
            } finally {
              setConnecting(null);
            }
          },
        },
        {
          text: "Manual Entry",
          onPress: () => {
            // Manual fallback — prompt for handle
            setConnecting(platform);
            Alert.prompt(
              `Connect ${platform}`,
              `Enter your ${platform} handle (e.g., @username):`,
              [
                { text: "Cancel", style: "cancel", onPress: () => setConnecting(null) },
                {
                  text: "Connect",
                  onPress: async (handle?: string) => {
                    if (!handle || handle.trim().length === 0) {
                      setConnecting(null);
                      return;
                    }
                    try {
                      triggerHaptic("blockTriggered");
                      await connectPlatform(platform, handle.trim());
                      Alert.alert("Connected", `${platform} account @${handle.trim()} connected successfully.`);
                    } catch (err: any) {
                      Alert.alert("Connection Failed", err.message || `Could not connect ${platform}.`);
                    } finally {
                      setConnecting(null);
                    }
                  },
                },
              ],
              "plain-text",
              "",
            );
          },
        },
      ]
    );
  }, [connected, startOAuth, connectPlatform, disconnectPlatform, fetchSocialAccounts]);

  const getHandleForPlatform = useCallback((platform: PlatformKey) => {
    const account = socialAccounts.find((a) => a.platform === platform);
    return account?.handle;
  }, [socialAccounts]);

  return (
    <SafeAreaView edges={["top"]} style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <View style={styles.avatar}>
            <UserRound
              size={tokens.icon.size.xl}
              color={tokens.color.text.secondary}
              strokeWidth={tokens.icon.stroke.default}
            />
          </View>
          <Text style={styles.displayName}>{user?.full_name || user?.email || "User"}</Text>
          <Text style={styles.email}>{user?.email || ""}</Text>
          <View style={styles.tierPill}>
            <Text style={styles.tierText}>{subscriptionTier.charAt(0).toUpperCase() + subscriptionTier.slice(1)}</Text>
          </View>
        </View>

        <View style={styles.linkGroup}>
          <LinkRow
            icon={CreditCard}
            label="Subscription & billing"
            onPress={() => router.push("/(app)/profile/billing")}
          />
          <LinkRow
            icon={Link2}
            label={`Connected accounts${showAccounts ? "" : ""}`}
            onPress={() => {
              triggerHaptic("selection");
              setShowAccounts((v) => !v);
            }}
          />
          {showAccounts ? (
            <View style={styles.accountsInline}>
              {PLATFORMS.map((p) => {
                const isConnected = connected[p.key];
                const handle = getHandleForPlatform(p.key);
                return (
                  <View key={p.key} style={styles.accountRow}>
                    <AccountBadge
                      platform={p.key as Platform}
                      handle={isConnected ? handle || "@connected" : undefined}
                      variant={isConnected ? "pill" : "dot"}
                    />
                    <Text style={styles.accountLabel}>{p.label}</Text>
                    <ActionButton
                      label={isConnected ? "Disconnect" : "Connect"}
                      variant={isConnected ? "ghost" : "secondary"}
                      size="sm"
                      onPress={() => handleConnect(p.key)}
                      disabled={connecting === p.key}
                    />
                  </View>
                );
              })}
            </View>
          ) : null}
          <LinkRow
            icon={SettingsIcon}
            label="Settings"
            onPress={() => router.push("/(app)/profile/settings")}
          />
          <LinkRow
            icon={Bot}
            label="Swarm Agents"
            onPress={() => router.push("/(app)/profile/swarm")}
          />
          <LinkRow
            icon={CircleHelp}
            label="Help & support"
            onPress={() => {
              const url = process.env.EXPO_PUBLIC_API_BASE_URL?.replace('/api/v1', '') || 'http://localhost:8000';
              Linking.openURL(`${url}/help`).catch(() => {
                Alert.alert("Help Center", "Visit our help center at support@blissclip.app");
              });
            }}
          />
          <LinkRow
            icon={FileText}
            label="About / Legal"
            onPress={() => {
              const url = process.env.EXPO_PUBLIC_API_BASE_URL?.replace('/api/v1', '') || 'http://localhost:8000';
              Linking.openURL(`${url}/legal/privacy`).catch(() => {
                Alert.alert("Legal", "Privacy policy and terms available in web dashboard.");
              });
            }}
            last
          />
        </View>

        <ActionButton label="Sign out" variant="danger" size="md" fullWidth onPress={onSignOut} />

        <Text style={styles.versionText}>MVC · v0.1.0</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

interface LinkRowProps {
  icon: LucideIcon;
  label: string;
  onPress: () => void;
  last?: boolean;
}

function LinkRow({ icon: Icon, label, onPress, last }: LinkRowProps) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.row,
        !last ? styles.rowDivider : null,
        pressed ? styles.rowPressed : null,
      ]}
      accessibilityRole="button"
    >
      <View style={styles.rowIcon}>
        <Icon
          size={tokens.icon.size.md}
          color={tokens.color.text.secondary}
          strokeWidth={tokens.icon.stroke.default}
        />
      </View>
      <Text style={styles.rowLabel}>{label}</Text>
      <ChevronRight
        size={tokens.icon.size.sm}
        color={tokens.color.text.tertiary}
        strokeWidth={tokens.icon.stroke.default}
      />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: tokens.color.bg.base },
  content: {
    padding: tokens.layout.screenPadding,
    paddingBottom: tokens.spacing.xxl,
    gap: tokens.spacing.lg,
  },
  header: {
    alignItems: "center",
    gap: tokens.spacing.sm,
    paddingTop: tokens.spacing.md,
  },
  avatar: {
    width: 88,
    height: 88,
    borderRadius: tokens.radius.pill,
    backgroundColor: tokens.color.bg.surface,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    alignItems: "center",
    justifyContent: "center",
  },
  displayName: {
    fontFamily: tokens.type.scale.h2.family,
    fontSize: tokens.type.scale.h2.size,
    lineHeight: tokens.type.scale.h2.lineHeight,
    letterSpacing: tokens.type.scale.h2.letterSpacing,
    color: tokens.color.text.primary,
  },
  email: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    color: tokens.color.text.secondary,
  },
  tierPill: {
    marginTop: tokens.spacing.xs,
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: 4,
    borderRadius: tokens.radius.pill,
    backgroundColor: tokens.color.brand.indigo[900],
    borderWidth: 1,
    borderColor: tokens.color.brand.indigo[700],
  },
  tierText: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.brand.indigo[200],
  },
  linkGroup: {
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    overflow: "hidden",
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
    paddingHorizontal: tokens.spacing.md,
    minHeight: tokens.layout.minTouchTarget + 8,
  },
  rowDivider: {
    borderBottomWidth: 1,
    borderBottomColor: tokens.color.border.subtle,
  },
  rowPressed: {
    backgroundColor: tokens.color.bg.elevated,
  },
  rowIcon: {
    width: tokens.icon.size.md + 4,
    alignItems: "center",
  },
  rowLabel: {
    flex: 1,
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.primary,
  },
  accountsInline: {
    backgroundColor: tokens.color.bg.raised,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    gap: tokens.spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: tokens.color.border.subtle,
  },
  accountRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.sm,
  },
  accountLabel: {
    flex: 1,
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    color: tokens.color.text.primary,
  },
  versionText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
    textAlign: "center",
  },
});
