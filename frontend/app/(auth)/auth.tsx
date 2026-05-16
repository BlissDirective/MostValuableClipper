import React, { useState } from "react";
import { StyleSheet, Text, View, TextInput, Alert } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { LinearGradient } from "expo-linear-gradient";
import { router } from "expo-router";

import { tokens } from "@/constants/tokens";
import { ActionButton } from "@/components/ActionButton";
import { useAuthStore } from "@/lib/store";

export default function AuthScreen() {
  const [isSignUp, setIsSignUp] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const signIn = useAuthStore((s) => s.signIn);
  const signUp = useAuthStore((s) => s.signUp);

  const handleSubmit = async () => {
    if (!email.trim() || !password.trim()) {
      Alert.alert("Missing fields", "Please enter both email and password.");
      return;
    }

    setIsLoading(true);
    try {
      if (isSignUp) {
        await signUp(email.trim(), password.trim(), fullName.trim() || undefined);
      } else {
        await signIn(email.trim(), password.trim());
      }
      router.replace("/(app)");
    } catch (err: any) {
      Alert.alert("Authentication failed", err.message || "Please try again.");
    } finally {
      setIsLoading(false);
    }
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
          <Text style={styles.wordmark}>{isSignUp ? "Create account" : "Welcome back"}</Text>
          <Text style={styles.tagline}>
            {isSignUp
              ? "Start turning themes into clip pipelines."
              : "Sign in to continue managing your pipelines."}
          </Text>
        </View>

        <View style={styles.form}>
          {isSignUp && (
            <TextInput
              style={styles.input}
              placeholder="Full name (optional)"
              placeholderTextColor={tokens.color.text.tertiary}
              value={fullName}
              onChangeText={setFullName}
              autoCapitalize="words"
            />
          )}
          <TextInput
            style={styles.input}
            placeholder="Email"
            placeholderTextColor={tokens.color.text.tertiary}
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            keyboardType="email-address"
            autoComplete="email"
          />
          <TextInput
            style={styles.input}
            placeholder="Password"
            placeholderTextColor={tokens.color.text.tertiary}
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            autoComplete="password"
          />

          <ActionButton
            label={isLoading ? "Please wait…" : isSignUp ? "Create account" : "Sign in"}
            variant="primary"
            size="lg"
            fullWidth
            onPress={handleSubmit}
            disabled={isLoading}
          />

          <ActionButton
            label={isSignUp ? "I already have an account" : "Create a new account"}
            variant="ghost"
            size="md"
            fullWidth
            onPress={() => setIsSignUp(!isSignUp)}
            disabled={isLoading}
          />
        </View>

        <Text style={styles.legal}>
          By continuing you accept the terms of service and privacy policy.
        </Text>
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
    fontSize: 36,
    lineHeight: 44,
    letterSpacing: -1,
    color: tokens.color.text.primary,
    textAlign: "center",
  },
  tagline: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    lineHeight: tokens.type.scale.bodySmall.lineHeight,
    color: tokens.color.text.secondary,
    textAlign: "center",
  },
  form: {
    gap: tokens.spacing.md,
  },
  input: {
    fontFamily: tokens.type.scale.body.family,
    fontSize: tokens.type.scale.body.size,
    color: tokens.color.text.primary,
    backgroundColor: tokens.color.bg.raised,
    borderRadius: tokens.radius.md,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.md,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
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
