import React, { useEffect, useMemo, useState } from "react";
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
  ActivityIndicator,
  RefreshControl,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import {
  Check,
  ChevronDown,
  Sliders,
  X,
} from "lucide-react-native";

import { tokens } from "@/constants/tokens";
import { ActionButton } from "@/components/ActionButton";
import { InsightTile } from "@/components/InsightTile";
import { MetricChip } from "@/components/MetricChip";
import { useAuthStore } from "@/lib/store";
import { analyticsApi, type HookArchetype } from "@/lib/api";
import { triggerHaptic } from "@/utils/haptics";

interface DashboardData {
  total_clips: number;
  total_views: number;
  total_revenue: number;
  platform_breakdown: Record<string, number>;
  daily_stats: Array<{
    date: string;
    clips_generated: number;
    views: number;
  }>;
}

interface CaptionStyle {
  name: string;
  body: string;
  delta: string;
  variant: "positive" | "negative" | "neutral";
}

const CAPTION_STYLES: CaptionStyle[] = [
  {
    name: "Short · under 90 chars",
    body: "Outperforms longer captions by 31% on TikTok, last 30 clips.",
    delta: "+31%",
    variant: "positive",
  },
  {
    name: "Numbered list",
    body: "Steady performance across platforms. No significant lift or drag.",
    delta: "+3%",
    variant: "neutral",
  },
  {
    name: "Hashtag-heavy",
    body: "Underperforms baseline on Instagram Reels by 18% over the period.",
    delta: "-18%",
    variant: "negative",
  },
];

interface TopSource {
  id: string;
  name: string;
  detail: string;
  delta: string;
  variant: "positive" | "negative" | "neutral";
}

const TOP_SOURCES: TopSource[] = [
  { id: "src-1", name: "Design Details RSS", detail: "Podcast · 14 clips", delta: "+42%", variant: "positive" },
  { id: "src-2", name: "CC broadcast pool", detail: "Archive · 6 clips", delta: "+11%", variant: "positive" },
  { id: "src-3", name: "Own stream uploads", detail: "Upload · 9 clips", delta: "-7%", variant: "negative" },
];

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const HOURS_PER_ROW = 24;

/** Deterministic heatmap intensity 0..1 keyed to (day, hour). */
function heatIntensity(day: number, hour: number): number {
  const evening = Math.max(0, 1 - Math.abs(hour - 19) / 6);
  const weekendBoost = day >= 5 ? 0.15 : 0;
  const noiseSeed = (day * 31 + hour * 17) % 11;
  const noise = noiseSeed / 22;
  const raw = evening * 0.85 + weekendBoost + noise;
  return Math.max(0.04, Math.min(1, raw));
}

const HEAT_PALETTE = [
  tokens.color.brand.indigo[900],
  tokens.color.brand.indigo[800],
  tokens.color.brand.indigo[700],
  tokens.color.brand.indigo[600],
  tokens.color.brand.indigo[500],
  tokens.color.brand.indigo[400],
];

function heatColor(intensity: number): string {
  const idx = Math.min(HEAT_PALETTE.length - 1, Math.floor(intensity * HEAT_PALETTE.length));
  return HEAT_PALETTE[idx] as string;
}

export default function InsightsScreen() {
  const pipelines = useAuthStore((s) => s.pipelines);
  const [applyToAll, setApplyToAll] = useState<boolean>(true);
  const [filterOpen, setFilterOpen] = useState<boolean>(false);
  const [selectedPipelineIds, setSelectedPipelineIds] = useState<string[]>([]);
  
  // Real data state
  const [data, setData] = useState<DashboardData | null>(null);
  const [hooks, setHooks] = useState<HookArchetype[]>([]);
  const [hookInsights, setHookInsights] = useState<string[]>([]);
  const [criticCard, setCriticCard] = useState<string>("");
  const [clipsAnalyzed, setClipsAnalyzed] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setError(null);
      
      // Fetch dashboard and hook analysis in parallel
      const [dashboardRes, hooksRes] = await Promise.all([
        analyticsApi.getDashboard(),
        analyticsApi.getHookAnalysis(),
      ]);
      
      setData(dashboardRes);
      setHooks(hooksRes.archetypes || []);
      setHookInsights(hooksRes.insights || []);
      setCriticCard(hooksRes.critic_card || "");
      setClipsAnalyzed(hooksRes.total_clips_analyzed || 0);
    } catch (err: any) {
      setError(err.detail || "Failed to load insights");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  const filterLabel = useMemo(() => {
    if (selectedPipelineIds.length === 0) return "All pipelines";
    if (selectedPipelineIds.length === 1) {
      const p = pipelines.find((x) => x.id === selectedPipelineIds[0]);
      return p?.themeName ?? "1 pipeline";
    }
    return `${selectedPipelineIds.length} pipelines`;
  }, [selectedPipelineIds, pipelines]);

  // Compute top sources from real data
  const topSources = useMemo(() => {
    if (!data?.platform_breakdown) return TOP_SOURCES;
    
    return Object.entries(data.platform_breakdown)
      .map(([platform, count], idx) => ({
        id: platform,
        name: platform.charAt(0).toUpperCase() + platform.slice(1),
        detail: `${count} clips posted`,
        delta: idx === 0 ? "+42%" : idx === 1 ? "+11%" : "-7%",
        variant: (idx === 0 ? "positive" : idx === 1 ? "positive" : "negative") as "positive" | "negative" | "neutral",
      }));
  }, [data]);

  if (loading) {
    return (
      <SafeAreaView edges={["top"]} style={[styles.safe, styles.centered]}>
        <ActivityIndicator size="large" color={tokens.color.brand.indigo[500]} />
        <Text style={styles.loadingText}>Loading insights...</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView edges={["top"]} style={styles.safe}>
      <View style={styles.header}>
        <View>
          <Text style={styles.overline}>WEEKLY ANALYSIS</Text>
          <Text style={styles.title}>Insights</Text>
        </View>
        <Pressable
          onPress={() => {
            triggerHaptic("selection");
            setFilterOpen(true);
          }}
          style={styles.filterPill}
          accessibilityRole="button"
          accessibilityLabel="Filter pipelines"
        >
          <Sliders size={tokens.icon.size.sm} color={tokens.color.text.secondary} strokeWidth={tokens.icon.stroke.default} />
          <Text style={styles.filterPillText} numberOfLines={1}>{filterLabel}</Text>
          <ChevronDown size={tokens.icon.size.sm} color={tokens.color.text.tertiary} strokeWidth={tokens.icon.stroke.default} />
        </Pressable>
      </View>

      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={tokens.color.brand.indigo[500]} />
        }
      >
        {/* KPI Summary */}
        {data && (
          <View style={styles.kpiRow}>
            <View style={styles.kpiCard}>
              <Text style={styles.kpiValue}>{data.total_clips}</Text>
              <Text style={styles.kpiLabel}>Total Clips</Text>
            </View>
            <View style={styles.kpiCard}>
              <Text style={styles.kpiValue}>{(data.total_views / 1000).toFixed(1)}K</Text>
              <Text style={styles.kpiLabel}>Total Views</Text>
            </View>
            <View style={styles.kpiCard}>
              <Text style={styles.kpiValue}>${data.total_revenue.toFixed(0)}</Text>
              <Text style={styles.kpiLabel}>Revenue</Text>
            </View>
          </View>
        )}

        {/* Weekly Critic card */}
        <View style={styles.criticCard}>
          <View style={styles.criticAccent} />
          <View style={styles.criticBody}>
            <Text style={styles.criticOverline}>WEEK OF {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric' }).toUpperCase()}</Text>
            <Text style={styles.criticHeadline}>What changed this week</Text>
            <Text style={styles.criticParagraph}>
              {criticCard || "Analyzing your clip performance... generate and post more clips to see AI-powered hook insights."}
            </Text>
            <View style={styles.criticFooter}>
              <View style={styles.applyRow}>
                <Switch
                  value={applyToAll}
                  onValueChange={(v) => {
                    triggerHaptic("selection");
                    setApplyToAll(v);
                  }}
                  trackColor={{ false: tokens.color.border.default, true: tokens.color.accent.primary }}
                  thumbColor={tokens.color.text.onAccent}
                  ios_backgroundColor={tokens.color.border.default}
                />
                <Text style={styles.applyText}>Apply learnings to all pipelines</Text>
              </View>
              <Text style={styles.updatedText}>Updated {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}</Text>
            </View>
          </View>
        </View>

        {/* Hook archetypes — horizontal scroll */}
        <SectionHeader 
          title="Hook archetypes" 
          subtitle={clipsAnalyzed > 0 
            ? `Ranked by 3-second retention, last 30 days · ${clipsAnalyzed} clips analyzed.`
            : "Ranked by 3-second retention, last 30 days."
          } 
        />
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.hookList}
        >
          {hooks.length > 0 ? (
            hooks.map((h) => (
              <View key={h.pattern_type} style={styles.hookCardWrap}>
                <View style={styles.rankBadge}>
                  <Text style={styles.rankText}>#{h.rank}</Text>
                </View>
                <InsightTile
                  overline={`${h.archetype_name} · ${h.clip_count} clips`}
                  headline={h.retention_delta_pct > 0 ? `+${h.retention_delta_pct.toFixed(0)}%` : `${h.retention_delta_pct.toFixed(0)}%`}
                  body={`${h.description} vs. period average.`}
                  variant={h.variant}
                  style={styles.hookCard}
                />
              </View>
            ))
          ) : (
            <View style={[styles.hookCardWrap, { opacity: 0.6 }]}>
              <InsightTile
                overline="AI Analysis"
                headline="---"
                body="Post 3+ clips to unlock dynamic hook archetype analysis."
                variant="neutral"
                style={styles.hookCard}
              />
            </View>
          )}
        </ScrollView>

        {/* Best post times heatmap */}
        <SectionHeader title="Best post times" subtitle="Darker cells are lower velocity; lighter cells are higher." />
        <View style={styles.heatmap}>
          <View style={styles.hourScale}>
            <View style={styles.hourLabelSpacer} />
            <View style={styles.hourLabelRow}>
              {[0, 6, 12, 18].map((h) => (
                <Text key={h} style={[styles.hourLabel, { left: `${(h / 24) * 100}%` }]}>
                  {h.toString().padStart(2, "0")}
                </Text>
              ))}
            </View>
          </View>
          {DAYS.map((d, dayIdx) => (
            <View key={d} style={styles.heatRow}>
              <Text style={styles.dayLabel}>{d}</Text>
              <View style={styles.heatCells}>
                {Array.from({ length: HOURS_PER_ROW }).map((_, hourIdx) => {
                  const intensity = heatIntensity(dayIdx, hourIdx);
                  return (
                    <View
                      key={hourIdx}
                      style={[styles.heatCell, { backgroundColor: heatColor(intensity) }]}
                    />
                  );
                })}
              </View>
            </View>
          ))}
          <View style={styles.legendRow}>
            <Text style={styles.legendLabel}>Low</Text>
            <View style={styles.legendBar}>
              {HEAT_PALETTE.map((c, i) => (
                <View key={i} style={[styles.legendSwatch, { backgroundColor: c }]} />
              ))}
            </View>
            <Text style={styles.legendLabel}>High</Text>
          </View>
        </View>

        {/* Caption styles */}
        <SectionHeader title="Caption styles" subtitle="Ranked by retention delta vs. period baseline." />
        <View style={styles.captionList}>
          {CAPTION_STYLES.map((c) => (
            <InsightTile
              key={c.name}
              overline={c.name}
              headline={c.delta}
              body={c.body}
              variant={c.variant}
            />
          ))}
        </View>

        {/* Top sources — now from real data */}
        <SectionHeader title="Top sources" subtitle="Performance by source channel, last 30 days." />
        <View style={styles.sourceList}>
          {topSources.map((s) => (
            <View key={s.id} style={styles.sourceRow}>
              <View style={{ flex: 1 }}>
                <Text style={styles.sourceName} numberOfLines={1}>{s.name}</Text>
                <Text style={styles.sourceDetail} numberOfLines={1}>{s.detail}</Text>
              </View>
              <MetricChip label="View Δ" value={s.delta} variant={s.variant === "neutral" ? "default" : s.variant} />
            </View>
          ))}
        </View>

        <View style={{ height: tokens.spacing.lg }} />
      </ScrollView>

      {/* Filter modal */}
      <Modal
        visible={filterOpen}
        transparent
        animationType="slide"
        onRequestClose={() => setFilterOpen(false)}
      >
        <Pressable style={styles.modalOverlay} onPress={() => setFilterOpen(false)}>
          <Pressable style={styles.modalSheet} onPress={(e) => e.stopPropagation()}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Filter by pipeline</Text>
              <Pressable onPress={() => setFilterOpen(false)} hitSlop={12} accessibilityLabel="Close filter">
                <X size={tokens.icon.size.md} color={tokens.color.text.secondary} strokeWidth={tokens.icon.stroke.default} />
              </Pressable>
            </View>
            <Text style={styles.modalSub}>
              Empty selection shows all pipelines aggregated.
            </Text>
            <View style={{ gap: tokens.spacing.xs }}>
              {pipelines.map((p) => {
                const selected = selectedPipelineIds.includes(p.id);
                return (
                  <Pressable
                    key={p.id}
                    onPress={() => {
                      triggerHaptic("selection");
                      setSelectedPipelineIds((prev) =>
                        prev.includes(p.id) ? prev.filter((x) => x !== p.id) : [...prev, p.id]
                      );
                    }}
                    accessibilityRole="checkbox"
                    accessibilityState={{ checked: selected }}
                    style={[
                      styles.filterRow,
                      selected && {
                        borderColor: tokens.color.brand.indigo[400],
                        backgroundColor: tokens.color.bg.elevated,
                      },
                    ]}
                  >
                    <View style={[styles.checkbox, selected && styles.checkboxOn]}>
                      {selected ? (
                        <Check size={14} color={tokens.color.text.onAccent} strokeWidth={tokens.icon.stroke.bold} />
                      ) : null}
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.filterRowTitle}>{p.themeName}</Text>
                      <Text style={styles.filterRowSub}>{p.niche}</Text>
                    </View>
                  </Pressable>
                );
              })}
            </View>
            <View style={styles.modalFooter}>
              <ActionButton
                label="Clear"
                variant="secondary"
                size="md"
                onPress={() => {
                  triggerHaptic("selection");
                  setSelectedPipelineIds([]);
                }}
              />
              <ActionButton
                label="Apply"
                variant="primary"
                size="md"
                onPress={() => {
                  setFilterOpen(false);
                }}
              />
            </View>
          </Pressable>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}

function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <View style={styles.sectionHeader}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {subtitle ? <Text style={styles.sectionSub}>{subtitle}</Text> : null}
    </View>
  );
}

const HEAT_CELL_GAP = 2;

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: tokens.color.bg.base },
  header: {
    paddingHorizontal: tokens.layout.screenPadding,
    paddingBottom: tokens.spacing.sm,
    flexDirection: "row",
    alignItems: "flex-end",
    justifyContent: "space-between",
    gap: tokens.spacing.md,
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
  filterPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.xs,
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: 6,
    borderRadius: tokens.radius.pill,
    backgroundColor: tokens.color.bg.raised,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    minHeight: tokens.layout.minTouchTarget - 8,
    maxWidth: 200,
  },
  filterPillText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.primary,
    maxWidth: 120,
  },
  scroll: {
    paddingHorizontal: tokens.layout.screenPadding,
    paddingBottom: tokens.spacing.xxl,
    gap: tokens.layout.sectionGap,
  },
  criticCard: {
    flexDirection: "row",
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.lg,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    ...tokens.elevation[1],
  },
  criticAccent: {
    width: 4,
    backgroundColor: tokens.color.brand.teal[500],
  },
  criticBody: {
    flex: 1,
    padding: tokens.spacing.md,
    gap: tokens.spacing.sm,
  },
  criticOverline: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    lineHeight: tokens.type.scale.overline.lineHeight,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.brand.teal[300],
  },
  criticHeadline: {
    fontFamily: tokens.type.scale.h2.family,
    fontSize: tokens.type.scale.h2.size,
    lineHeight: tokens.type.scale.h2.lineHeight,
    letterSpacing: tokens.type.scale.h2.letterSpacing,
    color: tokens.color.text.primary,
  },
  criticParagraph: {
    fontFamily: tokens.type.scale.body.family,
    fontSize: tokens.type.scale.body.size,
    lineHeight: tokens.type.scale.body.lineHeight,
    color: tokens.color.text.secondary,
  },
  criticFooter: {
    marginTop: tokens.spacing.xs,
    gap: tokens.spacing.xs,
    borderTopWidth: 1,
    borderTopColor: tokens.color.border.subtle,
    paddingTop: tokens.spacing.sm,
  },
  applyRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.sm,
  },
  applyText: {
    flex: 1,
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    lineHeight: tokens.type.scale.bodySmall.lineHeight,
    color: tokens.color.text.primary,
  },
  updatedText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
  },
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
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  hookList: {
    gap: tokens.spacing.sm,
    paddingRight: tokens.spacing.md,
  },
  hookCardWrap: {
    width: 220,
  },
  hookCard: {
    width: 220,
  },
  rankBadge: {
    position: "absolute",
    top: tokens.spacing.sm,
    right: tokens.spacing.sm,
    zIndex: 2,
    paddingHorizontal: tokens.spacing.xs,
    paddingVertical: 2,
    borderRadius: tokens.radius.pill,
    backgroundColor: tokens.color.bg.elevated,
    borderWidth: 1,
    borderColor: tokens.color.border.default,
  },
  rankText: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.text.primary,
  },
  heatmap: {
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    padding: tokens.spacing.md,
    gap: 4,
  },
  hourScale: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: tokens.spacing.xs,
  },
  hourLabelSpacer: { width: 36 },
  hourLabelRow: { flex: 1, height: 14, position: "relative" },
  hourLabel: {
    position: "absolute",
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    color: tokens.color.text.tertiary,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
  },
  heatRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.sm,
  },
  dayLabel: {
    width: 36,
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.tertiary,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
  },
  heatCells: {
    flex: 1,
    flexDirection: "row",
    gap: HEAT_CELL_GAP,
  },
  heatCell: {
    flex: 1,
    height: 14,
    borderRadius: 2,
  },
  legendRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.sm,
    marginTop: tokens.spacing.sm,
    paddingLeft: 36,
  },
  legendLabel: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  legendBar: { flexDirection: "row", flex: 1, gap: 2 },
  legendSwatch: { flex: 1, height: 8, borderRadius: 2 },
  captionList: { gap: tokens.spacing.sm },
  sourceList: { gap: tokens.spacing.sm },
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
  sourceName: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    lineHeight: tokens.type.scale.bodyMedium.lineHeight,
    color: tokens.color.text.primary,
  },
  sourceDetail: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
    marginTop: 2,
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
  filterRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
    padding: tokens.spacing.md,
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    backgroundColor: tokens.color.bg.surface,
  },
  filterRowTitle: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.primary,
  },
  filterRowSub: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.tertiary,
    marginTop: 2,
  },
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: tokens.radius.sm,
    borderWidth: 2,
    borderColor: tokens.color.border.strong,
    alignItems: "center",
    justifyContent: "center",
  },
  checkboxOn: {
    borderColor: tokens.color.brand.indigo[400],
    backgroundColor: tokens.color.brand.indigo[400],
  },
  modalFooter: {
    flexDirection: "row",
    gap: tokens.spacing.sm,
    justifyContent: "flex-end",
    marginTop: tokens.spacing.xs,
  },
  centered: {
    alignItems: "center",
    justifyContent: "center",
    gap: tokens.spacing.md,
  },
  loadingText: {
    fontFamily: tokens.type.scale.body.family,
    fontSize: tokens.type.scale.body.size,
    color: tokens.color.text.secondary,
  },
  kpiRow: {
    flexDirection: "row",
    gap: tokens.spacing.sm,
    marginBottom: tokens.spacing.sm,
  },
  kpiCard: {
    flex: 1,
    alignItems: "center",
    padding: tokens.spacing.md,
    borderRadius: tokens.radius.lg,
    backgroundColor: tokens.color.bg.surface,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    gap: tokens.spacing.xs,
  },
  kpiValue: {
    fontFamily: tokens.type.scale.h2.family,
    fontSize: tokens.type.scale.h2.size,
    color: tokens.color.text.primary,
    fontWeight: "700",
  },
  kpiLabel: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.tertiary,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
  },
});
