import * as Haptics from "expo-haptics";
import { Platform } from "react-native";
import { tokens } from "@/constants/tokens";

type HapticName = keyof typeof tokens.haptics;

/**
 * Trigger a named haptic. Maps token names to expo-haptics feedback types.
 * No-op on web.
 */
export function triggerHaptic(name: HapticName): void {
  if (Platform.OS === "web") return;
  const kind = tokens.haptics[name];
  try {
    switch (kind) {
      case "light":
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
        break;
      case "medium":
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
        break;
      case "success":
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        break;
      case "warning":
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
        break;
      case "error":
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
        break;
      default:
        Haptics.selectionAsync();
    }
  } catch {
    // ignore haptic failures
  }
}
