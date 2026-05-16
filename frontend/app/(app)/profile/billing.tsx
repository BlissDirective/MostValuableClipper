import React, { useCallback, useEffect, useState } from "react";
import { Alert, Linking, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { Stack, useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { Check, ChevronLeft, ExternalLink, Sparkles } from "lucide-react-native";

import { tokens } from "@/constants/tokens";
import { ActionButton } from "@/components/ActionButton";
import { useAuthStore } from "@/lib/store";
import { subscriptionsApi } from "@/lib/api";

interface TierFeature {
  label: string;
  basic: string | boolean;
  premium: string | boolean;
}

const FEATURES: TierFeature[] = [
  { label: "Active pipelines", basic: "2", premium: "10" },
  { label: "Accounts per platform", basic: "1", premium: "5" },
  { label: "Clips / month", basic: "50", premium: "500" },
  { label: "Autonomy modes", basic: "Approve · Suggest", premium: "Full Auto · Approve · Suggest" },
  { label: "Posting platforms", basic: "TikTok · IG", premium: "TikTok · IG · YouTube · FB" },
  { label: "Caption styles", basic: "3 presets", premium: "Custom + presets" },
  { label: "Learning loop depth", basic: "Per-pipeline", premium: "Cross-pipeline + cohort" },
  { label: "Support tier", basic: "Community", premium: "Priority" },
];

export default function BillingScreen() {
  const router = useRouter();
  const subscriptionTier = useAuthStore((s) => s.subscriptionTier);
  const fetchSubscription = useAuthStore((s) => s.fetchSubscription);
  const [loading, setLoading] = useState<string | null>(null);

  useEffect(() => {
    fetchSubscription();
  }, [fetchSubscription]);

  const openCheckout = useCallback(async (tier: string) => {
    setLoading(tier);
    try {
      const res = await subscriptionsApi.createCheckoutSession(tier);
      if (res.data.checkout_url) {
        await Linking.openURL(res.data.checkout_url);
      }
    } catch (err: any) {
      Alert.alert("Checkout error", err.message || "Could not start checkout.");
    } finally {
      setLoading(null);
    }
  }, []);

  const openPortal = useCallback(async () => {
    setLoading("portal");
    try {
      const res = await subscriptionsApi.createCustomerPortal();
      if (res.data.portal_url) {
        await Linking.openURL(res.data.portal_url);
      }
    } catch (err: any) {
      Alert.alert("Portal error", err.message || "Could not open billing portal.");
    } finally {
      setLoading(null);
    }
  }, []);

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
          <Text style={styles.headerTitle}>Subscription</Text>
          <View style={styles.backBtnPlaceholder} />
        </View>

        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <View style={styles.trialBanner}>
            <Sparkles
              size={tokens.icon.size.sm}
              color={tokens.color.brand.teal[300]}
              strokeWidth={tokens.icon.stroke.default}
            />
            <Text style={styles.trialText}>14-day trial · ends Mar 31</Text>
          </View>

          <View style={styles.planCard}>
            <Text style={styles.planOverline}>CURRENT PLAN</Text>
            <View style={styles.planRow}>
              <Text style={styles.planName}>Basic</Text>
              <Text style={styles.planPrice}>$19 / mo</Text>
            </View>
            <Text style={styles.planMeta}>Renews Apr 14, 2026 · Card ending 4242</Text>
          </View>

          <View style={styles.compare}>
            <View style={styles.compareHeader}>
              <Text style={[styles.compareCol, styles.compareLabelCol]} />
              <Text style={[styles.compareCol, styles.compareHeadText]}>Basic</Text>
              <View style={[styles.compareCol, styles.premiumHeadWrap]}>
                <Text style={styles.compareHeadTextAccent}>Premium</Text>
              </View>
            </View>
            {FEATURES.map((f, i) => (
              <View
                key={f.label}
                style={[styles.compareRow, i === FEATURES.length - 1 ? null : styles.compareDivider]}
              >
                <Text style={[styles.compareCol, styles.compareLabelCol, styles.compareLabel]}>
                  {f.label}
                </Text>
                <CompareCell value={f.basic} />
                <CompareCell value={f.premium} accent />
              </View>
            ))}
          </View>

          <View style={styles.ctaGroup}>
            <ActionButton
              label={loading === 'pro' ? 'Loading...' : 'Upgrade to Premium'}
              variant="primary"
              size="lg"
              fullWidth
              disabled={!!loading}
              onPress={() => openCheckout('pro')}
            />
            <ActionButton
              label={loading === 'annual' ? 'Loading...' : 'Switch to annual (save 15%)'}
              variant="secondary"
              size="md"
              fullWidth
              disabled={!!loading}
              onPress={() => openCheckout('pro')}
            />
            <ActionButton
              label={loading === 'portal' ? 'Loading...' : 'Manage in Stripe'}
              variant="ghost"
              size="md"
              fullWidth
              iconRight={ExternalLink}
              disabled={!!loading}
              onPress={openPortal}
            />
          </View>

          <Text style={styles.fineprint}>
            Billing managed via Stripe. Cancel anytime — access continues through the end of the
            current period.
          </Text>
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

function CompareCell({ value, accent }: { value: string | boolean; accent?: boolean }) {
  const isBool = typeof value === "boolean";
  return (
    <View style={[styles.compareCol, styles.compareCell]}>
      {isBool ? (
        value ? (
          <Check
            size={tokens.icon.size.sm}
            color={accent ? tokens.color.brand.teal[300] : tokens.color.status.success}
            strokeWidth={tokens.icon.stroke.bold}
          />
        ) : (
          <Text style={styles.compareDash}>—</Text>
        )
      ) : (
        <Text style={[styles.compareValue, accent ? styles.compareValueAccent : null]}>
          {value as string}
        </Text>
      )}
    </View>
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
  backBtnPlaceholder: {
    width: tokens.layout.minTouchTarget,
    height: tokens.layout.minTouchTarget,
  },
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
  trialBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.sm,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    backgroundColor: tokens.color.brand.teal[900],
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    borderColor: tokens.color.brand.teal[700],
  },
  trialText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.brand.teal[100],
  },
  planCard: {
    padding: tokens.spacing.md,
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    gap: tokens.spacing.xs,
  },
  planOverline: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  planRow: {
    flexDirection: "row",
    alignItems: "baseline",
    justifyContent: "space-between",
  },
  planName: {
    fontFamily: tokens.type.scale.h1.family,
    fontSize: tokens.type.scale.h1.size,
    lineHeight: tokens.type.scale.h1.lineHeight,
    letterSpacing: tokens.type.scale.h1.letterSpacing,
    color: tokens.color.text.primary,
  },
  planPrice: {
    fontFamily: tokens.type.scale.h2.family,
    fontSize: tokens.type.scale.h2.size,
    color: tokens.color.text.primary,
  },
  planMeta: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  compare: {
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    overflow: "hidden",
  },
  compareHeader: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: tokens.spacing.sm,
    backgroundColor: tokens.color.bg.raised,
    borderBottomWidth: 1,
    borderBottomColor: tokens.color.border.subtle,
  },
  compareRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: tokens.spacing.sm,
    paddingHorizontal: 0,
  },
  compareDivider: {
    borderBottomWidth: 1,
    borderBottomColor: tokens.color.border.subtle,
  },
  compareCol: {
    flex: 1,
    paddingHorizontal: tokens.spacing.sm,
  },
  compareLabelCol: {
    flex: 1.4,
  },
  compareCell: {
    alignItems: "center",
    justifyContent: "center",
  },
  premiumHeadWrap: {
    alignItems: "center",
  },
  compareHeadText: {
    textAlign: "center",
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.text.secondary,
  },
  compareHeadTextAccent: {
    textAlign: "center",
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.brand.teal[300],
  },
  compareLabel: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    color: tokens.color.text.secondary,
  },
  compareValue: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.primary,
    textAlign: "center",
  },
  compareValueAccent: {
    color: tokens.color.brand.teal[200],
  },
  compareDash: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    color: tokens.color.text.tertiary,
  },
  ctaGroup: {
    gap: tokens.spacing.sm,
  },
  fineprint: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
    textAlign: "center",
  },
});
