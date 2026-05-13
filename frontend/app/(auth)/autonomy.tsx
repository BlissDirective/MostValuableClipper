import React from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, router } from "expo-router";
import { Zap, Hand, Pencil, LucideIcon } from "lucide-react-native";

import { tokens } from "@/constants/tokens";
import { ActionButton } from "@/components/ActionButton";
import { AutonomyMode, useAuthStore } from "@/lib/store";
import { triggerHaptic } from "@/utils/haptics";

interface OptionConfig {
  key: AutonomyMode;
  title: string;
  body: string;
  icon: LucideIcon;
  tint: string;
}

const OPTIONS: OptionConfig[] = [
  {
    key: "fullAuto",
    title: "Full Auto",
    body: "Clips are generated and posted on schedule. The analyst flags only safety holds.",
    icon: Zap,
    tint: tokens.color.semantic.autonomy.fullAuto,
  },
  {
    key: "approveEach",
    title: "Approve Each Post",
    body: "Every clip enters the approval queue. You approve, edit, or reject before anything ships.",
    icon: Hand,
    tint: tokens.color.semantic.autonomy.approveEach,
  },
  {
    key: "suggestOnly",
    title: "Suggest Only",
    body: "The analyst proposes clips and posting windows. You generate and publish manually.",
    icon: Pencil,
    tint: tokens.color.semantic.autonomy.suggestOnly,
  },
];

export default function AutonomyScreen() {
  const autonomy = useAuthStore((s) => s.draft.autonomy);
  const setAutonomy = useAuthStore((s) => s.setAutonomy);

  const select = (mode: AutonomyMode) => {
    triggerHaptic("selection");
    setAutonomy(mode);
  };

  return (
    <View style={styles.root}>
      <Stack.Screen options={{ headerShown: false }} />
      <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <Text style={styles.step}>STEP 3 OF 4</Text>
          <Text style={styles.title}>How hands-on do you want to be?</Text>
          <Text style={styles.subtitle}>You can change this for any pipeline later.</Text>

          <View style={styles.list}>
            {OPTIONS.map((o) => {
              const selected = autonomy === o.key;
              const Icon = o.icon;
              return (
                <Pressable
                  key={o.key}
                  onPress={() => select(o.key)}
                  accessibilityRole="radio"
                  accessibilityState={{ selected }}
                  style={[
                    styles.card,
                    selected && {
                      borderColor: tokens.color.brand.indigo[400],
                      backgroundColor: tokens.color.bg.elevated,
                      ...tokens.elevation[2],
                      shadowColor: tokens.color.brand.indigo[500],
                    },
                  ]}
                >
                  <View style={[styles.cardIcon, { backgroundColor: `${o.tint}1F`, borderColor: `${o.tint}66` }]}>
                    <Icon size={tokens.icon.size.lg} color={o.tint} strokeWidth={tokens.icon.stroke.default} />
                  </View>
                  <View style={styles.cardBody}>
                    <Text style={styles.cardTitle}>{o.title}</Text>
                    <Text style={styles.cardText}>{o.body}</Text>
                  </View>
                  <View
                    style={[
                      styles.radio,
                      selected && { borderColor: tokens.color.brand.indigo[400], backgroundColor: tokens.color.brand.indigo[400] },
                    ]}
                  >
                    {selected ? <View style={styles.radioDot} /> : null}
                  </View>
                </Pressable>
              );
            })}
          </View>
        </ScrollView>

        <View style={styles.footer}>
          <ActionButton
            label="Continue"
            variant="primary"
            size="lg"
            fullWidth
            onPress={() => router.push("/(auth)/cohort-opt-in")}
          />
        </View>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg.base },
  safe: { flex: 1, paddingHorizontal: tokens.layout.screenPadding },
  content: { paddingBottom: tokens.spacing.xl, gap: tokens.spacing.sm },
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
  list: { gap: tokens.spacing.md },
  card: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
    padding: tokens.spacing.md,
    borderRadius: tokens.radius.lg,
    borderWidth: 2,
    borderColor: tokens.color.border.default,
    backgroundColor: tokens.color.bg.surface,
  },
  cardIcon: {
    width: 48,
    height: 48,
    borderRadius: tokens.radius.md,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
  },
  cardBody: { flex: 1, gap: tokens.spacing.xs },
  cardTitle: {
    fontFamily: tokens.type.scale.h2.family,
    fontSize: tokens.type.scale.h2.size,
    lineHeight: tokens.type.scale.h2.lineHeight,
    letterSpacing: tokens.type.scale.h2.letterSpacing,
    color: tokens.color.text.primary,
  },
  cardText: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    lineHeight: tokens.type.scale.bodySmall.lineHeight,
    color: tokens.color.text.secondary,
  },
  radio: {
    width: 22,
    height: 22,
    borderRadius: tokens.radius.pill,
    borderWidth: 2,
    borderColor: tokens.color.border.strong,
    alignItems: "center",
    justifyContent: "center",
  },
  radioDot: {
    width: 8,
    height: 8,
    borderRadius: tokens.radius.pill,
    backgroundColor: tokens.color.text.onAccent,
  },
  footer: {
    paddingVertical: tokens.spacing.md,
    borderTopWidth: 1,
    borderTopColor: tokens.color.border.subtle,
  },
});
