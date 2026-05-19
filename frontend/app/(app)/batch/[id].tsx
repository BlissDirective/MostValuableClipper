import React, { useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import {
  ArrowLeft,
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  AlertCircle,
  Layers,
  Pause,
} from 'lucide-react-native';

import { tokens } from '@/constants/tokens';
import { useBatchJob, useBatchProgress } from '@/lib/api-hooks';

const STATUS_ICON: Record<string, any> = {
  queued: Clock,
  running: Play,
  completed: CheckCircle2,
  failed: XCircle,
  cancelled: AlertCircle,
};

const STATUS_COLOR: Record<string, string> = {
  queued: tokens.color.text.secondary,
  running: tokens.color.brand.indigo[400],
  completed: tokens.color.semantic.success,
  failed: tokens.color.semantic.error,
  cancelled: tokens.color.text.tertiary,
};

const POOL_LABEL: Record<string, string> = {
  hook: 'Hook Swarm',
  remix: 'Remix Swarm',
  post: 'Post Swarm',
  ab_test: 'A/B Test Swarm',
  music_match: 'Music Match Swarm',
  thumbnail: 'Thumbnail Swarm',
  safety: 'Safety Swarm',
  hooks_analysis: 'Hook Analysis Swarm',
  segment_analyze: 'Segment Analysis Swarm',
  edit: 'Edit Swarm',
};

export default function BatchDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { job, clipResults, isLoading } = useBatchJob(id || null);
  const progress = useBatchProgress(id || null);

  const batchId = id || '';
  const status = progress?.current_status || job?.status || 'queued';
  const Icon = STATUS_ICON[status] || Clock;
  const color = STATUS_COLOR[status] || tokens.color.text.secondary;
  const poolLabel = POOL_LABEL[job?.pool_type] || job?.pool_type || 'Batch';

  const processed = progress?.processed || job?.processed_clips || 0;
  const total = progress?.total || job?.total_clips || 1;
  const failed = progress?.failed || job?.failed_clips || 0;
  const percent = progress?.percent || Math.round((processed / total) * 100);

  const isRunning = status === 'running' || status === 'queued';

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => router.back()}
          style={styles.backBtn}
          hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
        >
          <ArrowLeft
            color={tokens.color.text.primary}
            size={24}
            strokeWidth={2}
          />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Batch Detail</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Status Card */}
        <View style={[styles.statusCard, { borderColor: `${color}30` }]}>
          <View style={styles.statusHeader}>
            <View style={[styles.statusIconBg, { backgroundColor: `${color}15` }]}>
              <Icon color={color} size={28} strokeWidth={2} />
            </View>
            <View style={styles.statusTextWrap}>
              <Text style={styles.statusLabel}>{poolLabel}</Text>
              <Text style={[styles.statusValue, { color }]}>
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </Text>
            </View>
          </View>

          <View style={styles.statsRow}>
            <View style={styles.stat}>
              <Text style={styles.statValue}>{total}</Text>
              <Text style={styles.statLabel}>Clips</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.stat}>
              <Text style={[styles.statValue, { color: tokens.color.semantic.success }]}>
                {processed}
              </Text>
              <Text style={styles.statLabel}>Done</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.stat}>
              <Text style={[styles.statValue, { color: tokens.color.semantic.error }]}>
                {failed}
              </Text>
              <Text style={styles.statLabel}>Failed</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.stat}>
              <Text style={styles.statValue}>
                {job?.agent_count || 1}
              </Text>
              <Text style={styles.statLabel}>Agents</Text>
            </View>
          </View>
        </View>

        {/* Progress Bar */}
        <View style={styles.progressCard}>
          <View style={styles.progressHeader}>
            <Text style={styles.progressTitle}>Progress</Text>
            <Text style={styles.progressPercent}>{percent}%</Text>
          </View>
          <View style={styles.progressBarBg}>
            <View
              style={[
                styles.progressBarFill,
                {
                  width: `${percent}%`,
                  backgroundColor: isRunning
                    ? tokens.color.brand.indigo[400]
                    : status === 'failed'
                    ? tokens.color.semantic.error
                    : tokens.color.semantic.success,
                },
              ]}
            />
          </View>
          {isRunning && (
            <View style={styles.pulseDotWrap}>
              <View style={[styles.pulseDot, { backgroundColor: tokens.color.brand.indigo[400] }]} />
              <Text style={styles.pulseText}>
                {progress?.detail || 'Processing clips...'}
              </Text>
            </View>
          )}
        </View>

        {/* Cost Info */}
        {job?.cost_cents > 0 && (
          <View style={styles.infoCard}>
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Estimated Cost</Text>
              <Text style={styles.infoValue}>
                ${(job.cost_cents / 100).toFixed(2)}
              </Text>
            </View>
            {job?.results_summary?.savings_percent > 0 && (
              <View style={styles.infoRow}>
                <Text style={styles.infoLabel}>Savings</Text>
                <Text style={[styles.infoValue, { color: tokens.color.semantic.success }]}>
                  {job.results_summary.savings_percent}% vs individual
                </Text>
              </View>
            )}
          </View>
        )}

        {/* Clip Results */}
        {clipResults.length > 0 && (
          <View style={styles.resultsSection}>
            <Text style={styles.sectionTitle}>Clip Results</Text>
            {clipResults.map((result: any) => (
              <View key={result.result_id} style={styles.resultCard}>
                <View style={styles.resultHeader}>
                  <Text style={styles.resultClipId} numberOfLines={1}>
                    {result.clip_id}
                  </Text>
                  {result.status === 'completed' ? (
                    <CheckCircle2
                      color={tokens.color.semantic.success}
                      size={16}
                      strokeWidth={2}
                    />
                  ) : result.status === 'failed' ? (
                    <XCircle
                      color={tokens.color.semantic.error}
                      size={16}
                      strokeWidth={2}
                    />
                  ) : (
                    <Clock
                      color={tokens.color.text.tertiary}
                      size={16}
                      strokeWidth={2}
                    />
                  )}
                </View>
                {result.error_message && (
                  <Text style={styles.errorText}>{result.error_message}</Text>
                )}
                {result.duration_ms > 0 && (
                  <Text style={styles.durationText}>
                    {(result.duration_ms / 1000).toFixed(1)}s
                  </Text>
                )}
              </View>
            ))}
          </View>
        )}

        {/* Error */}
        {job?.error && (
          <View style={[styles.infoCard, { borderColor: tokens.color.semantic.error + '30' }]}>
            <View style={styles.infoRow}>
              <AlertCircle
                color={tokens.color.semantic.error}
                size={18}
                strokeWidth={2}
              />
              <Text style={[styles.infoValue, { color: tokens.color.semantic.error, flex: 1 }]}>
                {job.error}
              </Text>
            </View>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: tokens.color.bg.base,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: tokens.layout.screenPadding,
    paddingTop: tokens.layout.screenPadding + 8,
    paddingBottom: 12,
  },
  backBtn: {
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerTitle: {
    fontFamily: tokens.type.scale.h2.family,
    fontSize: tokens.type.scale.h2.size,
    color: tokens.color.text.primary,
    letterSpacing: tokens.type.scale.h2.letterSpacing,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    padding: tokens.layout.screenPadding,
    gap: 16,
  },
  statusCard: {
    backgroundColor: tokens.color.bg.raised,
    borderRadius: tokens.layout.cardRadius,
    padding: 20,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
  },
  statusHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    marginBottom: 20,
  },
  statusIconBg: {
    width: 52,
    height: 52,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
  },
  statusTextWrap: {
    flex: 1,
  },
  statusLabel: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.secondary,
    marginBottom: 2,
  },
  statusValue: {
    fontFamily: tokens.type.scale.h3.family,
    fontSize: tokens.type.scale.h3.size,
    fontWeight: '700',
  },
  statsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  stat: {
    alignItems: 'center',
    flex: 1,
  },
  statValue: {
    fontFamily: tokens.type.scale.h3.family,
    fontSize: 20,
    color: tokens.color.text.primary,
    fontWeight: '700',
  },
  statLabel: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: 12,
    color: tokens.color.text.tertiary,
    marginTop: 2,
  },
  statDivider: {
    width: 1,
    height: 32,
    backgroundColor: tokens.color.border.subtle,
  },
  progressCard: {
    backgroundColor: tokens.color.bg.raised,
    borderRadius: tokens.layout.cardRadius,
    padding: 20,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
  },
  progressHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  progressTitle: {
    fontFamily: tokens.type.scale.body.family,
    fontSize: tokens.type.scale.body.size,
    color: tokens.color.text.primary,
    fontWeight: '600',
  },
  progressPercent: {
    fontFamily: tokens.type.scale.h3.family,
    fontSize: tokens.type.scale.h3.size,
    color: tokens.color.text.primary,
    fontWeight: '700',
  },
  progressBarBg: {
    height: 10,
    backgroundColor: tokens.color.bg.base,
    borderRadius: 5,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    borderRadius: 5,
  },
  pulseDotWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 12,
  },
  pulseDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  pulseText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: 13,
    color: tokens.color.text.secondary,
  },
  infoCard: {
    backgroundColor: tokens.color.bg.raised,
    borderRadius: tokens.layout.cardRadius,
    padding: 16,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
  },
  infoLabel: {
    fontFamily: tokens.type.scale.body.family,
    fontSize: tokens.type.scale.body.size,
    color: tokens.color.text.secondary,
  },
  infoValue: {
    fontFamily: tokens.type.scale.body.family,
    fontSize: tokens.type.scale.body.size,
    color: tokens.color.text.primary,
    fontWeight: '600',
  },
  resultsSection: {
    gap: 10,
  },
  sectionTitle: {
    fontFamily: tokens.type.scale.h3.family,
    fontSize: tokens.type.scale.h3.size,
    color: tokens.color.text.primary,
    fontWeight: '600',
    marginBottom: 4,
  },
  resultCard: {
    backgroundColor: tokens.color.bg.raised,
    borderRadius: tokens.layout.cardRadius,
    padding: 14,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    gap: 4,
  },
  resultHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  resultClipId: {
    fontFamily: tokens.type.scale.mono.family,
    fontSize: 12,
    color: tokens.color.text.secondary,
    flex: 1,
  },
  errorText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: 12,
    color: tokens.color.semantic.error,
    marginTop: 4,
  },
  durationText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: 12,
    color: tokens.color.text.tertiary,
    marginTop: 2,
  },
});
