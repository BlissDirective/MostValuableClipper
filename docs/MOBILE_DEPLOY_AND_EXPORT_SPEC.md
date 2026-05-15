# Mobile Store Deployment + Video Export Spec

> This doc covers: (1) building native iOS/Android binaries from your existing Expo frontend, (2) the backend R2 presigned-URL flow for clip downloads, and (3) the client-side share implementation using native OS share sheets.

---

## Part 1 — Native Build Setup (Expo / EAS)

You already have an Expo app (`frontend/`). The cleanest path to App Store + Play Store is **EAS Build** — Expo's cloud build service. You do not need a Mac in your pocket.

### 1.1 What you need to acquire

| Item | Cost | Notes |
|------|------|-------|
| Apple Developer Program | $99/year | Required for App Store. No workaround. |
| Google Play Developer | $25 one-time | Required for Play Store. |
| EAS Build subscription | ~$30/mo (or pay-per-build) | Build iOS in the cloud without owning a Mac. Free tier exists but queue is slower. |

### 1.2 EAS configuration

Create `frontend/eas.json`:

```json
{
  "cli": {
    "version": ">= 14.0.0"
  },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal"
    },
    "preview": {
      "distribution": "internal",
      "android": {
        "buildType": "apk"
      }
    },
    "production": {
      "autoIncrement": true
    }
  },
  "submit": {
    "production": {}
  }
}
```

Update `frontend/app.json` — add the iOS bundle identifier and Android package name:

```json
{
  "expo": {
    "name": "BlissClip",
    "slug": "bliss-clip",
    "version": "1.0.0",
    "orientation": "portrait",
    "icon": "./assets/icon.png",
    "splash": {
      "image": "./assets/splash.png",
      "resizeMode": "contain",
      "backgroundColor": "#000000"
    },
    "assetBundlePatterns": ["**/*"],
    "ios": {
      "supportsTablet": false,
      "bundleIdentifier": "com.blissdirective.blissclip",
      "buildNumber": "1.0.0"
    },
    "android": {
      "package": "com.blissdirective.blissclip",
      "versionCode": 1,
      "adaptiveIcon": {
        "foregroundImage": "./assets/adaptive-icon.png",
        "backgroundColor": "#000000"
      }
    },
    "plugins": [
      "expo-router"
    ]
  }
}
```

### 1.3 Install EAS CLI and login

```bash
cd /root/.openclaw/workspace/mvc-combined/frontend
npx expo install expo-updates
npm install -g eas-cli
eas login   # uses your Expo account (free to create)
```

### 1.4 Configure build credentials

```bash
eas build:configure   # picks platforms, sets up project
```

This creates `frontend/eas.json` and links your project to EAS.

### 1.5 Build commands

```bash
# Internal test build (no store needed)
eas build --profile preview --platform ios    # gives you an IPA for TestFlight/internal
eas build --profile preview --platform android  # gives you an APK

# Production build (submits to stores)
eas build --profile production --platform ios
eas build --profile production --platform android
```

**For iOS production builds**, EAS handles certificates and provisioning profiles automatically. You just need your Apple Developer account connected:

```bash
eas credentials:manager   # add your Apple Developer Team ID
```

### 1.6 Store submission flow

After production build succeeds:

```bash
# iOS — upload to App Store Connect, then you manually submit via App Store Connect web UI
eas submit --platform ios

# Android — upload to Google Play Console internal track
eas submit --platform android
```

**Critical for App Store review:** Your app auto-posts to social platforms. Apple scrutinizes this. Make sure:
- The user explicitly authorizes each social account connection (OAuth consent screen visible)
- Approval-mode review screen is prominent (show the TikTok-style swipe deck)
- App Store description frames the product as "content creation assistant" not "automation bot"
- Include a demo video showing the approval flow

---

## Part 2 — R2 Presigned URL Flow (Backend)

Clips live in R2 at `/clips/{clip_id}.mp4`. Users need to download them to their device, then share outward.

### 2.1 Presigned URL generation (FastAPI endpoint)

Add to your pipeline service:

```python
# backend/api/routers/clips.py
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta
import boto3
from botocore.config import Config
from ..deps import get_current_user

router = APIRouter(prefix="/clips", tags=["clips"])

# R2 S3-compatible client
r2 = boto3.client(
    "s3",
    endpoint_url="https://<account-id>.r2.cloudflarestorage.com",
    aws_access_key_id="<r2-access-key>",
    aws_secret_access_key="<r2-secret-key>",
    config=Config(signature_version="s3v4"),
    region_name="auto",
)

R2_BUCKET = "bliss-clip-assets"
PRESIGN_TTL = 300  # 5 minutes, enough for a download start

@router.post("/{clip_id}/download-url")
async def get_download_url(
    clip_id: str,
    user = Depends(get_current_user),
):
    """
    Generate a presigned GET URL for a clip.
    User must own the clip (enforced by DB check).
    """
    # Verify ownership (pseudocode — use your actual DB)
    clip = await db.clips.find_one({
        "id": clip_id,
        "user_id": user.id,
        "status": "rendered"
    })
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    key = f"clips/{clip_id}.mp4"

    url = r2.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": R2_BUCKET,
            "Key": key,
            "ResponseContentDisposition": f'attachment; filename="blissclip_{clip_id}.mp4"',
        },
        ExpiresIn=PRESIGN_TTL,
    )

    return {
        "url": url,
        "expires_at": (datetime.utcnow() + timedelta(seconds=PRESIGN_TTL)).isoformat(),
        "filename": f"blissclip_{clip_id}.mp4",
        "content_type": "video/mp4",
    }
```

**Why `ResponseContentDisposition`?** This tells the browser / OS to treat it as a download rather than streaming inline. The `attachment` directive triggers the native "Save file" dialog.

### 2.2 R2 CORS (required for direct browser download)

In your R2 bucket settings (Cloudflare dashboard), add CORS policy:

```json
[
  {
    "AllowedOrigins": ["*"],
    "AllowedMethods": ["GET"],
    "AllowedHeaders": ["*"],
    "MaxAgeSeconds": 300
  }
]
```

Restrict `AllowedOrigins` to your production domain once deployed. For now `*` is fine during development.

### 2.3 Security notes

- URL expires in 5 minutes — cannot be shared as a permanent link
- Ownership check ensures users can't guess other clip IDs
- No auth token in the URL itself — the signature is HMAC, not a bearer token
- Log every presigned URL generation to `compliance_events` table

---

## Part 3 — Client-Side Share + Download (Frontend / Expo)

### 3.1 Install required Expo modules

```bash
cd /root/.openclaw/workspace/mvc-combined/frontend
npx expo install expo-sharing expo-file-system expo-media-library
```

| Module | Purpose |
|--------|---------|
| `expo-sharing` | Invoke the native OS share sheet (iOS UIActivityViewController / Android Intent) |
| `expo-file-system` | Save to app's sandbox, move to Downloads/Photos |
| `expo-media-library` | Save video to device's Photos / Gallery |

### 3.2 The download-then-share hook

Create `frontend/hooks/useClipExport.ts`:

```typescript
import { useState, useCallback } from "react";
import * as Sharing from "expo-sharing";
import * as FileSystem from "expo-file-system";
import * as MediaLibrary from "expo-media-library";
import { Platform } from "react-native";
import { api } from "@/lib/api";

interface ExportResult {
  success: boolean;
  savedToGallery?: boolean;
  error?: string;
}

export function useClipExport() {
  const [isExporting, setIsExporting] = useState(false);
  const [progress, setProgress] = useState(0);

  const requestPermissions = async (): Promise<boolean> => {
    if (Platform.OS === "ios") {
      const { status } = await MediaLibrary.requestPermissionsAsync();
      return status === "granted";
    }
    // Android — expo-file-system writes to app's sandbox without extra perms
    // MediaLibrary needs WRITE_EXTERNAL_STORAGE on older Android
    const { status } = await MediaLibrary.requestPermissionsAsync();
    return status === "granted";
  };

  const downloadClip = async (clipId: string): Promise<string | null> => {
    // 1. Get presigned URL from backend
    const { url, filename } = await api.post(`/clips/${clipId}/download-url`);

    // 2. Local path in app sandbox
    const localUri = FileSystem.documentDirectory + filename;

    // 3. Download with progress tracking
    const downloadResumable = FileSystem.createDownloadResumable(
      url,
      localUri,
      {},
      (downloadProgress) => {
        const pct =
          downloadProgress.totalBytesWritten /
          downloadProgress.totalBytesExpectedToWrite;
        setProgress(Math.round(pct * 100));
      }
    );

    const result = await downloadResumable.downloadAsync();
    return result?.uri ?? null;
  };

  const shareClip = async (clipId: string): Promise<ExportResult> => {
    setIsExporting(true);
    setProgress(0);

    try {
      const localUri = await downloadClip(clipId);
      if (!localUri) throw new Error("Download failed");

      // Check if sharing is available
      const isAvailable = await Sharing.isAvailableAsync();
      if (!isAvailable) {
        throw new Error("Sharing not available on this device");
      }

      // Open native share sheet — user picks Instagram, TikTok, Messages, etc.
      await Sharing.shareAsync(localUri, {
        mimeType: "video/mp4",
        dialogTitle: "Share your clip",
        UTI: "public.mpeg-4", // iOS uniform type identifier
      });

      return { success: true };
    } catch (err: any) {
      return { success: false, error: err.message };
    } finally {
      setIsExporting(false);
      setProgress(0);
    }
  };

  const saveToGallery = async (clipId: string): Promise<ExportResult> => {
    setIsExporting(true);
    setProgress(0);

    try {
      const hasPerms = await requestPermissions();
      if (!hasPerms) {
        return { success: false, error: "Photo library permission denied" };
      }

      const localUri = await downloadClip(clipId);
      if (!localUri) throw new Error("Download failed");

      // Save to Photos (iOS) / Gallery (Android)
      const asset = await MediaLibrary.createAssetAsync(localUri);
      await MediaLibrary.createAlbumAsync("BlissClip", asset, false);

      return { success: true, savedToGallery: true };
    } catch (err: any) {
      return { success: false, error: err.message };
    } finally {
      setIsExporting(false);
      setProgress(0);
    }
  };

  return {
    shareClip,
    saveToGallery,
    isExporting,
    progress,
  };
}
```

### 3.3 UI integration — add to ClipCard

Update `frontend/components/ClipCard.tsx` (or wherever clip actions live):

```typescript
import { useClipExport } from "@/hooks/useClipExport";
import { ActionButton } from "./ActionButton";

// Inside ClipCard component:
const { shareClip, saveToGallery, isExporting, progress } = useClipExport();

// In your action row:
<ActionButton
  icon="Share2"
  label={isExporting ? `${progress}%` : "Share"}
  onPress={() => shareClip(clip.id)}
  disabled={isExporting}
/>

<ActionButton
  icon="Download"
  label={isExporting ? `${progress}%` : "Save"}
  onPress={() => saveToGallery(clip.id)}
  disabled={isExporting}
/>
```

### 3.4 What the user sees

**Share flow:**
1. Taps "Share" on a clip
2. Video downloads to app sandbox (progress shown)
3. Native iOS share sheet (or Android share chooser) slides up
4. User sees all apps that accept video: Instagram, TikTok, YouTube, Messages, WhatsApp, etc.
5. User picks app — the OS hands off the file. Your app never sees credentials.

**Save flow:**
1. Taps "Save"
2. If first time, system permission dialog: "BlissClip wants to access your Photos"
3. Video downloads, then copies to device's Photos/Gallery album named "BlissClip"
4. User can find it in their camera roll and post manually anywhere.

---

## Part 4 — Store-Specific Gotchas

### iOS
- **App Store Guideline 4.2.3** — apps that auto-post must have explicit user approval per post. Your approval-mode swipe deck satisfies this. Full Auto mode must be clearly labeled and togglable.
- **Photo Library usage description** — add to `app.json`:
  ```json
  "ios": {
    "infoPlist": {
      "NSPhotoLibraryUsageDescription": "BlissClip saves your generated clips to your photo library so you can share them.",
      "NSPhotoLibraryAddUsageDescription": "BlissClip saves your generated clips to your photo library."
    }
  }
  ```

### Android
- **Scoped storage** — Android 10+ restricts raw file system access. `expo-file-system` handles this by writing to app-private directories, then `MediaLibrary` copies to shared storage. No `WRITE_EXTERNAL_STORAGE` needed on Android 10+.
- **Share sheet appearance** — Android share chooser shows all apps that register `video/mp4` intent filters. This is exactly what you want.

---

## Part 5 — Wiring Checklist

| Step | Where | What |
|------|-------|------|
| ☐ | Cloudflare R2 | Create bucket, upload a test clip, set CORS policy |
| ☐ | Backend | Implement `/clips/{id}/download-url` endpoint |
| ☐ | Backend | Add `clip_id → user_id` ownership check |
| ☐ | Frontend | `npx expo install expo-sharing expo-file-system expo-media-library` |
| ☐ | Frontend | Create `useClipExport.ts` hook |
| ☐ | Frontend | Wire share + save buttons into ClipCard / clip detail screen |
| ☐ | Expo | `eas build:configure` and first preview build |
| ☐ | Apple | Enroll in Apple Developer Program |
| ☐ | Google | Create Play Developer account |
| ☐ | EAS | Connect Apple Developer account to EAS credentials |
| ☐ | App Store Connect | Create app record, fill metadata, upload build |
| ☐ | Google Play Console | Create app, upload AAB, set up internal testing |

---

## Part 6 — Future: Direct Platform Posting (Phase 2)

If you later want "Post directly to my accounts" without the share sheet:

- **TikTok:** Share Kit (iOS/Android SDK) — requires TikTok developer approval, can share video directly to TikTok's publish flow
- **Instagram:** Instagram Content Publishing API — requires Business/Creator account, app review, heavy restrictions
- **YouTube:** YouTube Data API v3 — most permissive, standard OAuth 2.0
- **Twitter/X:** API v2 — expensive and unstable under current ownership

Recommendation: Ship with native share sheet (Option A) for MVP. Add direct integrations only after you have revenue and can justify the OAuth + review overhead per platform.
