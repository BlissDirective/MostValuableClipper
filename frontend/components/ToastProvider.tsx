import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
  useEffect,
} from "react";
import {
  Animated,
  StyleSheet,
  Text,
  View,
} from "react-native";
import {
  CheckCircle2,
  AlertCircle,
  Info,
  XCircle,
  LucideIcon,
} from "lucide-react-native";

import { tokens } from "@/constants/tokens";

type ToastType = "success" | "error" | "warning" | "info";

interface ToastMessage {
  id: string;
  type: ToastType;
  title?: string;
  message: string;
  duration?: number;
}

interface ToastContextValue {
  show: (options: { type: ToastType; title?: string; message: string; duration?: number }) => void;
  success: (message: string, title?: string) => void;
  error: (message: string, title?: string) => void;
  warning: (message: string, title?: string) => void;
  info: (message: string, title?: string) => void;
}

const ToastContext = createContext<ToastContextValue>({
  show: () => {},
  success: () => {},
  error: () => {},
  warning: () => {},
  info: () => {},
});

export const useToast = () => useContext(ToastContext);

const ICONS: Record<ToastType, LucideIcon> = {
  success: CheckCircle2,
  error: XCircle,
  warning: AlertCircle,
  info: Info,
};

const COLORS: Record<ToastType, { bg: string; border: string; icon: string }> = {
  success: {
    bg: tokens.color.status.successBg || "#064e3b",
    border: tokens.color.status.success || "#10b981",
    icon: tokens.color.status.success || "#10b981",
  },
  error: {
    bg: tokens.color.status.dangerBg || "#450a0a",
    border: tokens.color.status.danger || "#ef4444",
    icon: tokens.color.status.danger || "#ef4444",
  },
  warning: {
    bg: tokens.color.status.warningBg || "#422006",
    border: tokens.color.status.warning || "#f59e0b",
    icon: tokens.color.status.warning || "#f59e0b",
  },
  info: {
    bg: tokens.color.status.infoBg || "#172554",
    border: tokens.color.status.info || "#3b82f6",
    icon: tokens.color.status.info || "#3b82f6",
  },
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const show = useCallback(
    ({
      type,
      title,
      message,
      duration = 3000,
    }: {
      type: ToastType;
      title?: string;
      message: string;
      duration?: number;
    }) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      const toast: ToastMessage = { id, type, title, message, duration };
      setToasts((prev) => [...prev, toast]);

      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration + 400); // Extra time for exit animation
    },
    []
  );

  const success = useCallback(
    (message: string, title?: string) => show({ type: "success", title, message }),
    [show]
  );
  const error = useCallback(
    (message: string, title?: string) => show({ type: "error", title, message, duration: 5000 }),
    [show]
  );
  const warning = useCallback(
    (message: string, title?: string) => show({ type: "warning", title, message }),
    [show]
  );
  const info = useCallback(
    (message: string, title?: string) => show({ type: "info", title, message }),
    [show]
  );

  return (
    <ToastContext.Provider value={{ show, success, error, warning, info }}>
      {children}
      <View style={styles.container} pointerEvents="none">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} />
        ))}
      </View>
    </ToastContext.Provider>
  );
}

function ToastItem({ toast }: { toast: ToastMessage }) {
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(-20)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 250,
        useNativeDriver: true,
      }),
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 250,
        useNativeDriver: true,
      }),
    ]).start();

    const hideTimer = setTimeout(() => {
      Animated.parallel([
        Animated.timing(fadeAnim, {
          toValue: 0,
          duration: 200,
          useNativeDriver: true,
        }),
        Animated.timing(slideAnim, {
          toValue: -20,
          duration: 200,
          useNativeDriver: true,
        }),
      ]).start();
    }, toast.duration || 3000);

    return () => clearTimeout(hideTimer);
  }, [toast.id, toast.duration]);

  const colors = COLORS[toast.type];
  const Icon = ICONS[toast.type];

  return (
    <Animated.View
      style={[
        styles.toast,
        {
          backgroundColor: colors.bg,
          borderColor: colors.border,
          opacity: fadeAnim,
          transform: [{ translateY: slideAnim }],
        },
      ]}
    >
      <Icon size={18} color={colors.icon} strokeWidth={2.5} />
      <View style={styles.textBlock}>
        {toast.title ? (
          <Text style={[styles.title, { color: colors.border }]}>{toast.title}</Text>
        ) : null}
        <Text style={styles.message}>{toast.message}</Text>
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: "absolute",
    top: 48,
    left: 0,
    right: 0,
    alignItems: "center",
    zIndex: 9999,
  },
  toast: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.sm,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    marginHorizontal: tokens.spacing.md,
    marginBottom: tokens.spacing.sm,
    maxWidth: 360,
    minWidth: 280,
  },
  textBlock: {
    flex: 1,
    gap: 2,
  },
  title: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    fontWeight: "600",
  },
  message: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    lineHeight: tokens.type.scale.bodySmall.lineHeight,
    color: tokens.color.text.primary,
  },
});
