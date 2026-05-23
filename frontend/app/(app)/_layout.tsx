import { Tabs } from "expo-router";
import { Home, GitBranch, LineChart, DollarSign, UserRound, Search } from "lucide-react-native";
import React from "react";

import { tokens } from "@/constants/tokens";

export default function AppTabsLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: tokens.color.brand.indigo[400],
        tabBarInactiveTintColor: tokens.color.text.tertiary,
        tabBarStyle: {
          backgroundColor: tokens.color.bg.raised,
          borderTopColor: tokens.color.border.subtle,
          borderTopWidth: 1,
          height: tokens.layout.tabBarHeight,
          paddingTop: 6,
          paddingBottom: 8,
        },
        tabBarLabelStyle: {
          fontFamily: tokens.type.scale.caption.family,
          fontSize: tokens.type.scale.caption.size,
          letterSpacing: tokens.type.scale.caption.letterSpacing,
        },
        headerStyle: { backgroundColor: tokens.color.bg.base },
        headerTintColor: tokens.color.text.primary,
        headerShadowVisible: false,
        headerTitleStyle: {
          fontFamily: tokens.type.scale.h2.family,
          fontSize: tokens.type.scale.h2.size,
          letterSpacing: tokens.type.scale.h2.letterSpacing,
        },
        sceneStyle: { backgroundColor: tokens.color.bg.base },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Home",
          tabBarIcon: ({ color }) => <Home color={color} size={tokens.icon.size.md} strokeWidth={tokens.icon.stroke.default} />,
        }}
      />
      <Tabs.Screen
        name="content-discovery"
        options={{
          title: "Discover",
          tabBarIcon: ({ color }) => <Search color={color} size={tokens.icon.size.md} strokeWidth={tokens.icon.stroke.default} />,
        }}
      />
      <Tabs.Screen
        name="pipelines"
        options={{
          title: "Pipelines",
          tabBarIcon: ({ color }) => <GitBranch color={color} size={tokens.icon.size.md} strokeWidth={tokens.icon.stroke.default} />,
        }}
      />
      <Tabs.Screen
        name="insights"
        options={{
          title: "Insights",
          tabBarIcon: ({ color }) => <LineChart color={color} size={tokens.icon.size.md} strokeWidth={tokens.icon.stroke.default} />,
        }}
      />
      <Tabs.Screen
        name="earnings"
        options={{
          title: "Earnings",
          tabBarIcon: ({ color }) => <DollarSign color={color} size={tokens.icon.size.md} strokeWidth={tokens.icon.stroke.default} />,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: "Profile",
          tabBarIcon: ({ color }) => <UserRound color={color} size={tokens.icon.size.md} strokeWidth={tokens.icon.stroke.default} />,
        }}
      />
      <Tabs.Screen
        name="clip/[id]"
        options={{
          href: null,
          headerShown: false,
          tabBarStyle: { display: "none" },
        }}
      />
      <Tabs.Screen
        name="pipelines/[id]"
        options={{
          href: null,
          headerShown: false,
          tabBarStyle: { display: "none" },
        }}
      />
      <Tabs.Screen
        name="pipelines/new"
        options={{
          href: null,
          headerShown: false,
          tabBarStyle: { display: "none" },
        }}
      />
      <Tabs.Screen
        name="approval"
        options={{
          href: null,
          headerShown: false,
          tabBarStyle: { display: "none" },
        }}
      />
      <Tabs.Screen
        name="profile/billing"
        options={{
          href: null,
          headerShown: false,
          tabBarStyle: { display: "none" },
        }}
      />
      <Tabs.Screen
        name="profile/swarm"
        options={{
          href: null,
          headerShown: false,
          tabBarStyle: { display: "none" },
        }}
      />
      <Tabs.Screen
        name="profile/settings"
        options={{
          href: null,
          headerShown: false,
          tabBarStyle: { display: "none" },
        }}
      />
      <Tabs.Screen
        name="add-source"
        options={{
          href: null,
          headerShown: false,
          tabBarStyle: { display: "none" },
        }}
      />
      <Tabs.Screen
        name="batch/index"
        options={{
          href: null,
          headerShown: false,
          tabBarStyle: { display: "none" },
        }}
      />
      <Tabs.Screen
        name="batch/[id]"
        options={{
          href: null,
          headerShown: false,
          tabBarStyle: { display: "none" },
        }}
      />
    </Tabs>
  );
}
