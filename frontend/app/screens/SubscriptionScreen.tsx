import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, ActivityIndicator, Alert } from 'react-native';
import { useRouter } from 'expo-router';
import { api } from '@/lib/api';
import type { SubscriptionTier } from '@/lib/api';

export default function SubscriptionScreen() {
  const router = useRouter();
  const [currentTier, setCurrentTier] = useState<SubscriptionTier>('free');
  const [loading, setLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);

  useEffect(() => {
    fetchSubscription();
  }, []);

  const fetchSubscription = async () => {
    try {
      const data = await api.get<{ tier: SubscriptionTier; status: string }>('/subscriptions/current');
      setCurrentTier(data.tier);
    } catch {
      // User not subscribed, default to free
    } finally {
      setLoading(false);
    }
  };

  const handleSubscribe = async (priceId: string, tierName: string) => {
    setCheckoutLoading(priceId);
    try {
      const { checkout_url } = await api.post<{ checkout_url: string }>('/subscriptions/checkout', {
        price_id: priceId,
        success_url: 'https://your-app.com/success',
        cancel_url: 'https://your-app.com/cancel',
      });
      // On mobile, open the checkout URL in browser
      // router.push({ pathname: '/checkout', params: { url: checkout_url } });
      Alert.alert('Checkout', `Opening Stripe checkout for ${tierName}...`);
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Could not start checkout');
    } finally {
      setCheckoutLoading(null);
    }
  };

  const handleCancel = async () => {
    Alert.alert('Cancel Subscription', 'Are you sure? You will keep access until the end of your billing period.', [
      { text: 'Keep Subscription', style: 'cancel' },
      {
        text: 'Cancel',
        style: 'destructive',
        onPress: async () => {
          try {
            await api.post('/subscriptions/cancel', {});
            setCurrentTier('free');
            Alert.alert('Cancelled', 'Your subscription will end at the current period.');
          } catch {
            Alert.alert('Error', 'Could not cancel subscription');
          }
        },
      },
    ]);
  };

  const plans = [
    {
      name: 'Basic',
      tier: 'basic' as SubscriptionTier,
      price: '$19',
      period: '/month',
      features: ['10 clips/week', '1 pipeline', 'Basic analytics', 'Email support'],
      priceId: 'price_1TWnuCBDUozvBAiKXv9a3Ftx',
    },
    {
      name: 'Pro',
      tier: 'pro' as SubscriptionTier,
      price: '$49',
      period: '/month',
      features: ['50 clips/week', '3 pipelines', 'Advanced analytics', 'Priority support', 'A/B testing'],
      priceId: 'price_1TWnuDBDUozvBAiKAbVl1yls',
      popular: true,
    },
    {
      name: 'Enterprise',
      tier: 'enterprise' as SubscriptionTier,
      price: '$99',
      period: '/month',
      features: ['Unlimited clips', 'Unlimited pipelines', 'White-glove support', 'Custom integrations', 'API access'],
      priceId: 'price_1TWnuDBDUozvBAiKofXmoUaO',
    },
  ];

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#6366f1" />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.header}>Choose Your Plan</Text>
      <Text style={styles.subheader}>Current: {currentTier.charAt(0).toUpperCase() + currentTier.slice(1)}</Text>

      {plans.map((plan) => {
        const isCurrent = currentTier === plan.tier;
        return (
          <View key={plan.tier} style={[styles.card, plan.popular && styles.popularCard]}>
            {plan.popular && <View style={styles.badge}><Text style={styles.badgeText}>Most Popular</Text></View>}
            <Text style={styles.planName}>{plan.name}</Text>
            <View style={styles.priceRow}>
              <Text style={styles.price}>{plan.price}</Text>
              <Text style={styles.period}>{plan.period}</Text>
            </View>

            {plan.features.map((feature, i) => (
              <View key={i} style={styles.featureRow}>
                <Text style={styles.check}>✓</Text>
                <Text style={styles.feature}>{feature}</Text>
              </View>
            ))}

            {isCurrent ? (
              <TouchableOpacity style={[styles.button, styles.currentButton]} disabled>
                <Text style={styles.currentButtonText}>Current Plan</Text>
              </TouchableOpacity>
            ) : (
              <TouchableOpacity
                style={[styles.button, checkoutLoading === plan.priceId && styles.buttonDisabled]}
                onPress={() => handleSubscribe(plan.priceId, plan.name)}
                disabled={!!checkoutLoading}
              >
                <Text style={styles.buttonText}>
                  {checkoutLoading === plan.priceId ? 'Loading...' : 'Subscribe'}
                </Text>
              </TouchableOpacity>
            )}
          </View>
        );
      })}

      {currentTier !== 'free' && (
        <TouchableOpacity style={styles.cancelButton} onPress={handleCancel}>
          <Text style={styles.cancelText}>Cancel Subscription</Text>
        </TouchableOpacity>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f0f0f',
    padding: 16,
  },
  center: {
    flex: 1,
    backgroundColor: '#0f0f0f',
    justifyContent: 'center',
    alignItems: 'center',
  },
  header: {
    fontSize: 24,
    fontWeight: '700',
    color: '#fff',
    textAlign: 'center',
    marginTop: 16,
  },
  subheader: {
    fontSize: 14,
    color: '#888',
    textAlign: 'center',
    marginBottom: 20,
    marginTop: 4,
  },
  card: {
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    padding: 20,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#2a2a2a',
  },
  popularCard: {
    borderColor: '#6366f1',
  },
  badge: {
    alignSelf: 'flex-start',
    backgroundColor: '#6366f1',
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 4,
    marginBottom: 10,
  },
  badgeText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '600',
  },
  planName: {
    fontSize: 20,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 4,
  },
  priceRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    marginBottom: 16,
  },
  price: {
    fontSize: 32,
    fontWeight: '700',
    color: '#fff',
  },
  period: {
    fontSize: 14,
    color: '#888',
    marginLeft: 4,
  },
  featureRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  check: {
    color: '#22c55e',
    fontWeight: '700',
    marginRight: 8,
    fontSize: 14,
  },
  feature: {
    color: '#ccc',
    fontSize: 14,
  },
  button: {
    backgroundColor: '#6366f1',
    borderRadius: 12,
    padding: 14,
    alignItems: 'center',
    marginTop: 12,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 16,
  },
  currentButton: {
    backgroundColor: '#2a2a2a',
  },
  currentButtonText: {
    color: '#888',
    fontWeight: '600',
    fontSize: 16,
  },
  cancelButton: {
    marginTop: 20,
    marginBottom: 40,
    alignItems: 'center',
  },
  cancelText: {
    color: '#ef4444',
    fontSize: 15,
  },
});
