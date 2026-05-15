# Legal Pages — Quick Reference for Developer Account Applications

## Live URLs (Once Deployed)

Replace `https://your-domain.com` with your actual Fly.io deployment URL.

| Document | URL | HTML Content Length |
|----------|-----|---------------------|
| **Privacy Policy** | `https://your-domain.com/privacy` | ~18KB |
| **Terms of Service** | `https://your-domain.com/terms` | ~21KB |
| **DMCA/Copyright** | `https://your-domain.com/dmca` | ~8KB |

## Platform-Specific Requirements

### TikTok Developer Account
**What you need:**
- App Name: BlissClip
- App Icon: Your app icon (1024x1024 PNG)
- App Description: AI-powered video clip generation for content creators
- Privacy Policy URL: `https://your-domain.com/privacy`
- Terms of Service URL: `https://your-domain.com/terms`
- Data Deletion URL: `https://your-domain.com/privacy` (Section 7.5)
- App Category: Content Creation / Social Media
- Website: `https://your-domain.com`
- Callback URLs: `https://your-domain.com/api/v1/auth/tiktok/callback`

**Approval time:** 1-3 business days
**Notes:** TikTok requires business verification. Be prepared to provide business registration docs.

---

### Meta (Instagram / Facebook) Developer
**What you need:**
- App Name: BlissClip
- App Icon: Your app icon
- Privacy Policy URL: `https://your-domain.com/privacy`
- Terms of Service URL: `https://your-domain.com/terms`
- Data Deletion URL: `https://your-domain.com/privacy`
- App Domains: `your-domain.com`
- Category: Business and Pages
- Business Use Case: Content Publishing API

**Additional requirements:**
- Business Verification required for Content Publishing API
- You need to record a screencast showing app usage
- Explain how your app uses each permission you request

**Approval time:** Instant for basic, 1-2 weeks for publishing permissions

---

### Google / YouTube Data API
**What you need:**
- Project Name: BlissClip
- Privacy Policy URL: `https://your-domain.com/privacy`
- Terms of Service URL: `https://your-domain.com/terms`
- Authorized Redirect URIs: `https://your-domain.com/api/v1/auth/google/callback`
- Authorized JavaScript Origins: `https://your-domain.com`
- Application Type: Web application

**Scopes needed:**
- `youtube.upload` — Upload videos to YouTube
- `youtube.readonly` — Read channel data (optional)

**Approval time:** Instant for development, 1-2 weeks for production quota

---

### Twitter/X API
**What you need:**
- App Name: BlissClip
- Description: AI-powered video clip generation and posting
- Website URL: `https://your-domain.com`
- Callback URL: `https://your-domain.com/api/v1/auth/twitter/callback`
- Privacy Policy: `https://your-domain.com/privacy`
- Terms of Service: `https://your-domain.com/terms`

**Note:** Twitter/X API v2 requires paid access for most posting features. Consider this carefully.

---

## Quick Fill Template

Use this when filling out application forms:

**App Name:** BlissClip

**App Description:** 
AI-powered video content creation platform. Users upload or link source videos (podcasts, long-form content, creator-licensed clips), and our AI pipeline generates optimized short-form clips for TikTok, Instagram, YouTube Shorts, and Facebook. Features include automatic caption generation, multi-platform posting, performance analytics, and monetization tracking.

**Privacy Policy URL:** https://your-domain.com/privacy

**Terms of Service URL:** https://your-domain.com/terms

**Data Deletion URL:** https://your-domain.com/privacy (Section 7.5 — Account Deletion)

**Contact Email:** privacy@blissclip.app

**Support Email:** support@blissclip.app

**Business Name:** BlissDirective LLC (or your LLC name)

**Business Address:** [Your business address]

**App Category:** Content Creation / Social Media Tools

**Platform:** iOS, Android, Web

---

## Data Handling Answers (Common Questions)

**How do you handle user data?**
> We collect account information, video content, social media OAuth tokens (encrypted), and usage analytics. Data is stored securely with TLS 1.3 encryption in transit and encryption at rest. We use Supabase for database storage, Cloudflare R2 for video storage, and Stripe for payment processing. Full details in our Privacy Policy.

**Do you sell user data?**
> No. We do not sell, rent, or trade user personal information. We only share data with service providers necessary to operate the platform (listed in Privacy Policy Section 5).

**How can users delete their data?**
> Users can delete their account anytime via Settings → Account → Delete Account. All personal data, videos, and clips are permanently deleted within 30 days. OAuth tokens are revoked immediately upon disconnecting a social account.

**What data do you share with social platforms?**
> With explicit user authorization, we share generated clips and captions for posting. We store OAuth tokens encrypted. Users control which platforms to connect and which content to post. Users can revoke authorization at any time.

**Do you use AI?**
> Yes, we use AI for video analysis, scene detection, caption generation, and transcript creation. Users retain ownership of source videos. AI-generated clips are licensed to users for use, distribution, and monetization. We disclose AI use in our Privacy Policy (Section 8) and clearly label AI-generated content.

**How do you handle copyrighted content?**
> Our Service includes audio fingerprinting (Chromaprint) to detect copyrighted material. Infringing content is automatically blocked from posting. Users must attest they have rights to source content. We process DMCA notices within 24 hours and terminate accounts with 3+ valid notices.

---

## Test the Pages

After deploying, verify the pages are accessible:

```bash
# Replace with your actual domain
curl -I https://your-domain.com/privacy
curl -I https://your-domain.com/terms
curl -I https://your-domain.com/dmca
```

All should return HTTP 200 with `Content-Type: text/html; charset=utf-8`.

---

## Screenshots for App Review

Most platforms require screenshots. Take these from your app:

1. **Home/Dashboard** — Shows the main interface
2. **Clip Review** — Shows AI-generated clips with approve/queue buttons
3. **Social Accounts** — Shows connected platforms
4. **Settings → Legal** — Shows the privacy/terms links in your app
5. **Data Deletion Flow** — Shows Settings → Account → Delete Account

## Important Notes

- **Business Verification:** Meta and TikTok require business verification. Have your LLC docs ready.
- **Screencast:** Record a 2-3 minute video walking through your app's main features.
- **Permissions Justification:** Be ready to explain why you need each API permission.
- **Development vs Production:** Most platforms let you develop with limited access. Apply for production/scoped access separately.
- **Rate Limits:** Start with conservative rate limits. You can request increases later.

## Contact Info Template

| Role | Email | Used For |
|------|-------|----------|
| Privacy Officer | privacy@blissclip.app | Privacy inquiries, DPO (GDPR) |
| DMCA Agent | dmca@blissclip.app | Copyright claims |
| Support | support@blissclip.app | User support |
| Legal | legal@blissclip.app | Legal inquiries |
| Data Protection | dpo@blissclip.app | EU data protection |

---

*Keep this document handy when filling out developer applications. Most fields are standardized across platforms.*
