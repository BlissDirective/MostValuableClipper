import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Switch,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useSwarmAllocation, useSwarmConfig } from '@/lib/api-hooks';

const POOL_COLORS: Record<string, string> = {
  hook: '#6366f1',
  remix: '#10b981',
  post: '#f59e0b',
  ab_test: '#f97316',
  music_match: '#14b8a6',
  thumbnail: '#8b5cf6',
  safety: '#f59e0b',
  hooks_analysis: '#ec4899',
  segment_analyze: '#0ea5e9',
  edit: '#06b6d4',
};

const POOL_LABELS: Record<string, string> = {
  hook: 'Hook Generation',
  remix: 'Remix / Edit',
  post: 'Social Posting',
  ab_test: 'A/B Test Analysis',
  music_match: 'Music Matching',
  thumbnail: 'Thumbnail Generation',
  safety: 'Safety Screening',
  hooks_analysis: 'Hooks Analysis',
  segment_analyze: 'Segment Analysis',
  edit: 'Edit Recipes',
};

const TIER_LABELS: Record<string, string> = {
  free: 'Free',
  basic: 'Basic',
  pro: 'Pro',
  enterprise: 'Enterprise',
};

export default function SwarmSettingsScreen() {
  const router = useRouter();
  const { allocation, tier, totalMaxAgents, availableAgents: apiAvailable, autoBalance: apiAutoBalance, isLoading: allocLoading, setAllocation, enableAutoBalance } = useSwarmAllocation();
  const { config, isLoading: configLoading } = useSwarmConfig();

  const [localAllocation, setLocalAllocation] = useState<Record<string, number>>({});
  const [autoBalance, setAutoBalance] = useState(true);
  const [saving, setSaving] = useState(false);

  // Sync local state with fetched data
  useEffect(() => {
    if (allocation) {
      setLocalAllocation({ ...allocation });
    }
    if (apiAutoBalance !== undefined) {
      setAutoBalance(apiAutoBalance);
    }
  }, [allocation, apiAutoBalance]);

  const totalMax = totalMaxAgents || 1;
  const allocatedTotal = Object.values(localAllocation).reduce((sum, n) => sum + n, 0);
  const available = totalMax - allocatedTotal;

  const handleIncrement = (pool: string) => {
    if (available > 0) {
      setLocalAllocation((prev) => ({
        ...prev,
        [pool]: (prev[pool] || 0) + 1,
      }));
      setAutoBalance(false);
    }
  };

  const handleDecrement = (pool: string) => {
    setLocalAllocation((prev) => {
      const current = prev[pool] || 0;
      if (current > 0) {
        return { ...prev, [pool]: current - 1 };
      }
      return prev;
    });
    setAutoBalance(false);
  };

  const handleSave = async () => {
    if (allocatedTotal === 0) {
      Alert.alert('Error', 'You must allocate at least 1 agent');
      return;
    }

    if (allocatedTotal > totalMax) {
      Alert.alert('Error', `Total allocation (${allocatedTotal}) exceeds your tier limit (${totalMax})`);
      return;
    }

    setSaving(true);
    try {
      await setAllocation.mutateAsync(localAllocation);
      Alert.alert('Saved', 'Agent allocation updated');
    } catch (err: any) {
      Alert.alert('Error', err?.detail || 'Failed to save allocation');
    } finally {
      setSaving(false);
    }
  };

  const handleEnableAutoBalance = async () => {
    try {
      await enableAutoBalance.mutateAsync();
      setAutoBalance(true);
      Alert.alert('Auto-Balance Enabled', 'Agents will be distributed evenly across enabled pools.');
    } catch (err: any) {
      Alert.alert('Error', err?.detail || 'Failed to enable auto-balance');
    }
  };

  if (allocLoading || configLoading) {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator size="large" color="#6366f1" />
        <Text style={styles.loadingText}>Loading swarm config...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      {/* Tier Info */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Swarm Tier</Text>
        <View style={styles.tierBadge}>
          <Text style={styles.tierText}>
            {TIER_LABELS[tier || 'free'] || 'Free'}
          </Text>
        </View>
        <Text style={styles.description}>
          You have <Text style={styles.highlight}>{totalMax}</Text> total agents available.
          {available > 0 && (
            <Text> ({available} unallocated)</Text>
          )}
        </Text>
      </View>

      {/* Auto-Balance Toggle */}
      <View style={styles.section}>
        <View style={styles.row}>
          <View style={styles.rowText}>
            <Text style={styles.label}>Auto-Balance Agents</Text>
            <Text style={styles.sublabel}>
              Automatically distribute agents evenly across all enabled pools
            </Text>
          </View>
          <Switch
            value={autoBalance}
            onValueChange={(val) => {
              if (val) {
                handleEnableAutoBalance();
              } else {
                setAutoBalance(false);
              }
            }}
            trackColor={{ false: '#3a3a3a', true: '#6366f1' }}
          />
        </View>
      </View>

      {/* Agent Allocation */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Custom Allocation</Text>
        <Text style={styles.description}>
          Allocate your {totalMax} agents across swarm types. Drag to adjust.
        </Text>

        {['hook', 'remix', 'post', 'ab_test', 'music_match', 'thumbnail', 'safety', 'hooks_analysis', 'segment_analyze', 'edit'].map((pool) => {
          const count = localAllocation[pool] || 0;
          const color = POOL_COLORS[pool];
          const isDisabled = autoBalance;

          return (
            <View key={pool} style={styles.poolRow}>
              <View style={[styles.poolDot, { backgroundColor: color }]} />
              <View style={styles.poolInfo}>
                <Text style={styles.poolLabel}>{POOL_LABELS[pool]}</Text>
                <Text style={styles.poolCount}>{count} agent{count !== 1 ? 's' : ''}</Text>
              </View>
              <View style={styles.controls}>
                <TouchableOpacity
                  style={[styles.controlBtn, isDisabled && styles.controlBtnDisabled]}
                  onPress={() => handleDecrement(pool)}
                  disabled={isDisabled || count <= 0}
                >
                  <Text style={styles.controlBtnText}>−</Text>
                </TouchableOpacity>
                <View style={styles.countBadge}>
                  <Text style={styles.countText}>{count}</Text>
                </View>
                <TouchableOpacity
                  style={[styles.controlBtn, isDisabled && styles.controlBtnDisabled]}
                  onPress={() => handleIncrement(pool)}
                  disabled={isDisabled || available <= 0}
                >
                  <Text style={styles.controlBtnText}>+</Text>
                </TouchableOpacity>
              </View>
            </View>
          );
        })}

        {/* Validation Message */}
        {allocatedTotal > totalMax && (
          <Text style={styles.errorText}>
            ⚠ Total ({allocatedTotal}) exceeds limit ({totalMax})
          </Text>
        )}
        {allocatedTotal === 0 && (
          <Text style={styles.errorText}>
            ⚠ Allocate at least 1 agent
          </Text>
        )}
      </View>

      {/* Cost Estimate */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Estimated Cost Per Run</Text>
        {['hook', 'remix', 'post'].map((pool) => {
          const count = localAllocation[pool] || 0;
          const costPerAgent = pool === 'hook' ? 5 : pool === 'remix' ? 20 : 1;
          const cost = count * costPerAgent;
          if (count === 0) return null;

          return (
            <View key={pool} style={styles.costRow}>
              <Text style={styles.costLabel}>{POOL_LABELS[pool]}</Text>
              <Text style={styles.costValue}>
                {count} × {costPerAgent}¢ = <Text style={styles.highlight}>{cost}¢</Text>
              </Text>
            </View>
          );
        })}
        <View style={[styles.costRow, styles.totalRow]}>
          <Text style={[styles.costLabel, styles.totalLabel]}>Total per run</Text>
          <Text style={styles.totalValue}>
            {Object.entries(localAllocation).reduce((sum, [pool, count]) => {
              const costPerAgent = pool === 'hook' ? 5 : pool === 'remix' ? 20 : 1;
              return sum + count * costPerAgent;
            }, 0)}¢
          </Text>
        </View>
      </View>

      {/* Save Button */}
      <View style={styles.section}>
        <TouchableOpacity
          style={[
            styles.saveBtn,
            (saving || autoBalance || allocatedTotal === 0 || allocatedTotal > totalMax) &&
              styles.saveBtnDisabled,
          ]}
          onPress={handleSave}
          disabled={saving || autoBalance || allocatedTotal === 0 || allocatedTotal > totalMax}
        >
          <Text style={styles.saveBtnText}>
            {saving ? 'Saving...' : autoBalance ? 'Auto-Balance Enabled' : 'Save Allocation'}
          </Text>
        </TouchableOpacity>

        {!autoBalance && (
          <TouchableOpacity
            style={styles.secondaryBtn}
            onPress={handleEnableAutoBalance}
          >
            <Text style={styles.secondaryBtnText}>Reset to Auto-Balance</Text>
          </TouchableOpacity>
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f0f0f',
  },
  centered: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    color: '#888',
    marginTop: 12,
    fontSize: 14,
  },
  section: {
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    margin: 16,
    marginBottom: 8,
    padding: 16,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: '#6366f1',
    textTransform: 'uppercase',
    marginBottom: 12,
  },
  tierBadge: {
    backgroundColor: '#6366f1',
    alignSelf: 'flex-start',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 6,
    marginBottom: 8,
  },
  tierText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 14,
  },
  description: {
    fontSize: 14,
    color: '#888',
    lineHeight: 20,
  },
  highlight: {
    color: '#fff',
    fontWeight: '600',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
  },
  rowText: {
    flex: 1,
    marginRight: 12,
  },
  label: {
    fontSize: 15,
    color: '#fff',
    marginBottom: 4,
  },
  sublabel: {
    fontSize: 12,
    color: '#666',
  },
  poolRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2a2a',
  },
  poolDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: 12,
  },
  poolInfo: {
    flex: 1,
  },
  poolLabel: {
    fontSize: 15,
    color: '#fff',
    marginBottom: 2,
  },
  poolCount: {
    fontSize: 13,
    color: '#888',
  },
  controls: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  controlBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#2a2a2a',
    justifyContent: 'center',
    alignItems: 'center',
  },
  controlBtnDisabled: {
    opacity: 0.4,
  },
  controlBtnText: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '600',
    lineHeight: 22,
  },
  countBadge: {
    width: 40,
    alignItems: 'center',
  },
  countText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  errorText: {
    color: '#ef4444',
    fontSize: 13,
    marginTop: 12,
  },
  costRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2a2a',
  },
  costLabel: {
    fontSize: 14,
    color: '#aaa',
  },
  costValue: {
    fontSize: 14,
    color: '#fff',
  },
  totalRow: {
    borderBottomWidth: 0,
    marginTop: 4,
    paddingTop: 12,
  },
  totalLabel: {
    fontWeight: '600',
    color: '#fff',
  },
  totalValue: {
    fontSize: 16,
    fontWeight: '700',
    color: '#10b981',
  },
  saveBtn: {
    backgroundColor: '#6366f1',
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    marginBottom: 10,
  },
  saveBtnDisabled: {
    backgroundColor: '#3a3a3a',
  },
  saveBtnText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '600',
  },
  secondaryBtn: {
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#3a3a3a',
  },
  secondaryBtnText: {
    color: '#888',
    fontSize: 14,
  },
});
