import React, { useCallback, useEffect, useState } from "react";
import {
  Alert,
  FlatList,
  ListRenderItem,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useRouter } from "expo-router";
import { GitBranch, Plus } from "lucide-react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { tokens } from "@/constants/tokens";
import { ActionButton } from "@/components/ActionButton";
import { PipelineRow } from "@/components/PipelineRow";
import { Pipeline, useAuthStore } from "@/lib/store";
import { triggerHaptic } from "@/utils/haptics";

export default function PipelinesScreen() {
  const router = useRouter();
  const pipelines = useAuthStore((s) => s.pipelines);
  const pipelinesLoading = useAuthStore((s) => s.pipelinesLoading);
  const fetchPipelines = useAuthStore((s) => s.fetchPipelines);
  const updatePipeline = useAuthStore((s) => s.updatePipeline);
  const removePipeline = useAuthStore((s) => s.removePipeline);
  const [refreshing, setRefreshing] = useState(false);
  const [showEmpty, setShowEmpty] = useState<boolean>(false);

  useEffect(() => {
    fetchPipelines();
  }, []);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchPipelines();
    setRefreshing(false);
  }, [fetchPipelines]);

  const data = showEmpty ? [] : pipelines;

  const handleLongPress = useCallback(
    (p: Pipeline) => {
      triggerHaptic("selection");
      const togglePauseLabel = p.status === "paused" ? "Resume" : "Pause";
      Alert.alert(
        p.themeName,
        "Quick actions",
        [
          {
            text: togglePauseLabel,
            onPress: () => {
              updatePipeline(p.id, { status: p.status === "paused" ? "running" : "paused" });
            },
          },
          {
            text: "Edit",
            onPress: () => router.push(`/(app)/pipelines/${p.id}`),
          },
          {
            text: "Delete",
            style: "destructive",
            onPress: () => removePipeline(p.id),
          },
          { text: "Cancel", style: "cancel" },
        ],
        { cancelable: true }
      );
    },
    [router, updatePipeline, removePipeline]
  );

  const renderItem: ListRenderItem<Pipeline> = useCallback(
    ({ item }) => (
      <PipelineRow
        themeName={item.themeName}
        niche={item.niche}
        status={item.status}
        clipsThisWeek={item.clipsThisWeek}
        viewDelta={item.viewDelta}
        deltaVariant={item.deltaVariant}
        onTap={() => router.push(`/(app)/pipelines/${item.id}`)}
        onLongPress={() => handleLongPress(item)}
      />
    ),
    [router, handleLongPress]
  );

  return (
    <SafeAreaView edges={["top"]} style={styles.safe}>
      <View style={styles.header}>
        <View>
          <Text style={styles.overline}>YOUR THEMES</Text>
          <Text style={styles.title}>Pipelines</Text>
        </View>
        <ActionButton
          label="New"
          variant="primary"
          size="sm"
          iconLeft={Plus}
          onPress={() => router.push("/(app)/pipelines/new")}
        />
      </View>

      <FlatList
        data={data}
        keyExtractor={(p) => p.id}
        renderItem={renderItem}
        contentContainerStyle={styles.listContent}
        ItemSeparatorComponent={Separator}
        refreshControl={
          <RefreshControl refreshing={refreshing || pipelinesLoading} onRefresh={onRefresh} tintColor={tokens.color.text.tertiary} />
        }
        ListEmptyComponent={
          <EmptyPipelines onCreate={() => router.push("/(app)/pipelines/new")} />
        }
        ListFooterComponent={
          data.length > 0 ? (
            <View style={styles.footerHint}>
              <Text style={styles.footerHintText}>
                Long-press a row for quick actions.
              </Text>
              <ActionButton
                label={showEmpty ? "Show pipelines" : "Preview empty state"}
                variant="ghost"
                size="sm"
                onPress={() => setShowEmpty((v) => !v)}
              />
            </View>
          ) : null
        }
        showsVerticalScrollIndicator={false}
      />
    </SafeAreaView>
  );
}

function Separator() {
  return <View style={{ height: tokens.layout.feedCardGap }} />;
}

interface EmptyPipelinesProps {
  onCreate: () => void;
}

function EmptyPipelines({ onCreate }: EmptyPipelinesProps) {
  return (
    <View style={styles.empty}>
      <View style={styles.emptyIconWrap}>
        <GitBranch
          size={tokens.icon.size.xl * 2.5}
          color={tokens.color.text.tertiary}
          strokeWidth={tokens.icon.stroke.thin}
        />
      </View>
      <Text style={styles.emptyTitle}>No pipelines yet</Text>
      <Text style={styles.emptyBody}>Themes you spin up appear here.</Text>
      <View style={{ height: tokens.spacing.md }} />
      <ActionButton
        label="Create your first pipeline"
        variant="primary"
        size="lg"
        onPress={onCreate}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: tokens.color.bg.base },
  header: {
    height: tokens.layout.headerHeight,
    paddingHorizontal: tokens.layout.screenPadding,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  overline: {
    fontFamily: tokens.type.scale.overline.family,
    fontSize: tokens.type.scale.overline.size,
    lineHeight: tokens.type.scale.overline.lineHeight,
    letterSpacing: tokens.type.scale.overline.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  title: {
    fontFamily: tokens.type.scale.h1.family,
    fontSize: tokens.type.scale.h1.size,
    lineHeight: tokens.type.scale.h1.lineHeight,
    letterSpacing: tokens.type.scale.h1.letterSpacing,
    color: tokens.color.text.primary,
  },
  listContent: {
    paddingHorizontal: tokens.layout.screenPadding,
    paddingBottom: tokens.spacing.xxl,
    flexGrow: 1,
  },
  footerHint: {
    marginTop: tokens.spacing.lg,
    alignItems: "center",
    gap: tokens.spacing.sm,
  },
  footerHintText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    lineHeight: tokens.type.scale.caption.lineHeight,
    letterSpacing: tokens.type.scale.caption.letterSpacing,
    color: tokens.color.text.tertiary,
  },
  empty: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: tokens.spacing.xxxl,
    paddingHorizontal: tokens.spacing.lg,
    gap: tokens.spacing.sm,
  },
  emptyIconWrap: { marginBottom: tokens.spacing.md, opacity: 0.6 },
  emptyTitle: {
    fontFamily: tokens.type.scale.h1.family,
    fontSize: tokens.type.scale.h1.size,
    lineHeight: tokens.type.scale.h1.lineHeight,
    letterSpacing: tokens.type.scale.h1.letterSpacing,
    color: tokens.color.text.primary,
    textAlign: "center",
  },
  emptyBody: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    lineHeight: tokens.type.scale.bodySmall.lineHeight,
    color: tokens.color.text.secondary,
    textAlign: "center",
    maxWidth: 280,
  },
});
