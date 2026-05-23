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
  Modal,
  FlatList,
  Image,
  Dimensions,
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
  Sticker,
  Wand2,
  Clapperboard,
  Volume2,
  VolumeX,
  Image as ImageIcon,
  Bot,
} from "lucide-react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { tokens } from "@/constants/tokens";
import { ActionButton } from "@/components/ActionButton";
import TimelineScrubber, { Thumbnail } from "@/components/TimelineScrubber";
import { clipsApi, Clip } from "@/lib/api";
import { useToast } from "@/components/ToastProvider";

/* ── Types ────────────────────────────────────────────── */

interface EditRecipe {
  trim?: { start_seconds: number; end_seconds: number };
  segments?: { start: number; end: number }[];
  caption?: string;
  caption_style?: { position?: string; color?: string; size?: number };
  audio?: string;
  speed?: number;
  filters?: string[];
  text_overlays?: { text: string; x?: number; y?: number; start?: number; end?: number; color?: string; size?: number }[];
  transitions?: { type: string; duration: number; between_segments?: number[] }[];
  stickers?: { url: string; x?: number; y?: number; scale?: number; start?: number; end?: number }[];
  music_track?: { url: string; volume: number; fade_in: number; fade_out: number };
  color_grade?: string;
}

interface StickerItem {
  id: string;
  url: string;
  category: "reactions" | "badges" | "cta";
  label: string;
}

interface MusicTrack {
  id: string;
  url: string;
  mood: string;
  label: string;
  duration: number;
}

interface TransitionType {
  id: string;
  label: string;
  duration: number;
}

type AgentId = "sticker" | "transition" | "music" | "color" | "caption" | "pacing" | "thumbnail";

interface AgentConfig {
  id: AgentId;
  label: string;
  icon: React.ReactNode;
  description: string;
  cost: string;
}

/* ── Asset Libraries ──────────────────────────────────── */

const STICKER_LIBRARY: StickerItem[] = [
  { id: "fire", url: "https://cdn.blissclip.io/stickers/fire.png", category: "reactions", label: "🔥" },
  { id: "heart", url: "https://cdn.blissclip.io/stickers/heart.png", category: "reactions", label: "❤️" },
  { id: "star", url: "https://cdn.blissclip.io/stickers/star.png", category: "reactions", label: "⭐" },
  { id: "laugh", url: "https://cdn.blissclip.io/stickers/laugh.png", category: "reactions", label: "😂" },
  { id: "shock", url: "https://cdn.blissclip.io/stickers/shock.png", category: "reactions", label: "😱" },
  { id: "badge-new", url: "https://cdn.blissclip.io/stickers/badge-new.png", category: "badges", label: "NEW" },
  { id: "badge-trending", url: "https://cdn.blissclip.io/stickers/badge-trending.png", category: "badges", label: "TRENDING" },
  { id: "badge-viral", url: "https://cdn.blissclip.io/stickers/badge-viral.png", category: "badges", label: "VIRAL" },
  { id: "cta-subscribe", url: "https://cdn.blissclip.io/stickers/cta-subscribe.png", category: "cta", label: "Subscribe" },
  { id: "cta-follow", url: "https://cdn.blissclip.io/stickers/cta-follow.png", category: "cta", label: "Follow" },
  { id: "cta-link", url: "https://cdn.blissclip.io/stickers/cta-link.png", category: "cta", label: "Link in Bio" },
];

const MUSIC_LIBRARY: MusicTrack[] = [
  { id: "upbeat-1", url: "https://cdn.blissclip.io/music/upbeat-pop-1.mp3", mood: "upbeat", label: "Pop Energy", duration: 120 },
  { id: "upbeat-2", url: "https://cdn.blissclip.io/music/upbeat-pop-2.mp3", mood: "upbeat", label: "Bright Vibes", duration: 90 },
  { id: "chill-1", url: "https://cdn.blissclip.io/music/chill-lofi-1.mp3", mood: "chill", label: "LoFi Chill", duration: 180 },
  { id: "chill-2", url: "https://cdn.blissclip.io/music/chill-ambient.mp3", mood: "chill", label: "Ambient", duration: 240 },
  { id: "dramatic-1", url: "https://cdn.blissclip.io/music/dramatic-cinematic.mp3", mood: "dramatic", label: "Cinematic", duration: 150 },
  { id: "dramatic-2", url: "https://cdn.blissclip.io/music/dramatic-epic.mp3", mood: "dramatic", label: "Epic", duration: 120 },
  { id: "trending-1", url: "https://cdn.blissclip.io/music/trending-viral-1.mp3", mood: "trending", label: "Viral Hit 1", duration: 60 },
  { id: "trending-2", url: "https://cdn.blissclip.io/music/trending-viral-2.mp3", mood: "trending", label: "Viral Hit 2", duration: 60 },
];

const TRANSITION_TYPES: TransitionType[] = [
  { id: "fade", label: "Fade", duration: 0.5 },
  { id: "dissolve", label: "Dissolve", duration: 0.6 },
  { id: "wipe_left", label: "Wipe Left", duration: 0.4 },
  { id: "wipe_right", label: "Wipe Right", duration: 0.4 },
  { id: "slide_up", label: "Slide Up", duration: 0.5 },
  { id: "slide_down", label: "Slide Down", duration: 0.5 },
  { id: "zoom_in", label: "Zoom In", duration: 0.6 },
  { id: "zoom_out", label: "Zoom Out", duration: 0.6 },
  { id: "spin", label: "Spin", duration: 0.7 },
];

const COLOR_PRESETS = [
  { id: "none", label: "None", filters: [] },
  { id: "tiktok", label: "TikTok Vibrant", filters: ["vibrant"], lut: "tiktok" },
  { id: "instagram", label: "Instagram", filters: ["warm"], lut: "instagram" },
  { id: "youtube", label: "YouTube Cinematic", filters: ["cinematic"], lut: "youtube" },
  { id: "grayscale", label: "B&W", filters: ["grayscale"] },
  { id: "sepia", label: "Sepia", filters: ["sepia"] },
  { id: "vintage", label: "Vintage", filters: ["vintage"] },
];

const AGENTS: AgentConfig[] = [
  { id: "sticker", label: "Sticker Agent", icon: <Sticker size={16} color={tokens.color.brand.indigo[500]} />, description: "Adds trending stickers & CTA overlays", cost: "$0.01" },
  { id: "transition", label: "Transition Agent", icon: <Clapperboard size={16} color={tokens.color.brand.indigo[500]} />, description: "Smooth cuts between segments", cost: "$0.02" },
  { id: "music", label: "Music Agent", icon: <Music size={16} color={tokens.color.brand.indigo[500]} />, description: "Background music & beat sync", cost: "$0.03" },
  { id: "color", label: "Color Agent", icon: <Sparkles size={16} color={tokens.color.brand.indigo[500]} />, description: "Platform-optimized color grading", cost: "$0.015" },
  { id: "caption", label: "Caption Agent", icon: <Type size={16} color={tokens.color.brand.indigo[500]} />, description: "Styled captions & text overlays", cost: "$0.02" },
  { id: "pacing", label: "Pacing Agent", icon: <Gauge size={16} color={tokens.color.brand.indigo[500]} />, description: "Speed ramps & jump cuts", cost: "$0.025" },
  { id: "thumbnail", label: "Thumbnail Agent", icon: <ImageIcon size={16} color={tokens.color.brand.indigo[500]} />, description: "Platform-optimized thumbnails", cost: "$0.01" },
];

/* ── Main Screen ───────────────────────────────────────── */

export default function ClipEditScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ id: string }>();
  const toast = useToast();
  
  const [clip, setClip] = useState<Clip | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  
  const [thumbnails, setThumbnails] = useState<Thumbnail[]>([]);
  const [clipDuration, setClipDuration] = useState<number>(30);
  const [startTime, setStartTime] = useState<number>(0);
  const [endTime, setEndTime] = useState<number>(30);
  
  const [caption, setCaption] = useState<string>("");
  const [speed, setSpeed] = useState<string>("1.0");
  const [audioMode, setAudioMode] = useState<"keep" | "mute" | "music">("keep");
  const [selectedFilters, setSelectedFilters] = useState<string[]>([]);
  const [colorPreset, setColorPreset] = useState<string>("none");
  const [textOverlays, setTextOverlays] = useState<{ text: string; start: string; end: string }[]>([]);
  const [newOverlayText, setNewOverlayText] = useState<string>("");
  const [newOverlayStart, setNewOverlayStart] = useState<string>("0");
  const [newOverlayEnd, setNewOverlayEnd] = useState<string>("5");
  
  const [selectedStickers, setSelectedStickers] = useState<{ item: StickerItem; start: number; end: number; scale: number; position: string }[]>([]);
  const [stickerModalVisible, setStickerModalVisible] = useState(false);
  const [activeStickerCategory, setActiveStickerCategory] = useState<"all" | "reactions" | "badges" | "cta">("all");
  
  const [selectedTransitions, setSelectedTransitions] = useState<{ type: string; duration: number }[]>([]);
  const [transitionModalVisible, setTransitionModalVisible] = useState(false);
  
  const [selectedTrack, setSelectedTrack] = useState<MusicTrack | null>(null);
  const [musicVolume, setMusicVolume] = useState<number>(0.25);
  const [musicModalVisible, setMusicModalVisible] = useState(false);
  const [activeMusicMood, setActiveMusicMood] = useState<"all" | "upbeat" | "chill" | "dramatic" | "trending">("all");
  
  const [agentModalVisible, setAgentModalVisible] = useState(false);
  const [selectedAgents, setSelectedAgents] = useState<AgentId[]>([]);
  const [agentProcessing, setAgentProcessing] = useState(false);

  useEffect(() => {
    if (!params.id) return;
    let cancelled = false;
    setLoading(true);
    
    Promise.all([
      clipsApi.getById(params.id),
      clipsApi.thumbnails(params.id)
    ])
      .then(([clipRes, thumbRes]) => {
        if (cancelled) return;
        const clipData = clipRes.data;
        setClip(clipData);
        setCaption(clipData.caption || "");
        
        const duration = clipData.duration || 30;
        setClipDuration(duration);
        setEndTime(duration);
        
        if (thumbRes.thumbnails) {
          setThumbnails(thumbRes.thumbnails.map((url: string, i: number) => ({
            time: (i / thumbRes.thumbnails.length) * duration,
            url,
          })));
        }
        
        // Handle return from Music Library
        const musicTrackId = (params as any).musicTrackId as string | undefined;
        if (musicTrackId) {
          const track = MUSIC_LIBRARY.find(m => m.id === musicTrackId);
          if (track) {
            setSelectedTrack(track);
            setAudioMode("music");
            const duck = parseFloat((params as any).musicDuckFactor as string) || 0.25;
            setMusicVolume(Math.min(duck * 2, 0.5)); // Convert duck factor to volume
          }
        }
      })
      .catch((err) => {
        console.warn("[edit] fetch failed:", err.message);
        toast.show({ type: "success", message: "Failed to load clip data", title: "error" });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true };
  }, [params.id]);

  const buildRecipe = useCallback((): EditRecipe => {
    const recipe: EditRecipe = {};
    
    if (startTime > 0 || endTime < clipDuration) {
      recipe.trim = { start_seconds: startTime, end_seconds: endTime };
    }
    
    if (caption && caption !== clip?.caption) {
      recipe.caption = caption;
      recipe.caption_style = { position: "bottom", color: "white", size: 24 };
    }
    
    const speedValue = parseFloat(speed) || 1.0;
    if (speedValue !== 1.0) {
      recipe.speed = speedValue;
    }
    
    if (audioMode === "mute") {
      recipe.audio = "mute";
    } else if (audioMode === "music" && selectedTrack) {
      recipe.music_track = {
        url: selectedTrack.url,
        volume: musicVolume,
        fade_in: 1.0,
        fade_out: 2.0,
      };
      recipe.audio = `replace:${selectedTrack.url}`;
    }
    
    const allFilters = [...selectedFilters];
    const preset = COLOR_PRESETS.find(p => p.id === colorPreset);
    if (preset && preset.filters.length > 0) {
      allFilters.push(...preset.filters);
    }
    if (allFilters.length > 0) {
      recipe.filters = allFilters;
    }
    if (preset?.lut) {
      recipe.color_grade = preset.lut;
    }
    
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
    
    if (selectedStickers.length > 0) {
      recipe.stickers = selectedStickers.map(s => ({
        url: s.item.url,
        x: s.position === "top_left" || s.position === "bottom_left" ? 20 : -20,
        y: s.position === "top_left" || s.position === "top_right" ? 20 : -20,
        scale: s.scale,
        start: s.start,
        end: s.end,
      }));
    }
    
    if (selectedTransitions.length > 0) {
      recipe.transitions = selectedTransitions;
    }
    
    return recipe;
  }, [startTime, endTime, clipDuration, caption, clip, speed, audioMode, selectedTrack, musicVolume, selectedFilters, colorPreset, textOverlays, selectedStickers, selectedTransitions]);

  const onSave = useCallback(async () => {
    if (!params.id || saving) return;
    
    const recipe = buildRecipe();
    if (Object.keys(recipe).length === 0) {
      toast.show({ type: "success", message: "Make some edits before saving", title: "warning" });
      return;
    }
    
    setSaving(true);
    try {
      const result = await clipsApi.edit(params.id, recipe);
      if (result.success) {
        toast.show({ type: "success", message: "Edit queued — processing in background", title: "success" });
        router.back();
      } else {
        toast.show({ type: "success", message: result.message || "Edit failed", title: "error" });
      }
    } catch (err: any) {
      console.warn("[edit] save failed:", err.message);
      toast.show({ type: "success", message: err.message || "Edit failed", title: "error" });
    } finally {
      setSaving(false);
    }
  }, [params.id, saving, buildRecipe, router, toast]);

  const onRunAgents = useCallback(async () => {
    if (!params.id || selectedAgents.length === 0) {
      toast.show({ type: "success", message: "Select at least one agent", title: "warning" });
      return;
    }
    
    setAgentProcessing(true);
    try {
      const result = await clipsApi.runEditAgents(params.id, {
        agents: selectedAgents,
        clip_data: {
          id: params.id,
          caption: caption,
          duration: clipDuration,
          platform: clip?.platform || "tiktok",
        }
      });
      
      if (result.recipe) {
        const recipe = result.recipe;
        if (recipe.caption) setCaption(recipe.caption);
        if (recipe.speed) setSpeed(recipe.speed.toString());
        if (recipe.filters) setSelectedFilters(recipe.filters);
        if (recipe.stickers) {
          const mapped = recipe.stickers.map((s: any) => ({
            item: STICKER_LIBRARY.find(st => st.url === s.url) || STICKER_LIBRARY[0],
            start: s.start || 0,
            end: s.end || clipDuration,
            scale: s.scale || 0.5,
            position: s.x < 100 ? "top_left" : "top_right",
          }));
          setSelectedStickers(mapped);
        }
        if (recipe.transitions) {
          setSelectedTransitions(recipe.transitions);
        }
        if (recipe.music_track) {
          const track = MUSIC_LIBRARY.find(m => m.url === recipe.music_track.url);
          if (track) {
            setSelectedTrack(track);
            setMusicVolume(recipe.music_track.volume);
            setAudioMode("music");
          }
        }
        
        toast.show({ type: "success", message: `${selectedAgents.length} agents applied edits — review and save`, title: "success" });
      } else {
        toast.show({ type: "success", message: "Agents analyzed but no edits suggested", title: "info" });
      }
    } catch (err: any) {
      console.warn("[edit] agents failed:", err.message);
      toast.show({ type: "success", message: "Agent swarm failed: " + err.message, title: "error" });
    } finally {
      setAgentProcessing(false);
      setAgentModalVisible(false);
    }
  }, [params.id, selectedAgents, caption, clipDuration, clip, toast]);

  const addSticker = useCallback((item: StickerItem) => {
    setSelectedStickers(prev => [...prev, {
      item,
      start: 0,
      end: clipDuration,
      scale: 0.5,
      position: "top_right"
    }]);
    setStickerModalVisible(false);
    toast.show({ type: "success", message: `Added ${item.label} sticker`, title: "success" });
  }, [clipDuration, toast]);

  const removeSticker = useCallback((index: number) => {
    setSelectedStickers(prev => prev.filter((_, i) => i !== index));
  }, []);

  const addTransition = useCallback((type: TransitionType) => {
    setSelectedTransitions(prev => [...prev, { type: type.id, duration: type.duration }]);
    setTransitionModalVisible(false);
    toast.show({ type: "success", message: `Added ${type.label} transition`, title: "success" });
  }, [toast]);

  const removeTransition = useCallback((index: number) => {
    setSelectedTransitions(prev => prev.filter((_, i) => i !== index));
  }, []);

  const selectTrack = useCallback((track: MusicTrack) => {
    setSelectedTrack(track);
    setAudioMode("music");
    setMusicModalVisible(false);
    toast.show({ type: "success", message: `Selected: ${track.label}`, title: "success" });
  }, [toast]);

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

  const toggleAgent = useCallback((agentId: AgentId) => {
    setSelectedAgents(prev =>
      prev.includes(agentId)
        ? prev.filter(a => a !== agentId)
        : [...prev, agentId]
    );
  }, []);

  const filteredStickers = useMemo(() => {
    if (activeStickerCategory === "all") return STICKER_LIBRARY;
    return STICKER_LIBRARY.filter(s => s.category === activeStickerCategory);
  }, [activeStickerCategory]);

  const filteredMusic = useMemo(() => {
    if (activeMusicMood === "all") return MUSIC_LIBRARY;
    return MUSIC_LIBRARY.filter(m => m.mood === activeMusicMood);
  }, [activeMusicMood]);

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
      
      {/* Header */}
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
        
        {/* ── AI Edit Swarm Banner ───────────────────────── */}
        <Pressable style={styles.swarmBanner} onPress={() => setAgentModalVisible(true)}>
          <Bot size={20} color={tokens.color.brand.indigo[300]} />
          <View style={styles.swarmText}>
            <Text style={styles.swarmTitle}>AI Edit Swarm</Text>
            <Text style={styles.swarmSubtitle}>
              {selectedAgents.length > 0 
                ? `${selectedAgents.length} agents selected — tap to run`
                : "Select AI agents to auto-enhance this clip"
              }
            </Text>
          </View>
          <Wand2 size={18} color={tokens.color.brand.indigo[400]} />
        </Pressable>

        {/* ── Trim Section ──────────────────────────────── */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Scissors size={tokens.icon.size.sm} color={tokens.color.brand.indigo[500]} />
            <Text style={styles.sectionTitle}>Trim</Text>
          </View>
          
          {thumbnails.length > 0 ? (
            <TimelineScrubber
              thumbnails={thumbnails}
              duration={clipDuration}
              startTime={startTime}
              endTime={endTime}
              onStartTimeChange={setStartTime}
              onEndTimeChange={setEndTime}
            />
          ) : (
            <View style={styles.thumbsLoading}>
              <ActivityIndicator size="small" color={tokens.color.brand.indigo[500]} />
              <Text style={styles.thumbsLoadingText}>Generating preview...</Text>
            </View>
          )}
          
          <View style={styles.row}>
            <View style={styles.inputGroup}>
              <Text style={styles.label}>Start (s)</Text>
              <TextInput
                style={styles.input}
                value={startTime.toFixed(1)}
                onChangeText={(v) => setStartTime(parseFloat(v) || 0)}
                keyboardType="numeric"
                placeholder="0"
              />
            </View>
            <View style={styles.inputGroup}>
              <Text style={styles.label}>End (s)</Text>
              <TextInput
                style={styles.input}
                value={endTime.toFixed(1)}
                onChangeText={(v) => setEndTime(parseFloat(v) || clipDuration)}
                keyboardType="numeric"
                placeholder={clipDuration.toString()}
              />
            </View>
          </View>
        </View>

        {/* ── Caption Section ──────────────────────────── */}
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

        {/* ── Speed Section ──────────────────────────────── */}
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

        {/* ── Color Grade Section ────────────────────────── */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Sparkles size={tokens.icon.size.sm} color={tokens.color.brand.indigo[500]} />
            <Text style={styles.sectionTitle}>Color Grade</Text>
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.colorScroll}>
            <View style={styles.colorRow}>
              {COLOR_PRESETS.map((preset) => (
                <Pressable
                  key={preset.id}
                  style={[styles.colorBtn, colorPreset === preset.id && styles.colorBtnActive]}
                  onPress={() => setColorPreset(preset.id)}
                >
                  <View style={[styles.colorPreview, { backgroundColor: getColorPreview(preset.id) }]} />
                  <Text style={[styles.colorText, colorPreset === preset.id && styles.colorTextActive]}>
                    {preset.label}
                  </Text>
                </Pressable>
              ))}
            </View>
          </ScrollView>
        </View>

        {/* ── Audio Section ──────────────────────────────── */}
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
              <Volume2 size={16} color={audioMode === "keep" ? tokens.color.brand.indigo[300] : tokens.color.text.secondary} />
              <Text style={[styles.audioText, audioMode === "keep" && styles.audioTextActive]}>Keep</Text>
            </Pressable>
            <Pressable
              style={[styles.audioBtn, audioMode === "mute" && styles.audioBtnActive]}
              onPress={() => { setAudioMode("mute"); setSelectedTrack(null); }}
            >
              <VolumeX size={16} color={audioMode === "mute" ? tokens.color.brand.indigo[300] : tokens.color.text.secondary} />
              <Text style={[styles.audioText, audioMode === "mute" && styles.audioTextActive]}>Mute</Text>
            </Pressable>
            <Pressable
              style={[styles.audioBtn, audioMode === "music" && styles.audioBtnActive]}
              onPress={() => setMusicModalVisible(true)}
            >
              <Music size={16} color={audioMode === "music" ? tokens.color.brand.indigo[300] : tokens.color.text.secondary} />
              <Text style={[styles.audioText, audioMode === "music" && styles.audioTextActive]}>
                {selectedTrack ? selectedTrack.label : "Music"}
              </Text>
            </Pressable>
          </View>
          
          {/* Navigate to full Music Library */}
          <Pressable
            style={styles.libraryBtn}
            onPress={() => router.push({ pathname: "/(app)/music-library", params: { clipId: params.id } })}
          >
            <Sparkles size={16} color={tokens.color.brand.indigo[400]} />
            <Text style={styles.libraryBtnText}>Browse Music Library — Mix, Preview & Apply</Text>
            <ChevronLeft size={16} color={tokens.color.text.tertiary} style={{ transform: [{ rotate: "180deg" }] }} />
          </Pressable>
          
          {selectedTrack && (
            <View style={styles.volumeControl}>
              <Text style={styles.label}>Music Volume: {Math.round(musicVolume * 100)}%</Text>
              <View style={styles.volumeBar}>
                {[0.1, 0.2, 0.3, 0.4, 0.5].map((v) => (
                  <Pressable
                    key={v}
                    style={[styles.volumeTick, musicVolume >= v && styles.volumeTickActive]}
                    onPress={() => setMusicVolume(v)}
                  />
                ))}
              </View>
            </View>
          )}
        </View>

        {/* ── Filters Section ──────────────────────────── */}
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

        {/* ── Stickers Section ─────────────────────────── */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Sticker size={tokens.icon.size.sm} color={tokens.color.brand.indigo[500]} />
            <Text style={styles.sectionTitle}>Stickers</Text>
            <Pressable style={styles.addBtn} onPress={() => setStickerModalVisible(true)}>
              <Text style={styles.addBtnText}>+ Add</Text>
            </Pressable>
          </View>
          
          {selectedStickers.length === 0 ? (
            <Text style={styles.emptyText}>No stickers added. Tap + to browse.</Text>
          ) : (
            <View style={styles.stickerList}>
              {selectedStickers.map((s, index) => (
                <View key={index} style={styles.stickerChip}>
                  <Image source={{ uri: s.item.url }} style={styles.stickerThumb} />
                  <Text style={styles.stickerChipText}>{s.item.label}</Text>
                  <Pressable onPress={() => removeSticker(index)} style={styles.stickerRemove}>
                    <X size={14} color={tokens.color.text.tertiary} />
                  </Pressable>
                </View>
              ))}
            </View>
          )}
        </View>

        {/* ── Transitions Section ────────────────────────── */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Clapperboard size={tokens.icon.size.sm} color={tokens.color.brand.indigo[500]} />
            <Text style={styles.sectionTitle}>Transitions</Text>
            <Pressable style={styles.addBtn} onPress={() => setTransitionModalVisible(true)}>
              <Text style={styles.addBtnText}>+ Add</Text>
            </Pressable>
          </View>
          
          {selectedTransitions.length === 0 ? (
            <Text style={styles.emptyText}>No transitions added. Tap + to browse.</Text>
          ) : (
            <View style={styles.transitionList}>
              {selectedTransitions.map((t, index) => {
                const typeInfo = TRANSITION_TYPES.find(tt => tt.id === t.type);
                return (
                  <View key={index} style={styles.transitionChip}>
                    <Text style={styles.transitionChipText}>{typeInfo?.label || t.type}</Text>
                    <Text style={styles.transitionChipMeta}>{t.duration}s</Text>
                    <Pressable onPress={() => removeTransition(index)} style={styles.stickerRemove}>
                      <X size={14} color={tokens.color.text.tertiary} />
                    </Pressable>
                  </View>
                );
              })}
            </View>
          )}
        </View>

        {/* ── Text Overlays Section ──────────────────────── */}
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
            <Pressable onPress={addTextOverlay} style={styles.addBtnSmall}>
              <Check size={20} color={tokens.color.brand.indigo[500]} />
            </Pressable>
          </View>
        </View>

        <View style={{ height: 40 }} />
      </ScrollView>

      {/* Footer */}
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

      {/* ── Sticker Modal ──────────────────────────────── */}
      <Modal visible={stickerModalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Add Sticker</Text>
              <Pressable onPress={() => setStickerModalVisible(false)}>
                <X size={24} color={tokens.color.text.primary} />
              </Pressable>
            </View>
            
            <View style={styles.categoryRow}>
              {(["all", "reactions", "badges", "cta"] as const).map((cat) => (
                <Pressable
                  key={cat}
                  style={[styles.categoryTab, activeStickerCategory === cat && styles.categoryTabActive]}
                  onPress={() => setActiveStickerCategory(cat)}
                >
                  <Text style={[styles.categoryText, activeStickerCategory === cat && styles.categoryTextActive]}>
                    {cat.charAt(0).toUpperCase() + cat.slice(1)}
                  </Text>
                </Pressable>
              ))}
            </View>
            
            <FlatList
              data={filteredStickers}
              numColumns={3}
              keyExtractor={(item) => item.id}
              renderItem={({ item }) => (
                <Pressable style={styles.stickerGridItem} onPress={() => addSticker(item)}>
                  <Image source={{ uri: item.url }} style={styles.stickerGridImage} />
                  <Text style={styles.stickerGridLabel}>{item.label}</Text>
                </Pressable>
              )}
              contentContainerStyle={styles.stickerGrid}
            />
          </View>
        </View>
      </Modal>

      {/* ── Transition Modal ───────────────────────────── */}
      <Modal visible={transitionModalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Add Transition</Text>
              <Pressable onPress={() => setTransitionModalVisible(false)}>
                <X size={24} color={tokens.color.text.primary} />
              </Pressable>
            </View>
            
            <FlatList
              data={TRANSITION_TYPES}
              keyExtractor={(item) => item.id}
              renderItem={({ item }) => (
                <Pressable style={styles.transitionGridItem} onPress={() => addTransition(item)}>
                  <View style={styles.transitionPreview}>
                    <Text style={styles.transitionPreviewText}>{item.label[0]}</Text>
                  </View>
                  <View style={styles.transitionInfo}>
                    <Text style={styles.transitionName}>{item.label}</Text>
                    <Text style={styles.transitionDuration}>{item.duration}s</Text>
                  </View>
                  <Check size={20} color={tokens.color.brand.indigo[500]} />
                </Pressable>
              )}
              contentContainerStyle={styles.transitionGrid}
            />
          </View>
        </View>
      </Modal>

      {/* ── Music Modal ────────────────────────────────── */}
      <Modal visible={musicModalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Music Library</Text>
              <Pressable onPress={() => setMusicModalVisible(false)}>
                <X size={24} color={tokens.color.text.primary} />
              </Pressable>
            </View>
            
            <View style={styles.categoryRow}>
              {(["all", "upbeat", "chill", "dramatic", "trending"] as const).map((mood) => (
                <Pressable
                  key={mood}
                  style={[styles.categoryTab, activeMusicMood === mood && styles.categoryTabActive]}
                  onPress={() => setActiveMusicMood(mood)}
                >
                  <Text style={[styles.categoryText, activeMusicMood === mood && styles.categoryTextActive]}>
                    {mood.charAt(0).toUpperCase() + mood.slice(1)}
                  </Text>
                </Pressable>
              ))}
            </View>
            
            <FlatList
              data={filteredMusic}
              keyExtractor={(item) => item.id}
              renderItem={({ item }) => (
                <Pressable 
                  style={[styles.musicItem, selectedTrack?.id === item.id && styles.musicItemActive]} 
                  onPress={() => selectTrack(item)}
                >
                  <View style={styles.musicIcon}>
                    <Music size={20} color={tokens.color.brand.indigo[500]} />
                  </View>
                  <View style={styles.musicInfo}>
                    <Text style={styles.musicName}>{item.label}</Text>
                    <Text style={styles.musicMeta}>{item.mood} · {item.duration}s</Text>
                  </View>
                  {selectedTrack?.id === item.id && (
                    <Check size={20} color={tokens.color.brand.indigo[500]} />
                  )}
                </Pressable>
              )}
              contentContainerStyle={styles.musicList}
            />
          </View>
        </View>
      </Modal>

      {/* ── Agent Swarm Modal ──────────────────────────── */}
      <Modal visible={agentModalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, styles.agentModalContent]}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>AI Edit Swarm</Text>
              <Pressable onPress={() => setAgentModalVisible(false)}>
                <X size={24} color={tokens.color.text.primary} />
              </Pressable>
            </View>
            
            <Text style={styles.agentDescription}>
              Select agents to autonomously enhance this clip. Each agent specializes in one editing dimension.
            </Text>
            
            <ScrollView style={styles.agentList} showsVerticalScrollIndicator={false}>
              {AGENTS.map((agent) => (
                <Pressable
                  key={agent.id}
                  style={[styles.agentItem, selectedAgents.includes(agent.id) && styles.agentItemActive]}
                  onPress={() => toggleAgent(agent.id)}
                >
                  <View style={styles.agentIcon}>{agent.icon}</View>
                  <View style={styles.agentInfo}>
                    <Text style={styles.agentName}>{agent.label}</Text>
                    <Text style={styles.agentDesc}>{agent.description}</Text>
                    <Text style={styles.agentCost}>~{agent.cost}/clip</Text>
                  </View>
                  <View style={[styles.agentCheck, selectedAgents.includes(agent.id) && styles.agentCheckActive]}>
                    {selectedAgents.includes(agent.id) && <Check size={14} color="#fff" />}
                  </View>
                </Pressable>
              ))}
            </ScrollView>
            
            <View style={styles.agentFooter}>
              <Text style={styles.agentTotal}>
                {selectedAgents.length} agents · ~${AGENTS.filter(a => selectedAgents.includes(a.id)).reduce((sum, a) => sum + parseFloat(a.cost.replace("$", "")), 0).toFixed(3)}/clip
              </Text>
              <ActionButton
                label={agentProcessing ? "Running..." : "Run Agents"}
                variant="primary"
                size="md"
                fullWidth
                onPress={onRunAgents}
                disabled={agentProcessing || selectedAgents.length === 0}
              />
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

/* ── Helpers ──────────────────────────────────────────── */

function getColorPreview(id: string): string {
  const map: Record<string, string> = {
    none: "#888",
    tiktok: "#ff0050",
    instagram: "#e1306c",
    youtube: "#ff0000",
    grayscale: "#666",
    sepia: "#704214",
    vintage: "#d4a373",
  };
  return map[id] || "#888";
}

/* ── Styles ───────────────────────────────────────────── */

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg.base },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: tokens.color.border.subtle,
  },
  backBtn: { padding: tokens.spacing.xs },
  title: {
    flex: 1,
    fontFamily: tokens.type.scale.h3.family,
    fontSize: tokens.type.scale.h3.size,
    fontWeight: "600",
    color: tokens.color.text.primary,
    textAlign: "center",
  },
  headerRight: { width: 40, alignItems: "flex-end" },
  saveBtn: { padding: tokens.spacing.xs },
  scroll: { padding: tokens.spacing.md, paddingBottom: tokens.spacing.xxl, gap: tokens.spacing.lg },
  section: { gap: tokens.spacing.sm },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.sm,
  },
  sectionTitle: {
    flex: 1,
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    fontWeight: "600",
    color: tokens.color.text.primary,
  },
  row: { flexDirection: "row", gap: tokens.spacing.md },
  inputGroup: { flex: 1, gap: tokens.spacing.xs },
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
  speedRow: { flexDirection: "row", gap: tokens.spacing.sm },
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
  colorScroll: { marginHorizontal: -tokens.spacing.md },
  colorRow: { flexDirection: "row", gap: tokens.spacing.sm, paddingHorizontal: tokens.spacing.md },
  colorBtn: {
    alignItems: "center",
    gap: tokens.spacing.xs,
    padding: tokens.spacing.sm,
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    backgroundColor: tokens.color.bg.surface,
    width: 72,
  },
  colorBtnActive: {
    borderColor: tokens.color.brand.indigo[500],
    backgroundColor: tokens.color.brand.indigo[900],
  },
  colorPreview: {
    width: 40,
    height: 40,
    borderRadius: tokens.radius.sm,
  },
  colorText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.secondary,
  },
  colorTextActive: {
    color: tokens.color.brand.indigo[300],
    fontWeight: "600",
  },
  audioRow: { flexDirection: "row", gap: tokens.spacing.sm },
  audioBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: tokens.spacing.xs,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    backgroundColor: tokens.color.bg.surface,
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
  volumeControl: { marginTop: tokens.spacing.sm, gap: tokens.spacing.xs },
  libraryBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.sm,
    paddingVertical: tokens.spacing.sm,
    paddingHorizontal: tokens.spacing.md,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.color.brand.indigo[700],
    backgroundColor: tokens.color.brand.indigo[900] + "20",
    marginTop: tokens.spacing.sm,
  },
  libraryBtnText: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    fontWeight: "500",
    color: tokens.color.brand.indigo[300],
    flex: 1,
  },
  volumeBar: { flexDirection: "row", gap: tokens.spacing.xs },
  volumeTick: {
    flex: 1,
    height: 8,
    borderRadius: tokens.radius.sm,
    backgroundColor: tokens.color.border.subtle,
  },
  volumeTickActive: {
    backgroundColor: tokens.color.brand.indigo[500],
  },
  filterRow: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
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
  addBtn: {
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: tokens.spacing.xs,
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.brand.indigo[900],
  },
  addBtnText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.brand.indigo[300],
    fontWeight: "600",
  },
  emptyText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.tertiary,
    fontStyle: "italic",
  },
  stickerList: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
  stickerChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.xs,
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: tokens.spacing.xs,
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.bg.surface,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
  },
  stickerThumb: { width: 24, height: 24, borderRadius: tokens.radius.sm },
  stickerChipText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.secondary,
  },
  stickerRemove: { padding: tokens.spacing.xs },
  transitionList: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
  transitionChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.xs,
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: tokens.spacing.xs,
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.bg.surface,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
  },
  transitionChipText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.secondary,
  },
  transitionChipMeta: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.tertiary,
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
  removeBtn: { padding: tokens.spacing.xs },
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
  addBtnSmall: { padding: tokens.spacing.xs },
  thumbsLoading: {
    height: 72,
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.bg.surface,
    alignItems: "center",
    justifyContent: "center",
    gap: tokens.spacing.xs,
  },
  thumbsLoadingText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.tertiary,
  },
  footer: {
    padding: tokens.spacing.md,
    borderTopWidth: 1,
    borderTopColor: tokens.color.border.subtle,
    backgroundColor: tokens.color.bg.base,
  },
  swarmBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
    padding: tokens.spacing.md,
    borderRadius: tokens.radius.lg,
    backgroundColor: tokens.color.brand.indigo[900],
    borderWidth: 1,
    borderColor: tokens.color.brand.indigo[700],
  },
  swarmText: { flex: 1 },
  swarmTitle: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    fontWeight: "600",
    color: tokens.color.brand.indigo[200],
  },
  swarmSubtitle: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.brand.indigo[400],
  },
  modalOverlay: {
    flex: 1,
    justifyContent: "flex-end",
    backgroundColor: "rgba(0,0,0,0.5)",
  },
  modalContent: {
    backgroundColor: tokens.color.bg.base,
    borderTopLeftRadius: tokens.radius.xl,
    borderTopRightRadius: tokens.radius.xl,
    padding: tokens.spacing.md,
    maxHeight: "80%",
    minHeight: "50%",
  },
  agentModalContent: {
    maxHeight: "85%",
  },
  modalHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: tokens.spacing.md,
  },
  modalTitle: {
    fontFamily: tokens.type.scale.h3.family,
    fontSize: tokens.type.scale.h3.size,
    fontWeight: "600",
    color: tokens.color.text.primary,
  },
  categoryRow: {
    flexDirection: "row",
    gap: tokens.spacing.sm,
    marginBottom: tokens.spacing.md,
  },
  categoryTab: {
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.xs,
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.bg.surface,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
  },
  categoryTabActive: {
    backgroundColor: tokens.color.brand.indigo[900],
    borderColor: tokens.color.brand.indigo[500],
  },
  categoryText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.secondary,
  },
  categoryTextActive: {
    color: tokens.color.brand.indigo[300],
    fontWeight: "600",
  },
  stickerGrid: { paddingBottom: tokens.spacing.xl },
  stickerGridItem: {
    flex: 1,
    alignItems: "center",
    padding: tokens.spacing.sm,
    margin: tokens.spacing.xs,
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.bg.surface,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
  },
  stickerGridImage: { width: 64, height: 64, borderRadius: tokens.radius.sm },
  stickerGridLabel: {
    marginTop: tokens.spacing.xs,
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.secondary,
  },
  transitionGrid: { paddingBottom: tokens.spacing.xl },
  transitionGridItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
    padding: tokens.spacing.md,
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.bg.surface,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    marginBottom: tokens.spacing.sm,
  },
  transitionPreview: {
    width: 40,
    height: 40,
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.brand.indigo[900],
    alignItems: "center",
    justifyContent: "center",
  },
  transitionPreviewText: {
    fontSize: 18,
    fontWeight: "700",
    color: tokens.color.brand.indigo[300],
  },
  transitionInfo: { flex: 1 },
  transitionName: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    fontWeight: "600",
    color: tokens.color.text.primary,
  },
  transitionDuration: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.secondary,
  },
  musicList: { paddingBottom: tokens.spacing.xl },
  musicItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
    padding: tokens.spacing.md,
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.bg.surface,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    marginBottom: tokens.spacing.sm,
  },
  musicItemActive: {
    borderColor: tokens.color.brand.indigo[500],
    backgroundColor: tokens.color.brand.indigo[900],
  },
  musicIcon: {
    width: 40,
    height: 40,
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.brand.indigo[900],
    alignItems: "center",
    justifyContent: "center",
  },
  musicInfo: { flex: 1 },
  musicName: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    fontWeight: "600",
    color: tokens.color.text.primary,
  },
  musicMeta: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.secondary,
  },
  agentDescription: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.secondary,
    marginBottom: tokens.spacing.md,
  },
  agentList: { maxHeight: 400 },
  agentItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
    padding: tokens.spacing.md,
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.bg.surface,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    marginBottom: tokens.spacing.sm,
  },
  agentItemActive: {
    borderColor: tokens.color.brand.indigo[500],
    backgroundColor: tokens.color.brand.indigo[900],
  },
  agentIcon: {
    width: 36,
    height: 36,
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.brand.indigo[900],
    alignItems: "center",
    justifyContent: "center",
  },
  agentInfo: { flex: 1 },
  agentName: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    fontWeight: "600",
    color: tokens.color.text.primary,
  },
  agentDesc: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.secondary,
  },
  agentCost: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.brand.indigo[400],
  },
  agentCheck: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: tokens.color.border.subtle,
    alignItems: "center",
    justifyContent: "center",
  },
  agentCheckActive: {
    backgroundColor: tokens.color.brand.indigo[500],
    borderColor: tokens.color.brand.indigo[500],
  },
  agentFooter: {
    marginTop: tokens.spacing.md,
    gap: tokens.spacing.sm,
    borderTopWidth: 1,
    borderTopColor: tokens.color.border.subtle,
    paddingTop: tokens.spacing.md,
  },
  agentTotal: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.secondary,
    textAlign: "center",
  },
});