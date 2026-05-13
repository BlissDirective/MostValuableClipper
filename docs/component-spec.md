# MVC — Component Spec (v0.1)

Companion to `design-tokens.json`. Every Rork prompt references this file. Components below are the shared MVP set from build-spec §6.2.

All components consume tokens by name (e.g. `color.bg.surface`, `spacing.md`) — never inline hex or raw numbers. Components are platform-neutral; iOS and Android render identically.

---

## 1. ClipCard

**Purpose**: The atomic unit of the home feed and per-clip detail. Represents one generated clip with its source, posting state, performance, and any safety flags.

**Anatomy** (top → bottom):
1. **Thumbnail** (9:16 aspect, `radius.md`, full-bleed within card). Frame-pick still in MVP.
2. **Source label row**: source badge (icon + truncated source name) on left; safety badge on right if any flag present.
3. **Caption preview**: 2 lines max, `type.scale.bodySmall`, `color.text.secondary`, ellipsis.
4. **Platform badges row**: small AccountBadges for each platform the clip was posted to (or "Queued" / "Held" state if not yet posted).
5. **Metric chips row**: views, retention, earnings — each rendered as a MetricChip.
6. **Quick actions row** (right-aligned, ghost buttons): Boost · Replicate · Kill.

**States**:
- `posted` — full color, all metrics visible.
- `queued` — desaturated thumbnail (60% opacity), platform badges replaced with "Queued for {time}" caption.
- `held-safety-block` — danger border (`color.semantic.safety.block.border`), banner across thumbnail with category and "Tap to review", actions replaced with Override (Premium only) · Discard.
- `held-safety-warn` — warning border, advisory banner, normal actions enabled.
- `processing` — skeleton shimmer, no actions.
- `failed` — error tint, retry action.

**Key props**: `clip`, `variant` ('feed' | 'detail' | 'queue'), `onAction(actionId)`.

**Behavior**:
- Tap → opens per-clip detail screen.
- Long-press → no-op in feed; reserved for SwipeDeckCard variant.
- All metric chips tappable for drill-down (detail view only).

---

## 2. PipelineRow

**Purpose**: One row per active pipeline (theme) on the Pipelines list screen.

**Anatomy** (left → right):
1. Status dot (`color.status.success` running, `color.status.warning` paused, `color.status.danger` errored).
2. Theme name (`type.scale.h3`, `color.text.primary`) + niche tag below (`type.scale.caption`, `color.text.tertiary`).
3. Stats stack (right-aligned): clips this week + 7-day view delta as MetricChip.
4. Trailing chevron icon.

**States**: `running`, `paused`, `errored`, `setup-incomplete`.

**Key props**: `pipeline`, `onTap`, `onLongPress` (long-press → quick-action sheet: Pause/Resume/Edit/Delete).

---

## 3. InsightTile

**Purpose**: Surfaces one Critic Agent finding on Home and Insights screens. Voice is **neutral analyst**, never "crushing it" / "killing it" — locked in build-spec §0.

**Anatomy**:
1. Tile header: small overline label (`type.scale.overline`, `color.text.tertiary`) — e.g. "HOOK ARCHETYPE".
2. Headline metric (large): "+124% retention" — uses `semantic.metric.positive` or `negative` color.
3. One-sentence body (`type.scale.bodySmall`): "Question-before-second-1 hooks vs. statement hooks, last 30 clips."
4. Optional CTA row: "Apply to all pipelines" ghost button.

**States**: `positive` (green accent), `negative` (red accent), `neutral` (default border).

**Key props**: `insight`, `onApply`.

---

## 4. AccountBadge

**Purpose**: Compact platform-and-handle representation. Used in ClipCard, Pipelines detail, Settings.

**Anatomy**: Platform glyph (color from `semantic.platform.*`) + truncated handle (`type.scale.caption`).

**Variants**:
- `dot` — glyph only, used in tight rows (ClipCard).
- `pill` — glyph + handle, `radius.pill`, used in Settings.
- `rich` — glyph + handle + follower count + eligibility flag (sub-1K marker), used in onboarding and settings.

**States**: `connected`, `expired-token` (warning), `not-eligible` (subdued).

---

## 5. SafetyFlag

**Purpose**: Surfaces Safety Classifier output. Always visible when a clip has any non-General classification.

**Anatomy**: Small pill — icon (lucide: `shield`, `shield-alert`, `shield-x`, `eye-off`) + category label.

**Variants** (driven by `semantic.safety.*`):
- `general` — neutral, rarely shown.
- `warn` — yellow pill (Health, Finance, News-Political, Identifiable Individual, Violent-Graphic, Children's).
- `block` — red pill (Adult-NSFW, Copyrighted-Material-Risk).
- `review` — blue pill (held for user approval, not blocked).

**Behavior**: tap opens explanation sheet showing category, classifier reasoning summary, action taken, and any user options (override for Premium on copyrighted-risk only).

**Key props**: `categories[]`, `actionTaken`, `onTap`.

---

## 6. MetricChip

**Purpose**: Compact KPI display. Used in ClipCard, PipelineRow, Earnings, Insights.

**Anatomy**: Optional icon (size `icon.size.xs`) + label (`type.scale.caption`, uppercase) + value (`type.scale.bodyMedium`).

**Variants**:
- `default` — `color.text.secondary` label, `color.text.primary` value.
- `positive` — value uses `semantic.metric.positive`, optional up-arrow icon.
- `negative` — value uses `semantic.metric.negative`, optional down-arrow icon.
- `loading` — shimmering bar in place of value.
- `manual` — small "M" badge to indicate sub-1K manual entry source.

**Key props**: `label`, `value`, `delta`, `variant`.

---

## 7. ActionButton

**Purpose**: All taps that do something. Standardized to four flavors.

**Variants**:
- `primary` — `accent.primary` bg, `text.onAccent` fg, `radius.md`. Used for "Create Pipeline", "Connect Account", confirmation primaries.
- `secondary` — transparent bg, `border.strong` border, `text.primary` fg. Used for non-destructive secondary actions.
- `ghost` — no bg, no border, `text.secondary` fg. Used for inline quick actions in ClipCard.
- `danger` — `status.danger` bg, `text.onAccent` fg. Used for Discard, Kill, Account Deletion.

**Sizes**: `sm` (32 height), `md` (44 height — meets `layout.minTouchTarget`), `lg` (56 height for primary CTAs).

**States**: default, pressed (color shifts to `*Pressed` token), disabled (50% opacity, no haptic), loading (spinner replaces label, button locked).

**Behavior**: every press triggers `haptics.selection` except `danger` which uses no haptic on initial press but `haptics.blockTriggered` on confirm.

**Key props**: `label`, `variant`, `size`, `iconLeft`, `iconRight`, `loading`, `disabled`, `onPress`.

---

## 8. SwipeDeckCard

**Purpose**: The Approval Queue card. Full-screen, gesture-driven. **Layout only is built in Rork** — gesture logic ships in Claude Code with `react-native-gesture-handler` + `react-native-reanimated`. Rork prompts render this as a static stacked-card preview with placeholder buttons; gesture wiring happens post-eject.

**Anatomy** (full-screen):
1. **Top safety banner** (only if any safety flag) — full-width SafetyFlag, 56pt tall, persistent.
2. **Video preview region** — 9:16 aspect, fills available space above the caption.
3. **Bottom sheet (non-modal, ~40% height)**:
   - Source label row.
   - Caption preview (full text, scrollable if long).
   - Platform-target badges (which platforms it's queued for).
   - MetricChip row showing predicted reach (Critic estimate).
4. **Action affordance bar** (Rork placeholder; replaced by gestures in Claude Code):
   - Reject (left, ghost danger).
   - Edit (center, secondary).
   - Approve & Post (right, primary).
   - Long-press target indicator below: "Hold to remix".

**Gesture behavior** *(deferred to Claude Code — Rork prompt should NOT attempt this)*:
- Right swipe (>40% width) → approve, `haptics.approve`, advances deck.
- Left swipe (>40% width) → reject, `haptics.reject`, 5-second undo toast.
- Tap → opens editor.
- Long-press 500ms + haptic tick → confirmation overlay "Remix this clip?" → confirm/cancel.

**Key props (for Rork mock)**: `clip`, `safetyFlags[]`, `onApprove`, `onReject`, `onEdit`, `onRemix` (all stubbed in Rork).

---

## Cross-component conventions

- **Touch targets**: every interactive element ≥ `layout.minTouchTarget` (44pt), even when visually smaller (use hit-slop).
- **Loading states**: every component that fetches data has a skeleton variant. No spinners except inside `ActionButton`.
- **Empty states**: every list-bearing screen shows an EmptyState (not a component above — built per-screen) with one-line copy + primary CTA.
- **Error states**: every component that can fail has an inline error variant — no global error modals.
- **Motion**: use `motion.duration.base` + `motion.easing.standard` as the default for everything. State transitions use `fast`. Page transitions use `slow`.
- **Voice in copy**: neutral analyst. No emojis unless system-meaningful (e.g. ✓ checkmarks). No "🚀", no "🎉", no "Crushing it".

---

## What this spec deliberately omits

- B-roll insertion controls (post-MVP per spec §3.6).
- Full thumbnail editor (frame-pick only in MVP).
- Campaign auto-submit UI (manual submission only in MVP).
- Studio multi-account workspace components.
- Browser-automation toggle UI (code path stubbed, UI disabled per spec §0).

These are explicit deferrals. Do not extend the component set in Rork beyond what's listed above.
