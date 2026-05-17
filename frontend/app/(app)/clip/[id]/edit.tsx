import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  ActivityIndicator,
} from "react-native";
import { useLocalSearchParams, useRouter, Stack } from "expo-router";
import {
  ChevronLeft,
  Scissors,
  Type,
  Music,
  Gauge,
  Sparkles,
  Check,
  X,
} from "lucide-react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { tokens } from "@/constants/tokens";
import { ActionButton } from "@/components/ActionButton";
import { clipsApi, Clip } from "@/lib/api";

interface EditRecipe {
  trim?: { start_seconds: number; end_seconds: number };
  segments?: { start: number; end: number }[];
  caption?: string;
  caption_style?: { position?: string; color?: string; size?: number };
  audio?: string;
  speed?: number;
  filters?: string[];
  text_overlays?: { text: string; x?: number; y?: number; start?: number; end?: number; color?: string; size?: number }[];
  transitions?: string[];
  stickers?: { url: string; x?: number; y?: number; scale?: number; start?: number; end?: number }[];
}

export default function ClipEditScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ id: string }>();
  const [clip, setClip] = useState<Clip | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  
  // Edit state
  const [caption, setCaption] = useState<string>("");
  const [startTime, setStartTime] = useState<string>("0");
  const [endTime, setEndTime] = useState<string>("30");
  const [speed, setSpeed] = useState<string>("1.0");
  const [audioMode, setAudioMode] = useState<"keep" | "mute">("keep");
  const [selectedFilters, setSelectedFilters] = useState<string[]>([]);
  const [textOverlays, setTextOverlays] = useState<{ text: string; start: string; end: string }[]>([]);
  const [newOverlayText, setNewOverlayText] = useState<string>("");
  const [newOverlayStart, setNewOverlayStart] = useState<string>("0");
  const [newOverlayEnd, setNewOverlayEnd] = useState<string>("5");

  useEffect(() => {
    if (!params.id) return;
    let cancelled = false;
    setLoading(true);
    clipsApi.getById(params.id)
      .then((res) => {
        if (!cancelled) {
          setClip(res.data);
          setCaption(res.data.caption || "");
        }
      })
      .catch((err) => {
        console.warn("[edit] fetch failed:", err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [params.id]);

  const buildRecipe = useCallback((): EditRecipe => {
    const recipe: EditRecipe = {};
    
    // Trim
    const start = parseFloat(startTime) || 0;
    const end = parseFloat(endTime) || 30;
    if (start > 0 || end < 60) {
      recipe.trim = { start_seconds: start, end_seconds: end };
    }
    
    // Caption
    if (caption && caption !== clip?.caption) {
      recipe.caption = caption;
      recipe.caption_style = { position: "bottom", color: "white", size: 24 };
    }
    
    // Speed
    const speedValue = parseFloat(speed) || 1.0;
    if (speedValue !== 1.0) {
      recipe.speed = speedValue;
    }
    
    // Audio
    if (audioMode === "mute") {
      recipe.audio = "mute";
    }
    
    // Filters
    if (selectedFilters.length > 0) {
      recipe.filters = selectedFilters;
    }
    
    // Text overlays
    const overlays = textOverlays
      .filter(o => o.text.trim())
      .map(o => ({
        text: o.text,
        start: parseFloat(o.start) || 0,
        end: parseFloat(o.end) || 5,
        x: 100,
        y: 100,
        color: "white",
        size: 36
      }));
    if (overlays.length > 0) {
      recipe.text_overlays = overlays;
    }
    
    return recipe;
  }, [startTime, endTime, caption, clip, speed, audioMode, selectedFilters, textOverlays]);

  const onSave = useCallback(async () => {
    if (!params.id || saving) return;
    
    const recipe = buildRecipe();
    if (Object.keys(recipe).length === 0) {
      Alert.alert("No changes", "Make some edits before saving.");
      return;
    }
    
    setSaving(true);
    try {
      const result = await clipsApi.edit(params.id, recipe);
      if (result.data.success) {
        Alert.alert(
          "Edit Queued",
          "Your clip is being processed. Check back in a few moments.",
          [{ text: "OK", onPress: () => router.back() }]
        );
      } else {
        Alert.alert("Edit Failed", result.data.message || "Unknown error");
      }
    } catch (err: any) {
      console.warn("[edit] save failed:", err.message);
      Alert.alert("Edit Failed", err.message || "Unknown error");
    } finally {
      setSaving(false);
    }
  }, [params.id, saving, buildRecipe, router]);

  const toggleFilter = useCallback((filter: string) => {
    setSelectedFilters(prev => 
      prev.includes(filter) 
        ? prev.filter(f => f !== filter)
        : [...prev, filter]
    );
  }, []);

  const addTextOverlay = useCallback(() => {
    if (!newOverlayText.trim()) return;
    setTextOverlays(prev => [...prev, {
      text: newOverlayText,
      start: newOverlayStart,
      end: newOverlayEnd
    }]);
    setNewOverlayText("");
    setNewOverlayStart("0");
    setNewOverlayEnd("5");
  }, [newOverlayText, newOverlayStart, newOverlayEnd]);

  const removeOverlay = useCallback((index: number) => {
    setTextOverlays(prev => prev.filter((_, i) => i !== index));
  }, []);

  if (loading) {
    return (
      <View style={styles.root}>
        <ActivityIndicator size="large" color={tokens.color.brand.indigo[500]} />
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <Stack.Screen options={{ headerShown: false }} />
      
      <SafeAreaView edges={["top"]} style={styles.header}>
        <Pressable onPress={() => router.back()} style={styles.backBtn}>
          <ChevronLeft size={tokens.icon.size.lg} color={tokens.color.text.primary} />
        </Pressable>
        <Text style={styles.title}>Edit Clip</Text>
        <View style={styles.headerRight}>
          {saving ? (
            <ActivityIndicator size="small" color={tokens.color.brand.indigo[500]} />
          ) : (
            <Pressable onPress={onSave} style={styles.saveBtn}>
              <Check size={tokens.icon.size.md} color={tokens.color.brand.indigo[500]} />
            </Pressable>
          )}
        </View>
      </SafeAreaView>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {/* Trim Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Scissors size={tokens.icon.size.sm} color={tokens.color.brand.indigo[500]} />
            <Text style={styles.sectionTitle}>Trim</Text>
          </View>
          <View style={styles.row}>
            <View style={styles.inputGroup}>
              <Text style={styles.label}>Start (s)</Text>
              <TextInput
                style={styles.input}
                value={startTime}
                onChangeText={setStartTime}
                keyboardType="numeric"
                placeholder="0"
              />
            </View>
            <View style={styles.inputGroup}>
              <Text style={styles.label}>End (s)</Text>
              <TextInput
                style={styles.input}
                value={endTime}
                onChangeText={setEndTime}
                keyboardType="numeric"
                placeholder="30"
              />
            </View>
          </View>
        </View>

        {/* Caption Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Type size={tokens.icon.size.sm} color={tokens.color.brand.indigo[500]} />
            <Text style={styles.sectionTitle}>Caption</Text>
          </View>
          <TextInput
            style={styles.textArea}
            value={caption}
            onChangeText={setCaption}
            multiline
            numberOfLines={3}
            placeholder="Enter caption..."
            placeholderTextColor={tokens.color.text.tertiary}
          />
        </View>

        {/* Speed Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Gauge size={tokens.icon.size.sm} color={tokens.color.brand.indigo[500]} />
            <Text style={styles.sectionTitle}>Speed</Text>
          </View>
          <View style={styles.speedRow}>
            {["0.5", "0.75", "1.0", "1.5", "2.0"].map((s) => (
              <Pressable
                key={s}
                style={[styles.speedBtn, speed === s && styles.speedBtnActive]}
                onPress={() => setSpeed(s)}
              >
                <Text style={[styles.speedText, speed === s && styles.speedTextActive]}>{s}x</Text>
              </Pressable>
            ))}
          </View>
        </View>

        {/* Audio Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Music size={tokens.icon.size.sm} color={tokens.color.brand.indigo[500]} />
            <Text style={styles.sectionTitle}>Audio</Text>
          </View>
          <View style={styles.audioRow}>
            <Pressable
              style={[styles.audioBtn, audioMode === "keep" && styles.audioBtnActive]}
              onPress={() => setAudioMode("keep")}
            >
              <Text style={[styles.audioText, audioMode === "keep" && styles.audioTextActive]}>Keep</Text>
            </Pressable>
            <Pressable
              style={[styles.audioBtn, audioMode === "mute" && styles.audioBtnActive]}
              onPress={() => setAudioMode("mute")}
            >
              <Text style={[styles.audioText, audioMode === "mute" && styles.audioTextActive]}>Mute</Text>
            </Pressable>
          </View>
        </View>

        {/* Filters Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Sparkles size={tokens.icon.size.sm} color={tokens.color.brand.indigo[500]} />
            <Text style={styles.sectionTitle}>Filters</Text>
          </View>
          <View style={styles.filterRow}>
            {["grayscale", "sepia", "vintage", "blur", "sharpen"].map((filter) => (
              <Pressable
                key={filter}
                style={[styles.filterBtn, selectedFilters.includes(filter) && styles.filterBtnActive]}
                onPress={() => toggleFilter(filter)}
              >
                <Text style={[styles.filterText, selectedFilters.includes(filter) && styles.filterTextActive]}>
                  {filter.charAt(0).toUpperCase() + filter.slice(1)}
                </Text>
              </Pressable>
            ))}
          </View>
        </View>

        {/* Text Overlays Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Type size={tokens.icon.size.sm} color={tokens.color.brand.indigo[500]} />
            <Text style={styles.sectionTitle}>Text Overlays</Text>
          </View>
          
          {textOverlays.map((overlay, index) => (
            <View key={index} style={styles.overlayRow}>
              <Text style={styles.overlayText}>{overlay.text}</Text>
              <Text style={styles.overlayTime}>{overlay.start}s - {overlay.end}s</Text>
              <Pressable onPress={() => removeOverlay(index)} style={styles.removeBtn}>
                <X size={16} color={tokens.color.text.tertiary} />
              </Pressable>
            </View>
          ))}
          
          <View style={styles.addOverlayRow}>
            <TextInput
              style={styles.overlayInput}
              value={newOverlayText}
              onChangeText={setNewOverlayText}
              placeholder="Overlay text..."
              placeholderTextColor={tokens.color.text.tertiary}
            />
            <TextInput
              style={styles.timeInput}
              value={newOverlayStart}
              onChangeText={setNewOverlayStart}
              keyboardType="numeric"
              placeholder="0"
            />
            <Text style={styles.timeSep}>to</Text>
            <TextInput
              style={styles.timeInput}
              value={newOverlayEnd}
              onChangeText={setNewOverlayEnd}
              keyboardType="numeric"
              placeholder="5"
            />
            <Pressable onPress={addTextOverlay} style={styles.addBtn}>
              <Check size={20} color={tokens.color.brand.indigo[500]} />
            </Pressable>
          </View>
        </View>
      </ScrollView>

      <SafeAreaView edges={["bottom"]} style={styles.footer}>
        <ActionButton
          label={saving ? "Processing..." : "Save Edit"}
          variant="primary"
          size="md"
          fullWidth
          onPress={onSave}
          disabled={saving}
        />
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: tokens.color.bg.base,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: tokens.color.border.subtle,
  },
  backBtn: {
    padding: tokens.spacing.xs,
  },
  title: {
    flex: 1,
    fontFamily: tokens.type.scale.h3.family,
    fontSize: tokens.type.scale.h3.size,
    fontWeight: "600",
    color: tokens.color.text.primary,
    textAlign: "center",
  },
  headerRight: {
    width: 40,
    alignItems: "flex-end",
  },
  saveBtn: {
    padding: tokens.spacing.xs,
  },
  scroll: {
    padding: tokens.spacing.md,
    paddingBottom: tokens.spacing.xxl,
    gap: tokens.spacing.lg,
  },
  section: {
    gap: tokens.spacing.sm,
  },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.sm,
  },
  sectionTitle: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    fontWeight: "600",
    color: tokens.color.text.primary,
  },
  row: {
    flexDirection: "row",
    gap: tokens.spacing.md,
  },
  inputGroup: {
    flex: 1,
    gap: tokens.spacing.xs,
  },
  label: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.secondary,
  },
  input: {
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    borderRadius: tokens.radius.md,
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: tokens.spacing.sm,
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.primary,
    backgroundColor: tokens.color.bg.surface,
  },
  textArea: {
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    borderRadius: tokens.radius.md,
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: tokens.spacing.sm,
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.primary,
    backgroundColor: tokens.color.bg.surface,
    minHeight: 80,
    textAlignVertical: "top",
  },
  speedRow: {
    flexDirection: "row",
    gap: tokens.spacing.sm,
  },
  speedBtn: {
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    backgroundColor: tokens.color.bg.surface,
  },
  speedBtnActive: {
    borderColor: tokens.color.brand.indigo[500],
    backgroundColor: tokens.color.brand.indigo[900],
  },
  speedText: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.secondary,
  },
  speedTextActive: {
    color: tokens.color.brand.indigo[300],
    fontWeight: "600",
  },
  audioRow: {
    flexDirection: "row",
    gap: tokens.spacing.sm,
  },
  audioBtn: {
    flex: 1,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    backgroundColor: tokens.color.bg.surface,
    alignItems: "center",
  },
  audioBtnActive: {
    borderColor: tokens.color.brand.indigo[500],
    backgroundColor: tokens.color.brand.indigo[900],
  },
  audioText: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.secondary,
  },
  audioTextActive: {
    color: tokens.color.brand.indigo[300],
    fontWeight: "600",
  },
  filterRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: tokens.spacing.sm,
  },
  filterBtn: {
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    backgroundColor: tokens.color.bg.surface,
  },
  filterBtnActive: {
    borderColor: tokens.color.brand.indigo[500],
    backgroundColor: tokens.color.brand.indigo[900],
  },
  filterText: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.secondary,
  },
  filterTextActive: {
    color: tokens.color.brand.indigo[300],
    fontWeight: "600",
  },
  overlayRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.sm,
    paddingVertical: tokens.spacing.xs,
  },
  overlayText: {
    flex: 1,
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.primary,
  },
  overlayTime: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.secondary,
  },
  removeBtn: {
    padding: tokens.spacing.xs,
  },
  addOverlayRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.sm,
    marginTop: tokens.spacing.sm,
  },
  overlayInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    borderRadius: tokens.radius.md,
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: tokens.spacing.xs,
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.primary,
    backgroundColor: tokens.color.bg.surface,
  },
  timeInput: {
    width: 50,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    borderRadius: tokens.radius.md,
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: tokens.spacing.xs,
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.primary,
    backgroundColor: tokens.color.bg.surface,
    textAlign: "center",
  },
  timeSep: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.secondary,
  },
  addBtn: {
    padding: tokens.spacing.xs,
  },
  footer: {
    padding: tokens.spacing.md,
    borderTopWidth: 1,
    borderTopColor: tokens.color.border.subtle,
    backgroundColor: tokens.color.bg.base,
  },
});
