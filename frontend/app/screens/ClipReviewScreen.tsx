import React, { useCallback, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Image,
  RefreshControl,
  Alert,
  Dimensions,
} from 'react-native';
import { useClips, usePipelines } from '../../lib/api-hooks';
import { design, haptics } from '../../constants';

const { width } = Dimensions.get('window');

/**
 * ClipReviewScreen — Swipe deck for approving/rejecting generated clips
 * 
 * Fetches clips in "ready_for_review" status. 
 * Swipe right = approve, left = reject.
 */
export function ClipReviewScreen() {
  const { clips, isLoading, refetch, approveClip, rejectClip } = useClips();
  const { pipelines } = usePipelines();
  const [refreshing, setRefreshing] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);

  // Filter to only reviewable clips
  const reviewClips = clips.filter((c: any) => c.status === 'ready_for_review');

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  }, [refetch]);

  const handleApprove = useCallback(
    async (clipId: string) => {
      haptics.success();
      try {
        await approveClip.mutate(clipId);
        setCurrentIndex((i) => Math.min(i + 1, reviewClips.length - 1));
      } catch (err: any) {
        Alert.alert('Error', err.message);
      }
    },
    [approveClip, reviewClips.length]
  );

  const handleReject = useCallback(
    async (clipId: string) => {
      haptics.error();
      try {
        await rejectClip.mutate(clipId);
        setCurrentIndex((i) => Math.min(i + 1, reviewClips.length - 1));
      } catch (err: any) {
        Alert.alert('Error', err.message);
      }
    },
    [rejectClip, reviewClips.length]
  );

  const currentClip = reviewClips[currentIndex];

  if (isLoading && !reviewClips.length) {
    return (
      <View style={[styles.container, styles.center]}>
        <Text style={styles.loadingText}>Loading clips…</Text>
      </View>
    );
  }

  if (!currentClip) {
    return (
      <View style={[styles.container, styles.center]}>
        <Text style={styles.emptyTitle}>All caught up! 🎉</Text>
        <Text style={styles.emptySub}>
          No clips waiting for review. Check back later.
        </Text>
        <TouchableOpacity style={styles.refreshBtn} onPress={onRefresh}>
          <Text style={styles.refreshText}>Refresh</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>
          Review ({currentIndex + 1}/{reviewClips.length})
        </Text>
      </View>

      <View style={styles.card}>
        {currentClip.thumbnail_url ? (
          <Image
            source={{ uri: currentClip.thumbnail_url }}
            style={styles.thumbnail}
            resizeMode="cover"
          />
        ) : (
          <View style={[styles.thumbnail, styles.thumbPlaceholder]}>
            <Text style={styles.thumbPlaceholderText}>🎬</Text>
          </View>
        )}

        <View style={styles.cardContent}>
          <Text style={styles.clipTitle} numberOfLines={2}>
            {currentClip.title || 'Untitled Clip'}
          </Text>
          <Text style={styles.clipCaption} numberOfLines={3}>
            {currentClip.caption || 'No caption generated'}
          </Text>
          {currentClip.hashtags?.length > 0 && (
            <Text style={styles.hashtags}>
              {currentClip.hashtags.slice(0, 5).join(' ')}
            </Text>
          )}
          <View style={styles.metaRow}>
            <Text style={styles.metaText}>
              {Math.round(currentClip.duration_seconds || 0)}s
            </Text>
            {currentClip.safety_flags?.length > 0 && (
              <View style={styles.safetyBadge}>
                <Text style={styles.safetyText}>⚠️ Flagged</Text>
              </View>
            )}
          </View>
        </View>
      </View>

      <View style={styles.actions}>
        <TouchableOpacity
          style={[styles.actionBtn, styles.rejectBtn]}
          onPress={() => handleReject(currentClip.id)}
        >
          <Text style={styles.actionText}>✕ Reject</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.actionBtn, styles.approveBtn]}
          onPress={() => handleApprove(currentClip.id)}
        >
          <Text style={styles.actionText}>✓ Approve</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: design.colors.bg },
  center: { justifyContent: 'center', alignItems: 'center', padding: 24 },
  header: { padding: 20, borderBottomWidth: 1, borderBottomColor: design.colors.border },
  headerTitle: { fontSize: 20, fontWeight: '700', color: design.colors.text },
  card: {
    margin: 16,
    backgroundColor: design.colors.card,
    borderRadius: 16,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  thumbnail: { width: '100%', height: width * 0.56 },
  thumbPlaceholder: {
    backgroundColor: design.colors.border,
    justifyContent: 'center',
    alignItems: 'center',
  },
  thumbPlaceholderText: { fontSize: 48 },
  cardContent: { padding: 16 },
  clipTitle: { fontSize: 18, fontWeight: '700', color: design.colors.text, marginBottom: 8 },
  clipCaption: { fontSize: 14, color: design.colors.muted, lineHeight: 20, marginBottom: 8 },
  hashtags: { fontSize: 13, color: design.colors.primary, marginBottom: 8 },
  metaRow: { flexDirection: 'row', alignItems: 'center', marginTop: 4 },
  metaText: { fontSize: 13, color: design.colors.muted },
  safetyBadge: {
    marginLeft: 12,
    backgroundColor: design.colors.warning + '20',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  safetyText: { fontSize: 12, color: design.colors.warning, fontWeight: '600' },
  actions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  actionBtn: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
    marginHorizontal: 6,
  },
  rejectBtn: { backgroundColor: design.colors.error + '15' },
  approveBtn: { backgroundColor: design.colors.success + '15' },
  actionText: { fontSize: 15, fontWeight: '600' },
  emptyTitle: { fontSize: 22, fontWeight: '700', color: design.colors.text, marginBottom: 8 },
  emptySub: { fontSize: 14, color: design.colors.muted, textAlign: 'center', marginBottom: 20 },
  refreshBtn: {
    backgroundColor: design.colors.primary,
    paddingHorizontal: 24,
    paddingVertical: 10,
    borderRadius: 8,
  },
  refreshText: { color: '#fff', fontWeight: '600', fontSize: 15 },
  loadingText: { fontSize: 16, color: design.colors.muted },
});
