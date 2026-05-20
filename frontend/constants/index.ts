import * as Haptics from 'expo-haptics';
import { Platform } from 'react-native';

export const design = {
  colors: {
    bg: '#0f0f0f',
    text: '#ffffff',
    card: '#1a1a1a',
    border: '#2a2a2a',
    primary: '#6366f1',
    muted: '#888888',
    success: '#10b981',
    error: '#ef4444',
    warning: '#f59e0b',
  },
};

const noop = () => {};
const impact = (style: Haptics.ImpactFeedbackStyle) => {
  if (Platform.OS === 'web') return;
  Haptics.impactAsync(style).catch(noop);
};
const notify = (type: Haptics.NotificationFeedbackType) => {
  if (Platform.OS === 'web') return;
  Haptics.notificationAsync(type).catch(noop);
};

export const haptics = {
  light: () => impact(Haptics.ImpactFeedbackStyle.Light),
  medium: () => impact(Haptics.ImpactFeedbackStyle.Medium),
  heavy: () => impact(Haptics.ImpactFeedbackStyle.Heavy),
  success: () => notify(Haptics.NotificationFeedbackType.Success),
  warning: () => notify(Haptics.NotificationFeedbackType.Warning),
  error: () => notify(Haptics.NotificationFeedbackType.Error),
};
