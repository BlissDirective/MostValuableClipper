import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, ActivityIndicator } from 'react-native';
import { api } from '@/lib/api';

interface EarningsData {
  total_revenue_cents: number;
  total_views: number;
  by_platform: Array<{
    platform: string;
    revenue_cents: number;
    views: number;
  }>;
  history: Array<{
    period: string;
    revenue_cents: number;
    views: number;
  }>;
}

export default function EarningsScreen() {
  const [data, setData] = useState<EarningsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchEarnings();
  }, []);

  const fetchEarnings = async () => {
    try {
      const result = await api.get<EarningsData>('/earnings/summary');
      setData(result);
    } catch {
      // Show empty state
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#6366f1" />
      </View>
    );
  }

  const revenue = (data?.total_revenue_cents || 0) / 100;

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.header}>Earnings</Text>

      <View style={styles.totalCard}>
        <Text style={styles.totalLabel}>Total Revenue</Text>
        <Text style={styles.totalAmount}>${revenue.toFixed(2)}</Text>
        <Text style={styles.totalViews}>{(data?.total_views || 0).toLocaleString()} total views</Text>
      </View>

      <Text style={styles.sectionTitle}>By Platform</Text>
      {(data?.by_platform || []).map((item) => (
        <View key={item.platform} style={styles.platformCard}>
          <View style={styles.platformRow}>
            <Text style={styles.platformName}>{item.platform}</Text>
            <Text style={styles.platformRevenue}>${(item.revenue_cents / 100).toFixed(2)}</Text>
          </View>
          <Text style={styles.platformViews}>{item.views.toLocaleString()} views</Text>
        </View>
      ))}

      {!data?.by_platform?.length && (
        <View style={styles.emptyCard}>
          <Text style={styles.emptyText}>No earnings yet</Text>
          <Text style={styles.emptySub}>Connect platforms and post clips to start earning</Text>
        </View>
      )}

      <Text style={styles.sectionTitle}>Recent History</Text>
      {(data?.history || []).slice(0, 10).map((item, i) => (
        <View key={i} style={styles.historyRow}>
          <Text style={styles.historyPeriod}>{item.period}</Text>
          <Text style={styles.historyAmount}>${(item.revenue_cents / 100).toFixed(2)}</Text>
          <Text style={styles.historyViews}>{item.views.toLocaleString()} views</Text>
        </View>
      ))}
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
    marginTop: 16,
    marginBottom: 20,
  },
  totalCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    marginBottom: 24,
    borderWidth: 1,
    borderColor: '#6366f1',
  },
  totalLabel: {
    fontSize: 14,
    color: '#888',
    marginBottom: 8,
  },
  totalAmount: {
    fontSize: 40,
    fontWeight: '700',
    color: '#22c55e',
  },
  totalViews: {
    fontSize: 14,
    color: '#888',
    marginTop: 8,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 12,
    marginTop: 8,
  },
  platformCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 16,
    marginBottom: 8,
  },
  platformRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  platformName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  platformRevenue: {
    fontSize: 16,
    fontWeight: '700',
    color: '#22c55e',
  },
  platformViews: {
    fontSize: 13,
    color: '#888',
    marginTop: 4,
  },
  emptyCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 24,
    alignItems: 'center',
    marginBottom: 16,
  },
  emptyText: {
    fontSize: 16,
    color: '#888',
    marginBottom: 4,
  },
  emptySub: {
    fontSize: 13,
    color: '#666',
    textAlign: 'center',
  },
  historyRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2a2a',
  },
  historyPeriod: {
    color: '#888',
    fontSize: 14,
    flex: 1,
  },
  historyAmount: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
    marginRight: 12,
  },
  historyViews: {
    color: '#666',
    fontSize: 13,
  },
});
