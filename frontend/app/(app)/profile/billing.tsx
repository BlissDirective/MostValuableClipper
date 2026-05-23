import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Linking, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { Stack, useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { Check, ChevronLeft, ExternalLink, Sparkles } from "lucide-react-native";

import { tokens } from "@/constants/tokens";
import { ActionButton } from "@/components/ActionButton";
import { useAuthStore } from "@/lib/store";
import { subscriptionsApi } from "@/lib/api";
import { useToast } from "@/components/ToastProvider";

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

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return iso.slice(0, 10);
  }
}

function daysUntil(iso: string | null | undefined): number | null {
  if (!iso) return null;
  try {
    const end = new Date(iso).getTime();
    const now = Date.now();
    return Math.ceil((end - now) / (1000 * 60 * 60 * 24));
  } catch {
    return null;
  }
}

export default function BillingScreen() {
  const router = useRouter();
  const toast = useToast();
  
  const subscription = useAuthStore((s) => s.subscription);
  const fetchSubscription = useAuthStore((s) => s.fetchSubscription);
  const [loading, setLoading] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    fetchSubscription();
  }, [fetchSubscription]);

  const periodEnd = subscription.current_period_end;
  const trialEnd = subscription.trial_end;
  const cancelAtPeriodEnd = subscription.cancel_at_period_end;
  const tier = subscription.tier;
  const status = subscription.status;

  const isTrialing = status === "trialing" && !!trialEnd;
  const isActive = status === "active" || status === "trialing";
  const daysLeft = daysUntil(periodEnd);
  const trialDaysLeft = daysUntil(trialEnd);

  const planName = useMemo(() => {
    if (tier === "pro" || tier === "premium") return "Premium";
    if (tier === "basic") return "Basic";
    return "Free";
  }, [tier]);

  const planPrice = useMemo(() => {
    if (tier === "pro" || tier === "premium") return "$49 / mo";
    if (tier === "basic") return "$19 / mo";
    return "Free";
  }, [tier]);

  const openCheckout = useCallback(async (tierKey: string) => {
    setLoading(tierKey);
    try {
      const res = await subscriptionsApi.createCheckoutSession(tierKey);
      if (res.checkout_url) {
        await Linking.openURL(res.checkout_url);
      }
    } catch (err: any) {
      toast.show({ type: "success", message: err.message || "Could not start checkout.", title: "error" });
    } finally {
      setLoading(null);
    }
  }, [toast]);

  const openPortal = useCallback(async () => {
    setLoading("portal");
    try {
      const res = await subscriptionsApi.createCustomerPortal();
      if (res.portal_url) {
        await Linking.openURL(res.portal_url);
      }
    } catch (err: any) {
      toast.show({ type: "success", message: err.message || "Could not open billing portal.", title: "error" });
    } finally {
      setLoading(null);
    }
  }, [toast]);

  const onCancel = useCallback(async () => {
    if (cancelling) return;
    setCancelling(true);
    try {
      const res = await subscriptionsApi.cancel();
      if (res.success) {
        toast.show({ type: "success", message: "Subscription cancelled — you have access until the end of your billing period", title: "success" });
        await fetchSubscription();
      } else {
        toast.show({ type: "success", message: res.message || "Cancellation failed", title: "error" });
      }
    } catch (err: any) {
      toast.show({ type: "success", message: err.message || "Cancellation failed", title: "error" });
    } finally {
      setCancelling(false);
    }
  }, [cancelling, fetchSubscription, toast]);

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
          {/* Trial / Status Banner */}
          {isTrialing && trialDaysLeft !== null && trialDaysLeft > 0 && (
            <View style={styles.trialBanner}>
              <Sparkles
                size={tokens.icon.size.sm}
                color={tokens.color.brand.teal[300]}
                strokeWidth={tokens.icon.stroke.default}
              />
              <Text style={styles.trialText}>
                {trialDaysLeft === 1
                  ? "Trial ends tomorrow"
                  : `${trialDaysLeft}-day trial remaining · ends ${formatDate(trialEnd)}`}
              </Text>
            </View>
          )}
          
          {cancelAtPeriodEnd && (
            <View style={[styles.trialBanner, { backgroundColor: tokens.color.status.dangerBg }]}>
              <Text style={[styles.trialText, { color: tokens.color.status.danger }]}>
                Cancels on {formatDate(periodEnd)} · no further charges
              </Text>
            </View>
          )}

          {/* Current Plan Card */}
          <View style={styles.planCard}>
            <Text style={styles.planOverline}>CURRENT PLAN</Text>
            <View style={styles.planRow}>
              <Text style={styles.planName}>{planName}</Text>
              <Text style={styles.planPrice}>{planPrice}</Text>
            </View>
            <Text style={styles.planMeta}>
              {isActive
                ? periodEnd
                  ? cancelAtPeriodEnd
                    ? `Active until ${formatDate(periodEnd)}`
                    : `Renews ${formatDate(periodEnd)}`
                  : "Active"
                : status === "canceled"
                ? "Canceled"
                : status}
            </Text>
            {daysLeft !== null && daysLeft > 0 && !cancelAtPeriodEnd && (
              <Text style={styles.planDaysLeft}>{daysLeft} days left in current period</Text>
            )}
          </View>

          {/* Feature Comparison */}
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

          {/* CTAs */}
          <View style={styles.ctaGroup}>
            {tier === "free" || tier === "basic" ? (
              <>
                <ActionButton
                  label={loading === "pro" ? "Loading..." : "Upgrade to Premium"}
                  variant="primary"
                  size="lg"
                  fullWidth
                  disabled={!!loading}
                  onPress={() => openCheckout("pro")}
                />
                <ActionButton
                  label={loading === "annual" ? "Loading..." : "Switch to annual (save 15%)"}
                  variant="secondary"
                  size="md"
                  fullWidth
                  disabled={!!loading}
                  onPress={() => openCheckout("pro")}
                />
              </>
            ) : (
              <>
                <ActionButton
                  label="Manage in Stripe"
                  variant="secondary"
                  size="md"
                  fullWidth
                  disabled={!!loading}
                  onPress={openPortal}
                />
                {!cancelAtPeriodEnd && (
                  <ActionButton
                    label={cancelling ? "Cancelling..." : "Cancel subscription"}
                    variant="ghost"
                    size="md"
                    fullWidth
                    disabled={cancelling}
                    onPress={onCancel}
                  />
                )}
              </>
            )}
          </View>

          <View style={{ height: 40 }} />
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

function CompareCell({ value, accent }: { value: string | boolean; accent?: boolean }) {
  const isBool = typeof value === "boolean";
  return (
    <View style={styles.compareCol}>
      {isBool ? (
        value ? (
          <Check
            size={tokens.icon.size.sm}
            color={accent ? tokens.color.brand.teal[300] : tokens.color.text.secondary}
            strokeWidth={tokens.icon.stroke.bold}
          />
        ) : (
          <Text style={styles.compareDash}>—</Text>
        )
      ) : (
        <Text style={[styles.compareCellText, accent && styles.compareCellTextAccent]}>
          {value}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg.base },
  safe: { flex: 1 },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: tokens.spacing.md,
    paddingTop: tokens.spacing.md,
    paddingBottom: tokens.spacing.sm,
  },
  backBtn: { padding: tokens.spacing.xs },
  backBtnPlaceholder: { width: 40 },
  headerTitle: {
    fontFamily: tokens.type.scale.h3.family,
    fontSize: tokens.type.scale.h3.size,
    fontWeight: "600",
    color: tokens.color.text.primary,
  },
  content: {
    paddingHorizontal: tokens.spacing.md,
    paddingBottom: tokens.spacing.xl,
    gap: tokens.spacing.lg,
  },
  trialBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.sm,
    backgroundColor: tokens.color.status.successBg,
    borderRadius: tokens.radius.lg,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
  },
  trialText: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.status.success,
    fontWeight: "500",
  },
  planCard: {
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.lg,
    padding: tokens.spacing.lg,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
  },
  planOverline: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    fontWeight: "600",
    color: tokens.color.text.tertiary,
    textTransform: "uppercase",
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    marginBottom: tokens.spacing.xs,
  },
  planRow: {
    flexDirection: "row",
    alignItems: "baseline",
    justifyContent: "space-between",
    marginBottom: tokens.spacing.xs,
  },
  planName: {
    fontFamily: tokens.type.scale.h2.family,
    fontSize: tokens.type.scale.h2.size,
    fontWeight: "700",
    color: tokens.color.text.primary,
  },
  planPrice: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.secondary,
  },
  planMeta: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.secondary,
  },
  planDaysLeft: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.tertiary,
    marginTop: tokens.spacing.xs,
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
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    backgroundColor: tokens.color.bg.surface,
    borderBottomWidth: 1,
    borderBottomColor: tokens.color.border.subtle,
  },
  compareRow: {
    flexDirection: "row",
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    alignItems: "center",
  },
  compareDivider: {
    borderBottomWidth: 1,
    borderBottomColor: tokens.color.border.subtle,
  },
  compareCol: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  compareLabelCol: {
    flex: 2,
    alignItems: "flex-start",
  },
  compareHeadText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    fontWeight: "600",
    color: tokens.color.text.secondary,
  },
  compareHeadTextAccent: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    fontWeight: "600",
    color: tokens.color.brand.teal[300],
  },
  premiumHeadWrap: {
    backgroundColor: tokens.color.brand.teal[900],
    borderRadius: tokens.radius.md,
    paddingVertical: tokens.spacing.xs,
  },
  compareLabel: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.primary,
  },
  compareCellText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.secondary,
  },
  compareCellTextAccent: {
    color: tokens.color.brand.teal[300],
    fontWeight: "600",
  },
  compareDash: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.tertiary,
  },
  ctaGroup: {
    gap: tokens.spacing.sm,
  },
});