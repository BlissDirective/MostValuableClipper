import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Dimensions,
  FlatList,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  ActivityIndicator,
  Modal,
} from "react-native";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import {
  ChevronLeft,
  Music,
  Play,
  Pause,
  Volume2,
  Sparkles,
  Search,
  Upload,
  X,
  FolderOpen,
  User,
  Globe,
  Filter,
} from "lucide-react-native";
import { Video, ResizeMode } from "expo-av";

import { tokens } from "@/constants/tokens";
import { ActionButton } from "@/components/ActionButton";
import { musicApi, clipsApi } from "@/lib/api";
import { useToast } from "@/components/ToastProvider";

const { width: SCREEN_W } = Dimensions.get("window");

interface MusicTrack {
  id: string;
  title: string;
  artist: string;
  genre: string;
  vibe: string;
  mood: string;
  tempo_bpm: number;
  duration_seconds: number;
  source: string;
  license_type: string;
  available: boolean;
  is_user_upload: boolean;
}

interface MixProfile {
  id: string;
  name: string;
  duck_factor: number;
  description: string;
}

const SOURCE_COLORS: Record<string, string> = {
  bundled: tokens.color.brand.teal[400],
  pixabay: tokens.color.brand.green[400],
  fma: tokens.color.brand.amber[400],
  incompetech: tokens.color.brand.violet[400],
  user_upload: tokens.color.brand.pink[400],
  demo: tokens.color.text.secondary,
  youtube_audio_library: tokens.color.brand.red[400],
  ccmixter: tokens.color.brand.cyan[400],
};

const SOURCE_LABELS: Record<string, string> = {
  bundled: "Bundled",
  pixabay: "Pixabay",
  fma: "FMA",
  incompetech: "Incompetech",
  user_upload: "My Upload",
  demo: "Demo (Synth)",
  youtube_audio_library: "YouTube Audio",
  ccmixter: "ccMixter",
};

export default function MusicLibraryScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ clipId?: string }>();
  const toast = useToast();

  const [tracks, setTracks] = useState<MusicTrack[]>([]);
  const [profiles, setProfiles] = useState<MixProfile[]>([]);
  const [filters, setFilters] = useState<{
    genres: string[];
    vibes: string[];
    moods: string[];
    sources: string[];
  }>({ genres: [], vibes: [], moods: [], sources: [] });
  
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedGenre, setSelectedGenre] = useState<string | null>(null);
  const [selectedVibe, setSelectedVibe] = useState<string | null>(null);
  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  const [selectedTrack, setSelectedTrack] = useState<MusicTrack | null>(null);
  const [selectedProfile, setSelectedProfile] = useState<string>("background");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [duckFactor, setDuckFactor] = useState(0.15);
  
  // Upload modal state
  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadArtist, setUploadArtist] = useState("");
  const [uploadGenre, setUploadGenre] = useState("misc");
  const [uploadVibe, setUploadVibe] = useState("neutral");
  const [uploading, setUploading] = useState(false);

  const clipId = params.clipId;

  useEffect(() => {
    loadData();
  }, []);

  // Refetch when filters change
  useEffect(() => {
    loadTracks();
  }, [selectedGenre, selectedVibe, selectedSource, searchQuery]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [tracksRes, profilesRes] = await Promise.all([
        musicApi.getTracks(),
        musicApi.getProfiles(),
      ]);
      setTracks(tracksRes.tracks || []);
      setProfiles(profilesRes.profiles || []);
      setFilters(tracksRes.filters as { genres: string[]; vibes: string[]; moods: string[]; sources: string[]; });
    } catch (err: any) {
      toast.error("Failed to load music library");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  const loadTracks = useCallback(async () => {
    try {
      const filters: any = {};
      if (selectedGenre) filters.genre = selectedGenre;
      if (selectedVibe) filters.vibe = selectedVibe;
      if (selectedSource) filters.source = selectedSource;
      if (searchQuery.trim()) filters.search = searchQuery.trim();
      
      const res = await musicApi.getTracks(
        Object.keys(filters).length > 0 ? filters : undefined
      );
      setTracks(res.tracks || []);
    } catch (err: any) {
      // Silent fail for filter changes
    }
  }, [selectedGenre, selectedVibe, selectedSource, searchQuery]);

  const filteredTracks = useMemo(() => tracks, [tracks]);

  const generatePreview = useCallback(async () => {
    if (!clipId || !selectedTrack) {
      toast.warning("Select a track first");
      return;
    }
    setPreviewLoading(true);
    try {
      const res = await clipsApi.previewMusic(
        clipId,
        selectedTrack.id,
        selectedProfile,
        10,
        duckFactor
      );
      if (res.preview_url) {
        setPreviewUrl(res.preview_url);
        setIsPlaying(true);
        toast.success("Preview generated!");
      }
    } catch (err: any) {
      toast.error(err.message || "Preview failed");
    } finally {
      setPreviewLoading(false);
    }
  }, [clipId, selectedTrack, selectedProfile, duckFactor, toast]);

  const applyToClip = useCallback(() => {
    if (!clipId || !selectedTrack) {
      toast.warning("Select a track first");
      return;
    }
    Alert.alert(
      "Apply Music Mix",
      `Mix "${selectedTrack.title}" with ${profiles.find((p) => p.id === selectedProfile)?.name || selectedProfile} profile?`,
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Apply",
          onPress: () => {
            router.push({
              pathname: `/(app)/clip/${clipId}/edit`,
              params: {
                musicTrackId: selectedTrack.id,
                musicProfile: selectedProfile,
                musicDuckFactor: String(duckFactor),
              },
            });
          },
        },
      ]
    );
  }, [clipId, selectedTrack, selectedProfile, duckFactor, profiles, router]);

  const handleUpload = useCallback(async () => {
    if (!uploadTitle.trim()) {
      toast.warning("Title is required");
      return;
    }
    setUploading(true);
    try {
      // In a real app, you'd use DocumentPicker to select a file
      // For now, we'll show a success message indicating the flow
      toast.info("Upload feature: Use the web dashboard or API to upload MP3s");
      setUploadModalVisible(false);
    } catch (err: any) {
      toast.error(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  }, [uploadTitle, toast]);

  const renderTrack = useCallback(
    ({ item }: { item: MusicTrack }) => {
      const isSelected = selectedTrack?.id === item.id;
      const sourceColor = SOURCE_COLORS[item.source] || tokens.color.text.secondary;
      const sourceLabel = SOURCE_LABELS[item.source] || item.source;

      return (
        <Pressable
          onPress={() => setSelectedTrack(item)}
          style={[styles.trackCard, isSelected && styles.trackCardSelected]}
        >
          <View style={styles.trackLeft}>
            <View style={[styles.trackIconWrap, { backgroundColor: sourceColor + "15" }]}>
              {item.is_user_upload ? (
                <User size={18} color={sourceColor} />
              ) : (
                <Globe size={18} color={sourceColor} />
              )}
            </View>
            <View style={styles.trackInfo}>
              <Text style={styles.trackTitle}>{item.title}</Text>
              <Text style={styles.trackMeta}>
                {item.artist} · {item.tempo_bpm} BPM · {Math.round(item.duration_seconds)}s
              </Text>
              <View style={styles.trackTags}>
                <View style={[styles.genreTag, { backgroundColor: tokens.color.brand.indigo[900] + "30" }]}>
                  <Text style={[styles.genreTagText, { color: tokens.color.brand.indigo[300] }]}>
                    {item.genre}
                  </Text>
                </View>
                <View style={[styles.vibeTag, { backgroundColor: tokens.color.brand.teal[900] + "30" }]}>
                  <Text style={[styles.vibeTagText, { color: tokens.color.brand.teal[300] }]}>
                    {item.vibe}
                  </Text>
                </View>
                <View style={[styles.sourceTag, { backgroundColor: sourceColor + "15" }]}>
                  <Text style={[styles.sourceTagText, { color: sourceColor }]}>
                    {sourceLabel}
                  </Text>
                </View>
              </View>
            </View>
          </View>
          {isSelected && (
            <View style={styles.selectedIndicator}>
              <Sparkles size={16} color={tokens.color.brand.teal[300]} />
            </View>
          )}
        </Pressable>
      );
    },
    [selectedTrack]
  );

  const currentProfile = profiles.find((p) => p.id === selectedProfile);

  return (
    <View style={styles.root}>
      <Stack.Screen options={{ headerShown: false }} />
      <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
        {/* Header */}
        <View style={styles.header}>
          <Pressable onPress={() => router.back()} hitSlop={12} style={styles.backBtn}>
            <ChevronLeft size={tokens.icon.size.md} color={tokens.color.text.primary} />
          </Pressable>
          <View style={styles.headerCenter}>
            <Text style={styles.headerTitle}>Music Library</Text>
            <Text style={styles.headerSubtitle}>{tracks.length} tracks · Multi-source</Text>
          </View>
          <Pressable onPress={() => setUploadModalVisible(true)} style={styles.uploadBtn}>
            <Upload size={20} color={tokens.color.brand.teal[300]} />
          </Pressable>
        </View>

        {/* Search Bar */}
        <View style={styles.searchRow}>
          <Search size={16} color={tokens.color.text.tertiary} />
          <TextInput
            style={styles.searchInput}
            value={searchQuery}
            onChangeText={setSearchQuery}
            placeholder="Search by title, artist, genre, vibe..."
            placeholderTextColor={tokens.color.text.tertiary}
          />
          {searchQuery.length > 0 && (
            <Pressable onPress={() => setSearchQuery("")}>
              <X size={16} color={tokens.color.text.tertiary} />
            </Pressable>
          )}
        </View>

        {/* Genre Tabs */}
        {filters.genres.length > 0 && (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.genreScroll}>
            <Pressable
              onPress={() => setSelectedGenre(null)}
              style={[styles.genreChip, !selectedGenre && styles.genreChipActive]}
            >
              <Text style={[styles.genreChipText, !selectedGenre && styles.genreChipTextActive]}>
                All
              </Text>
            </Pressable>
            {filters.genres.map((genre) => (
              <Pressable
                key={genre}
                onPress={() => setSelectedGenre(selectedGenre === genre ? null : genre)}
                style={[styles.genreChip, selectedGenre === genre && styles.genreChipActive]}
              >
                <Text style={[styles.genreChipText, selectedGenre === genre && styles.genreChipTextActive]}>
                  {genre.charAt(0).toUpperCase() + genre.slice(1)}
                </Text>
              </Pressable>
            ))}
          </ScrollView>
        )}

        {/* Vibe Filters */}
        {filters.vibes.length > 0 && (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.vibeScroll}>
            {filters.vibes.map((vibe) => (
              <Pressable
                key={vibe}
                onPress={() => setSelectedVibe(selectedVibe === vibe ? null : vibe)}
                style={[styles.vibeChip, selectedVibe === vibe && styles.vibeChipActive]}
              >
                <Text style={[styles.vibeChipText, selectedVibe === vibe && styles.vibeChipTextActive]}>
                  {vibe.charAt(0).toUpperCase() + vibe.slice(1)}
                </Text>
              </Pressable>
            ))}
          </ScrollView>
        )}

        {/* Source Filter */}
        <View style={styles.sourceRow}>
          <Filter size={14} color={tokens.color.text.tertiary} />
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <Pressable
              onPress={() => setSelectedSource(null)}
              style={[styles.sourceFilterChip, !selectedSource && styles.sourceFilterChipActive]}
            >
              <Text style={[styles.sourceFilterText, !selectedSource && styles.sourceFilterTextActive]}>All Sources</Text>
            </Pressable>
            {filters.sources.map((source) => (
              <Pressable
                key={source}
                onPress={() => setSelectedSource(selectedSource === source ? null : source)}
                style={[styles.sourceFilterChip, selectedSource === source && styles.sourceFilterChipActive]}
              >
                <Text style={[styles.sourceFilterText, selectedSource === source && styles.sourceFilterTextActive]}>
                  {SOURCE_LABELS[source] || source}
                </Text>
              </Pressable>
            ))}
          </ScrollView>
        </View>

        {/* Track List */}
        {loading ? (
          <View style={styles.loadingWrap}>
            <ActivityIndicator size="large" color={tokens.color.brand.teal[300]} />
            <Text style={styles.loadingText}>Loading tracks...</Text>
          </View>
        ) : (
          <FlatList
            data={filteredTracks}
            renderItem={renderTrack}
            keyExtractor={(item) => item.id}
            contentContainerStyle={styles.trackList}
            showsVerticalScrollIndicator={false}
            ItemSeparatorComponent={() => <View style={styles.trackSeparator} />}
            ListEmptyComponent={
              <View style={styles.emptyWrap}>
                <Music size={48} color={tokens.color.text.tertiary} />
                <Text style={styles.emptyTitle}>No tracks found</Text>
                <Text style={styles.emptyBody}>
                  {searchQuery 
                    ? "Try different search terms or filters"
                    : "Run the music downloader or upload your own tracks"
                  }
                </Text>
              </View>
            }
          />
        )}

        {/* Bottom Sheet — Mix Config + Preview */}
        {selectedTrack && (
          <View style={styles.bottomSheet}>
            <View style={styles.bottomHandle} />

            <View style={styles.selectedTrackRow}>
              <View style={[styles.miniIconWrap, { backgroundColor: (SOURCE_COLORS[selectedTrack.source] || tokens.color.text.secondary) + "15" }]}>
                {selectedTrack.is_user_upload ? (
                  <User size={18} color={SOURCE_COLORS[selectedTrack.source]} />
                ) : (
                  <Globe size={18} color={SOURCE_COLORS[selectedTrack.source]} />
                )}
              </View>
              <View style={styles.selectedTrackInfo}>
                <Text style={styles.selectedTrackTitle}>{selectedTrack.title}</Text>
                <Text style={styles.selectedTrackMeta}>
                  {selectedTrack.artist} · {selectedTrack.genre} · {selectedTrack.vibe}
                </Text>
              </View>
            </View>

            {/* Profile Selector */}
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.profileScroll}>
              {profiles.map((profile) => (
                <Pressable
                  key={profile.id}
                  onPress={() => {
                    setSelectedProfile(profile.id);
                    setDuckFactor(profile.duck_factor);
                  }}
                  style={[styles.profileChip, selectedProfile === profile.id && styles.profileChipActive]}
                >
                  <Text style={[styles.profileChipText, selectedProfile === profile.id && styles.profileChipTextActive]}>
                    {profile.name}
                  </Text>
                  {selectedProfile === profile.id && (
                    <Text style={styles.profileChipDesc}>{profile.description}</Text>
                  )}
                </Pressable>
              ))}
            </ScrollView>

            {/* Ducking Slider */}
            <View style={styles.duckRow}>
              <Volume2 size={16} color={tokens.color.text.secondary} />
              <Text style={styles.duckLabel}>Music Volume</Text>
              <View style={styles.duckBar}>
                <View style={[styles.duckFill, { width: `${Math.min(duckFactor * 100 * 4, 100)}%` }]} />
              </View>
              <Text style={styles.duckValue}>{Math.round(duckFactor * 100)}%</Text>
            </View>

            {/* Preview Player */}
            {previewUrl && (
              <View style={styles.previewPlayer}>
                <Video
                  source={{ uri: previewUrl }}
                  style={styles.previewVideo}
                  resizeMode={ResizeMode.CONTAIN}
                  useNativeControls={false}
                  isLooping
                  shouldPlay={isPlaying}
                  onPlaybackStatusUpdate={(status: any) => {
                    if (status.isLoaded) {
                      setIsPlaying(status.isPlaying);
                    }
                  }}
                />
                <Pressable onPress={() => setIsPlaying(!isPlaying)} style={styles.playOverlay}>
                  {isPlaying ? (
                    <Pause size={32} color={tokens.color.text.primary} />
                  ) : (
                    <Play size={32} color={tokens.color.text.primary} />
                  )}
                </Pressable>
              </View>
            )}

            {/* Action Buttons */}
            <View style={styles.actionRow}>
              <ActionButton
                label={previewLoading ? "Generating..." : previewUrl ? "Regenerate" : "Preview Mix"}
                variant="secondary"
                size="md"
                onPress={generatePreview}
                disabled={previewLoading}
                style={styles.flex1}
              />
              <ActionButton
                label="Apply to Clip"
                variant="primary"
                size="md"
                onPress={applyToClip}
                style={styles.flex1}
              />
            </View>
          </View>
        )}
      </SafeAreaView>

      {/* Upload Modal */}
      <Modal
        visible={uploadModalVisible}
        animationType="slide"
        transparent
        onRequestClose={() => setUploadModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalSheet}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Upload Music</Text>
              <Pressable onPress={() => setUploadModalVisible(false)}>
                <X size={24} color={tokens.color.text.secondary} />
              </Pressable>
            </View>

            <Text style={styles.modalBody}>
              Upload your own MP3 tracks to use in clip mixing.{"\n"}
              Files are stored privately and only accessible to your account.
            </Text>

            <TextInput
              style={styles.modalInput}
              value={uploadTitle}
              onChangeText={setUploadTitle}
              placeholder="Track title *"
              placeholderTextColor={tokens.color.text.tertiary}
            />
            <TextInput
              style={styles.modalInput}
              value={uploadArtist}
              onChangeText={setUploadArtist}
              placeholder="Artist name"
              placeholderTextColor={tokens.color.text.tertiary}
            />

            <View style={styles.modalRow}>
              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Genre</Text>
                <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                  {["misc", "electronic", "pop", "rock", "hip-hop", "classical", "jazz", "ambient", "cinematic", "folk"].map((g) => (
                    <Pressable
                      key={g}
                      onPress={() => setUploadGenre(g)}
                      style={[styles.modalChip, uploadGenre === g && styles.modalChipActive]}
                    >
                      <Text style={[styles.modalChipText, uploadGenre === g && styles.modalChipTextActive]}>
                        {g}
                      </Text>
                    </Pressable>
                  ))}
                </ScrollView>
              </View>
            </View>

            <View style={styles.modalRow}>
              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Vibe</Text>
                <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                  {["neutral", "energetic", "happy", "calm", "emotional", "dramatic", "chill", "upbeat"].map((v) => (
                    <Pressable
                      key={v}
                      onPress={() => setUploadVibe(v)}
                      style={[styles.modalChip, uploadVibe === v && styles.modalChipActive]}
                    >
                      <Text style={[styles.modalChipText, uploadVibe === v && styles.modalChipTextActive]}>
                        {v}
                      </Text>
                    </Pressable>
                  ))}
                </ScrollView>
              </View>
            </View>

            <View style={styles.modalUploadArea}>
              <FolderOpen size={32} color={tokens.color.text.tertiary} />
              <Text style={styles.modalUploadText}>
                MP3 upload via API or web dashboard{"\n"}
                (Mobile file picker coming soon)
              </Text>
            </View>

            <ActionButton
              label={uploading ? "Uploading..." : "Upload Track"}
              variant="primary"
              size="md"
              onPress={handleUpload}
              disabled={uploading || !uploadTitle.trim()}
              style={styles.modalSubmit}
            />
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg.base },
  safe: { flex: 1 },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: tokens.spacing.md,
    paddingTop: tokens.spacing.md,
    paddingBottom: tokens.spacing.sm,
  },
  backBtn: { padding: tokens.spacing.xs },
  uploadBtn: { padding: tokens.spacing.xs },
  headerCenter: { alignItems: "center", flex: 1 },
  headerTitle: {
    fontFamily: tokens.type.scale.h3.family,
    fontSize: tokens.type.scale.h3.size,
    fontWeight: "600",
    color: tokens.color.text.primary,
  },
  headerSubtitle: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.tertiary,
    marginTop: 2,
  },
  searchRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.sm,
    marginHorizontal: tokens.spacing.md,
    marginBottom: tokens.spacing.sm,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    backgroundColor: tokens.color.bg.surface,
  },
  searchInput: {
    flex: 1,
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.primary,
    paddingVertical: 0,
  },
  genreScroll: {
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.xs,
    gap: tokens.spacing.sm,
  },
  genreChip: {
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    borderRadius: tokens.radius.pill,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    backgroundColor: tokens.color.bg.surface,
  },
  genreChipActive: {
    borderColor: tokens.color.brand.indigo[500],
    backgroundColor: tokens.color.brand.indigo[900] + "30",
  },
  genreChipText: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    color: tokens.color.text.secondary,
  },
  genreChipTextActive: {
    color: tokens.color.brand.indigo[300],
    fontWeight: "600",
  },
  vibeScroll: {
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.xs,
    gap: tokens.spacing.sm,
  },
  vibeChip: {
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.xs,
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    backgroundColor: tokens.color.bg.surface,
  },
  vibeChipActive: {
    borderColor: tokens.color.brand.teal[400],
    backgroundColor: tokens.color.brand.teal[900] + "20",
  },
  vibeChipText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.secondary,
  },
  vibeChipTextActive: {
    color: tokens.color.brand.teal[300],
    fontWeight: "600",
  },
  sourceRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.sm,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.xs,
    borderBottomWidth: 1,
    borderBottomColor: tokens.color.border.subtle,
  },
  sourceFilterChip: {
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: tokens.spacing.xs,
    borderRadius: tokens.radius.sm,
    marginRight: tokens.spacing.xs,
  },
  sourceFilterChipActive: {
    backgroundColor: tokens.color.brand.indigo[900] + "30",
  },
  sourceFilterText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.tertiary,
  },
  sourceFilterTextActive: {
    color: tokens.color.brand.indigo[300],
    fontWeight: "600",
  },
  loadingWrap: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: tokens.spacing.md,
  },
  loadingText: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    color: tokens.color.text.secondary,
  },
  trackList: {
    paddingHorizontal: tokens.spacing.md,
    paddingBottom: tokens.spacing.xl,
  },
  trackSeparator: {
    height: 1,
    backgroundColor: tokens.color.border.subtle,
    marginVertical: tokens.spacing.sm,
  },
  trackCard: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: tokens.spacing.sm,
    paddingHorizontal: tokens.spacing.sm,
    borderRadius: tokens.radius.lg,
  },
  trackCardSelected: {
    backgroundColor: tokens.color.brand.teal[900] + "30",
    borderWidth: 1,
    borderColor: tokens.color.brand.teal[700],
  },
  trackLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
    flex: 1,
  },
  trackIconWrap: {
    width: 48,
    height: 48,
    borderRadius: tokens.radius.md,
    alignItems: "center",
    justifyContent: "center",
  },
  trackInfo: {
    gap: 2,
    flex: 1,
  },
  trackTitle: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    fontWeight: "600",
    color: tokens.color.text.primary,
  },
  trackMeta: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.secondary,
  },
  trackTags: {
    flexDirection: "row",
    gap: tokens.spacing.xs,
    marginTop: 2,
  },
  genreTag: {
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: 2,
    borderRadius: tokens.radius.sm,
  },
  genreTagText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: 10,
    fontWeight: "600",
  },
  vibeTag: {
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: 2,
    borderRadius: tokens.radius.sm,
  },
  vibeTagText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: 10,
    fontWeight: "600",
  },
  sourceTag: {
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: 2,
    borderRadius: tokens.radius.sm,
  },
  sourceTagText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: 10,
    fontWeight: "600",
  },
  selectedIndicator: {
    width: 32,
    height: 32,
    borderRadius: tokens.radius.pill,
    backgroundColor: tokens.color.brand.teal[900] + "40",
    alignItems: "center",
    justifyContent: "center",
  },
  emptyWrap: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: tokens.spacing.xxxl,
    gap: tokens.spacing.md,
  },
  emptyTitle: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    fontWeight: "600",
    color: tokens.color.text.secondary,
  },
  emptyBody: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.tertiary,
    textAlign: "center",
    paddingHorizontal: tokens.spacing.xl,
  },
  bottomSheet: {
    backgroundColor: tokens.color.bg.surface,
    borderTopLeftRadius: tokens.radius.xl,
    borderTopRightRadius: tokens.radius.xl,
    borderTopWidth: 1,
    borderTopColor: tokens.color.border.subtle,
    paddingHorizontal: tokens.spacing.md,
    paddingTop: tokens.spacing.md,
    paddingBottom: tokens.spacing.xl,
    gap: tokens.spacing.md,
  },
  bottomHandle: {
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: tokens.color.border.subtle,
    alignSelf: "center",
    marginBottom: tokens.spacing.sm,
  },
  selectedTrackRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.md,
  },
  miniIconWrap: {
    width: 40,
    height: 40,
    borderRadius: tokens.radius.md,
    alignItems: "center",
    justifyContent: "center",
  },
  selectedTrackInfo: {
    gap: 2,
    flex: 1,
  },
  selectedTrackTitle: {
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    fontWeight: "600",
    color: tokens.color.text.primary,
  },
  selectedTrackMeta: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.secondary,
  },
  profileScroll: {
    gap: tokens.spacing.sm,
  },
  profileChip: {
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    backgroundColor: tokens.color.bg.base,
    minWidth: 120,
  },
  profileChipActive: {
    borderColor: tokens.color.brand.teal[400],
    backgroundColor: tokens.color.brand.teal[900] + "30",
  },
  profileChipText: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    fontWeight: "500",
    color: tokens.color.text.secondary,
  },
  profileChipTextActive: {
    color: tokens.color.brand.teal[300],
    fontWeight: "600",
  },
  profileChipDesc: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.tertiary,
    marginTop: 2,
  },
  duckRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing.sm,
    paddingVertical: tokens.spacing.sm,
  },
  duckLabel: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    color: tokens.color.text.secondary,
    width: 90,
  },
  duckBar: {
    flex: 1,
    height: 4,
    backgroundColor: tokens.color.border.subtle,
    borderRadius: 2,
    overflow: "hidden",
  },
  duckFill: {
    height: "100%",
    backgroundColor: tokens.color.brand.teal[400],
    borderRadius: 2,
  },
  duckValue: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.secondary,
    width: 40,
    textAlign: "right",
  },
  previewPlayer: {
    width: "100%",
    aspectRatio: 16 / 9,
    borderRadius: tokens.radius.lg,
    overflow: "hidden",
    backgroundColor: tokens.color.bg.base,
    position: "relative",
  },
  previewVideo: {
    width: "100%",
    height: "100%",
  },
  playOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: tokens.color.bg.overlay,
    alignItems: "center",
    justifyContent: "center",
  },
  actionRow: {
    flexDirection: "row",
    gap: tokens.spacing.sm,
  },
  flex1: { flex: 1 },
  
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: tokens.color.bg.overlay,
    justifyContent: "flex-end",
  },
  modalSheet: {
    backgroundColor: tokens.color.bg.surface,
    borderTopLeftRadius: tokens.radius.xl,
    borderTopRightRadius: tokens.radius.xl,
    paddingHorizontal: tokens.spacing.md,
    paddingTop: tokens.spacing.md,
    paddingBottom: tokens.spacing.xxl,
    gap: tokens.spacing.md,
    maxHeight: "90%",
  },
  modalHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  modalTitle: {
    fontFamily: tokens.type.scale.h3.family,
    fontSize: tokens.type.scale.h3.size,
    fontWeight: "600",
    color: tokens.color.text.primary,
  },
  modalBody: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    color: tokens.color.text.secondary,
    lineHeight: 20,
  },
  modalInput: {
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    borderRadius: tokens.radius.md,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    fontFamily: tokens.type.scale.bodyMedium.family,
    fontSize: tokens.type.scale.bodyMedium.size,
    color: tokens.color.text.primary,
    backgroundColor: tokens.color.bg.base,
  },
  modalRow: {
    flexDirection: "row",
    gap: tokens.spacing.md,
  },
  modalField: {
    flex: 1,
  },
  modalLabel: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.secondary,
    marginBottom: tokens.spacing.xs,
  },
  modalChip: {
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: tokens.spacing.xs,
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    borderColor: tokens.color.border.subtle,
    marginRight: tokens.spacing.xs,
    backgroundColor: tokens.color.bg.base,
  },
  modalChipActive: {
    borderColor: tokens.color.brand.teal[400],
    backgroundColor: tokens.color.brand.teal[900] + "30",
  },
  modalChipText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.secondary,
  },
  modalChipTextActive: {
    color: tokens.color.brand.teal[300],
    fontWeight: "600",
  },
  modalUploadArea: {
    borderWidth: 2,
    borderColor: tokens.color.border.subtle,
    borderStyle: "dashed",
    borderRadius: tokens.radius.lg,
    paddingVertical: tokens.spacing.xl,
    alignItems: "center",
    justifyContent: "center",
    gap: tokens.spacing.sm,
  },
  modalUploadText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.tertiary,
    textAlign: "center",
  },
  modalSubmit: {
    marginTop: tokens.spacing.sm,
  },
});
