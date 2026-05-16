import React from "react";
import { ScrollView, StyleSheet, Switch, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, router } from "expo-router";
import { ShieldCheck } from "lucide-react-native";

import { tokens } from "@/constants/tokens";
import { ActionButton } from "@/components/ActionButton";
import { useAuthStore } from "@/lib/store";
import { triggerHaptic } from "@/utils/haptics";
import { usersApi } from "@/lib/api";

export default function CohortOptInScreen() {
  const cohortOptIn = useAuthStore((s) => s.draft.cohortOptIn);
  const setCohortOptIn = useAuthStore((s) => s.setCohortOptIn);
  const finishOnboarding = useAuthStore((s) => s.finishOnboarding);

  const onToggle = (v: boolean) => {
    triggerHaptic("selection");
    setCohortOptIn(v);
  };

  const onFinish = async () => {
    console.log("[onboarding] finished");
    try {
      await usersApi.updateOnboarding({
        current_step: "cohort-opt-in",
        completed: true,
        data: { cohortOptIn },
      });
    } catch (err: any) {
      console.warn("[onboarding] persist failed:", err.message);
    }
    finishOnboarding();
    router.replace("/(app)");
  };

  return (
    <View style={styles.root}>
      <Stack.Screen options={{ headerShown: false }} />
      <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <Text style={styles.step}>STEP 4 OF 4</Text>
          <Text style={styles.title}>Borrow what&apos;s working from similar pipelines?</Text>
          <Text style={styles.body}>
            Some users let our system apply patterns learned from similar pipelines to give themselves a head start. No raw data is shared between users. You can change this anytime.
          </Text>

          <View style={styles.toggleCard}>
            <View style={styles.toggleIcon}>
              <ShieldCheck size={tokens.icon.size.md} color={tokens.color.accent.secondary} strokeWidth={tokens.icon.stroke.default} />
            </View>
            <View style={styles.toggleBody}>
              <Text style={styles.toggleTitle}>Cohort pattern transfer</Text>
              <Text style={styles.toggleCaption}>
                {cohortOptIn ? "On — analyst will seed from cohort signal." : "Off — analyst starts from your data only."}
              </Text>
            </View>
            <Switch
              value={cohortOptIn}
              onValueChange={onToggle}
              trackColor={{ false: tokens.color.border.default, true: tokens.color.accent.primary }}
              thumbColor={tokens.color.text.onAccent}
              ios_backgroundColor={tokens.color.border.default}
            />
          </View>

          <Text style={styles.fineprint}>
            Privacy: cohort signal is derived from aggregate performance only. Source media, captions, and account handles are never shared with other workspaces.
          </Text>
        </ScrollView>

        <View style={styles.footer}>
          <ActionButton label="Finish setup" variant="primary" size="lg" fullWidth onPress={onFinish} />
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
  body: {
    fontFamily: tokens.type.scale.body.family,
    fontSize: tokens.type.scale.body.size,
    lineHeight: tokens.type.scale.body.lineHeight,
    color: tokens.color.text.secondary,
  },
  toggleCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
    padding: tokens.spacing.md,
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    marginTop: tokens.spacing.sm,
  },
  toggleIcon: {
    width: 40,
    height: 40,
    borderRadius: tokens.radius.md,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: tokens.color.bg.raised,
    borderWidth: 1,
    borderColor: tokens.color.border.default,
  },
  toggleBody: { flex: 1, gap: 2 },
  toggleTitle: {
    fontFamily: tokens.type.scale.h3.family,
    fontSize: tokens.type.scale.h3.size,
    lineHeight: tokens.type.scale.h3.lineHeight,
    color: tokens.color.text.primary,
  },
  toggleCaption: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  fineprint: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
    marginTop: tokens.spacing.md,
  },
  footer: {
    paddingVertical: tokens.spacing.md,
    borderTopWidth: 1,
    borderTopColor: tokens.color.border.subtle,
  },
});
