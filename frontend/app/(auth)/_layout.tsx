import { Stack } from "expo-router";
import React from "react";
import { tokens } from "@/constants/tokens";

export default function AuthLayout() {
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: tokens.color.bg.base },
        animation: "slide_from_right",
        gestureEnabled: true,
      }}
    />
  );
}
