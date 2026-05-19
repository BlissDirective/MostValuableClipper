import React, { useCallback } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
} from 'react-native';
import { useRouter } from 'expo-router';
import {
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  AlertCircle,
  Layers,
  ChevronRight,
} from 'lucide-react-native';

import { tokens } from '@/constants/tokens';
import { useBatchJobs } from '@/lib/api-hooks';

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
  hook: 'Hook',
  remix: 'Remix',
  post: 'Post',
  ab_test: 'A/B Test',
  music_match: 'Music',
  thumbnail: 'Thumbnail',
  safety: 'Safety',
  hooks_analysis: 'Hook Analysis',
  segment_analyze: 'Segment',
  edit: 'Edit',
};

export default function BatchJobsScreen() {
  const router = useRouter();
  const { jobs, isLoading, refetch } = useBatchJobs(50);

  const renderItem = useCallback(
    ({ item }: { item: any }) => {
      const Icon = STATUS_ICON[item.status] || Layers;
      const color = STATUS_COLOR[item.status] || tokens.color.text.secondary;
      const poolLabel = POOL_LABEL[item.pool_type] || item.pool_type;
      const progress = item.total_clips > 0
        ? Math.round((item.processed_clips / item.total_clips) * 100)
        : 0;

      return (
        <TouchableOpacity
          style={styles.card}
          onPress={() => router.push(`/batch/${item.batch_id}`)}
          activeOpacity={0.7}
        >
          <View style={styles.cardHeader}>
            <View style={styles.poolBadge}>
              <Layers
                color={tokens.color.brand.indigo[400]}
                size={14}
                strokeWidth={2}
              />
              <Text style={styles.poolText}>{poolLabel}</Text>
            </View>
            <View style={[styles.statusBadge, { backgroundColor: `${color}15` }]}>
              <Icon color={color} size={14} strokeWidth={2} />
              <Text style={[styles.statusText, { color }]}>
                {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
              </Text>
            </View>
          </View>

          <Text style={styles.batchId} numberOfLines={1}>
            {item.batch_id}
          </Text>

          <View style={styles.progressRow}>
            <View style={styles.progressBarBg}>
              <View
                style={[
                  styles.progressBarFill,
                  {
                    width: `${progress}%`,
                    backgroundColor:
                      item.status === 'failed'
                        ? tokens.color.semantic.error
                        : item.status === 'completed'
                        ? tokens.color.semantic.success
                        : tokens.color.brand.indigo[400],
                  },
                ]}
              />
            </View>
            <Text style={styles.progressText}>
              {item.processed_clips}/{item.total_clips}
            </Text>
          </View>

          <View style={styles.footer}>
            <Text style={styles.footerText}>
              {item.agent_count} agent{item.agent_count !== 1 ? 's' : ''} per clip
            </Text>
            <Text style={styles.footerText}>
              ${((item.cost_cents || 0) / 100).toFixed(2)}
            </Text>
          </View>

          <ChevronRight
            color={tokens.color.text.tertiary}
            size={16}
            style={styles.chevron}
          />
        </TouchableOpacity>
      );
    },
    [router]
  );

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Batch Jobs</Text>
        <Text style={styles.subtitle}>
          {jobs.length} job{jobs.length !== 1 ? 's' : ''}
        </Text>
      </View>

      <FlatList
        data={jobs}
        keyExtractor={(item) => item.batch_id}
        renderItem={renderItem}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={isLoading} onRefresh={refetch} />
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            <Layers
              color={tokens.color.text.tertiary}
              size={48}
              strokeWidth={1.5}
            />
            <Text style={styles.emptyTitle}>No batch jobs yet</Text>
            <Text style={styles.emptyText}>
              Select multiple clips from Home and run a swarm batch to see them here.
            </Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: tokens.color.bg.base,
  },
  header: {
    paddingHorizontal: tokens.layout.screenPadding,
    paddingTop: tokens.layout.screenPadding + 8,
    paddingBottom: 16,
  },
  title: {
    fontFamily: tokens.type.scale.h1.family,
    fontSize: tokens.type.scale.h1.size,
    color: tokens.color.text.primary,
    letterSpacing: tokens.type.scale.h1.letterSpacing,
  },
  subtitle: {
    fontFamily: tokens.type.scale.body.family,
    fontSize: tokens.type.scale.body.size,
    color: tokens.color.text.secondary,
    marginTop: 4,
  },
  list: {
    padding: tokens.layout.screenPadding,
    gap: 12,
  },
  card: {
    backgroundColor: tokens.color.bg.raised,
    borderRadius: tokens.layout.cardRadius,
    padding: 16,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  poolBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  poolText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.brand.indigo[400],
    fontWeight: '600',
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: 12,
    fontWeight: '600',
  },
  batchId: {
    fontFamily: tokens.type.scale.mono.family,
    fontSize: 11,
    color: tokens.color.text.tertiary,
    marginBottom: 12,
  },
  progressRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 8,
  },
  progressBarBg: {
    flex: 1,
    height: 6,
    backgroundColor: tokens.color.bg.base,
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    borderRadius: 3,
  },
  progressText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: 12,
    color: tokens.color.text.secondary,
    minWidth: 36,
    textAlign: 'right',
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  footerText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: 12,
    color: tokens.color.text.tertiary,
  },
  chevron: {
    position: 'absolute',
    right: 12,
    top: '50%',
    marginTop: -8,
  },
  empty: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 80,
    paddingHorizontal: 32,
  },
  emptyTitle: {
    fontFamily: tokens.type.scale.h3.family,
    fontSize: tokens.type.scale.h3.size,
    color: tokens.color.text.primary,
    marginTop: 16,
  },
  emptyText: {
    fontFamily: tokens.type.scale.body.family,
    fontSize: tokens.type.scale.body.size,
    color: tokens.color.text.secondary,
    textAlign: 'center',
    marginTop: 8,
    lineHeight: 22,
  },
});
