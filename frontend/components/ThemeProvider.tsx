import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { useColorScheme } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";

export type ThemeMode = "dark" | "light" | "system";

interface ThemeContextValue {
  mode: ThemeMode;
  resolvedMode: "dark" | "light";
  setMode: (mode: ThemeMode) => void;
  isDark: boolean;
}

const ThemeContext = createContext<ThemeContextValue>({
  mode: "dark",
  resolvedMode: "dark",
  setMode: () => {},
  isDark: true,
});

export const useTheme = () => useContext(ThemeContext);

const STORAGE_KEY = "mvc_theme_mode";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const systemScheme = useColorScheme();
  const [mode, setModeState] = useState<ThemeMode>("system");

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY).then((stored) => {
      if (stored === "dark" || stored === "light" || stored === "system") {
        setModeState(stored);
      }
    });
  }, []);

  const setMode = useCallback((newMode: ThemeMode) => {
    setModeState(newMode);
    AsyncStorage.setItem(STORAGE_KEY, newMode);
  }, []);

  const resolvedMode: "dark" | "light" =
    mode === "system" ? (systemScheme ?? "dark") : mode;

  const isDark = resolvedMode === "dark";

  return (
    <ThemeContext.Provider value={{ mode, resolvedMode, setMode, isDark }}>
      {children}
    </ThemeContext.Provider>
  );
}
