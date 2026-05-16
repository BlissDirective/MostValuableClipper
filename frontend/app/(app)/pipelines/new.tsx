import React, { useCallback, useMemo, useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";
import { Stack, useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import {
  Check,
  ChevronLeft,
  Hand,
  Lock,
  LucideIcon,
  Pencil,
  Zap,
} from "lucide-react-native";

import { tokens } from "@/constants/tokens";
import { ActionButton } from "@/components/ActionButton";
import {
  AutonomyMode,
  DEFAULT_WARNING_CATEGORIES,
  Pipeline,
  PlatformKey,
  useAuthStore,
} from "@/lib/store";
import { triggerHaptic } from "@/utils/haptics";

const PLATFORMS: { key: PlatformKey; label: string }[] = [
  { key: "tiktok", label: "TikTok" },
  { key: "instagram", label: "Instagram" },
  { key: "youtube", label: "YouTube" },
];

const AUTONOMY_OPTIONS: { key: AutonomyMode; title: string; body: string; icon: LucideIcon; tint: string }[] = [
  {
    key: "fullAuto",
    title: "Full Auto",
    body: "Generated and posted on schedule.",
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
    body: "Proposes clips; you publish manually.",
    icon: Pencil,
    tint: tokens.color.semantic.autonomy.suggestOnly,
  },
];

const TOTAL_STEPS = 5;

export default function NewPipelineScreen() {
  const router = useRouter();
  const addPipeline = useAuthStore((s) => s.addPipeline);

  const [step, setStep] = useState<number>(1);
  const [theme, setTheme] = useState<string>("");
  const [creatorLicensed, setCreatorLicensed] = useState<boolean>(true);
  const [ccArchive, setCcArchive] = useState<boolean>(false);
  const [clipsPerDay, setClipsPerDay] = useState<number>(3);
  const [platforms, setPlatforms] = useState<PlatformKey[]>(["tiktok", "instagram"]);
  const [autonomy, setAutonomy] = useState<AutonomyMode>("fullAuto");

  const canNext = useMemo(() => {
    if (step === 1) return theme.trim().length >= 3;
    if (step === 3) return platforms.length > 0;
    return true;
  }, [step, theme, platforms]);

  const onCancel = useCallback(() => {
    router.back();
  }, [router]);

  const onBack = useCallback(() => {
    if (step === 1) {
      onCancel();
      return;
    }
    triggerHaptic("selection");
    setStep((s) => s - 1);
  }, [step, onCancel]);

  const onNext = useCallback(() => {
    if (!canNext) return;
    triggerHaptic("selection");
    setStep((s) => Math.min(TOTAL_STEPS, s + 1));
  }, [canNext]);

  const onActivate = useCallback(() => {
    const next: Pipeline = {
      id: `pipeline-${Date.now()}`,
      themeName: theme.trim(),
      niche: "Custom theme",
      status: "running",
      clipsThisWeek: 0,
      viewDelta: "—",
      deltaVariant: "default",
      clipsPerDay,
      platforms,
      autonomy,
      resolverOn: true,
      retention: "moderate",
      warningCategories: DEFAULT_WARNING_CATEGORIES,
      sources: [],
      sourcePlan: { uploads: true, creatorLicensed, ccArchive },
    };
    addPipeline(next);
    router.replace("/(app)/pipelines");
  }, [theme, clipsPerDay, platforms, autonomy, creatorLicensed, ccArchive, addPipeline, router]);

  return (
    <View style={styles.root}>
      <Stack.Screen options={{ headerShown: false }} />
      <SafeAreaView edges={["top"]} style={styles.safe}>
        <View style={styles.topBar}>
          <Pressable onPress={onBack} hitSlop={12} style={styles.iconBtn} accessibilityLabel="Back">
            <ChevronLeft size={tokens.icon.size.lg} color={tokens.color.text.primary} strokeWidth={tokens.icon.stroke.default} />
          </Pressable>
          <View style={styles.stepIndicator}>
            <Text style={styles.stepText}>Step {step} of {TOTAL_STEPS}</Text>
            <View style={styles.progressTrack}>
              <View style={[styles.progressFill, { width: `${(step / TOTAL_STEPS) * 100}%` }]} />
            </View>
          </View>
          <Pressable onPress={onCancel} hitSlop={12} style={styles.iconBtn} accessibilityLabel="Cancel">
            <Text style={styles.cancelText}>Cancel</Text>
          </Pressable>
        </View>

        <KeyboardAvoidingView
          style={styles.flex}
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          keyboardVerticalOffset={tokens.spacing.lg}
        >
          <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
            {step === 1 ? (
              <Step1 theme={theme} setTheme={setTheme} />
            ) : step === 2 ? (
              <Step2
                creatorLicensed={creatorLicensed}
                ccArchive={ccArchive}
                setCreatorLicensed={setCreatorLicensed}
                setCcArchive={setCcArchive}
              />
            ) : step === 3 ? (
              <Step3
                clipsPerDay={clipsPerDay}
                setClipsPerDay={setClipsPerDay}
                platforms={platforms}
                setPlatforms={setPlatforms}
              />
            ) : step === 4 ? (
              <Step4 autonomy={autonomy} setAutonomy={setAutonomy} />
            ) : (
              <Step5
                theme={theme}
                creatorLicensed={creatorLicensed}
                ccArchive={ccArchive}
                clipsPerDay={clipsPerDay}
                platforms={platforms}
                autonomy={autonomy}
              />
            )}
          </ScrollView>

          <View style={styles.footer}>
            {step < TOTAL_STEPS ? (
              <ActionButton
                label="Continue"
                variant="primary"
                size="lg"
                fullWidth
                disabled={!canNext}
                onPress={onNext}
              />
            ) : (
              <ActionButton
                label="Activate pipeline"
                variant="primary"
                size="lg"
                fullWidth
                onPress={onActivate}
              />
            )}
          </View>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </View>
  );
}

function Step1({ theme, setTheme }: { theme: string; setTheme: (v: string) => void }) {
  return (
    <View style={styles.stepBody}>
      <Text style={styles.h1}>What do you want to clip?</Text>
      <Text style={styles.sub}>A creator, a topic, an event. Anything.</Text>
      <TextInput
        value={theme}
        onChangeText={setTheme}
        multiline
        placeholder="e.g. design podcasts, F1 highlights, my own streams"
        placeholderTextColor={tokens.color.text.tertiary}
        style={styles.input}
        autoFocus
        selectionColor={tokens.color.accent.primary}
      />
      <Text style={styles.note}>We&apos;ll resolve sources after you continue.</Text>
    </View>
  );
}

function Step2({
  creatorLicensed,
  ccArchive,
  setCreatorLicensed,
  setCcArchive,
}: {
  creatorLicensed: boolean;
  ccArchive: boolean;
  setCreatorLicensed: (v: boolean) => void;
  setCcArchive: (v: boolean) => void;
}) {
  return (
    <View style={styles.stepBody}>
      <Text style={styles.h1}>Source plan</Text>
      <Text style={styles.sub}>What we&apos;d resolve for this theme.</Text>

      <View style={styles.sourceCard}>
        <View style={{ flex: 1, gap: 2 }}>
          <View style={styles.sourceTitleRow}>
            <Text style={styles.sourceTitle}>User uploads</Text>
            <View style={styles.lockChip}>
              <Lock size={tokens.icon.size.xs} color={tokens.color.text.tertiary} strokeWidth={tokens.icon.stroke.default} />
              <Text style={styles.lockText}>Always on</Text>
            </View>
          </View>
          <Text style={styles.sourceBody}>Files you upload directly. The foundation of every pipeline.</Text>
        </View>
      </View>

      <View style={styles.sourceCard}>
        <View style={{ flex: 1, gap: 2 }}>
          <Text style={styles.sourceTitle}>Creator-licensed sources</Text>
          <Text style={styles.sourceBody}>Partner catalogs and RSS feeds with explicit clipping permission.</Text>
        </View>
        <Switch
          value={creatorLicensed}
          onValueChange={(v) => {
            triggerHaptic("selection");
            setCreatorLicensed(v);
          }}
          trackColor={{ false: tokens.color.border.default, true: tokens.color.accent.primary }}
          thumbColor={tokens.color.text.onAccent}
          ios_backgroundColor={tokens.color.border.default}
        />
      </View>

      <View style={styles.sourceCard}>
        <View style={{ flex: 1, gap: 2 }}>
          <Text style={styles.sourceTitle}>Public-domain &amp; Creative Commons</Text>
          <Text style={styles.sourceBody}>Open archives with attribution. Lower volume, fully safe to clip.</Text>
        </View>
        <Switch
          value={ccArchive}
          onValueChange={(v) => {
            triggerHaptic("selection");
            setCcArchive(v);
          }}
          trackColor={{ false: tokens.color.border.default, true: tokens.color.accent.primary }}
          thumbColor={tokens.color.text.onAccent}
          ios_backgroundColor={tokens.color.border.default}
        />
      </View>

      <Text style={styles.note}>
        URL-based sources are not part of this MVP. Add files or licensed feeds only.
      </Text>
    </View>
  );
}

function Step3({
  clipsPerDay,
  setClipsPerDay,
  platforms,
  setPlatforms,
}: {
  clipsPerDay: number;
  setClipsPerDay: (n: number) => void;
  platforms: PlatformKey[];
  setPlatforms: (p: PlatformKey[]) => void;
}) {
  const togglePlatform = (k: PlatformKey) => {
    triggerHaptic("selection");
    setPlatforms(platforms.includes(k) ? platforms.filter((p) => p !== k) : [...platforms, k]);
  };
  return (
    <View style={styles.stepBody}>
      <Text style={styles.h1}>Cadence</Text>
      <Text style={styles.sub}>How many clips per day, and where they post.</Text>

      <Text style={styles.label}>Clips per day · {clipsPerDay}</Text>
      <View style={styles.stepperRow}>
        {[1, 2, 3, 4, 5, 6, 8, 10].map((n) => {
          const active = clipsPerDay === n;
          return (
            <Pressable
              key={n}
              onPress={() => {
                triggerHaptic("selection");
                setClipsPerDay(n);
              }}
              style={[styles.stepper, active && styles.stepperActive]}
            >
              <Text style={[styles.stepperText, active && styles.stepperTextActive]}>{n}</Text>
            </Pressable>
          );
        })}
      </View>

      <Text style={styles.label}>Platforms</Text>
      <View style={styles.platformChips}>
        {PLATFORMS.map((p) => {
          const active = platforms.includes(p.key);
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
  );
}

function Step4({
  autonomy,
  setAutonomy,
}: {
  autonomy: AutonomyMode;
  setAutonomy: (m: AutonomyMode) => void;
}) {
  return (
    <View style={styles.stepBody}>
      <Text style={styles.h1}>Autonomy</Text>
      <Text style={styles.sub}>You can change this later for any pipeline.</Text>

      <View style={{ gap: tokens.spacing.sm }}>
        {AUTONOMY_OPTIONS.map((o) => {
          const selected = autonomy === o.key;
          const Icon = o.icon;
          return (
            <Pressable
              key={o.key}
              onPress={() => {
                triggerHaptic("selection");
                setAutonomy(o.key);
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
    </View>
  );
}

function Step5({
  theme,
  creatorLicensed,
  ccArchive,
  clipsPerDay,
  platforms,
  autonomy,
}: {
  theme: string;
  creatorLicensed: boolean;
  ccArchive: boolean;
  clipsPerDay: number;
  platforms: PlatformKey[];
  autonomy: AutonomyMode;
}) {
  const platformLabel =
    platforms.length === 0
      ? "None"
      : platforms.map((p) => PLATFORMS.find((x) => x.key === p)?.label ?? p).join(" · ");
  const autonomyLabel = AUTONOMY_OPTIONS.find((a) => a.key === autonomy)?.title ?? autonomy;
  const sourceLines = [
    "User uploads",
    creatorLicensed ? "Creator-licensed sources" : null,
    ccArchive ? "Public-domain & CC archives" : null,
  ].filter(Boolean) as string[];

  return (
    <View style={styles.stepBody}>
      <Text style={styles.h1}>Review</Text>
      <Text style={styles.sub}>Confirm and activate. You can edit any of this from the pipeline later.</Text>

      <View style={styles.reviewCard}>
        <ReviewRow label="THEME" value={theme.trim()} />
        <ReviewRow label="SOURCES" value={sourceLines.join(", ")} />
        <ReviewRow label="CADENCE" value={`${clipsPerDay} clips/day`} />
        <ReviewRow label="PLATFORMS" value={platformLabel} />
        <ReviewRow label="AUTONOMY" value={autonomyLabel} />
      </View>
    </View>
  );
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.reviewRow}>
      <Text style={styles.reviewLabel}>{label}</Text>
      <Text style={styles.reviewValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg.base },
  safe: { flex: 1 },
  flex: { flex: 1 },
  topBar: {
    height: tokens.layout.headerHeight,
    paddingHorizontal: tokens.spacing.sm,
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.sm,
  },
  iconBtn: {
    minWidth: tokens.layout.minTouchTarget,
    height: tokens.layout.minTouchTarget,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: tokens.spacing.sm,
  },
  cancelText: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodySmall.size,
    color: tokens.color.text.secondary,
  },
  stepIndicator: { flex: 1, gap: tokens.spacing.xs },
  stepText: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.text.tertiary,
    textAlign: "center",
  },
  progressTrack: {
    height: 4,
    borderRadius: tokens.radius.pill,
    backgroundColor: tokens.color.border.subtle,
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    backgroundColor: tokens.color.brand.indigo[400],
  },
  scroll: {
    paddingHorizontal: tokens.layout.screenPadding,
    paddingBottom: tokens.spacing.xl,
  },
  stepBody: { gap: tokens.spacing.md },
  h1: {
    fontFamily: tokens.type.scale.h1.family,
    fontSize: tokens.type.scale.h1.size,
    lineHeight: tokens.type.scale.h1.lineHeight,
    letterSpacing: tokens.type.scale.h1.letterSpacing,
    color: tokens.color.text.primary,
    marginTop: tokens.spacing.md,
  },
  sub: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    lineHeight: tokens.type.scale.bodySmall.lineHeight,
    color: tokens.color.text.secondary,
  },
  input: {
    minHeight: 120,
    backgroundColor: tokens.color.bg.surface,
    borderWidth: 1,
    borderColor: tokens.color.border.default,
    borderRadius: tokens.radius.lg,
    padding: tokens.spacing.md,
    fontFamily: tokens.type.scale.body.family,
    fontSize: tokens.type.scale.body.size,
    lineHeight: tokens.type.scale.body.lineHeight,
    color: tokens.color.text.primary,
    textAlignVertical: "top",
  },
  note: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  label: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.text.tertiary,
    textTransform: "uppercase",
    marginTop: tokens.spacing.sm,
  },
  sourceCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
    padding: tokens.spacing.md,
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
  },
  sourceTitleRow: { flexDirection: "row", alignItems: "center", gap: tokens.spacing.sm },
  sourceTitle: {
    fontFamily: tokens.type.scale.h3.family,
    fontSize: tokens.type.scale.h3.size,
    color: tokens.color.text.primary,
  },
  sourceBody: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.secondary,
  },
  lockChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.xs,
    paddingHorizontal: tokens.spacing.xs,
    paddingVertical: 2,
    borderRadius: tokens.radius.pill,
    backgroundColor: tokens.color.bg.raised,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
  },
  lockText: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: 10,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.text.tertiary,
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
  platformChips: { flexDirection: "row", gap: tokens.spacing.xs, flexWrap: "wrap" },
  platformChip: {
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    borderRadius: tokens.radius.pill,
    borderWidth: 1,
    borderColor: tokens.color.border.default,
    backgroundColor: tokens.color.bg.raised,
  },
  platformChipText: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodySmall.size,
    color: tokens.color.text.secondary,
  },
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
  reviewCard: {
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    overflow: "hidden",
  },
  reviewRow: {
    paddingVertical: tokens.spacing.md,
    paddingHorizontal: tokens.spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: tokens.color.border.subtle,
    gap: 4,
  },
  reviewLabel: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  reviewValue: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.primary,
  },
  footer: {
    paddingHorizontal: tokens.layout.screenPadding,
    paddingVertical: tokens.spacing.md,
    borderTopWidth: 1,
    borderTopColor: tokens.color.border.subtle,
    backgroundColor: tokens.color.bg.base,
  },
});
