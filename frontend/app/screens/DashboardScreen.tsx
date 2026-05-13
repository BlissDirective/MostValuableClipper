import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
} from 'react-native';
import { usePipelines, useClips, useEarnings, useAnalytics } from '../../lib/api-hooks';
import { design, haptics } from '../../constants';

/**
 * DashboardScreen — Overview of all activity
 * 
 * Shows: active pipelines, clips this week, earnings, quick stats
 */
export function DashboardScreen() {
  const { pipelines, isLoading: pipelinesLoading } = usePipelines();
  const { clips } = useClips();
  const { earnings, isLoading: earningsLoading } = useEarnings();
  const { analytics, isLoading: analyticsLoading } = useAnalytics();

  const activePipelines = pipelines.filter((p: any) => p.status === 'running');
  const totalClips = clips.length;
  const reviewPending = clips.filter((c: any) => c.status === 'ready_for_review').length;

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.greeting}>Dashboard</Text>
        <Text style={styles.subtitle}>Your content at a glance</Text>
      </View>

      {/* Stats Row */}
      <View style={styles.statsRow}>
        <StatCard
          label="Active"
          value={activePipelines.length}
          icon="▶️"
          color={design.colors.success}
        />
        <StatCard
          label="Clips"
          value={totalClips}
          icon="🎬"
          color={design.colors.primary}
        />
        <StatCard
          label="Review"
          value={reviewPending}
          icon="👀"
          color={design.colors.warning}
        />
      </View>

      {/* Pipelines Section */}
      <Section title="Pipelines">
        {activePipelines.length === 0 ? (
          <EmptyState text="No active pipelines" action="Go to Pipelines tab to create one" />
        ) : (
          activePipelines.map((p: any) => (
            <PipelineMini key={p.id} pipeline={p} />
          ))
        )}
      </Section>

      {/* Earnings Section */}
      <Section title="Earnings">
        {earningsLoading ? (
          <Loading />
        ) : earnings ? (
          <View style={styles.earningsCard}>
            <Text style={styles.earningsValue}>
              ${((earnings.total_revenue_cents || 0) / 100).toFixed(2)}
            </Text>
            <Text style={styles.earningsLabel}>Total earnings</Text>
            {earnings.pending_payout > 0 && (
              <Text style={styles.pendingLabel}>
                ${(earnings.pending_payout / 100).toFixed(2)} pending
              </Text>
            )}
          </View>
        ) : (
          <EmptyState text="No earnings yet" action="Post clips to start earning" />
        )}
      </Section>

      {/* Quick Actions */}
      <Section title="Quick Actions">
        <View style={styles.quickActions}>
          <QuickAction
            label="Create Pipeline"
            icon="➕"
            onPress={() => { /* Navigate */ }}
          />
          <QuickAction
            label="Review Clips"
            icon="👀"
            onPress={() => { /* Navigate */ }}
          />
          <QuickAction
            label="Add Source"
            icon="🔗"
            onPress={() => { /* Navigate */ }}
          />
        </View>
      </Section>
    </ScrollView>
  );
}

function StatCard({ label, value, icon, color }: any) {
  return (
    <View style={[styles.statCard, { borderTopColor: color }]}>
      <Text style={styles.statIcon}>{icon}</Text>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

function PipelineMini({ pipeline }: { pipeline: any }) {
  return (
    <View style={styles.pipelineMini}>
      <View style={styles.pipelineMiniLeft}>
        <Text style={styles.pipelineMiniName}>{pipeline.name}</Text>
        <Text style={styles.pipelineMiniMeta}>
          {pipeline.niche} · {pipeline.total_clips_generated || 0} clips
        </Text>
      </View>
      <View style={[styles.statusDot, { backgroundColor: design.colors.success }]} />
    </View>
  );
}

function EmptyState({ text, action }: { text: string; action: string }) {
  return (
    <View style={styles.emptyState}>
      <Text style={styles.emptyText}>{text}</Text>
      <Text style={styles.emptyAction}>{action}</Text>
    </View>
  );
}

function Loading() {
  return (
    <View style={styles.emptyState}>
      <Text style={styles.emptyText}>Loading…</Text>
    </View>
  );
}

function QuickAction({ label, icon, onPress }: { label: string; icon: string; onPress: () => void }) {
  return (
    <TouchableOpacity style={styles.quickAction} onPress={onPress}>
      <Text style={styles.quickActionIcon}>{icon}</Text>
      <Text style={styles.quickActionLabel}>{label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: design.colors.bg },
  header: { padding: 20, paddingTop: 60 },
  greeting: { fontSize: 28, fontWeight: '800', color: design.colors.text },
  subtitle: { fontSize: 15, color: design.colors.muted, marginTop: 4 },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    marginBottom: 8,
  },
  statCard: {
    flex: 1,
    backgroundColor: design.colors.card,
    borderRadius: 12,
    padding: 14,
    marginHorizontal: 4,
    alignItems: 'center',
    borderTopWidth: 3,
  },
  statIcon: { fontSize: 20, marginBottom: 4 },
  statValue: { fontSize: 22, fontWeight: '700', color: design.colors.text },
  statLabel: { fontSize: 12, color: design.colors.muted, marginTop: 2 },
  section: { paddingHorizontal: 16, marginBottom: 20 },
  sectionTitle: { fontSize: 18, fontWeight: '700', color: design.colors.text, marginBottom: 12 },
  pipelineMini: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: design.colors.card,
    padding: 14,
    borderRadius: 12,
    marginBottom: 8,
  },
  pipelineMiniLeft: { flex: 1 },
  pipelineMiniName: { fontSize: 15, fontWeight: '600', color: design.colors.text },
  pipelineMiniMeta: { fontSize: 12, color: design.colors.muted, marginTop: 2 },
  statusDot: { width: 10, height: 10, borderRadius: 5, marginLeft: 8 },
  earningsCard: {
    backgroundColor: design.colors.card,
    padding: 20,
    borderRadius: 12,
    alignItems: 'center',
  },
  earningsValue: { fontSize: 32, fontWeight: '800', color: design.colors.success },
  earningsLabel: { fontSize: 14, color: design.colors.muted, marginTop: 4 },
  pendingLabel: { fontSize: 13, color: design.colors.warning, marginTop: 8 },
  emptyState: {
    backgroundColor: design.colors.card,
    padding: 20,
    borderRadius: 12,
    alignItems: 'center',
  },
  emptyText: { fontSize: 14, color: design.colors.muted },
  emptyAction: { fontSize: 12, color: design.colors.muted, marginTop: 4, fontStyle: 'italic' },
  quickActions: { flexDirection: 'row', justifyContent: 'space-between' },
  quickAction: {
    flex: 1,
    backgroundColor: design.colors.card,
    padding: 14,
    borderRadius: 12,
    alignItems: 'center',
    marginHorizontal: 4,
  },
  quickActionIcon: { fontSize: 24, marginBottom: 6 },
  quickActionLabel: { fontSize: 12, color: design.colors.text, fontWeight: '600' },
});
