import React, { useCallback, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  TextInput,
  RefreshControl,
  Alert,
} from 'react-native';
import { Link2 } from "lucide-react-native";
import { EmptyState } from "@/components/EmptyState";
import { useSources, usePipelines } from '../../lib/api-hooks';
import { design, haptics } from '../../constants';

/**
 * SourceScreen — Add and manage video sources for pipelines
 */
export function SourceScreen() {
  const { sources, isLoading, refetch, createSource, deleteSource } = useSources();
  const { pipelines } = usePipelines();
  const [refreshing, setRefreshing] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [newUrl, setNewUrl] = useState('');
  const [selectedPipeline, setSelectedPipeline] = useState('');

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  }, [refetch]);

  const handleAdd = useCallback(async () => {
    if (!newUrl.trim()) {
      Alert.alert('Error', 'Please enter a URL');
      return;
    }
    if (!selectedPipeline) {
      Alert.alert('Error', 'Please select a pipeline');
      return;
    }

    haptics.medium();
    try {
      await createSource.mutate({
        pipeline_id: selectedPipeline,
        source_url: newUrl.trim(),
        source_type: 'youtube',
      });
      setNewUrl('');
      setShowAdd(false);
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to add source');
    }
  }, [newUrl, selectedPipeline, createSource]);

  const handleDelete = useCallback(
    (id: string) => {
      Alert.alert('Delete Source', 'Are you sure?', [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await deleteSource.mutate(id);
            } catch (err: any) {
              Alert.alert('Error', err.message);
            }
          },
        },
      ]);
    },
    [deleteSource]
  );

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Sources</Text>
        <TouchableOpacity style={styles.addBtn} onPress={() => setShowAdd(!showAdd)}>
          <Text style={styles.addBtnText}>{showAdd ? 'Close' : '+ Add'}</Text>
        </TouchableOpacity>
      </View>

      {showAdd && (
        <View style={styles.addForm}>
          <Text style={styles.formLabel}>Pipeline</Text>
          <View style={styles.pipelinePicker}>
            {pipelines.map((p: any) => (
              <TouchableOpacity
                key={p.id}
                style={[
                  styles.pipelineChip,
                  selectedPipeline === p.id && styles.pipelineChipActive,
                ]}
                onPress={() => setSelectedPipeline(p.id)}
              >
                <Text
                  style={[
                    styles.pipelineChipText,
                    selectedPipeline === p.id && styles.pipelineChipTextActive,
                  ]}
                >
                  {p.name}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          <Text style={styles.formLabel}>Video URL</Text>
          <TextInput
            style={styles.input}
            placeholder="YouTube URL or direct link"
            placeholderTextColor={design.colors.muted}
            value={newUrl}
            onChangeText={setNewUrl}
            autoCapitalize="none"
            keyboardType="url"
          />

          <TouchableOpacity style={styles.submitBtn} onPress={handleAdd}>
            <Text style={styles.submitText}>Add Source</Text>
          </TouchableOpacity>
        </View>
      )}

      <FlatList
        data={sources}
        renderItem={({ item }) => (
          <SourceRow source={item} onDelete={() => handleDelete(item.id)} />
        )}
        keyExtractor={(item) => item.id}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListEmptyComponent={
          <EmptyState
            icon={Link2}
            title="No sources yet"
            subtitle="Add a YouTube channel or video URL to start generating clips."
            actionLabel="Add Source"
            size="md"
          />
        }
      />
    </View>
  );
}

function SourceRow({ source, onDelete }: { source: any; onDelete: () => void }) {
  const isActive = source.is_active !== false;

  return (
    <View style={styles.row}>
      <View style={styles.rowLeft}>
        <Text style={styles.rowUrl} numberOfLines={1}>
          {source.source_url}
        </Text>
        <View style={styles.rowMeta}>
          <Text style={styles.rowType}>{source.source_type}</Text>
          <Text style={[styles.rowStatus, isActive ? styles.active : styles.inactive]}>
            {isActive ? 'Active' : 'Inactive'}
          </Text>
          <Text style={styles.rowCount}>
            {source.videos_found_count || 0} videos found
          </Text>
        </View>
      </View>
      <TouchableOpacity style={styles.deleteBtn} onPress={onDelete}>
        <Text style={styles.deleteText}>🗑</Text>
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
  addForm: {
    padding: 16,
    backgroundColor: design.colors.card,
    margin: 16,
    borderRadius: 12,
  },
  formLabel: { fontSize: 14, fontWeight: '600', color: design.colors.text, marginBottom: 8 },
  pipelinePicker: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: 12 },
  pipelineChip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: design.colors.bg,
    marginRight: 8,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: design.colors.border,
  },
  pipelineChipActive: { backgroundColor: design.colors.primary, borderColor: design.colors.primary },
  pipelineChipText: { fontSize: 13, color: design.colors.text },
  pipelineChipTextActive: { color: '#fff', fontWeight: '600' },
  input: {
    borderWidth: 1,
    borderColor: design.colors.border,
    borderRadius: 8,
    padding: 12,
    fontSize: 15,
    color: design.colors.text,
    marginBottom: 12,
  },
  submitBtn: {
    backgroundColor: design.colors.success,
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  submitText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: design.colors.border,
  },
  rowLeft: { flex: 1 },
  rowUrl: { fontSize: 14, fontWeight: '600', color: design.colors.text, marginBottom: 4 },
  rowMeta: { flexDirection: 'row', alignItems: 'center' },
  rowType: {
    fontSize: 12,
    color: design.colors.muted,
    backgroundColor: design.colors.bg,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    marginRight: 8,
  },
  rowStatus: { fontSize: 12, fontWeight: '600', marginRight: 8 },
  active: { color: design.colors.success },
  inactive: { color: design.colors.error },
  rowCount: { fontSize: 12, color: design.colors.muted },
  deleteBtn: { padding: 8 },
  deleteText: { fontSize: 18 },
  empty: { padding: 40, alignItems: 'center' },
  emptyText: { fontSize: 16, color: design.colors.text, marginBottom: 8 },
  emptySub: { fontSize: 14, color: design.colors.muted },
});
