import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { LinearGradient } from "expo-linear-gradient";
import { router } from "expo-router";

import { tokens } from "@/constants/tokens";
import { ActionButton } from "@/components/ActionButton";

export default function WelcomeScreen() {
  const handleCreate = () => {
    console.log("[auth] create account — stub");
    // CLAUDE_CODE: wire to supabase auth signUp
    router.push("/(auth)/theme-input");
  };

  const handleSignIn = () => {
    console.log("[auth] sign in — stub");
    // CLAUDE_CODE: wire to supabase auth signIn
    router.push("/(auth)/theme-input");
  };

  return (
    <View style={styles.root}>
      <LinearGradient
        colors={[tokens.color.bg.base, tokens.color.bg.raised, tokens.color.bg.base]}
        locations={[0, 0.55, 1]}
        style={StyleSheet.absoluteFill}
      />
      <LinearGradient
        colors={[`${tokens.color.brand.indigo[700]}55`, "transparent"]}
        start={{ x: 0.5, y: 0 }}
        end={{ x: 0.5, y: 0.6 }}
        style={StyleSheet.absoluteFill}
      />
      <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
        <View style={styles.brandBlock}>
          <Text style={styles.overline}>MVC</Text>
          <Text style={styles.wordmark}>MVC</Text>
          <Text style={styles.tagline}>Turn any theme into a clip pipeline.</Text>
        </View>

        <View style={styles.actions}>
          <ActionButton label="Create account" variant="primary" size="lg" fullWidth onPress={handleCreate} />
          <ActionButton label="I already have an account" variant="ghost" size="md" fullWidth onPress={handleSignIn} />
          <Text style={styles.legal}>By continuing you accept the analyst-mode terms.</Text>
        </View>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg.base },
  safe: {
    flex: 1,
    paddingHorizontal: tokens.layout.screenPadding,
    paddingTop: tokens.spacing.xxl,
    paddingBottom: tokens.spacing.xl,
    justifyContent: "space-between",
  },
  brandBlock: {
    alignItems: "center",
    gap: tokens.spacing.md,
    paddingTop: tokens.spacing.xxxl,
  },
  overline: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.accent.secondary,
  },
  wordmark: {
    fontFamily: tokens.type.scale.display.family,
    fontSize: 72,
    lineHeight: 80,
    letterSpacing: -2,
    color: tokens.color.text.primary,
  },
  tagline: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    lineHeight: tokens.type.scale.bodySmall.lineHeight,
    color: tokens.color.text.secondary,
    textAlign: "center",
  },
  actions: {
    gap: tokens.spacing.sm,
  },
  legal: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
    textAlign: "center",
    marginTop: tokens.spacing.sm,
  },
});
