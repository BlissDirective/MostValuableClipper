import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useLocalSearchParams, useRouter, Stack } from "expo-router";
import {
  ChevronLeft,
  Film,
  Pencil,
  Repeat,
  Trash2,
} from "lucide-react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { tokens } from "@/constants/tokens";
import { ActionButton } from "@/components/ActionButton";
import { AccountBadge, Platform } from "@/components/AccountBadge";
import { MetricChip } from "@/components/MetricChip";
import { SafetyFlag, SafetyVariant } from "@/components/SafetyFlag";
import { clipsApi, Clip } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

interface DetailData {
  id: string;
  sourceName: string;
  sourceUrl: string;
  caption: string;
  platforms: { platform: Platform; handle: string; views: string; watchTime: string; earnings: string }[];
  safety?: { variant: SafetyVariant; categories: string[]; reasoning: string; actionTaken: string } | null;
}

const PLACEHOLDER: DetailData = {
  id: "clip-1",
  sourceName: "Design Details · Ep 412",
  sourceUrl: "designdetails.fm/412 · 14:22–14:58",
  caption:
    "The hidden cost of skeuomorphism in modern productivity apps and why nobody talks about it. Three examples, one fix.",
  platforms: [
    { platform: "tiktok", handle: "@studio", views: "12.4K", watchTime: "0:21 avg", earnings: "$1.80" },
    { platform: "instagram", handle: "@studio", views: "8.2K", watchTime: "0:18 avg", earnings: "$0.90" },
    { platform: "youtube", handle: "@studio", views: "3.5K", watchTime: "0:34 avg", earnings: "$0.70" },
  ],
  safety: null,
};

export default function ClipDetailScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ id: string }>();
  const [clipData, setClipData] = useState<Clip | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const doSignOut = useAuthStore((s) => s.doSignOut);

  useEffect(() => {
    if (!params.id) return;
    let cancelled = false;
    setLoading(true);
    clipsApi.getById(params.id)
      .then((res) => {
        if (!cancelled) setClipData(res.data);
      })
      .catch((err) => {
        console.warn("[clip-detail] fetch failed:", err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [params.id]);

  // Map backend Clip to DetailData for rendering
  const clip = useMemo<DetailData>(() => {
    if (clipData) {
      const safety = clipData.safety_flags?.length
        ? {
            variant: "warn" as SafetyVariant,
            categories: clipData.safety_flags,
            reasoning: "Automated safety screening flagged this clip.",
            actionTaken: "Review before posting.",
          }
        : null;
      return {
        id: clipData.id,
        sourceName: clipData.title || "Untitled clip",
        sourceUrl: clipData.video_url || `Clip · ${clipData.id.slice(0, 8)}`,
        caption: clipData.caption || "No caption provided.",
        platforms: [],
        safety,
      };
    }
    return { ...PLACEHOLDER, id: params.id ?? PLACEHOLDER.id };
  }, [clipData, params.id]);

  const handleAction = useCallback(
    async (action: string) => {
      console.log(`[clip-detail] ${action}`, { id: clip.id });
      if (action === "delete") {
        try {
          await clipsApi.delete(clip.id);
          router.back();
        } catch (err: any) {
          console.warn("[clip-detail] delete failed:", err.message);
        }
      }
    },
    [clip.id, router]
  );

  return (
    <>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.root}>
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          <View style={styles.thumb}>
            <Film
              size={tokens.icon.size.xl * 1.5}
              color={tokens.color.text.tertiary}
              strokeWidth={tokens.icon.stroke.thin}
            />
            <SafeAreaView edges={["top"]} style={styles.thumbOverlay} pointerEvents="box-none">
              <Pressable
                onPress={() => router.back()}
                hitSlop={12}
                style={styles.backBtn}
                accessibilityLabel="Back"
              >
                <ChevronLeft
                  size={tokens.icon.size.lg}
                  color={tokens.color.text.primary}
                  strokeWidth={tokens.icon.stroke.default}
                />
              </Pressable>
            </SafeAreaView>
          </View>

          <View style={styles.body}>
            <View style={styles.sourceBlock}>
              <Text style={styles.overline}>SOURCE</Text>
              <Text style={styles.sourceName}>{clip.sourceName}</Text>
              <Text style={styles.sourceUrl}>{clip.sourceUrl}</Text>
            </View>

            <View style={styles.captionBlock}>
              <Text style={styles.overline}>CAPTION</Text>
              <Text style={styles.caption}>{clip.caption}</Text>
            </View>

            {clip.safety ? (
              <View style={styles.safetyBlock}>
                <SafetyFlag
                  variant={clip.safety.variant}
                  categories={clip.safety.categories}
                  actionTaken={clip.safety.actionTaken}
                  size="banner"
                />
                <Text style={styles.safetyBody}>{clip.safety.reasoning}</Text>
              </View>
            ) : null}

            <View style={styles.platformBlock}>
              <Text style={styles.overline}>PER PLATFORM</Text>
              <View style={styles.platformHeader}>
                <Text style={[styles.colLabel, styles.colPlatform]}>Platform</Text>
                <Text style={[styles.colLabel, styles.colMetric]}>Views</Text>
                <Text style={[styles.colLabel, styles.colMetric]}>Watch</Text>
                <Text style={[styles.colLabel, styles.colMetric]}>Earnings</Text>
              </View>
              {clip.platforms.map((p) => (
                <View key={p.platform} style={styles.platformRow}>
                  <View style={styles.colPlatform}>
                    <AccountBadge platform={p.platform} handle={p.handle} variant="pill" />
                  </View>
                  <Text style={[styles.colValue, styles.colMetric]}>{p.views}</Text>
                  <Text style={[styles.colValue, styles.colMetric]}>{p.watchTime}</Text>
                  <Text style={[styles.colValue, styles.colMetric]}>{p.earnings}</Text>
                </View>
              ))}
            </View>

            <View style={styles.metricsBlock}>
              <MetricChip label="Total views" value="24.1K" variant="positive" delta="+18%" style={styles.flex1} />
              <MetricChip label="Retention" value="62%" variant="positive" style={styles.flex1} />
              <MetricChip label="Earnings" value="$3.40" style={styles.flex1} />
            </View>

            <View style={styles.attribution}>
              <Text style={styles.overline}>ATTRIBUTION</Text>
              <Text style={styles.attributionText}>
                Source clipped under fair-use review. Original creator credited in caption per pipeline policy.
              </Text>
            </View>
          </View>
        </ScrollView>

        <SafeAreaView edges={["bottom"]} style={styles.footer}>
          <View style={styles.footerRow}>
            <ActionButton
              label="Edit"
              variant="secondary"
              size="md"
              iconLeft={Pencil}
              onPress={() => handleAction("edit")}
            />
            <ActionButton
              label="Repost"
              variant="primary"
              size="md"
              iconLeft={Repeat}
              onPress={() => handleAction("repost")}
            />
            <ActionButton
              label="Kill"
              variant="danger"
              size="md"
              iconLeft={Trash2}
              onPress={() => handleAction("delete")}
            />
          </View>
        </SafeAreaView>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg.base },
  scroll: { paddingBottom: tokens.spacing.xxxl + tokens.layout.tabBarHeight },
  thumb: {
    aspectRatio: 9 / 16,
    maxHeight: 480,
    width: "100%",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: tokens.color.bg.surface,
    position: "relative",
  },
  thumbOverlay: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
  },
  backBtn: {
    margin: tokens.spacing.md,
    width: tokens.layout.minTouchTarget,
    height: tokens.layout.minTouchTarget,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: tokens.radius.pill,
    backgroundColor: tokens.color.bg.overlay,
  },
  body: {
    padding: tokens.layout.screenPadding,
    gap: tokens.layout.sectionGap,
  },
  overline: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    lineHeight: tokens.type.scale.overline.lineHeight,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.text.tertiary,
    marginBottom: tokens.spacing.xs,
  },
  sourceBlock: { gap: 2 },
  sourceName: {
    fontFamily: tokens.type.scale.h2.family,
    fontSize: tokens.type.scale.h2.size,
    lineHeight: tokens.type.scale.h2.lineHeight,
    letterSpacing: tokens.type.scale.h2.letterSpacing,
    color: tokens.color.text.primary,
  },
  sourceUrl: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  captionBlock: {},
  caption: {
    fontFamily: tokens.type.scale.body.family,
    fontSize: tokens.type.scale.body.size,
    lineHeight: tokens.type.scale.body.lineHeight,
    color: tokens.color.text.primary,
  },
  safetyBlock: {
    gap: tokens.spacing.sm,
  },
  safetyBody: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    lineHeight: tokens.type.scale.bodySmall.lineHeight,
    color: tokens.color.text.secondary,
  },
  platformBlock: {
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    padding: tokens.spacing.md,
  },
  platformHeader: {
    flexDirection: "row",
    paddingBottom: tokens.spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: tokens.color.border.subtle,
  },
  platformRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: tokens.spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: tokens.color.border.subtle,
  },
  colLabel: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  colValue: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    color: tokens.color.text.primary,
  },
  colPlatform: { flex: 1.4 },
  colMetric: { flex: 1, textAlign: "right" },
  metricsBlock: {
    flexDirection: "row",
    gap: tokens.spacing.sm,
  },
  flex1: { flex: 1, minWidth: 0 },
  attribution: {},
  attributionText: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    lineHeight: tokens.type.scale.bodySmall.lineHeight,
    color: tokens.color.text.secondary,
  },
  footer: {
    borderTopWidth: 1,
    borderTopColor: tokens.color.border.subtle,
    backgroundColor: tokens.color.bg.raised,
  },
  footerRow: {
    flexDirection: "row",
    gap: tokens.spacing.sm,
    padding: tokens.layout.screenPadding,
  },
});
