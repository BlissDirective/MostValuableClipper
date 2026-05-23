import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
} from "react-native";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import {
  ChevronDown,
  ChevronLeft,
  ChevronUp,
  Cloud,
  FileVideo,
  Hand,
  Link as LinkIcon,
  MoreHorizontal,
  Pause,
  Pencil,
  Play,
  Plus,
  Trash2,
  Upload,
  Zap,
  LucideIcon,
  Check,
} from "lucide-react-native";

import { tokens } from "@/constants/tokens";
import { ActionButton } from "@/components/ActionButton";
import { MetricChip } from "@/components/MetricChip";
import {
  AutonomyMode,
  Pipeline,
  PipelineSource,
  PlatformKey,
  RetentionPolicy,
  WarningCategoryKey,
  useAuthStore,
} from "@/lib/store";
import { triggerHaptic } from "@/utils/haptics";

const AUTONOMY_OPTIONS: { key: AutonomyMode; title: string; body: string; icon: LucideIcon; tint: string }[] = [
  {
    key: "fullAuto",
    title: "Full Auto",
    body: "Clips are generated and posted on schedule.",
    icon: Zap,
    tint: tokens.color.semantic.autonomy.fullAuto,
  },
  {
    key: "approveEach",
    title: "Approve Each Post",
    body: "Every clip enters the approval queue.",
    icon: Hand,
    tint: tokens.color.semantic.autonomy.approveEach,
  },
  {
    key: "suggestOnly",
    title: "Suggest Only",
    body: "The analyst proposes, you publish manually.",
    icon: Pencil,
    tint: tokens.color.semantic.autonomy.suggestOnly,
  },
];

const SOURCE_ICON: Record<PipelineSource["kind"], LucideIcon> = {
  upload: Upload,
  "creator-licensed": FileVideo,
  "cc-archive": Cloud,
};

const RETENTION_OPTIONS: { key: RetentionPolicy; label: string; sub: string }[] = [
  { key: "aggressive", label: "Aggressive", sub: "30 days" },
  { key: "moderate", label: "Moderate", sub: "90 days" },
  { key: "indefinite", label: "Indefinite", sub: "Keep until deleted" },
];

const WARNING_LABELS: Record<WarningCategoryKey, string> = {
  newsPolitical: "News · Political",
  health: "Health",
  finance: "Finance",
  children: "Children's content",
  identifiableIndividual: "Identifiable individual",
  violentGraphic: "Violent · Graphic",
};

const PLATFORMS: { key: PlatformKey; label: string }[] = [
  { key: "tiktok", label: "TikTok" },
  { key: "instagram", label: "Instagram" },
  { key: "youtube", label: "YouTube" },
];

const STATUS_LABEL: Record<Pipeline["status"], string> = {
  running: "Running",
  paused: "Paused",
  errored: "Error",
  "setup-incomplete": "Setup incomplete",
};
const STATUS_COLOR: Record<Pipeline["status"], string> = {
  running: tokens.color.status.success,
  paused: tokens.color.status.warning,
  errored: tokens.color.status.danger,
  "setup-incomplete": tokens.color.text.tertiary,
};

export default function PipelineDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const pipeline = useAuthStore((s) => s.pipelines.find((p) => p.id === id));
  const updatePipeline = useAuthStore((s) => s.updatePipeline);
  const removePipeline = useAuthStore((s) => s.removePipeline);
  const fetchSources = useAuthStore((s) => s.fetchSources);
  const addSource = useAuthStore((s) => s.addSource);
  const removeSourceAction = useAuthStore((s) => s.removeSource);
  const [settingsOpen, setSettingsOpen] = useState<boolean>(false);
  const [cadenceOpen, setCadenceOpen] = useState<boolean>(false);

  useEffect(() => {
    if (id) fetchSources();
  }, [id, fetchSources]);

  if (!pipeline) {
    return (
      <SafeAreaView style={styles.safe}>
        <Stack.Screen options={{ headerShown: false }} />
        <View style={styles.missing}>
          <Text style={styles.title}>Pipeline not found</Text>
          <ActionButton label="Back" variant="secondary" size="md" onPress={() => router.back()} />
        </View>
      </SafeAreaView>
    );
  }

  const togglePause = () => {
    triggerHaptic("selection");
    updatePipeline(pipeline.id, { status: pipeline.status === "paused" ? "running" : "paused" });
  };

  const onAddSource = () => {
    triggerHaptic("selection");
    Alert.alert(
      "Add source",
      "Choose a source type",
      [
        {
          text: "User upload",
          onPress: () => {
            addSource(id, { name: "new_upload.mp4", kind: "upload", sourceType: "upload", sourceUrl: "", status: "pending" });
          },
        },
        {
          text: "Creator-licensed",
          onPress: () => {
            addSource(id, { name: "Licensed catalog", kind: "creator-licensed", sourceType: "youtube", sourceUrl: "", status: "pending" });
          },
        },
        {
          text: "CC archive",
          onPress: () => {
            addSource(id, { name: "Public domain archive", kind: "cc-archive", sourceType: "rss", sourceUrl: "", status: "pending" });
          },
        },
        { text: "Cancel", style: "cancel" },
      ],
      { cancelable: true }
    );
  };

  const onRemoveSource = (sid: string) => {
    triggerHaptic("selection");
    removeSourceAction(id, sid);
  };

  const onDelete = () => {
    Alert.alert(
      "Delete pipeline?",
      `"${pipeline.themeName}" will stop producing clips. This cannot be undone.`,
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: () => {
            removePipeline(pipeline.id);
            router.back();
          },
        },
      ]
    );
  };

  return (
    <View style={styles.root}>
      <Stack.Screen options={{ headerShown: false }} />
      <SafeAreaView edges={["top"]} style={styles.safe}>
        <View style={styles.topBar}>
          <Pressable onPress={() => router.back()} hitSlop={12} style={styles.backBtn} accessibilityLabel="Back">
            <ChevronLeft size={tokens.icon.size.lg} color={tokens.color.text.primary} strokeWidth={tokens.icon.stroke.default} />
          </Pressable>
          <Text style={styles.topBarTitle}>Pipeline</Text>
          <View style={{ width: tokens.layout.minTouchTarget }} />
        </View>

        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          {/* Header card */}
          <View style={styles.headerCard}>
            <View style={styles.headerRow}>
              <View style={{ flex: 1 }}>
                <Text style={styles.themeName}>{pipeline.themeName}</Text>
                <Text style={styles.niche}>{pipeline.niche}</Text>
              </View>
              <View style={[styles.statusPill, { borderColor: STATUS_COLOR[pipeline.status] }]}>
                <View style={[styles.statusDot, { backgroundColor: STATUS_COLOR[pipeline.status] }]} />
                <Text style={[styles.statusText, { color: STATUS_COLOR[pipeline.status] }]}>{STATUS_LABEL[pipeline.status]}</Text>
              </View>
            </View>
            <ActionButton
              label={pipeline.status === "paused" ? "Resume pipeline" : "Pause pipeline"}
              variant="primary"
              size="md"
              fullWidth
              iconLeft={pipeline.status === "paused" ? Play : Pause}
              onPress={togglePause}
            />
          </View>

          {/* Sources */}
          <Section title="Sources">
            {pipeline.sources.map((s) => (
              <SourceRow key={s.id} source={s} onRemove={() => onRemoveSource(s.id)} />
            ))}
            <Pressable onPress={onAddSource} style={styles.addSource} accessibilityRole="button">
              <Plus size={tokens.icon.size.sm} color={tokens.color.accent.secondary} strokeWidth={tokens.icon.stroke.default} />
              <Text style={styles.addSourceText}>Add source</Text>
            </Pressable>
          </Section>

          {/* Cadence */}
          <Section title="Cadence">
            <View style={styles.summaryRow}>
              <Text style={styles.summaryText}>
                Posting up to {pipeline.clipsPerDay} clips/day across {pipeline.platforms.length} platform
                {pipeline.platforms.length === 1 ? "" : "s"}.
              </Text>
              <ActionButton label="Edit" variant="secondary" size="sm" onPress={() => setCadenceOpen(true)} />
            </View>
            <View style={styles.platformChips}>
              {PLATFORMS.map((p) => {
                const active = pipeline.platforms.includes(p.key);
                return (
                  <View
                    key={p.key}
                    style={[
                      styles.platformChip,
                      active
                        ? { backgroundColor: tokens.color.brand.indigo[900], borderColor: tokens.color.brand.indigo[600] }
                        : null,
                    ]}
                  >
                    <Text style={[styles.platformChipText, active ? { color: tokens.color.text.primary } : null]}>
                      {p.label}
                    </Text>
                  </View>
                );
              })}
            </View>
          </Section>

          {/* Autonomy */}
          <Section title="Autonomy">
            <View style={styles.autonomyList}>
              {AUTONOMY_OPTIONS.map((o) => {
                const selected = pipeline.autonomy === o.key;
                const Icon = o.icon;
                return (
                  <Pressable
                    key={o.key}
                    onPress={() => {
                      triggerHaptic("selection");
                      updatePipeline(pipeline.id, { autonomy: o.key });
                    }}
                    accessibilityRole="radio"
                    accessibilityState={{ selected }}
                    style={[
                      styles.autonomyCard,
                      selected && {
                        borderColor: tokens.color.brand.indigo[400],
                        backgroundColor: tokens.color.bg.elevated,
                      },
                    ]}
                  >
                    <View style={[styles.autonomyIcon, { backgroundColor: `${o.tint}1F`, borderColor: `${o.tint}66` }]}>
                      <Icon size={tokens.icon.size.md} color={o.tint} strokeWidth={tokens.icon.stroke.default} />
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.autonomyTitle}>{o.title}</Text>
                      <Text style={styles.autonomyBody}>{o.body}</Text>
                    </View>
                    {selected ? (
                      <View style={styles.checkDot}>
                        <Check size={14} color={tokens.color.text.onAccent} strokeWidth={tokens.icon.stroke.bold} />
                      </View>
                    ) : null}
                  </Pressable>
                );
              })}
            </View>
          </Section>

          {/* Settings collapsible */}
          <Pressable onPress={() => setSettingsOpen((v) => !v)} style={styles.collapseHeader}>
            <Text style={styles.sectionTitle}>Settings</Text>
            {settingsOpen ? (
              <ChevronUp size={tokens.icon.size.md} color={tokens.color.text.secondary} strokeWidth={tokens.icon.stroke.default} />
            ) : (
              <ChevronDown size={tokens.icon.size.md} color={tokens.color.text.secondary} strokeWidth={tokens.icon.stroke.default} />
            )}
          </Pressable>
          {settingsOpen ? (
            <View style={styles.settingsBody}>
              {/* Resolver */}
              <View style={styles.settingRow}>
                <View style={{ flex: 1, gap: 2 }}>
                  <Text style={styles.settingTitle}>Clipper-friendly source resolver</Text>
                  <Text style={styles.settingBody}>
                    Bias source resolution toward partner-licensed and public-domain assets first.
                  </Text>
                </View>
                <Switch
                  value={pipeline.resolverOn}
                  onValueChange={(v) => {
                    triggerHaptic("selection");
                    updatePipeline(pipeline.id, { resolverOn: v });
                  }}
                  trackColor={{ false: tokens.color.border.default, true: tokens.color.accent.primary }}
                  thumbColor={tokens.color.text.onAccent}
                  ios_backgroundColor={tokens.color.border.default}
                />
              </View>

              {/* Retention */}
              <View style={styles.settingBlock}>
                <Text style={styles.settingTitle}>Retention period</Text>
                <View style={{ gap: tokens.spacing.xs }}>
                  {RETENTION_OPTIONS.map((r) => {
                    const selected = pipeline.retention === r.key;
                    return (
                      <Pressable
                        key={r.key}
                        onPress={() => {
                          triggerHaptic("selection");
                          updatePipeline(pipeline.id, { retention: r.key });
                        }}
                        accessibilityRole="radio"
                        accessibilityState={{ selected }}
                        style={[
                          styles.radioRow,
                          selected && { borderColor: tokens.color.brand.indigo[400], backgroundColor: tokens.color.bg.elevated },
                        ]}
                      >
                        <View style={[styles.radio, selected && styles.radioOn]}>
                          {selected ? <View style={styles.radioDot} /> : null}
                        </View>
                        <View style={{ flex: 1 }}>
                          <Text style={styles.settingTitle}>{r.label}</Text>
                          <Text style={styles.settingBody}>{r.sub}</Text>
                        </View>
                      </Pressable>
                    );
                  })}
                </View>
              </View>

              {/* Warning categories */}
              <View style={styles.settingBlock}>
                <Text style={styles.settingTitle}>Warning-category safety</Text>
                <Text style={styles.settingBody}>
                  Adult-NSFW and Copyrighted-Material-Risk are always blocked and cannot be disabled.
                </Text>
                <View style={{ gap: tokens.spacing.xs, marginTop: tokens.spacing.xs }}>
                  {(Object.keys(WARNING_LABELS) as WarningCategoryKey[]).map((k) => {
                    const on = pipeline.warningCategories[k];
                    return (
                      <View key={k} style={styles.toggleRow}>
                        <Text style={styles.toggleLabel}>{WARNING_LABELS[k]}</Text>
                        <Switch
                          value={on}
                          onValueChange={(v) => {
                            triggerHaptic("selection");
                            updatePipeline(pipeline.id, {
                              warningCategories: { ...pipeline.warningCategories, [k]: v },
                            });
                          }}
                          trackColor={{ false: tokens.color.border.default, true: tokens.color.accent.primary }}
                          thumbColor={tokens.color.text.onAccent}
                          ios_backgroundColor={tokens.color.border.default}
                        />
                      </View>
                    );
                  })}
                </View>
              </View>
            </View>
          ) : null}

          {/* Performance */}
          <Section title="Performance · 7d">
            <View style={styles.perfRow}>
              <MetricChip
                label="Clips this week"
                value={String(pipeline.clipsThisWeek)}
                style={styles.flex1}
              />
              <MetricChip
                label="View delta"
                value={pipeline.viewDelta}
                variant={pipeline.deltaVariant === "default" ? "default" : pipeline.deltaVariant}
                style={styles.flex1}
              />
              <MetricChip
                label="Top hook"
                value="Question·s1"
                variant="positive"
                style={styles.flex1}
              />
            </View>
            <ActionButton
              label="Open Insights for this pipeline"
              variant="ghost"
              size="sm"
              onPress={() => {
                
                router.push("/(app)/insights");
              }}
            />
          </Section>

          {/* Danger zone */}
          <View style={styles.danger}>
            <Text style={styles.dangerOverline}>DANGER ZONE</Text>
            <ActionButton
              label="Delete pipeline"
              variant="danger"
              size="md"
              iconLeft={Trash2}
              fullWidth
              onPress={onDelete}
            />
          </View>
        </ScrollView>
      </SafeAreaView>

      <CadenceModal
        visible={cadenceOpen}
        clipsPerDay={pipeline.clipsPerDay}
        platforms={pipeline.platforms}
        onCancel={() => setCadenceOpen(false)}
        onSave={(clipsPerDay, platforms) => {
          updatePipeline(pipeline.id, { clipsPerDay, platforms });
          setCadenceOpen(false);
        }}
      />
    </View>
  );
}

interface SectionProps {
  title: string;
  children: React.ReactNode;
}
function Section({ title, children }: SectionProps) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <View style={{ gap: tokens.spacing.sm }}>{children}</View>
    </View>
  );
}

function SourceRow({ source, onRemove }: { source: PipelineSource; onRemove: () => void }) {
  const Icon = SOURCE_ICON[source.kind] ?? LinkIcon;
  const statusColor =
    source.status === "ingested"
      ? tokens.color.status.success
      : source.status === "failed"
      ? tokens.color.status.danger
      : tokens.color.status.warning;
  const statusLabel = source.status === "ingested" ? "Ingested" : source.status === "failed" ? "Failed" : "Pending";

  const onMenu = () => {
    triggerHaptic("selection");
    Alert.alert(source.name, undefined, [
      { text: "Remove", style: "destructive", onPress: onRemove },
      { text: "Cancel", style: "cancel" },
    ]);
  };

  return (
    <View style={styles.sourceRow}>
      <View style={styles.sourceIcon}>
        <Icon size={tokens.icon.size.sm} color={tokens.color.text.secondary} strokeWidth={tokens.icon.stroke.default} />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.sourceName} numberOfLines={1}>{source.name}</Text>
        <Text style={[styles.sourceStatus, { color: statusColor }]}>{statusLabel}</Text>
      </View>
      <Pressable onPress={onMenu} hitSlop={12} style={styles.menuBtn} accessibilityLabel="Source menu">
        <MoreHorizontal size={tokens.icon.size.md} color={tokens.color.text.tertiary} strokeWidth={tokens.icon.stroke.default} />
      </Pressable>
    </View>
  );
}

interface CadenceModalProps {
  visible: boolean;
  clipsPerDay: number;
  platforms: PlatformKey[];
  onCancel: () => void;
  onSave: (clipsPerDay: number, platforms: PlatformKey[]) => void;
}

export function CadenceModal({ visible, clipsPerDay, platforms, onCancel, onSave }: CadenceModalProps) {
  const [count, setCount] = useState<number>(clipsPerDay);
  const [selected, setSelected] = useState<PlatformKey[]>(platforms);

  const togglePlatform = (k: PlatformKey) => {
    triggerHaptic("selection");
    setSelected((prev) => (prev.includes(k) ? prev.filter((p) => p !== k) : [...prev, k]));
  };

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onCancel}>
      <View style={styles.modalOverlay}>
        <View style={styles.modalSheet}>
          <Text style={styles.modalTitle}>Cadence</Text>
          <Text style={styles.modalSub}>Set how many clips post per day and where.</Text>

          <View style={styles.modalBlock}>
            <Text style={styles.modalLabel}>Clips per day · {count}</Text>
            <View style={styles.stepperRow}>
              {[1, 2, 3, 4, 5, 6, 8, 10].map((n) => {
                const active = count === n;
                return (
                  <Pressable
                    key={n}
                    onPress={() => {
                      triggerHaptic("selection");
                      setCount(n);
                    }}
                    style={[styles.stepper, active && styles.stepperActive]}
                  >
                    <Text style={[styles.stepperText, active && styles.stepperTextActive]}>{n}</Text>
                  </Pressable>
                );
              })}
            </View>
          </View>

          <View style={styles.modalBlock}>
            <Text style={styles.modalLabel}>Platforms</Text>
            <View style={styles.platformChips}>
              {PLATFORMS.map((p) => {
                const active = selected.includes(p.key);
                return (
                  <Pressable
                    key={p.key}
                    onPress={() => togglePlatform(p.key)}
                    style={[
                      styles.platformChip,
                      active && {
                        backgroundColor: tokens.color.brand.indigo[900],
                        borderColor: tokens.color.brand.indigo[400],
                      },
                    ]}
                  >
                    <Text style={[styles.platformChipText, active && { color: tokens.color.text.primary }]}>
                      {p.label}
                    </Text>
                  </Pressable>
                );
              })}
            </View>
          </View>

          <View style={styles.modalFooter}>
            <ActionButton label="Cancel" variant="secondary" size="md" onPress={onCancel} />
            <ActionButton label="Save" variant="primary" size="md" onPress={() => onSave(count, selected)} />
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg.base },
  safe: { flex: 1 },
  missing: { flex: 1, alignItems: "center", justifyContent: "center", gap: tokens.spacing.md },
  topBar: {
    height: tokens.layout.headerHeight,
    paddingHorizontal: tokens.spacing.sm,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  topBarTitle: {
    fontFamily: tokens.type.scale.h3.family,
    fontSize: tokens.type.scale.h3.size,
    color: tokens.color.text.primary,
  },
  backBtn: {
    width: tokens.layout.minTouchTarget,
    height: tokens.layout.minTouchTarget,
    alignItems: "center",
    justifyContent: "center",
  },
  scroll: {
    paddingHorizontal: tokens.layout.screenPadding,
    paddingBottom: tokens.spacing.xxxl,
    gap: tokens.layout.sectionGap,
  },
  headerCard: {
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    padding: tokens.spacing.md,
    gap: tokens.spacing.md,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: tokens.spacing.md,
  },
  themeName: {
    fontFamily: tokens.type.scale.h1.family,
    fontSize: tokens.type.scale.h1.size,
    lineHeight: tokens.type.scale.h1.lineHeight,
    letterSpacing: tokens.type.scale.h1.letterSpacing,
    color: tokens.color.text.primary,
  },
  niche: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
    marginTop: 2,
  },
  statusPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.xs,
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: 4,
    borderRadius: tokens.radius.pill,
    borderWidth: 1,
  },
  statusDot: { width: 8, height: 8, borderRadius: tokens.radius.pill },
  statusText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
  },
  title: {
    fontFamily: tokens.type.scale.h1.family,
    fontSize: tokens.type.scale.h1.size,
    color: tokens.color.text.primary,
  },
  section: { gap: tokens.spacing.sm },
  sectionTitle: {
    fontFamily: tokens.type.scale.h2.family,
    fontSize: tokens.type.scale.h2.size,
    lineHeight: tokens.type.scale.h2.lineHeight,
    letterSpacing: tokens.type.scale.h2.letterSpacing,
    color: tokens.color.text.primary,
  },
  sourceRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
    padding: tokens.spacing.md,
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
  },
  sourceIcon: {
    width: 36,
    height: 36,
    borderRadius: tokens.radius.sm,
    backgroundColor: tokens.color.bg.raised,
    alignItems: "center",
    justifyContent: "center",
  },
  sourceName: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.primary,
  },
  sourceStatus: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    marginTop: 2,
  },
  menuBtn: {
    width: tokens.layout.minTouchTarget,
    height: tokens.layout.minTouchTarget,
    alignItems: "center",
    justifyContent: "center",
  },
  addSource: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.sm,
    paddingVertical: tokens.spacing.md,
    paddingHorizontal: tokens.spacing.md,
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    borderStyle: "dashed",
    borderColor: tokens.color.border.strong,
  },
  addSourceText: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.accent.secondary,
  },
  summaryRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
    padding: tokens.spacing.md,
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
  },
  summaryText: {
    flex: 1,
    fontFamily: tokens.type.scale.body.family,
    fontSize: tokens.type.scale.body.size,
    lineHeight: tokens.type.scale.body.lineHeight,
    color: tokens.color.text.primary,
  },
  platformChips: {
    flexDirection: "row",
    gap: tokens.spacing.xs,
    flexWrap: "wrap",
  },
  platformChip: {
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.xs,
    borderRadius: tokens.radius.pill,
    borderWidth: 1,
    borderColor: tokens.color.border.default,
    backgroundColor: tokens.color.bg.raised,
  },
  platformChipText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.secondary,
  },
  autonomyList: { gap: tokens.spacing.sm },
  autonomyCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
    padding: tokens.spacing.md,
    borderRadius: tokens.radius.md,
    borderWidth: 2,
    borderColor: tokens.color.border.default,
    backgroundColor: tokens.color.bg.surface,
  },
  autonomyIcon: {
    width: 40,
    height: 40,
    borderRadius: tokens.radius.md,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
  },
  autonomyTitle: {
    fontFamily: tokens.type.scale.h3.family,
    fontSize: tokens.type.scale.h3.size,
    color: tokens.color.text.primary,
  },
  autonomyBody: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
    marginTop: 2,
  },
  checkDot: {
    width: 22,
    height: 22,
    borderRadius: tokens.radius.pill,
    backgroundColor: tokens.color.brand.indigo[400],
    alignItems: "center",
    justifyContent: "center",
  },
  collapseHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: tokens.spacing.sm,
    borderTopWidth: 1,
    borderTopColor: tokens.color.border.subtle,
    paddingTop: tokens.spacing.md,
  },
  settingsBody: { gap: tokens.spacing.md, marginTop: -tokens.spacing.sm },
  settingRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
    padding: tokens.spacing.md,
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
  },
  settingBlock: {
    padding: tokens.spacing.md,
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    gap: tokens.spacing.sm,
  },
  settingTitle: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.primary,
  },
  settingBody: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.secondary,
  },
  radioRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    paddingHorizontal: tokens.spacing.md,
    borderRadius: tokens.radius.sm,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
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
  radioOn: {
    borderColor: tokens.color.brand.indigo[400],
    backgroundColor: tokens.color.brand.indigo[400],
  },
  radioDot: { width: 8, height: 8, borderRadius: tokens.radius.pill, backgroundColor: tokens.color.text.onAccent },
  toggleRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: tokens.spacing.xs,
  },
  toggleLabel: {
    fontFamily: tokens.type.scale.body.family,
    fontSize: tokens.type.scale.body.size,
    color: tokens.color.text.primary,
  },
  perfRow: { flexDirection: "row", gap: tokens.spacing.sm },
  flex1: { flex: 1, minWidth: 0 },
  danger: {
    padding: tokens.spacing.md,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.color.semantic.safety.block.border,
    backgroundColor: tokens.color.status.dangerBg,
    gap: tokens.spacing.sm,
  },
  dangerOverline: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.status.danger,
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
  modalTitle: {
    fontFamily: tokens.type.scale.h2.family,
    fontSize: tokens.type.scale.h2.size,
    color: tokens.color.text.primary,
  },
  modalSub: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    color: tokens.color.text.secondary,
  },
  modalBlock: { gap: tokens.spacing.sm },
  modalLabel: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
    textTransform: "uppercase",
  },
  stepperRow: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.xs },
  stepper: {
    minWidth: 44,
    height: 44,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    borderColor: tokens.color.border.default,
    backgroundColor: tokens.color.bg.surface,
    paddingHorizontal: tokens.spacing.sm,
  },
  stepperActive: {
    borderColor: tokens.color.brand.indigo[400],
    backgroundColor: tokens.color.brand.indigo[900],
  },
  stepperText: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.secondary,
  },
  stepperTextActive: { color: tokens.color.text.primary },
  modalFooter: { flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "flex-end" },
});
