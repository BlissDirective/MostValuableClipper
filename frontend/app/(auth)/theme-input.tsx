import React, { useCallback } from "react";
import { KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, router } from "expo-router";

import { tokens } from "@/constants/tokens";
import { ActionButton } from "@/components/ActionButton";
import { useAuthStore } from "@/lib/store";

export default function ThemeInputScreen() {
  const theme = useAuthStore((s) => s.draft.theme);
  const setTheme = useAuthStore((s) => s.setTheme);
  const canContinue = theme.trim().length >= 3;

  const onContinue = useCallback(() => {
    if (!canContinue) return;
    console.log("[onboarding] theme submitted", theme);
    // CLAUDE_CODE: wire to source-resolution service
    router.push("/(auth)/connect-accounts");
  }, [canContinue, theme]);

  return (
    <View style={styles.root}>
      <Stack.Screen options={{ headerShown: false }} />
      <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
        <KeyboardAvoidingView
          style={styles.flex}
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          keyboardVerticalOffset={tokens.spacing.lg}
        >
          <View style={styles.flex}>
            <Text style={styles.step}>STEP 1 OF 4</Text>
            <Text style={styles.title}>What do you want to clip?</Text>
            <Text style={styles.subtitle}>A creator, a topic, an event. Anything.</Text>

            <TextInput
              value={theme}
              onChangeText={setTheme}
              multiline
              placeholder="e.g. design podcasts, F1 highlights, my own streams"
              placeholderTextColor={tokens.color.text.tertiary}
              style={styles.input}
              autoFocus
              selectionColor={tokens.color.accent.primary}
              accessibilityLabel="Theme input"
            />

            <Text style={styles.note}>We&apos;ll suggest sources after you continue.</Text>
          </View>

          <View style={styles.footer}>
            <ActionButton
              label="Continue"
              variant="primary"
              size="lg"
              fullWidth
              disabled={!canContinue}
              onPress={onContinue}
            />
          </View>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg.base },
  safe: { flex: 1, paddingHorizontal: tokens.layout.screenPadding },
  flex: { flex: 1 },
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
    marginTop: tokens.spacing.sm,
  },
  subtitle: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    lineHeight: tokens.type.scale.bodySmall.lineHeight,
    color: tokens.color.text.secondary,
    marginTop: tokens.spacing.xs,
    marginBottom: tokens.spacing.lg,
  },
  input: {
    minHeight: 120,
    backgroundColor: tokens.color.bg.surface,
    borderWidth: 1,
    borderColor: tokens.color.border.default,
    borderRadius: tokens.radius.lg,
    padding: tokens.spacing.md,
    fontFamily: tokens.type.scale.body.family,
    fontSize: tokens.type.scale.body.size,
    lineHeight: tokens.type.scale.body.lineHeight,
    color: tokens.color.text.primary,
    textAlignVertical: "top",
  },
  note: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
    marginTop: tokens.spacing.sm,
  },
  footer: { paddingVertical: tokens.spacing.md },
});
