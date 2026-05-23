/**
 * MVC design tokens — typed mirror of design-tokens.json v0.1.0.
 * Single source of truth. Every style in the app reads from here.
 * Do not inline hex or raw numbers anywhere else.
 */

export const tokens = {
  meta: {
    product: "MVC",
    version: "0.1.0",
    mood: "dark-first, high-contrast, confident-saturated",
  },
  color: {
    bg: {
      base: "#0A0E1A",
      raised: "#10162A",
      surface: "#161D38",
      elevated: "#1D2645",
      overlay: "rgba(8, 11, 22, 0.72)",
    },
    border: {
      subtle: "#1F2747",
      default: "#2A3458",
      strong: "#3A4670",
      focus: "#5B7CFF",
    },
    text: {
      primary: "#F4F6FF",
      secondary: "#A8B0CC",
      tertiary: "#6B7494",
      disabled: "#444C6B",
      inverse: "#0A0E1A",
      onAccent: "#FFFFFF",
    },
    brand: {
      indigo: {
        50: "#EEF1FF",
        100: "#D7DEFF",
        200: "#A9B6FF",
        300: "#7C8EFF",
        400: "#5B72FF",
        500: "#4256F5",
        600: "#3441D6",
        700: "#2731A8",
        800: "#1C2480",
        900: "#141961",
      },
      teal: {
        50: "#E6FBFA",
        100: "#BFF3F0",
        200: "#85E6E0",
        300: "#4FD4CC",
        400: "#22BDB4",
        500: "#0FA39A",
        600: "#0A847C",
        700: "#08665F",
        800: "#054944",
        900: "#03332F",
      },
      green: {
        50: "#E6F9F0", 100: "#BFF3E0", 200: "#85E6C0", 300: "#4FD4A0",
        400: "#22BD80", 500: "#0FA360", 600: "#0A844C", 700: "#08663A",
        800: "#054928", 900: "#03331A",
      },
      amber: {
        50: "#FFF8E6", 100: "#FFEDBF", 200: "#FFDB85", 300: "#FFC94F",
        400: "#FFB822", 500: "#F5A30F", 600: "#D6840A", 700: "#A86808",
        800: "#7A4C05", 900: "#523203",
      },
      violet: {
        50: "#F3E6FF", 100: "#E0BFFF", 200: "#C785FF", 300: "#A94FFF",
        400: "#9122FF", 500: "#7A0FF5", 600: "#610AD6", 700: "#4C08A8",
        800: "#37057A", 900: "#240352",
      },
      pink: {
        50: "#FFE6F3", 100: "#FFBFE0", 200: "#FF85C7", 300: "#FF4FA9",
        400: "#FF2291", 500: "#F50F7A", 600: "#D60A61", 700: "#A8084C",
        800: "#7A0537", 900: "#520324",
      },
      red: {
        50: "#FFE6E6", 100: "#FFBFBF", 200: "#FF8585", 300: "#FF4F4F",
        400: "#FF2222", 500: "#F50F0F", 600: "#D60A0A", 700: "#A80808",
        800: "#7A0505", 900: "#520303",
      },
      cyan: {
        50: "#E6FAFF", 100: "#BFF3FF", 200: "#85E6FF", 300: "#4FD4FF",
        400: "#22BDFF", 500: "#0FA3F5", 600: "#0A84D6", 700: "#0866A8",
        800: "#05497A", 900: "#033352",
      },
    },
    accent: {
      primary: "#4256F5",
      primaryHover: "#5B72FF",
      primaryPressed: "#3441D6",
      secondary: "#0FA39A",
      secondaryHover: "#22BDB4",
      secondaryPressed: "#0A847C",
    },
    status: {
      success: "#1FCB8C",
      successBg: "#0E2A22",
      warning: "#F0B438",
      warningBg: "#2D2410",
      danger: "#F25555",
      dangerBg: "#2D1416",
      info: "#5B72FF",
      infoBg: "#141961",
    },
    semantic: {
      success: "#1FCB8C",
      error: "#F25555",
      safety: {
        general: { fg: "#A8B0CC", bg: "#1F2747", border: "#2A3458" },
        warn: { fg: "#F0B438", bg: "#2D2410", border: "#5C4515" },
        block: { fg: "#F25555", bg: "#2D1416", border: "#5C2326" },
        review: { fg: "#5B72FF", bg: "#141961", border: "#2731A8" },
      },
      metric: {
        positive: "#1FCB8C",
        positiveBg: "#0E2A22",
        negative: "#F25555",
        negativeBg: "#2D1416",
        neutral: "#A8B0CC",
        neutralBg: "#1F2747",
      },
      platform: {
        tiktok: "#FF2C55",
        youtube: "#FF3D3D",
        instagram: "#D946A0",
        facebook: "#3B6EF8",
        default: "#A8B0CC",
      },
      autonomy: {
        fullAuto: "#1FCB8C",
        approveEach: "#F0B438",
        suggestOnly: "#5B72FF",
      },
    },
  },
  spacing: {
    "0": 0,
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
    xxl: 48,
    xxxl: 64,
  },
  radius: {
    none: 0,
    sm: 8,
    md: 12,
    lg: 16,
    xl: 24,
    pill: 9999,
  },
  type: {
    fontFamily: {
      primary: "Inter_400Regular",
      primaryMedium: "Inter_500Medium",
      primarySemibold: "Inter_600SemiBold",
      primaryBold: "Inter_700Bold",
      mono: "JetBrains Mono",
    },
    weight: {
      regular: "400" as const,
      medium: "500" as const,
      semibold: "600" as const,
      bold: "700" as const,
    },
    scale: {
      display: { size: 32, lineHeight: 40, weight: "700" as const, letterSpacing: -0.5, family: "Inter_700Bold" },
      h1: { size: 24, lineHeight: 32, weight: "700" as const, letterSpacing: -0.3, family: "Inter_700Bold" },
      h2: { size: 20, lineHeight: 28, weight: "600" as const, letterSpacing: -0.2, family: "Inter_600SemiBold" },
      h3: { size: 17, lineHeight: 24, weight: "600" as const, letterSpacing: 0, family: "Inter_600SemiBold" },
      body: { size: 16, lineHeight: 24, weight: "400" as const, letterSpacing: 0, family: "Inter_400Regular" },
      bodyMedium: { size: 16, lineHeight: 24, weight: "500" as const, letterSpacing: 0, family: "Inter_500Medium" },
      bodySmall: { size: 14, lineHeight: 20, weight: "400" as const, letterSpacing: 0, family: "Inter_400Regular" },
      mono: { size: 12, lineHeight: 16, weight: "400" as const, letterSpacing: 0, family: "JetBrains Mono" },
      caption: { size: 12, lineHeight: 16, weight: "500" as const, letterSpacing: 0.2, family: "Inter_500Medium" },
      overline: { size: 11, lineHeight: 16, weight: "600" as const, letterSpacing: 1.0, family: "Inter_600SemiBold" },
    },
  },
  elevation: {
    "0": { shadowColor: "transparent", shadowOpacity: 0, shadowRadius: 0, shadowOffset: { width: 0, height: 0 }, elevation: 0 },
    "1": { shadowColor: "#000", shadowOpacity: 0.32, shadowRadius: 2, shadowOffset: { width: 0, height: 1 }, elevation: 2 },
    "2": { shadowColor: "#000", shadowOpacity: 0.4, shadowRadius: 12, shadowOffset: { width: 0, height: 4 }, elevation: 6 },
    "3": { shadowColor: "#000", shadowOpacity: 0.48, shadowRadius: 32, shadowOffset: { width: 0, height: 12 }, elevation: 12 },
    "4": { shadowColor: "#000", shadowOpacity: 0.56, shadowRadius: 64, shadowOffset: { width: 0, height: 24 }, elevation: 24 },
  },
  motion: {
    duration: {
      instant: 80,
      fast: 160,
      base: 240,
      slow: 360,
      deliberate: 520,
    },
    easing: {
      standard: [0.2, 0, 0, 1] as const,
      decelerate: [0, 0, 0, 1] as const,
      accelerate: [0.3, 0, 1, 1] as const,
      emphasized: [0.2, 0, 0, 1.2] as const,
    },
  },
  icon: {
    library: "lucide",
    size: { xs: 14, sm: 16, md: 20, lg: 24, xl: 32 },
    stroke: { thin: 1.25, default: 1.5, bold: 2.0 },
  },
  layout: {
    screenPadding: 16,
    sectionGap: 24,
    tabBarHeight: 64,
    headerHeight: 56,
    minTouchTarget: 44,
    maxContentWidth: 720,
    feedCardGap: 12,
    cardRadius: 16,
  },
  haptics: {
    selection: "light" as const,
    approve: "success" as const,
    reject: "warning" as const,
    remixConfirm: "medium" as const,
    heavy: "medium" as const,
    blockTriggered: "error" as const,
  },
} as const;

export type Tokens = typeof tokens;
export default tokens;


export const font = tokens.type;
export const layout = tokens.radius;
