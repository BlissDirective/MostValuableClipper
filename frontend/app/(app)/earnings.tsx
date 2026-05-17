import React, { useEffect, useMemo, useState } from "react";
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import {
  ArrowUpRight,
  Briefcase,
  Pencil,
  X,
} from "lucide-react-native";

import { tokens } from "@/constants/tokens";
import { ActionButton } from "@/components/ActionButton";
import { AccountBadge, Platform as AccountPlatform } from "@/components/AccountBadge";
import { InsightTile } from "@/components/InsightTile";
import { MetricChip } from "@/components/MetricChip";
import { useAuthStore, type PlatformKey } from "@/lib/store";
import { triggerHaptic } from "@/utils/haptics";

type Period = "7d" | "30d" | "all";

const PERIODS: { key: Period; label: string }[] = [
  { key: "7d", label: "7d" },
  { key: "30d", label: "30d" },
  { key: "all", label: "All time" },
];

const TOTAL_BY_PERIOD: Record<Period, { total: string; delta: string; variant: "positive" | "negative" | "default" }> = {
  "7d": { total: "$48", delta: "+12%", variant: "positive" },
  "30d": { total: "$214", delta: "+8%", variant: "positive" },
  all: { total: "$1,612", delta: "—", variant: "default" },
};

interface PlatformEarning {
  platform: AccountPlatform;
  handle: string;
  amount: string;
  cpm: string;
  spark: number[];
}

const PLATFORM_EARNINGS: PlatformEarning[] = [
  {
    platform: "tiktok",
    handle: "@studio",
    amount: "$112",
    cpm: "$0.48 CPM",
    spark: [0.3, 0.4, 0.55, 0.5, 0.7, 0.8, 0.95],
  },
  {
    platform: "youtube",
    handle: "@studio",
    amount: "$84",
    cpm: "$1.92 CPM",
    spark: [0.5, 0.45, 0.6, 0.7, 0.65, 0.8, 0.75],
  },
  {
    platform: "instagram",
    handle: "@studio",
    amount: "$18",
    cpm: "Manual entry",
    spark: [0.2, 0.25, 0.18, 0.3, 0.28, 0.35, 0.3],
  },
];

interface ManualEntry {
  accountId: string;
  clipId: string;
  views: string;
  likes: string;
  comments: string;
  shares: string;
}

const DEFAULT_ENTRY: ManualEntry = {
  accountId: "ig-studio",
  clipId: "",
  views: "",
  likes: "",
  comments: "",
  shares: "",
};

export default function EarningsScreen() {
  const pipelines = useAuthStore((s) => s.pipelines);
  const earningsSummary = useAuthStore((s) => s.earningsSummary);
  const socialAccounts = useAuthStore((s) => s.socialAccounts);
  const fetchEarnings = useAuthStore((s) => s.fetchEarnings);
  const fetchSocialAccounts = useAuthStore((s) => s.fetchSocialAccounts);
  const [period, setPeriod] = useState<Period>("30d");
  const [manualOpen, setManualOpen] = useState<boolean>(false);
  const [entry, setEntry] = useState<ManualEntry>(DEFAULT_ENTRY);

  useEffect(() => {
    fetchEarnings();
    fetchSocialAccounts();
  }, [fetchEarnings, fetchSocialAccounts]);

  const headline = TOTAL_BY_PERIOD[period];

  const clipOptions = useMemo(
    () =>
      pipelines.slice(0, 3).map((p, i) => ({
        id: `clip-${p.id}-${i}`,
        label: `${p.themeName} · clip ${i + 1}`,
      })),
    [pipelines]
  );

  const onSubmitManual = () => {
    triggerHaptic("approve");
    setManualOpen(false);
    setEntry(DEFAULT_ENTRY);
    Alert.alert(
      "Manual entry recorded",
      "Sub-1K manual metrics logged for tracking. These do not affect native platform payouts.",
      [{ text: "OK" }]
    );
  };

  return (
    <SafeAreaView edges={["top"]} style={styles.safe}>
      <View style={styles.header}>
        <Text style={styles.overline}>NATIVE PLATFORM PAYOUTS</Text>
        <Text style={styles.title}>Earnings</Text>
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {/* Headline */}
        <View style={styles.headlineCard}>
          <Text style={styles.headlineLabel}>Accrued · {periodLabel(period)}</Text>
          <Text style={styles.headlineNumber}>{headline.total}</Text>
          <View style={styles.headlineDeltaRow}>
            <MetricChip
              label="vs prior"
              value={headline.delta}
              variant={headline.variant === "default" ? "default" : headline.variant}
            />
            <Text style={styles.headlineNote}>Updated 4m ago</Text>
          </View>

          <View style={styles.periodRow}>
            {PERIODS.map((p) => {
              const active = period === p.key;
              return (
                <Pressable
                  key={p.key}
                  onPress={() => {
                    triggerHaptic("selection");
                    setPeriod(p.key);
                  }}
                  style={[styles.periodPill, active && styles.periodPillActive]}
                  accessibilityRole="button"
                  accessibilityState={{ selected: active }}
                >
                  <Text style={[styles.periodText, active && styles.periodTextActive]}>
                    {p.label}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </View>

        {/* Per-platform native CPM */}
        <SectionHeader title="Per-platform native CPM" subtitle="Payout from each connected platform over the period." />
        <View style={styles.platformList}>
          {PLATFORM_EARNINGS.map((row) => (
            <View key={row.platform} style={styles.platformRow}>
              <AccountBadge
                platform={row.platform}
                handle={row.handle}
                variant="pill"
                style={styles.platformBadge}
              />
              <View style={styles.sparkWrap}>
                <Sparkline values={row.spark} platform={row.platform} />
              </View>
              <View style={styles.platformValue}>
                <Text style={styles.platformAmount}>{row.amount}</Text>
                <Text style={styles.platformCpm}>{row.cpm}</Text>
              </View>
            </View>
          ))}
        </View>

        {/* Brand campaigns */}
        <SectionHeader title="Brand campaigns" />
        <View style={styles.campaignEmpty}>
          <View style={styles.campaignIcon}>
            <Briefcase
              size={tokens.icon.size.lg}
              color={tokens.color.text.tertiary}
              strokeWidth={tokens.icon.stroke.default}
            />
          </View>
          <View style={{ flex: 1, gap: 2 }}>
            <Text style={styles.campaignTitle}>Auto-submission is coming soon</Text>
            <Text style={styles.campaignBody}>
              Manually submitted clips will appear here once campaigns are wired up.
            </Text>
          </View>
        </View>

        {/* Projection */}
        <SectionHeader title="7-day projection" />
        <InsightTile
          overline="Forecast"
          headline="$58 next 7d"
          body="Projection updates after each metric snapshot. Based on current pipeline velocity and per-platform CPM, last 14 days."
          variant="positive"
        />

        {/* Manual entry */}
        <View style={styles.manualBlock}>
          <View style={{ flex: 1, gap: 2 }}>
            <Text style={styles.manualTitle}>Sub-1K manual entry</Text>
            <Text style={styles.manualBody}>
              For Instagram accounts under 1,000 followers, enter your numbers manually.
            </Text>
          </View>
          <ActionButton
            label="Enter"
            variant="secondary"
            size="md"
            iconLeft={Pencil}
            onPress={() => {
              triggerHaptic("selection");
              setManualOpen(true);
            }}
          />
        </View>

        <View style={{ height: tokens.spacing.lg }} />
      </ScrollView>

      {/* Manual entry modal */}
      <Modal
        visible={manualOpen}
        transparent
        animationType="slide"
        onRequestClose={() => setManualOpen(false)}
      >
        <Pressable style={styles.modalOverlay} onPress={() => setManualOpen(false)}>
          <Pressable style={styles.modalSheet} onPress={(e) => e.stopPropagation()}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Manual entry</Text>
              <Pressable onPress={() => setManualOpen(false)} hitSlop={12} accessibilityLabel="Close manual entry">
                <X size={tokens.icon.size.md} color={tokens.color.text.secondary} strokeWidth={tokens.icon.stroke.default} />
              </Pressable>
            </View>
            <Text style={styles.modalSub}>Values are timestamped at submit.</Text>

            <FormField label="Account">
              <View style={styles.accountPickerRow}>
                {[{ id: "ig-studio", label: "@studio · Instagram" }].map((opt) => {
                  const selected = entry.accountId === opt.id;
                  return (
                    <Pressable
                      key={opt.id}
                      onPress={() => {
                        triggerHaptic("selection");
                        setEntry((e) => ({ ...e, accountId: opt.id }));
                      }}
                      style={[styles.pickerPill, selected && styles.pickerPillActive]}
                    >
                      <Text style={[styles.pickerText, selected && styles.pickerTextActive]}>
                        {opt.label}
                      </Text>
                    </Pressable>
                  );
                })}
              </View>
            </FormField>

            <FormField label="Clip">
              <View style={styles.accountPickerRow}>
                {clipOptions.length === 0 ? (
                  <Text style={styles.helperText}>No clips available.</Text>
                ) : (
                  clipOptions.map((opt) => {
                    const selected = entry.clipId === opt.id;
                    return (
                      <Pressable
                        key={opt.id}
                        onPress={() => {
                          triggerHaptic("selection");
                          setEntry((e) => ({ ...e, clipId: opt.id }));
                        }}
                        style={[styles.pickerPill, selected && styles.pickerPillActive]}
                      >
                        <Text style={[styles.pickerText, selected && styles.pickerTextActive]} numberOfLines={1}>
                          {opt.label}
                        </Text>
                      </Pressable>
                    );
                  })
                )}
              </View>
            </FormField>

            <View style={styles.grid2}>
              <FormField label="Views" style={styles.gridItem}>
                <NumberInput
                  value={entry.views}
                  onChangeText={(v) => setEntry((e) => ({ ...e, views: v }))}
                />
              </FormField>
              <FormField label="Likes" style={styles.gridItem}>
                <NumberInput
                  value={entry.likes}
                  onChangeText={(v) => setEntry((e) => ({ ...e, likes: v }))}
                />
              </FormField>
              <FormField label="Comments" style={styles.gridItem}>
                <NumberInput
                  value={entry.comments}
                  onChangeText={(v) => setEntry((e) => ({ ...e, comments: v }))}
                />
              </FormField>
              <FormField label="Shares" style={styles.gridItem}>
                <NumberInput
                  value={entry.shares}
                  onChangeText={(v) => setEntry((e) => ({ ...e, shares: v }))}
                />
              </FormField>
            </View>

            <View style={styles.modalFooter}>
              <ActionButton label="Cancel" variant="secondary" size="md" onPress={() => setManualOpen(false)} />
              <ActionButton
                label="Submit"
                variant="primary"
                size="md"
                disabled={!entry.clipId || !entry.views}
                onPress={onSubmitManual}
              />
            </View>
          </Pressable>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}

function periodLabel(p: Period): string {
  if (p === "7d") return "Last 7 days";
  if (p === "30d") return "Last 30 days";
  return "All time";
}

function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <View style={styles.sectionHeader}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {subtitle ? <Text style={styles.sectionSub}>{subtitle}</Text> : null}
    </View>
  );
}

interface SparklineProps {
  values: number[];
  platform: AccountPlatform;
}

function Sparkline({ values, platform }: SparklineProps) {
  const tint = tokens.color.semantic.platform[platform];
  return (
    <View style={styles.spark}>
      {values.map((v, i) => (
        <View
          key={i}
          style={[
            styles.sparkBar,
            { height: Math.max(3, v * 28), backgroundColor: `${tint}AA` },
          ]}
        />
      ))}
      <View style={[styles.sparkArrow]}>
        <ArrowUpRight
          size={tokens.icon.size.xs}
          color={tokens.color.semantic.metric.positive}
          strokeWidth={tokens.icon.stroke.bold}
        />
      </View>
    </View>
  );
}

function FormField({
  label,
  children,
  style,
}: {
  label: string;
  children: React.ReactNode;
  style?: import("react-native").ViewStyle;
}) {
  return (
    <View style={[styles.field, style]}>
      <Text style={styles.fieldLabel}>{label.toUpperCase()}</Text>
      {children}
    </View>
  );
}

function NumberInput({
  value,
  onChangeText,
}: {
  value: string;
  onChangeText: (v: string) => void;
}) {
  return (
    <TextInput
      value={value}
      onChangeText={(t) => onChangeText(t.replace(/[^0-9]/g, ""))}
      keyboardType="number-pad"
      placeholder="0"
      placeholderTextColor={tokens.color.text.tertiary}
      style={styles.input}
    />
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: tokens.color.bg.base },
  header: {
    paddingHorizontal: tokens.layout.screenPadding,
    paddingBottom: tokens.spacing.sm,
  },
  overline: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    lineHeight: tokens.type.scale.overline.lineHeight,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  title: {
    fontFamily: tokens.type.scale.h1.family,
    fontSize: tokens.type.scale.h1.size,
    lineHeight: tokens.type.scale.h1.lineHeight,
    letterSpacing: tokens.type.scale.h1.letterSpacing,
    color: tokens.color.text.primary,
  },
  scroll: {
    paddingHorizontal: tokens.layout.screenPadding,
    paddingBottom: tokens.spacing.xxl,
    gap: tokens.layout.sectionGap,
  },
  headlineCard: {
    padding: tokens.spacing.lg,
    borderRadius: tokens.radius.lg,
    backgroundColor: tokens.color.bg.surface,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    gap: tokens.spacing.sm,
    ...tokens.elevation[1],
  },
  headlineLabel: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  headlineNumber: {
    fontFamily: tokens.type.scale.display.family,
    fontSize: tokens.type.scale.display.size,
    lineHeight: tokens.type.scale.display.lineHeight,
    letterSpacing: tokens.type.scale.display.letterSpacing,
    color: tokens.color.text.primary,
  },
  headlineDeltaRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.sm,
  },
  headlineNote: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  periodRow: {
    flexDirection: "row",
    gap: tokens.spacing.xs,
    marginTop: tokens.spacing.xs,
  },
  periodPill: {
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.xs,
    borderRadius: tokens.radius.pill,
    borderWidth: 1,
    borderColor: tokens.color.border.default,
    backgroundColor: tokens.color.bg.raised,
    minHeight: 32,
    justifyContent: "center",
  },
  periodPillActive: {
    borderColor: tokens.color.brand.indigo[400],
    backgroundColor: tokens.color.brand.indigo[900],
  },
  periodText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.secondary,
  },
  periodTextActive: { color: tokens.color.text.primary },
  sectionHeader: { gap: 4 },
  sectionTitle: {
    fontFamily: tokens.type.scale.h2.family,
    fontSize: tokens.type.scale.h2.size,
    lineHeight: tokens.type.scale.h2.lineHeight,
    letterSpacing: tokens.type.scale.h2.letterSpacing,
    color: tokens.color.text.primary,
  },
  sectionSub: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.tertiary,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
  },
  platformList: { gap: tokens.spacing.sm },
  platformRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
    padding: tokens.spacing.md,
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
  },
  platformBadge: { flexShrink: 0 },
  sparkWrap: { flex: 1, alignItems: "flex-end" },
  spark: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 3,
    height: 32,
  },
  sparkBar: {
    width: 4,
    borderRadius: 2,
  },
  sparkArrow: {
    marginLeft: tokens.spacing.xs,
    alignSelf: "center",
  },
  platformValue: { alignItems: "flex-end", minWidth: 72 },
  platformAmount: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.primary,
  },
  platformCpm: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
    marginTop: 2,
  },
  campaignEmpty: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
    padding: tokens.spacing.md,
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    borderStyle: "dashed",
    borderColor: tokens.color.border.default,
    backgroundColor: tokens.color.bg.raised,
  },
  campaignIcon: {
    width: 44,
    height: 44,
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.bg.surface,
    alignItems: "center",
    justifyContent: "center",
  },
  campaignTitle: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.primary,
  },
  campaignBody: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    lineHeight: tokens.type.scale.bodySmall.lineHeight,
    color: tokens.color.text.secondary,
  },
  manualBlock: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
    padding: tokens.spacing.md,
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    backgroundColor: tokens.color.bg.surface,
  },
  manualTitle: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.primary,
  },
  manualBody: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.secondary,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: tokens.color.bg.overlay,
    justifyContent: "flex-end",
  },
  modalSheet: {
    backgroundColor: tokens.color.bg.raised,
    borderTopLeftRadius: tokens.radius.xl,
    borderTopRightRadius: tokens.radius.xl,
    padding: tokens.spacing.lg,
    gap: tokens.spacing.md,
    borderTopWidth: 1,
    borderTopColor: tokens.color.border.subtle,
  },
  modalHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  modalTitle: {
    fontFamily: tokens.type.scale.h2.family,
    fontSize: tokens.type.scale.h2.size,
    color: tokens.color.text.primary,
  },
  modalSub: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    lineHeight: tokens.type.scale.bodySmall.lineHeight,
    color: tokens.color.text.secondary,
  },
  field: { gap: tokens.spacing.xs },
  fieldLabel: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  accountPickerRow: { flexDirection: "row", gap: tokens.spacing.xs, flexWrap: "wrap" },
  pickerPill: {
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.xs,
    borderRadius: tokens.radius.pill,
    borderWidth: 1,
    borderColor: tokens.color.border.default,
    backgroundColor: tokens.color.bg.surface,
    minHeight: 36,
    justifyContent: "center",
  },
  pickerPillActive: {
    borderColor: tokens.color.brand.indigo[400],
    backgroundColor: tokens.color.brand.indigo[900],
  },
  pickerText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.secondary,
    maxWidth: 240,
  },
  pickerTextActive: { color: tokens.color.text.primary },
  helperText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.tertiary,
  },
  grid2: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
  gridItem: { flexBasis: "47%", flexGrow: 1 },
  input: {
    height: 44,
    paddingHorizontal: tokens.spacing.md,
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.bg.surface,
    borderWidth: 1,
    borderColor: tokens.color.border.default,
    color: tokens.color.text.primary,
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
  },
  modalFooter: {
    flexDirection: "row",
    gap: tokens.spacing.sm,
    justifyContent: "flex-end",
    marginTop: tokens.spacing.xs,
  },
});
