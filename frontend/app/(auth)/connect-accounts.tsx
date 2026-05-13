import React from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, router } from "expo-router";
import { Music2, Youtube, Instagram, LucideIcon, Check } from "lucide-react-native";

import { tokens } from "@/constants/tokens";
import { ActionButton } from "@/components/ActionButton";
import { AccountBadge } from "@/components/AccountBadge";
import { PlatformKey, useAuthStore } from "@/lib/store";

interface PlatformRowConfig {
  key: PlatformKey;
  name: string;
  icon: LucideIcon;
}

const PLATFORMS: PlatformRowConfig[] = [
  { key: "tiktok", name: "TikTok", icon: Music2 },
  { key: "instagram", name: "Instagram", icon: Instagram },
  { key: "youtube", name: "YouTube", icon: Youtube },
];

export default function ConnectAccountsScreen() {
  const connected = useAuthStore((s) => s.draft.connected);
  const togglePlatform = useAuthStore((s) => s.togglePlatform);

  const onConnect = (p: PlatformKey) => {
    console.log("[onboarding] toggle platform", p);
    // CLAUDE_CODE: wire to OAuth platform connect service
    togglePlatform(p);
  };

  const goNext = () => router.push("/(auth)/autonomy");

  return (
    <View style={styles.root}>
      <Stack.Screen options={{ headerShown: false }} />
      <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <Text style={styles.step}>STEP 2 OF 4</Text>
          <Text style={styles.title}>Connect where you&apos;ll post.</Text>
          <Text style={styles.subtitle}>You can add more later. All accounts are optional during setup.</Text>

          <View style={styles.list}>
            {PLATFORMS.map((p) => {
              const isConnected = connected[p.key];
              const color = tokens.color.semantic.platform[p.key];
              const Icon = p.icon;
              return (
                <View key={p.key} style={styles.row}>
                  <View style={[styles.icon, { backgroundColor: `${color}1A`, borderColor: `${color}55` }]}>
                    <Icon size={tokens.icon.size.md} color={color} strokeWidth={tokens.icon.stroke.default} />
                  </View>
                  <View style={styles.rowBody}>
                    <Text style={styles.rowTitle}>{p.name}</Text>
                    <Text style={styles.rowCaption}>Required for posting.</Text>
                  </View>
                  {isConnected ? (
                    <View style={styles.connected}>
                      <AccountBadge platform={p.key} handle={`@analyst.${p.key}`} variant="pill" />
                    </View>
                  ) : (
                    <ActionButton
                      label="Connect"
                      variant="secondary"
                      size="sm"
                      onPress={() => onConnect(p.key)}
                    />
                  )}
                  {isConnected ? (
                    <View style={styles.checkBadge}>
                      <Check size={tokens.icon.size.xs} color={tokens.color.status.success} strokeWidth={tokens.icon.stroke.bold} />
                    </View>
                  ) : null}
                </View>
              );
            })}
          </View>

          <ActionButton
            label="Skip for now"
            variant="ghost"
            size="md"
            onPress={goNext}
          />
        </ScrollView>

        <View style={styles.footer}>
          <ActionButton label="Continue" variant="primary" size="lg" fullWidth onPress={goNext} />
        </View>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg.base },
  safe: { flex: 1, paddingHorizontal: tokens.layout.screenPadding },
  content: { paddingBottom: tokens.spacing.xl, gap: tokens.spacing.md },
  step: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.accent.secondary,
    marginTop: tokens.spacing.md,
  },
  title: {
    fontFamily: tokens.type.scale.h1.family,
    fontSize: tokens.type.scale.h1.size,
    lineHeight: tokens.type.scale.h1.lineHeight,
    letterSpacing: tokens.type.scale.h1.letterSpacing,
    color: tokens.color.text.primary,
  },
  subtitle: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    lineHeight: tokens.type.scale.bodySmall.lineHeight,
    color: tokens.color.text.secondary,
    marginBottom: tokens.spacing.md,
  },
  list: {
    gap: tokens.spacing.sm,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
    padding: tokens.spacing.md,
    backgroundColor: tokens.color.bg.surface,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    borderRadius: tokens.radius.lg,
  },
  icon: {
    width: 44,
    height: 44,
    borderRadius: tokens.radius.md,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
  },
  rowBody: { flex: 1, gap: 2 },
  rowTitle: {
    fontFamily: tokens.type.scale.h3.family,
    fontSize: tokens.type.scale.h3.size,
    lineHeight: tokens.type.scale.h3.lineHeight,
    color: tokens.color.text.primary,
  },
  rowCaption: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  connected: {
    alignItems: "flex-end",
  },
  checkBadge: {
    width: 22,
    height: 22,
    borderRadius: tokens.radius.pill,
    backgroundColor: tokens.color.status.successBg,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: tokens.color.status.success,
  },
  footer: {
    paddingVertical: tokens.spacing.md,
    borderTopWidth: 1,
    borderTopColor: tokens.color.border.subtle,
  },
});
