import React, { useCallback, useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Alert,
} from 'react-native';
import { usePipelines, useClips } from '../lib/api-hooks';
import { useAppStore } from '../lib/store';
import { design, haptics } from '../constants';

/**
 * PipelineScreen — Real API-integrated pipeline list
 * 
 * Uses usePipelines hook to fetch/create/manage pipelines.
 */
export function PipelineScreen() {
  const {
    pipelines,
    isLoading,
    refetch,
    createPipeline,
    startPipeline,
    pausePipeline,
  } = usePipelines();
  const { user } = useAppStore();
  const [refreshing, setRefreshing] = useState(false);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  }, [refetch]);

  const handleCreate = useCallback(() => {
    Alert.prompt(
      'New Pipeline',
      'Enter pipeline name:',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Create',
          onPress: async (name) => {
            if (!name) return;
            haptics.medium();
            try {
              await createPipeline.mutate({
                name,
                niche: 'technology',
                target_platforms: ['tiktok'],
                autonomy_mode: 'suggestOnly',
              });
            } catch (err: any) {
              Alert.alert('Error', err.message || 'Failed to create pipeline');
            }
          },
        },
      ]
    );
  }, [createPipeline]);

  const handleToggle = useCallback(
    async (id: string, currentStatus: string) => {
      haptics.medium();
      try {
        if (currentStatus === 'running') {
          await pausePipeline.mutate(id);
        } else {
          await startPipeline.mutate(id);
        }
      } catch (err: any) {
        Alert.alert('Error', err.message || 'Action failed');
      }
    },
    [startPipeline, pausePipeline]
  );

  const renderItem = useCallback(
    ({ item }: { item: any }) => (
      <PipelineRow
        pipeline={item}
        onToggle={() => handleToggle(item.id, item.status)}
      />
    ),
    [handleToggle]
  );

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Pipelines</Text>
        <TouchableOpacity style={styles.addBtn} onPress={handleCreate}>
          <Text style={styles.addBtnText}>+ New</Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={pipelines}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyText}>No pipelines yet</Text>
            <Text style={styles.emptySub}>Tap "New" to create one</Text>
          </View>
        }
      />
    </View>
  );
}

function PipelineRow({ pipeline, onToggle }: { pipeline: any; onToggle: () => void }) {
  const isRunning = pipeline.status === 'running';

  return (
    <View style={styles.row}>
      <View style={styles.rowLeft}>
        <Text style={styles.rowName}>{pipeline.name}</Text>
        <View style={styles.rowMeta}>
          <Text style={styles.rowTag}>{pipeline.niche}</Text>
          <Text
            style={[
              styles.rowStatus,
              isRunning ? styles.statusRunning : styles.statusPaused,
            ]}
          >
            {pipeline.status}
          </Text>
        </View>
        <Text style={styles.rowStats}>
          {pipeline.total_clips_generated || 0} clips · {pipeline.total_views || 0} views
        </Text>
      </View>
      <TouchableOpacity
        style={[styles.toggleBtn, isRunning ? styles.togglePause : styles.toggleStart]}
        onPress={onToggle}
      >
        <Text style={styles.toggleText}>{isRunning ? 'Pause' : 'Start'}</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: design.colors.bg },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: design.colors.border,
  },
  title: { fontSize: 24, fontWeight: '700', color: design.colors.text },
  addBtn: {
    backgroundColor: design.colors.primary,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
  },
  addBtnText: { color: '#fff', fontWeight: '600', fontSize: 14 },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: design.colors.border,
  },
  rowLeft: { flex: 1 },
  rowName: { fontSize: 16, fontWeight: '600', color: design.colors.text },
  rowMeta: { flexDirection: 'row', alignItems: 'center', marginTop: 4 },
  rowTag: {
    fontSize: 12,
    color: design.colors.muted,
    backgroundColor: design.colors.card,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    marginRight: 8,
  },
  rowStatus: { fontSize: 12, fontWeight: '600', textTransform: 'capitalize' },
  statusRunning: { color: design.colors.success },
  statusPaused: { color: design.colors.warning },
  rowStats: { fontSize: 12, color: design.colors.muted, marginTop: 4 },
  toggleBtn: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 6,
    marginLeft: 12,
  },
  togglePause: { backgroundColor: design.colors.warning + '20' },
  toggleStart: { backgroundColor: design.colors.success + '20' },
  toggleText: { fontSize: 13, fontWeight: '600' },
  empty: { padding: 40, alignItems: 'center' },
  emptyText: { fontSize: 16, color: design.colors.text, marginBottom: 8 },
  emptySub: { fontSize: 14, color: design.colors.muted },
});
