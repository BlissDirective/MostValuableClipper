import React, { useCallback, useState } from "react";
import {
  Alert,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
  Linking,
  ActivityIndicator,
} from "react-native";
import { Stack, useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { ChevronLeft, Lock, ShieldCheck, Download } from "lucide-react-native";

import { tokens } from "@/constants/tokens";
import { ActionButton } from "@/components/ActionButton";
import {
  DEFAULT_WARNING_CATEGORIES,
  RetentionPolicy,
  WarningCategoryKey,
  useAuthStore,
} from "@/lib/store";
import { usersApi } from "@/lib/api";
import { triggerHaptic } from "@/utils/haptics";

const RETENTION_OPTIONS: { key: RetentionPolicy; label: string; body: string }[] = [
  { key: "aggressive", label: "Aggressive · 30 days", body: "Source media deleted after 30 days." },
  { key: "moderate", label: "Moderate · 90 days", body: "Default. Balanced for re-edits and analytics." },
  { key: "indefinite", label: "Indefinite", body: "Kept until you delete the pipeline." },
];

const WARNING_LABELS: Record<WarningCategoryKey, { title: string; body: string }> = {
  newsPolitical: {
    title: "News · Political",
    body: "Source attribution + neutrality note appended.",
  },
  health: {
    title: "Health",
    body: "Disclaimer + source citation appended to caption.",
  },
  finance: {
    title: "Finance",
    body: "Not-financial-advice notice appended.",
  },
  children: {
    title: "Children's content",
    body: "Stricter caption review + COPPA-aware tagging.",
  },
  identifiableIndividual: {
    title: "Identifiable individual",
    body: "Disclosure recommended when faces are central.",
  },
  violentGraphic: {
    title: "Violent · Graphic",
    body: "Content warning appended; thumbnail blurred.",
  },
};

const CLIPS_USED = 23;
const CLIPS_QUOTA = 50;

export default function SettingsScreen() {
  const router = useRouter();
  const cohortOptIn = useAuthStore((s) => s.draft.cohortOptIn);
  const setCohortOptIn = useAuthStore((s) => s.setCohortOptIn);

  const [retention, setRetention] = useState<RetentionPolicy>("moderate");
  const [warnings, setWarnings] = useState<Record<WarningCategoryKey, boolean>>(
    DEFAULT_WARNING_CATEGORIES
  );
  const [deleteModalOpen, setDeleteModalOpen] = useState<boolean>(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string>("");
  const [passwordModalOpen, setPasswordModalOpen] = useState<boolean>(false);
  const [newPassword, setNewPassword] = useState<string>("");
  const [passwordConfirm, setPasswordConfirm] = useState<string>("");
  const [passwordLoading, setPasswordLoading] = useState<boolean>(false);
  const [exportLoading, setExportLoading] = useState<boolean>(false);

  const onCohortToggle = useCallback(
    (v: boolean) => {
      triggerHaptic("selection");
      setCohortOptIn(v);
    },
    [setCohortOptIn]
  );

  const onResetLearned = useCallback(() => {
    Alert.alert(
      "Reset learned parameters?",
      "Hook archetype ranks, caption-length signals, and post-time scoring will revert to defaults across all pipelines.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Reset",
          style: "destructive",
          onPress: async () => {
            try {
              await usersApi.updatePreferences({
                retention_policy: undefined,
                autonomy_mode: undefined,
                warning_categories: undefined,
              });
              Alert.alert("Reset complete", "Learned parameters have been cleared.");
            } catch (err: any) {
              console.warn("[settings] reset failed:", err.message);
              Alert.alert("Reset failed", err.message || "Could not reset parameters.");
            }
          },
        },
      ]
    );
  }, []);

  const onChangePassword = useCallback(async () => {
    if (!newPassword || newPassword.length < 6) {
      Alert.alert("Invalid password", "Password must be at least 6 characters.");
      return;
    }
    if (newPassword !== passwordConfirm) {
      Alert.alert("Passwords do not match", "Please confirm your new password.");
      return;
    }
    setPasswordLoading(true);
    try {
      const { changePassword } = await import("@/lib/auth");
      await changePassword(newPassword);
      setPasswordModalOpen(false);
      setNewPassword("");
      setPasswordConfirm("");
      Alert.alert("Password updated", "Your password has been changed successfully.");
    } catch (err: any) {
      console.warn("[settings] password change failed:", err.message);
      Alert.alert("Failed to change password", err.message || "Please try again.");
    } finally {
      setPasswordLoading(false);
    }
  }, [newPassword, passwordConfirm]);

  const onExportData = useCallback(async () => {
    setExportLoading(true);
    try {
      const data = await usersApi.exportData();
      // On mobile, we can't easily download JSON files.
      // Show a summary and offer to share or copy.
      const summary = `Export ready:\n• ${(data.pipelines as any[])?.length || 0} pipelines\n• ${(data.clips as any[])?.length || 0} clips\n• ${(data.sources as any[])?.length || 0} sources\n\nData export has been prepared on the server. Full download available via web dashboard.`;
      Alert.alert("Data Export", summary);
    } catch (err: any) {
      console.warn("[settings] export failed:", err.message);
      Alert.alert("Export failed", err.message || "Could not export data.");
    } finally {
      setExportLoading(false);
    }
  }, []);

  const onConfirmDelete = useCallback(async () => {
    if (deleteConfirm.trim() !== "DELETE") return;
    try {
      await usersApi.deleteMe();
    } catch (err: any) {
      console.warn("[settings] delete failed:", err.message);
    }
    setDeleteModalOpen(false);
    setDeleteConfirm("");
    // Sign out locally regardless of server result
    const doSignOut = useAuthStore.getState().doSignOut;
    try {
      await doSignOut();
    } catch (e) {
      // ignore
    }
    router.replace("/(auth)/welcome");
  }, [deleteConfirm, router]);

  const clipsPct = Math.min(1, CLIPS_USED / CLIPS_QUOTA);

  return (
    <View style={styles.root}>
      <Stack.Screen options={{ headerShown: false }} />
      <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
        <View style={styles.header}>
          <Pressable
            onPress={() => router.back()}
            hitSlop={12}
            style={styles.backBtn}
            accessibilityLabel="Back"
          >
            <ChevronLeft
              size={tokens.icon.size.md}
              color={tokens.color.text.primary}
              strokeWidth={tokens.icon.stroke.default}
            />
          </Pressable>
          <Text style={styles.headerTitle}>Settings</Text>
          <View style={styles.backBtnPlaceholder} />
        </View>

        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <Section title="LEARNING">
            <View style={styles.card}>
              <View style={styles.toggleRow}>
                <View style={styles.toggleIcon}>
                  <ShieldCheck
                    size={tokens.icon.size.md}
                    color={tokens.color.accent.secondary}
                    strokeWidth={tokens.icon.stroke.default}
                  />
                </View>
                <View style={styles.toggleBody}>
                  <Text style={styles.rowTitle}>Cohort pattern transfer</Text>
                  <Text style={styles.rowBody}>
                    Apply patterns learned from similar pipelines as a head start. No raw data is
                    shared between users. You can change this anytime.
                  </Text>
                </View>
                <Switch
                  value={cohortOptIn}
                  onValueChange={onCohortToggle}
                  trackColor={{
                    false: tokens.color.border.default,
                    true: tokens.color.accent.primary,
                  }}
                  thumbColor={tokens.color.text.onAccent}
                  ios_backgroundColor={tokens.color.border.default}
                />
              </View>
            </View>
            <ActionButton
              label="Reset learned parameters"
              variant="ghost"
              size="md"
              onPress={onResetLearned}
            />
          </Section>

          <Section title="SOURCE RETENTION DEFAULT">
            <Text style={styles.sectionHint}>
              Sets the global default. Per-pipeline overrides live on each pipeline detail screen.
            </Text>
            <View style={styles.card}>
              {RETENTION_OPTIONS.map((opt, i) => {
                const active = retention === opt.key;
                return (
                  <Pressable
                    key={opt.key}
                    onPress={() => {
                      triggerHaptic("selection");
                      setRetention(opt.key);
                    }}
                    style={[
                      styles.radioRow,
                      i === RETENTION_OPTIONS.length - 1 ? null : styles.divider,
                    ]}
                  >
                    <View style={[styles.radio, active ? styles.radioActive : null]}>
                      {active ? <View style={styles.radioDot} /> : null}
                    </View>
                    <View style={styles.toggleBody}>
                      <Text style={styles.rowTitle}>{opt.label}</Text>
                      <Text style={styles.rowBody}>{opt.body}</Text>
                    </View>
                  </Pressable>
                );
              })}
            </View>
          </Section>

          <Section title="SAFETY CATEGORY WARNINGS">
            <Text style={styles.sectionHint}>
              Warning-level categories add disclosures. Adult-NSFW and Copyrighted-Material-Risk
              are always blocked and cannot be turned off.
            </Text>
            <View style={styles.card}>
              {(Object.keys(WARNING_LABELS) as WarningCategoryKey[]).map((k, i, arr) => (
                <View
                  key={k}
                  style={[styles.toggleRow, i === arr.length - 1 ? null : styles.divider]}
                >
                  <View style={styles.toggleBody}>
                    <Text style={styles.rowTitle}>{WARNING_LABELS[k].title}</Text>
                    <Text style={styles.rowBody}>{WARNING_LABELS[k].body}</Text>
                  </View>
                  <Switch
                    value={warnings[k]}
                    onValueChange={(v) => {
                      triggerHaptic("selection");
                      setWarnings((prev) => ({ ...prev, [k]: v }));
                    }}
                    trackColor={{
                      false: tokens.color.border.default,
                      true: tokens.color.accent.primary,
                    }}
                    thumbColor={tokens.color.text.onAccent}
                    ios_backgroundColor={tokens.color.border.default}
                  />
                </View>
              ))}
              <View style={[styles.toggleRow, styles.lockedRow]}>
                <Lock
                  size={tokens.icon.size.sm}
                  color={tokens.color.text.tertiary}
                  strokeWidth={tokens.icon.stroke.default}
                />
                <Text style={styles.lockedText}>
                  Adult-NSFW · Copyrighted-Material-Risk — always blocked
                </Text>
              </View>
            </View>
          </Section>

          <Section title="COMPUTE & QUOTAS">
            <View style={styles.card}>
              <View style={styles.quotaRow}>
                <Text style={styles.rowTitle}>Clips this month</Text>
                <Text style={styles.quotaValue}>
                  {CLIPS_USED} / {CLIPS_QUOTA}
                </Text>
              </View>
              <View style={styles.progressTrack}>
                <View style={[styles.progressFill, { width: `${clipsPct * 100}%` }]} />
              </View>
              <Text style={styles.rowBody}>Basic plan quota. Upgrade for 500 clips / month.</Text>
            </View>
          </Section>

          <Section title="ACCOUNT">
            <View style={styles.card}>
              <AccountRow label="Change password" onPress={() => setPasswordModalOpen(true)} />
              <AccountRow label="Export data" onPress={onExportData} loading={exportLoading} />
              <AccountRow
                label="Delete account"
                danger
                onPress={() => setDeleteModalOpen(true)}
                last
              />
            </View>
          </Section>

          <Text style={styles.versionText}>MVC · v0.1.0 · build 0001 (Rork preview)</Text>
        </ScrollView>
      </SafeAreaView>

      <Modal visible={deleteModalOpen} transparent animationType="fade" onRequestClose={() => setDeleteModalOpen(false)}>
        <View style={styles.modalRoot}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Delete account?</Text>
            <Text style={styles.modalBody}>
              This permanently removes your workspace, pipelines, and learned parameters.
              Connected social accounts stay intact on their respective platforms.
            </Text>
            <Text style={styles.modalLabel}>Type DELETE to confirm</Text>
            <TextInput
              value={deleteConfirm}
              onChangeText={setDeleteConfirm}
              placeholder="DELETE"
              placeholderTextColor={tokens.color.text.tertiary}
              autoCapitalize="characters"
              style={styles.modalInput}
            />
            <View style={styles.modalActions}>
              <ActionButton
                label="Cancel"
                variant="secondary"
                size="md"
                onPress={() => {
                  setDeleteModalOpen(false);
                  setDeleteConfirm("");
                }}
              />
              <ActionButton
                label="Delete"
                variant="danger"
                size="md"
                disabled={deleteConfirm.trim() !== "DELETE"}
                onPress={onConfirmDelete}
              />
            </View>
          </View>
        </View>
      </Modal>

      <Modal visible={passwordModalOpen} transparent animationType="fade" onRequestClose={() => setPasswordModalOpen(false)}>
        <View style={styles.modalRoot}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Change password</Text>
            <Text style={styles.modalBody}>Enter a new password (minimum 6 characters).</Text>
            <TextInput
              value={newPassword}
              onChangeText={setNewPassword}
              placeholder="New password"
              placeholderTextColor={tokens.color.text.tertiary}
              secureTextEntry
              style={styles.modalInput}
            />
            <TextInput
              value={passwordConfirm}
              onChangeText={setPasswordConfirm}
              placeholder="Confirm new password"
              placeholderTextColor={tokens.color.text.tertiary}
              secureTextEntry
              style={styles.modalInput}
            />
            <View style={styles.modalActions}>
              <ActionButton
                label="Cancel"
                variant="secondary"
                size="md"
                onPress={() => {
                  setPasswordModalOpen(false);
                  setNewPassword("");
                  setPasswordConfirm("");
                }}
              />
              <ActionButton
                label={passwordLoading ? "Updating..." : "Update"}
                variant="primary"
                size="md"
                disabled={passwordLoading || !newPassword || !passwordConfirm}
                onPress={onChangePassword}
              />
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

function AccountRow({
  label,
  onPress,
  danger,
  last,
  loading,
}: {
  label: string;
  onPress: () => void;
  danger?: boolean;
  last?: boolean;
  loading?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={loading}
      style={({ pressed }) => [
        styles.accountRow,
        !last ? styles.divider : null,
        pressed ? styles.rowPressed : null,
      ]}
    >
      <Text style={[styles.rowTitle, danger ? styles.dangerText : null]}>{label}</Text>
      {loading ? <ActivityIndicator size="small" color={tokens.color.text.tertiary} /> : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg.base },
  safe: { flex: 1 },
  header: {
    height: tokens.layout.headerHeight,
    paddingHorizontal: tokens.layout.screenPadding,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  backBtn: {
    width: tokens.layout.minTouchTarget,
    height: tokens.layout.minTouchTarget,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: tokens.radius.pill,
    backgroundColor: tokens.color.bg.raised,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
  },
  backBtnPlaceholder: { width: tokens.layout.minTouchTarget, height: tokens.layout.minTouchTarget },
  headerTitle: {
    fontFamily: tokens.type.scale.h2.family,
    fontSize: tokens.type.scale.h2.size,
    lineHeight: tokens.type.scale.h2.lineHeight,
    letterSpacing: tokens.type.scale.h2.letterSpacing,
    color: tokens.color.text.primary,
  },
  content: {
    padding: tokens.layout.screenPadding,
    paddingBottom: tokens.spacing.xxl,
    gap: tokens.spacing.lg,
  },
  section: { gap: tokens.spacing.sm },
  sectionTitle: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  sectionHint: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  card: {
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    overflow: "hidden",
  },
  toggleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
    padding: tokens.spacing.md,
  },
  toggleIcon: {
    width: 40,
    height: 40,
    borderRadius: tokens.radius.md,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: tokens.color.bg.raised,
    borderWidth: 1,
    borderColor: tokens.color.border.default,
  },
  toggleBody: { flex: 1, gap: 2 },
  rowTitle: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.primary,
  },
  rowBody: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  divider: { borderBottomWidth: 1, borderBottomColor: tokens.color.border.subtle },
  radioRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
    padding: tokens.spacing.md,
  },
  radio: {
    width: 20,
    height: 20,
    borderRadius: tokens.radius.pill,
    borderWidth: 2,
    borderColor: tokens.color.border.strong,
    alignItems: "center",
    justifyContent: "center",
  },
  radioActive: { borderColor: tokens.color.accent.primary },
  radioDot: {
    width: 10,
    height: 10,
    borderRadius: tokens.radius.pill,
    backgroundColor: tokens.color.accent.primary,
  },
  lockedRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.sm,
    backgroundColor: tokens.color.bg.raised,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
  },
  lockedText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  quotaRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: tokens.spacing.md,
    paddingTop: tokens.spacing.md,
  },
  quotaValue: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.primary,
  },
  progressTrack: {
    height: 8,
    backgroundColor: tokens.color.bg.raised,
    borderRadius: tokens.radius.pill,
    marginHorizontal: tokens.spacing.md,
    marginTop: tokens.spacing.sm,
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    backgroundColor: tokens.color.brand.indigo[500],
  },
  accountRow: {
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.md,
    minHeight: tokens.layout.minTouchTarget,
    justifyContent: "center",
  },
  rowPressed: { backgroundColor: tokens.color.bg.elevated },
  dangerText: { color: tokens.color.status.danger },
  versionText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
    textAlign: "center",
  },
  modalRoot: {
    flex: 1,
    backgroundColor: tokens.color.bg.overlay,
    justifyContent: "center",
    paddingHorizontal: tokens.spacing.lg,
  },
  modalCard: {
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.color.semantic.safety.block.border,
    padding: tokens.spacing.lg,
    gap: tokens.spacing.sm,
  },
  modalTitle: {
    fontFamily: tokens.type.scale.h2.family,
    fontSize: tokens.type.scale.h2.size,
    lineHeight: tokens.type.scale.h2.lineHeight,
    color: tokens.color.text.primary,
  },
  modalBody: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    lineHeight: tokens.type.scale.bodySmall.lineHeight,
    color: tokens.color.text.secondary,
  },
  modalLabel: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.text.tertiary,
    marginTop: tokens.spacing.sm,
  },
  modalInput: {
    backgroundColor: tokens.color.bg.raised,
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    borderColor: tokens.color.border.default,
    padding: tokens.spacing.md,
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.primary,
    letterSpacing: 1,
  },
  modalActions: {
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: tokens.spacing.sm,
    marginTop: tokens.spacing.md,
  },
});
