import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Stack, useRouter, useSegments } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import React, { useEffect } from "react";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import {
  useFonts,
  Inter_400Regular,
  Inter_500Medium,
  Inter_600SemiBold,
  Inter_700Bold,
} from "@expo-google-fonts/inter";
import { View, Platform } from "react-native";

import { tokens } from "@/constants/tokens";
import { useAuthStore } from "@/lib/store";
import { ToastProvider } from "@/components/ToastProvider";

import { ThemeProvider } from "@/components/ThemeProvider";

SplashScreen.preventAutoHideAsync();

const queryClient = new QueryClient();

function AuthGate() {
  const segments = useSegments();
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const hasOnboarded = useAuthStore((s) => s.hasOnboarded);
  const isLoading = useAuthStore((s) => s.isLoading);
  const checkSession = useAuthStore((s) => s.checkSession);

  useEffect(() => {
    checkSession();
  }, []);

  useEffect(() => {
    if (isLoading) return;

    const first = segments[0] as string | undefined;
    const inAuth = first === "(auth)";
    const inApp = first === "(app)";
    const inLanding = first === "landing";

    // On web, allow landing page to be public
    if (Platform.OS === "web" && inLanding) return;

    if (!isAuthenticated && !inAuth && !inLanding) {
      router.replace("/(auth)/welcome");
    } else if (isAuthenticated && !hasOnboarded && !inAuth) {
      router.replace("/(auth)/theme-input");
    } else if (isAuthenticated && hasOnboarded && !inApp) {
      router.replace("/(app)");
    }
  }, [isAuthenticated, hasOnboarded, isLoading, segments, router]);

  if (isLoading) {
    return (
      <View style={{ flex: 1, backgroundColor: tokens.color.bg.base }} />
    );
  }

  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: tokens.color.bg.base },
      }}
    >
      <Stack.Screen name="(auth)" />
      <Stack.Screen name="(app)" />
    </Stack>
  );
}

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
    Inter_700Bold,
  });

  useEffect(() => {
    if (fontsLoaded) SplashScreen.hideAsync();
  }, [fontsLoaded]);

  if (!fontsLoaded) return null;

  return (
    <SafeAreaProvider>
      <GestureHandlerRootView style={{ flex: 1 }}>
        <QueryClientProvider client={queryClient}>
          <ThemeProvider>
            <ToastProvider>
              <AuthGate />
              <StatusBar style="auto" />
            </ToastProvider>
          </ThemeProvider>
        </QueryClientProvider>
      </GestureHandlerRootView>
    </SafeAreaProvider>
  );
}
