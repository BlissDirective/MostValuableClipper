import React, { useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, router } from "expo-router";
import { UploadCloud, FileVideo, CheckCircle2 } from "lucide-react-native";
import * as ImagePicker from "expo-image-picker";
// SDK 54: uploadAsync/FileSystemUploadType live in the legacy module.
import * as FileSystem from "expo-file-system/legacy";

import { tokens } from "@/constants/tokens";
import { ActionButton } from "@/components/ActionButton";
import { clipsApi } from "@/lib/api";
import { triggerHaptic } from "@/utils/haptics";

type Phase = "idle" | "picked" | "uploading" | "ingesting" | "done" | "error";

export default function UploadScreen() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [asset, setAsset] = useState<ImagePicker.ImagePickerAsset | null>(null);
  const [error, setError] = useState<string | null>(null);

  const pick = async () => {
    triggerHaptic("selection");
    setError(null);
    const res = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["videos"],
      allowsEditing: false,
      quality: 1,
    });
    if (!res.canceled && res.assets?.[0]) {
      setAsset(res.assets[0]);
      setPhase("picked");
    }
  };

  const upload = async () => {
    if (!asset) return;
    try {
      const filename = asset.fileName || `upload-${Date.now()}.mp4`;
      const contentType = asset.mimeType || "video/mp4";

      // 1. Mint a presigned PUT URL + create the source clip record.
      setPhase("uploading");
      const init = await clipsApi.uploadInit({ filename, content_type: contentType, title: filename });

      // 2. PUT the bytes straight to R2 (never through our API).
      const putRes = await FileSystem.uploadAsync(init.upload_url, asset.uri, {
        httpMethod: "PUT",
        uploadType: FileSystem.FileSystemUploadType.BINARY_CONTENT,
        headers: init.headers,
      });
      if (putRes.status < 200 || putRes.status >= 300) {
        throw new Error(`Upload failed (HTTP ${putRes.status})`);
      }

      // 3. Kick off transcription → segmentation → clip rendering.
      setPhase("ingesting");
      await clipsApi.startIngest(init.clip_id);

      triggerHaptic("approve");
      setPhase("done");
      router.replace(`/(app)/clip/${init.clip_id}`);
    } catch (e: any) {
      triggerHaptic("blockTriggered");
      setError(e?.message || "Something went wrong");
      setPhase("error");
    }
  };

  const busy = phase === "uploading" || phase === "ingesting";

  return (
    <View style={styles.root}>
      <Stack.Screen options={{ headerShown: false }} />
      <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <Text style={styles.title}>Upload your video</Text>
          <Text style={styles.subtitle}>
            Add your own long-form video. We&apos;ll transcribe it, find the best
            moments, and generate clip variants for you to review.
          </Text>

          <View style={styles.dropzone}>
            {asset ? (
              <>
                <FileVideo size={40} color={tokens.color.accent.secondary} strokeWidth={1.5} />
                <Text style={styles.fileName} numberOfLines={1}>
                  {asset.fileName || "Selected video"}
                </Text>
                {!!asset.duration && (
                  <Text style={styles.fileMeta}>{Math.round(asset.duration / 1000)}s</Text>
                )}
              </>
            ) : (
              <>
                <UploadCloud size={40} color={tokens.color.text.tertiary} strokeWidth={1.5} />
                <Text style={styles.dropHint}>No video selected yet</Text>
              </>
            )}
          </View>

          {phase === "done" && (
            <View style={styles.statusRow}>
              <CheckCircle2 size={18} color={tokens.color.semantic?.success ?? "#1FCB8C"} />
              <Text style={styles.statusOk}>Uploaded — opening your clips…</Text>
            </View>
          )}
          {!!error && <Text style={styles.statusErr}>{error}</Text>}
          {busy && (
            <Text style={styles.statusBusy}>
              {phase === "uploading" ? "Uploading to secure storage…" : "Starting AI processing…"}
            </Text>
          )}
        </ScrollView>

        <View style={styles.footer}>
          {asset ? (
            <ActionButton
              label={busy ? "Working…" : "Upload & generate clips"}
              variant="primary"
              size="lg"
              fullWidth
              disabled={busy}
              onPress={upload}
            />
          ) : (
            <ActionButton label="Choose a video" variant="primary" size="lg" fullWidth onPress={pick} />
          )}
          {asset && !busy && (
            <ActionButton label="Pick a different video" variant="ghost" size="md" fullWidth onPress={pick} />
          )}
        </View>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg.base },
  safe: { flex: 1, paddingHorizontal: tokens.layout.screenPadding },
  content: { paddingTop: tokens.spacing.lg, gap: tokens.spacing.md, paddingBottom: tokens.spacing.xl },
  title: {
    fontFamily: tokens.type.scale.h1.family,
    fontSize: tokens.type.scale.h1.size,
    lineHeight: tokens.type.scale.h1.lineHeight,
    color: tokens.color.text.primary,
  },
  subtitle: {
    fontFamily: tokens.type.scale.bodySmall.family,
    fontSize: tokens.type.scale.bodySmall.size,
    lineHeight: tokens.type.scale.bodySmall.lineHeight,
    color: tokens.color.text.secondary,
  },
  dropzone: {
    marginTop: tokens.spacing.md,
    minHeight: 180,
    borderRadius: tokens.radius.lg,
    borderWidth: 2,
    borderColor: tokens.color.border.default,
    borderStyle: "dashed",
    backgroundColor: tokens.color.bg.surface,
    alignItems: "center",
    justifyContent: "center",
    gap: tokens.spacing.sm,
    padding: tokens.spacing.lg,
  },
  dropHint: { color: tokens.color.text.tertiary, fontFamily: tokens.type.scale.body.family },
  fileName: { color: tokens.color.text.primary, fontFamily: tokens.type.scale.body.family, maxWidth: "90%" },
  fileMeta: { color: tokens.color.text.tertiary, fontFamily: tokens.type.scale.caption.family },
  statusRow: { flexDirection: "row", alignItems: "center", gap: tokens.spacing.xs },
  statusOk: { color: tokens.color.text.secondary, fontFamily: tokens.type.scale.bodySmall.family },
  statusErr: { color: tokens.color.semantic?.danger ?? "#F25555", fontFamily: tokens.type.scale.bodySmall.family },
  statusBusy: { color: tokens.color.accent.secondary, fontFamily: tokens.type.scale.bodySmall.family },
  footer: {
    paddingVertical: tokens.spacing.md,
    gap: tokens.spacing.sm,
    borderTopWidth: 1,
    borderTopColor: tokens.color.border.subtle,
  },
});
