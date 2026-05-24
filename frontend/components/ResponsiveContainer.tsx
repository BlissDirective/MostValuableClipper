import React from "react";
import { View, StyleSheet, useWindowDimensions, Platform } from "react-native";

interface ResponsiveContainerProps {
  children: React.ReactNode;
  style?: any;
}

export function ResponsiveContainer({ children, style }: ResponsiveContainerProps) {
  const { width } = useWindowDimensions();
  
  // Web-specific responsive breakpoints
  const isWeb = Platform.OS === "web";
  const isDesktop = isWeb && width >= 1024;
  const isTablet = isWeb && width >= 768 && width < 1024;
  
  return (
    <View
      style={[
        styles.container,
        isDesktop && styles.desktopContainer,
        isTablet && styles.tabletContainer,
        style,
      ]}
    >
      <View
        style={[
          styles.content,
          isDesktop && styles.desktopContent,
          isTablet && styles.tabletContent,
        ]}
      >
        {children}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    width: "100%",
    alignItems: "center",
  },
  desktopContainer: {
    paddingHorizontal: 32,
    paddingTop: 24,
    paddingBottom: 24,
    backgroundColor: "#0a0a0f",
  },
  tabletContainer: {
    paddingHorizontal: 16,
    paddingTop: 16,
    backgroundColor: "#0a0a0f",
  },
  content: {
    flex: 1,
    width: "100%",
    maxWidth: 430, // Mobile max width (iPhone Pro Max)
  },
  desktopContent: {
    maxWidth: 1200,
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 24,
  },
  tabletContent: {
    maxWidth: 800,
  },
});
