/**
 * Example: PipelineScreen with API integration
 * 
 * This file demonstrates how to use the API hooks
 * in a real screen component.
 */

import React, { useEffect } from 'react';
import { View, Text, FlatList, ActivityIndicator, RefreshControl } from 'react-native';
import { usePipelines, useClips } from '../lib/api-hooks';
import { PipelineRow } from '../components/PipelineRow';
import { ActionButton } from '../components/ActionButton';

export function PipelineScreen() {
  const { 
    pipelines, 
    isLoading, 
    refetch,
    createPipeline 
  } = usePipelines();
  
  const [refreshing, setRefreshing] = React.useState(false);
  
  const onRefresh = async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  };
  
  const handleCreatePipeline = async () => {
    try {
      await createPipeline.mutate({
        name: 'New Pipeline',
        niche: 'technology',
        target_platforms: ['tiktok', 'instagram'],
        autonomy_mode: 'suggestOnly'
      });
    } catch (error) {
      console.error('Failed to create pipeline:', error);
    }
  };
  
  if (isLoading && !pipelines.length) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" />
      </View>
    );
  }
  
  return (
    <View style={{ flex: 1 }}>
      <FlatList
        data={pipelines}
        renderItem={({ item }) => (
          <PipelineRow
            themeName={item.name}
            niche={item.niche}
            status={item.status}
            clipsThisWeek={item.clips_this_week || 0}
            onTap={() => console.log('Navigate to pipeline:', item.id)}
          />
        )}
        keyExtractor={(item) => item.id}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListEmptyComponent={
          <View style={{ padding: 20, alignItems: 'center' }}>
            <Text>No pipelines yet</Text>
            <ActionButton
              label="Create Pipeline"
              onPress={handleCreatePipeline}
            />
          </View>
        }
      />
    </View>
  );
}
