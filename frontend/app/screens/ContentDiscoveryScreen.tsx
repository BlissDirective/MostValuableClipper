import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  RefreshControl,
  TextInput,
  Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import {
  Search,
  Zap,
  RefreshCw,
  CheckCircle,
  XCircle,
  Clock,
  ChevronRight,
  Filter,
  Plus,
  Radio,
} from 'lucide-react-native';

import { tokens } from '@/constants/tokens';
import { useAuthStore } from '@/lib/store';
import { useToast } from '@/components/ToastProvider';
import {
  useDiscoveryStatus,
  useProposalAction,
  useAgentSources,
  useAgentStatus,
} from '@/lib/api-hooks';
import { agentsApi } from '@/lib/api';

export default function ContentDiscoveryScreen() {
  const router = useRouter();
  const { show: showToast } = useToast();
  const pipelines = useAuthStore((s) => s.pipelines);
  const fetchPipelines = useAuthStore((s) => s.fetchPipelines);

  const [activeTab, setActiveTab] = useState<'proposals' | 'sources'>('proposals');
  const [selectedPipelineId, setSelectedPipelineId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [discovering, setDiscovering] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // Select first pipeline by default
  useEffect(() => {
    fetchPipelines();
  }, [fetchPipelines]);

  useEffect(() => {
    if (pipelines.length > 0 && !selectedPipelineId) {
      setSelectedPipelineId(pipelines[0].id);
    }
  }, [pipelines, selectedPipelineId]);

  // Hooks
  const {
    proposals,
    pendingCount,
    lastDiscoveryRun,
    isLoading: proposalsLoading,
    refetch: refetchProposals,
  } = useDiscoveryStatus(selectedPipelineId);

  const {
    sources,
    total: sourcesTotal,
    isLoading: sourcesLoading,
    refetch: refetchSources,
  } = useAgentSources(selectedPipelineId);

  const { action: proposalAction, isPending: actionPending } = useProposalAction();
  const { status: agentStatus, isLoading: statusLoading } = useAgentStatus();

  const onRefresh = async () => {
    setRefreshing(true);
    if (activeTab === 'proposals') {
      await refetchProposals();
    } else {
      await refetchSources();
    }
    setRefreshing(false);
  };

  const runDiscovery = async () => {
    if (!selectedPipelineId) {
      showToast({ message: 'Select a pipeline first', type: 'error' });
      return;
    }
    setDiscovering(true);
    try {
      const data = await agentsApi.discover(selectedPipelineId, 10);
      showToast({
        message: `Discovery started! ${data.proposals_count ?? 0} proposals found`,
        type: 'success'
      });
      await refetchProposals();
    } catch (err: any) {
      showToast({ message: err?.message || 'Discovery failed', type: 'error' });
    } finally {
      setDiscovering(false);
    }
  };

  const handleApprove = async (clipId: string) => {
    try {
      await proposalAction({ clipId, action: 'approve' });
      showToast({ message: 'Proposal approved! Clip queued.', type: 'success' });
    } catch (err: any) {
      showToast({ message: err?.message || 'Failed to approve', type: 'error' });
    }
  };

  const handleReject = async (clipId: string) => {
    try {
      await proposalAction({ clipId, action: 'reject' });
      showToast({ message: 'Proposal rejected', type: 'info' });
    } catch (err: any) {
      showToast({ message: err?.message || 'Failed to reject', type: 'error' });
    }
  };

  const handleRefreshSource = async (sourceId: string) => {
    try {
      await agentsApi.refreshSource(sourceId);
      showToast({ message: 'Source refresh queued', type: 'success' });
      await refetchSources();
    } catch (err: any) {
      showToast({ message: err?.message || 'Failed to refresh', type: 'error' });
    }
  };

  const handleDeleteSource = async (sourceId: string) => {
    Alert.alert('Delete Source', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await agentsApi.deleteSource(sourceId);
            showToast({ message: 'Source deleted', type: 'info' });
            await refetchSources();
          } catch (err: any) {
            showToast({ message: err?.message || 'Failed to delete', type: 'error' });
          }
        },
      },
    ]);
  };

  // Filtering
  const filteredProposals = proposals.filter((p: any) => {
    if (filterStatus !== 'all' && p.status !== filterStatus) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        p.title?.toLowerCase().includes(q) ||
        p.description?.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const formatNumber = (n: number) => {
    if (!n) return '0';
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toString();
  };

  const confidenceColor = (score: number) => {
    if (score >= 0.8) return tokens.color.semantic.metric.positive;
    if (score >= 0.6) return tokens.color.semantic.metric.neutral;
    return tokens.color.semantic.metric.negative;
  };

  const isLoading = activeTab === 'proposals' ? proposalsLoading : sourcesLoading;

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.headerOverline}>DISCOVERY</Text>
          <Text style={styles.headerTitle}>Find Content</Text>
        </View>
        <TouchableOpacity
          style={[styles.discoverBtn, discovering && styles.discoverBtnActive]}
          onPress={runDiscovery}
          disabled={discovering || !selectedPipelineId}
        >
          {discovering ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <>
              <Zap size={16} color="#fff" strokeWidth={tokens.icon.stroke.default} />
              <Text style={styles.discoverBtnText}>Discover</Text>
            </>
          )}
        </TouchableOpacity>
      </View>

      {/* Pipeline Selector */}
      {pipelines.length > 0 && (
        <View style={styles.pipelineSelector}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            {pipelines.map((p) => (
              <TouchableOpacity
                key={p.id}
                style={[
                  styles.pipelineChip,
                  selectedPipelineId === p.id && styles.pipelineChipActive,
                ]}
                onPress={() => setSelectedPipelineId(p.id)}
              >
                <Radio
                  size={14}
                  color={
                    selectedPipelineId === p.id
                      ? tokens.color.brand.indigo[400]
                      : tokens.color.text.tertiary
                  }
                  strokeWidth={tokens.icon.stroke.default}
                />
                <Text
                  style={[
                    styles.pipelineChipText,
                    selectedPipelineId === p.id && styles.pipelineChipTextActive,
                  ]}
                  numberOfLines={1}
                >
                  {p.themeName || p.niche || 'Unnamed'}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>
      )}

      {/* Agent Status */}
      {agentStatus && (
        <View style={styles.statusBar}>
          <View style={styles.statusItem}>
            <Text style={styles.statusLabel}>Active</Text>
            <Text style={styles.statusValue}>
              {agentStatus.active_pipelines ?? 0} pipelines
            </Text>
          </View>
          <View style={styles.statusItem}>
            <Text style={styles.statusLabel}>Pending</Text>
            <Text style={styles.statusValue}>
              {agentStatus.pending_proposals ?? 0} proposals
            </Text>
          </View>
          {lastDiscoveryRun && (
            <View style={styles.statusItem}>
              <Text style={styles.statusLabel}>Last scan</Text>
              <Text style={styles.statusValue}>
                {new Date(lastDiscoveryRun).toLocaleDateString()}
              </Text>
            </View>
          )}
        </View>
      )}

      {/* Tab Switcher */}
      <View style={styles.tabBar}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'proposals' && styles.tabActive]}
          onPress={() => setActiveTab('proposals')}
        >
          <Text
            style={[
              styles.tabText,
              activeTab === 'proposals' && styles.tabTextActive,
            ]}
          >
            Proposals ({pendingCount})
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'sources' && styles.tabActive]}
          onPress={() => setActiveTab('sources')}
        >
          <Text
            style={[
              styles.tabText,
              activeTab === 'sources' && styles.tabTextActive,
            ]}
          >
            Sources ({sourcesTotal})
          </Text>
        </TouchableOpacity>
      </View>

      {/* Search & Filter */}
      <View style={styles.searchBar}>
        <Search
          size={16}
          color={tokens.color.text.tertiary}
          strokeWidth={tokens.icon.stroke.default}
        />
        <TextInput
          style={styles.searchInput}
          placeholder="Search..."
          placeholderTextColor={tokens.color.text.tertiary}
          value={searchQuery}
          onChangeText={setSearchQuery}
        />
        {activeTab === 'proposals' && (
          <TouchableOpacity
            style={styles.filterBtn}
            onPress={() => {
              const statuses = ['all', 'pending_review', 'approved', 'rejected'];
              const currentIndex = statuses.indexOf(filterStatus);
              setFilterStatus(statuses[(currentIndex + 1) % statuses.length]);
            }}
          >
            <Filter
              size={16}
              color={tokens.color.brand.indigo[400]}
              strokeWidth={tokens.icon.stroke.default}
            />
            <Text style={styles.filterText}>{filterStatus}</Text>
          </TouchableOpacity>
        )}
      </View>

      <ScrollView
        style={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={tokens.color.brand.indigo[400]}
            colors={[tokens.color.brand.indigo[400]]}
            progressBackgroundColor={tokens.color.bg.raised}
          />
        }
      >
        {isLoading && !refreshing ? (
          <View style={styles.loadingState}>
            <ActivityIndicator size="large" color={tokens.color.brand.indigo[400]} />
          </View>
        ) : activeTab === 'proposals' ? (
          <>
            {filteredProposals.length === 0 ? (
              <View style={styles.emptyState}>
                <Search
                  size={48}
                  color={tokens.color.text.tertiary}
                  strokeWidth={tokens.icon.stroke.thin}
                />
                <Text style={styles.emptyTitle}>No proposals yet</Text>
                <Text style={styles.emptySubtitle}>
                  Tap "Discover" to scan your sources for viral-worthy content
                </Text>
              </View>
            ) : (
              filteredProposals.map((proposal: any) => (
                <View key={proposal.id} style={styles.proposalCard}>
                  <View style={styles.proposalHeader}>
                    <View style={styles.proposalMeta}>
                      <Text style={styles.proposalSource}>
                        {proposal.source_name || proposal.source_type || 'Unknown'}
                      </Text>
                      <Text style={styles.proposalTime}>
                        {proposal.created_at
                          ? new Date(proposal.created_at).toLocaleDateString()
                          : 'Recently'}
                      </Text>
                    </View>
                    {proposal.confidence_score !== undefined && (
                      <View
                        style={[
                          styles.confidenceBadge,
                          {
                            backgroundColor:
                              confidenceColor(proposal.confidence_score) + '20',
                          },
                        ]}
                      >
                        <Text
                          style={[
                            styles.confidenceText,
                            {
                              color: confidenceColor(proposal.confidence_score),
                            },
                          ]}
                        >
                          {Math.round(proposal.confidence_score * 100)}% match
                        </Text>
                      </View>
                    )}
                  </View>

                  <Text style={styles.proposalTitle}>{proposal.title}</Text>
                  {proposal.description && (
                    <Text style={styles.proposalDesc} numberOfLines={2}>
                      {proposal.description}
                    </Text>
                  )}

                  <View style={styles.metricsRow}>
                    <View style={styles.metric}>
                      <Text style={styles.metricValue}>
                        {formatNumber(proposal.predicted_reach)}
                      </Text>
                      <Text style={styles.metricLabel}>predicted reach</Text>
                    </View>
                    <View style={styles.metric}>
                      <Text style={styles.metricValue}>
                        {proposal.predicted_retention
                          ? Math.round(proposal.predicted_retention * 100) + '%'
                          : '—'}
                      </Text>
                      <Text style={styles.metricLabel}>retention</Text>
                    </View>
                    {proposal.duration_seconds && (
                      <View style={styles.metric}>
                        <Text style={styles.metricValue}>
                          {Math.round(proposal.duration_seconds)}s
                        </Text>
                        <Text style={styles.metricLabel}>duration</Text>
                      </View>
                    )}
                  </View>

                  {proposal.status === 'pending_review' && (
                    <View style={styles.actionRow}>
                      <TouchableOpacity
                        style={[styles.actionBtn, styles.approveBtn]}
                        onPress={() => handleApprove(proposal.id)}
                        disabled={actionPending}
                      >
                        <CheckCircle size={16} color="#fff" strokeWidth={tokens.icon.stroke.default} />
                        <Text style={styles.actionBtnText}>Approve</Text>
                      </TouchableOpacity>
                      <TouchableOpacity
                        style={[styles.actionBtn, styles.rejectBtn]}
                        onPress={() => handleReject(proposal.id)}
                        disabled={actionPending}
                      >
                        <XCircle size={16} color={tokens.color.semantic.metric.negative} strokeWidth={tokens.icon.stroke.default} />
                        <Text style={[styles.actionBtnText, styles.rejectBtnText]}>
                          Reject
                        </Text>
                      </TouchableOpacity>
                    </View>
                  )}

                  {proposal.status !== 'pending_review' && (
                    <View
                      style={[
                        styles.statusBadge,
                        proposal.status === 'approved'
                          ? styles.statusApproved
                          : proposal.status === 'rejected'
                          ? styles.statusRejected
                          : styles.statusQueued,
                      ]}
                    >
                      <Text style={styles.statusText}>
                        {proposal.status
                          ?.replace('_', ' ')
                          .replace(/\b\w/g, (l: string) => l.toUpperCase())}
                      </Text>
                    </View>
                  )}
                </View>
              ))
            )}
          </>
        ) : (
          <>
            <TouchableOpacity
              style={styles.addSourceCard}
              onPress={() => router.push('/(app)/add-source')}
            >
              <Plus
                size={24}
                color={tokens.color.brand.indigo[400]}
                strokeWidth={tokens.icon.stroke.default}
              />
              <Text style={styles.addSourceText}>Add New Source</Text>
              <ChevronRight
                size={16}
                color={tokens.color.text.tertiary}
                strokeWidth={tokens.icon.stroke.default}
              />
            </TouchableOpacity>

            {sources.length === 0 ? (
              <View style={styles.emptyState}>
                <Search
                  size={48}
                  color={tokens.color.text.tertiary}
                  strokeWidth={tokens.icon.stroke.thin}
                />
                <Text style={styles.emptyTitle}>No sources yet</Text>
                <Text style={styles.emptySubtitle}>
                  Add YouTube channels, RSS feeds, or direct video links to get started
                </Text>
              </View>
            ) : (
              sources.map((source: any) => (
                <View key={source.id} style={styles.sourceCard}>
                  <View style={styles.sourceHeader}>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.sourceName}>{source.name}</Text>
                      <Text style={styles.sourceType}>{source.type}</Text>
                    </View>
                    <View
                      style={[
                        styles.healthBadge,
                        source.health_status === 'healthy'
                          ? styles.healthHealthy
                          : source.health_status === 'unhealthy'
                          ? styles.healthUnhealthy
                          : styles.healthUnknown,
                      ]}
                    >
                      <Text style={styles.healthText}>{source.health_status}</Text>
                    </View>
                  </View>

                  <Text style={styles.sourceUrl} numberOfLines={1}>
                    {source.url}
                  </Text>

                  <View style={styles.sourceFooter}>
                    <View style={styles.sourceMeta}>
                      <Clock
                        size={12}
                        color={tokens.color.text.tertiary}
                        strokeWidth={tokens.icon.stroke.default}
                      />
                      <Text style={styles.sourceMetaText}>
                        {source.last_fetched_at
                          ? new Date(source.last_fetched_at).toLocaleDateString()
                          : 'Never fetched'}
                      </Text>
                    </View>
                    <View style={styles.sourceActions}>
                      <TouchableOpacity
                        style={styles.sourceActionBtn}
                        onPress={() => handleRefreshSource(source.id)}
                      >
                        <RefreshCw
                          size={14}
                          color={tokens.color.brand.indigo[400]}
                          strokeWidth={tokens.icon.stroke.default}
                        />
                      </TouchableOpacity>
                      <TouchableOpacity
                        style={[styles.sourceActionBtn, styles.sourceActionBtnDanger]}
                        onPress={() => handleDeleteSource(source.id)}
                      >
                        <XCircle
                          size={14}
                          color={tokens.color.semantic.metric.negative}
                          strokeWidth={tokens.icon.stroke.default}
                        />
                      </TouchableOpacity>
                    </View>
                  </View>
                </View>
              ))
            )}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: tokens.color.bg.base,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: tokens.layout.screenPadding,
    paddingVertical: tokens.spacing.md,
  },
  headerOverline: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    lineHeight: tokens.type.scale.overline.lineHeight,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  headerTitle: {
    fontFamily: tokens.type.scale.h2.family,
    fontSize: tokens.type.scale.h2.size,
    lineHeight: tokens.type.scale.h2.lineHeight,
    letterSpacing: tokens.type.scale.h2.letterSpacing,
    color: tokens.color.text.primary,
  },
  discoverBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: tokens.color.brand.indigo[500],
    borderRadius: tokens.radius.lg,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    gap: tokens.spacing.xs,
  },
  discoverBtnActive: {
    backgroundColor: tokens.color.brand.indigo[700],
  },
  discoverBtnText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: tokens.type.scale.bodySmall.size,
    fontFamily: tokens.type.scale.bodySmall.family,
  },
  pipelineSelector: {
    paddingHorizontal: tokens.layout.screenPadding,
    marginBottom: tokens.spacing.sm,
  },
  pipelineChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.xs,
    backgroundColor: tokens.color.bg.raised,
    borderRadius: tokens.radius.pill,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.xs,
    marginRight: tokens.spacing.xs,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
  },
  pipelineChipActive: {
    borderColor: tokens.color.brand.indigo[400],
    backgroundColor: tokens.color.brand.indigo[900],
  },
  pipelineChipText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.secondary,
    maxWidth: 120,
  },
  pipelineChipTextActive: {
    color: tokens.color.text.primary,
  },
  statusBar: {
    flexDirection: 'row',
    paddingHorizontal: tokens.layout.screenPadding,
    marginBottom: tokens.spacing.sm,
    gap: tokens.spacing.md,
  },
  statusItem: {
    flex: 1,
  },
  statusLabel: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.tertiary,
  },
  statusValue: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.primary,
  },
  tabBar: {
    flexDirection: 'row',
    paddingHorizontal: tokens.layout.screenPadding,
    marginBottom: tokens.spacing.sm,
  },
  tab: {
    flex: 1,
    paddingVertical: tokens.spacing.sm,
    alignItems: 'center',
    borderBottomWidth: 2,
    borderBottomColor: tokens.color.border.subtle,
  },
  tabActive: {
    borderBottomColor: tokens.color.brand.indigo[400],
  },
  tabText: {
    color: tokens.color.text.tertiary,
    fontWeight: '500',
    fontSize: tokens.type.scale.bodySmall.size,
    fontFamily: tokens.type.scale.bodySmall.family,
  },
  tabTextActive: {
    color: tokens.color.text.primary,
  },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: tokens.color.bg.raised,
    borderRadius: tokens.radius.lg,
    marginHorizontal: tokens.layout.screenPadding,
    marginBottom: tokens.spacing.md,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    gap: tokens.spacing.sm,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
  },
  searchInput: {
    flex: 1,
    color: tokens.color.text.primary,
    fontSize: tokens.type.scale.bodyMedium.size,
    fontFamily: tokens.type.scale.bodyMedium.family,
    padding: 0,
  },
  filterBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.xs,
    backgroundColor: tokens.color.bg.surface,
    borderRadius: tokens.radius.md,
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: tokens.spacing.xs,
  },
  filterText: {
    color: tokens.color.brand.indigo[400],
    fontSize: tokens.type.scale.caption.size,
    fontWeight: '500',
    textTransform: 'capitalize',
    fontFamily: tokens.type.scale.caption.family,
  },
  content: {
    flex: 1,
    paddingHorizontal: tokens.layout.screenPadding,
  },
  loadingState: {
    paddingVertical: tokens.spacing.xxxl,
    alignItems: 'center',
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: tokens.spacing.xxxl,
  },
  emptyTitle: {
    fontFamily: tokens.type.scale.h2.family,
    fontSize: tokens.type.scale.h2.size,
    color: tokens.color.text.primary,
    marginTop: tokens.spacing.md,
  },
  emptySubtitle: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    color: tokens.color.text.secondary,
    textAlign: 'center',
    marginTop: tokens.spacing.xs,
    paddingHorizontal: tokens.spacing.xl,
  },
  proposalCard: {
    backgroundColor: tokens.color.bg.raised,
    borderRadius: tokens.radius.lg,
    padding: tokens.spacing.md,
    marginBottom: tokens.spacing.md,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
  },
  proposalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: tokens.spacing.sm,
  },
  proposalMeta: {
    flex: 1,
  },
  proposalSource: {
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.brand.indigo[400],
    fontWeight: '600',
    textTransform: 'uppercase',
    fontFamily: tokens.type.scale.caption.family,
  },
  proposalTime: {
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.tertiary,
    marginTop: 2,
    fontFamily: tokens.type.scale.caption.family,
  },
  confidenceBadge: {
    borderRadius: tokens.radius.md,
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: tokens.spacing.xs,
  },
  confidenceText: {
    fontSize: tokens.type.scale.caption.size,
    fontWeight: '600',
    fontFamily: tokens.type.scale.caption.family,
  },
  proposalTitle: {
    fontSize: tokens.type.scale.bodyMedium.size,
    fontWeight: '600',
    color: tokens.color.text.primary,
    marginBottom: tokens.spacing.xs,
    fontFamily: tokens.type.scale.bodyMedium.family,
  },
  proposalDesc: {
    fontSize: tokens.type.scale.bodySmall.size,
    color: tokens.color.text.secondary,
    marginBottom: tokens.spacing.md,
    fontFamily: tokens.type.scale.bodySmall.family,
  },
  metricsRow: {
    flexDirection: 'row',
    gap: tokens.spacing.md,
    marginBottom: tokens.spacing.md,
  },
  metric: {
    flex: 1,
  },
  metricValue: {
    fontSize: tokens.type.scale.h3.size,
    fontWeight: '700',
    color: tokens.color.text.primary,
    fontFamily: tokens.type.scale.h3.family,
  },
  metricLabel: {
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.tertiary,
    marginTop: 2,
    fontFamily: tokens.type.scale.caption.family,
  },
  actionRow: {
    flexDirection: 'row',
    gap: tokens.spacing.sm,
    marginTop: tokens.spacing.xs,
  },
  actionBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: tokens.spacing.xs,
    borderRadius: tokens.radius.md,
    paddingVertical: tokens.spacing.sm,
  },
  approveBtn: {
    backgroundColor: tokens.color.semantic.metric.positive,
  },
  rejectBtn: {
    backgroundColor: tokens.color.bg.surface,
  },
  actionBtnText: {
    fontWeight: '600',
    fontSize: tokens.type.scale.bodySmall.size,
    color: '#fff',
    fontFamily: tokens.type.scale.bodySmall.family,
  },
  rejectBtnText: {
    color: tokens.color.semantic.metric.negative,
  },
  statusBadge: {
    alignSelf: 'flex-start',
    borderRadius: tokens.radius.md,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.xs,
    marginTop: tokens.spacing.xs,
  },
  statusApproved: {
    backgroundColor: tokens.color.semantic.metric.positive + '20',
  },
  statusRejected: {
    backgroundColor: tokens.color.semantic.metric.negative + '20',
  },
  statusQueued: {
    backgroundColor: tokens.color.brand.indigo[900],
  },
  statusText: {
    fontSize: tokens.type.scale.caption.size,
    fontWeight: '600',
    color: tokens.color.text.primary,
    fontFamily: tokens.type.scale.caption.family,
  },
  addSourceCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: tokens.color.bg.raised,
    borderRadius: tokens.radius.lg,
    padding: tokens.spacing.md,
    marginBottom: tokens.spacing.md,
    gap: tokens.spacing.md,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    borderStyle: 'dashed',
  },
  addSourceText: {
    flex: 1,
    fontSize: tokens.type.scale.bodyMedium.size,
    fontWeight: '600',
    color: tokens.color.text.primary,
    fontFamily: tokens.type.scale.bodyMedium.family,
  },
  sourceCard: {
    backgroundColor: tokens.color.bg.raised,
    borderRadius: tokens.radius.lg,
    padding: tokens.spacing.md,
    marginBottom: tokens.spacing.md,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
  },
  sourceHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: tokens.spacing.sm,
  },
  sourceName: {
    fontSize: tokens.type.scale.bodyMedium.size,
    fontWeight: '600',
    color: tokens.color.text.primary,
    fontFamily: tokens.type.scale.bodyMedium.family,
  },
  sourceType: {
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.tertiary,
    marginTop: 2,
    textTransform: 'capitalize',
    fontFamily: tokens.type.scale.caption.family,
  },
  healthBadge: {
    borderRadius: tokens.radius.md,
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: tokens.spacing.xs,
  },
  healthHealthy: {
    backgroundColor: tokens.color.semantic.metric.positive + '20',
  },
  healthUnhealthy: {
    backgroundColor: tokens.color.semantic.metric.negative + '20',
  },
  healthUnknown: {
    backgroundColor: tokens.color.text.tertiary + '20',
  },
  healthText: {
    fontSize: tokens.type.scale.caption.size,
    fontWeight: '600',
    color: tokens.color.text.primary,
    fontFamily: tokens.type.scale.caption.family,
  },
  sourceUrl: {
    fontSize: tokens.type.scale.bodySmall.size,
    color: tokens.color.text.tertiary,
    marginBottom: tokens.spacing.md,
    fontFamily: tokens.type.scale.bodySmall.family,
  },
  sourceFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  sourceMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.xs,
  },
  sourceMetaText: {
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.tertiary,
    fontFamily: tokens.type.scale.caption.family,
  },
  sourceActions: {
    flexDirection: 'row',
    gap: tokens.spacing.sm,
  },
  sourceActionBtn: {
    width: 32,
    height: 32,
    borderRadius: tokens.radius.pill,
    backgroundColor: tokens.color.bg.surface,
    justifyContent: 'center',
    alignItems: 'center',
  },
  sourceActionBtnDanger: {
    backgroundColor: tokens.color.semantic.metric.negative + '15',
  },
});
