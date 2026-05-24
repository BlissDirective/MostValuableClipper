import React, { useEffect, useRef, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  Animated,
  Pressable,
  ScrollView,
  useWindowDimensions,
  Platform,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Zap, Sparkles, Share2, Bot, Film, ChevronRight, Star } from "lucide-react-native";
import { useRouter } from "expo-router";

/* ─── Concept Selector ─── */
export default function LandingPage() {
  const [activeConcept, setActiveConcept] = useState<1 | 2 | 3>(1);
  const { width } = useWindowDimensions();
  const isDesktop = Platform.OS === "web" && width >= 1024;

  return (
    <ScrollView style={styles.root} contentContainerStyle={styles.rootContent}>
      {/* Concept Switcher */}
      <View style={[styles.switcher, isDesktop && styles.switcherDesktop]}>
        {[1, 2, 3].map((n) => (
          <Pressable
            key={n}
            onPress={() => setActiveConcept(n as 1 | 2 | 3)}
            style={[
              styles.switcherBtn,
              activeConcept === n && styles.switcherBtnActive,
            ]}
          >
            <Text style={[styles.switcherText, activeConcept === n && styles.switcherTextActive]}>
              Concept {n}
            </Text>
          </Pressable>
        ))}
      </View>

      {activeConcept === 1 && <ConceptOne />}
      {activeConcept === 2 && <ConceptTwo />}
      {activeConcept === 3 && <ConceptThree />}
    </ScrollView>
  );
}

/* ═══════════════════════════════════════════════════════════════
   CONCEPT 1 — "NEON THREADS"
   React Bits: Threads background + metallic titles + star cards
   ═══════════════════════════════════════════════════════════════ */
function ConceptOne() {
  const shimmer = useRef(new Animated.Value(0)).current;
  const router = useRouter();

  useEffect(() => {
    const loop = Animated.loop(
      Animated.timing(shimmer, {
        toValue: 1,
        duration: 3000,
        useNativeDriver: false,
      })
    );
    loop.start();
    return () => loop.stop();
  }, []);

  const translateX = shimmer.interpolate({
    inputRange: [0, 1],
    outputRange: ["-100%", "100%"],
  });

  return (
    <View style={styles.conceptRoot}>
      {/* Threads Background */}
      <ThreadsBackground />

      {/* Metallic Title */}
      <View style={styles.titleBlock}>
        <View style={styles.metallicWrapper}>
          <Text style={[styles.metallicBase, styles.metallicLarge]}>BlissClip</Text>
          <Animated.View
            style={[
              styles.shimmerOverlay,
              { transform: [{ translateX }] },
            ]}
          >
            <LinearGradient
              colors={["transparent", "rgba(255,255,255,0.4)", "transparent"]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={StyleSheet.absoluteFill}
            />
          </Animated.View>
        </View>
        <Text style={styles.subtitle}>AI-Powered Video Clipping</Text>
      </View>

      {/* Star Border Cards */}
      <View style={styles.cardsRow}>
        <StarCard
          icon={<Sparkles size={28} color="#5B72FF" />}
          title="AI Analysis"
          body="Upload any video. Our AI identifies hooks, optimal cut points, and viral potential."
        />
        <StarCard
          icon={<Film size={28} color="#22BDB4" />}
          title="Auto-Remix"
          body="Generate multiple vertical variants with fresh captions and trending music."
        />
        <StarCard
          icon={<Share2 size={28} color="#9122FF" />}
          title="One-Click Post"
          body="Connect your social accounts and post to TikTok, Instagram, YouTube simultaneously."
        />
      </View>

      {/* CTA */}
      <Pressable style={styles.ctaButton} onPress={() => router.push("/(auth)/welcome")}>
        <Text style={styles.ctaText}>Get Started</Text>
        <ChevronRight size={20} color="#fff" />
      </Pressable>
    </View>
  );
}

/* ═══════════════════════════════════════════════════════════════
   CONCEPT 2 — "LIQUID AURORA"
   React Bits: Aurora mesh gradient + chrome titles + pulse cards
   ═══════════════════════════════════════════════════════════════ */
function ConceptTwo() {
  const pulse1 = useRef(new Animated.Value(1)).current;
  const pulse2 = useRef(new Animated.Value(1)).current;
  const router = useRouter();

  useEffect(() => {
    const a1 = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse1, { toValue: 1.15, duration: 2000, useNativeDriver: true }),
        Animated.timing(pulse1, { toValue: 1, duration: 2000, useNativeDriver: true }),
      ])
    );
    const a2 = Animated.loop(
      Animated.sequence([
        Animated.delay(1000),
        Animated.timing(pulse2, { toValue: 1.12, duration: 2000, useNativeDriver: true }),
        Animated.timing(pulse2, { toValue: 1, duration: 2000, useNativeDriver: true }),
      ])
    );
    a1.start();
    a2.start();
    return () => {
      a1.stop();
      a2.stop();
    };
  }, []);

  return (
    <View style={[styles.conceptRoot, { backgroundColor: "#050810" }]}>
      {/* Aurora Mesh Background */}
      <AuroraMesh />

      {/* Chrome Title */}
      <View style={styles.titleBlock}>
        <LinearGradient
          colors={["#FF4FD4", "#5B72FF", "#22BDB4", "#FFB822"]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.chromeGradient}
        >
          <Text style={[styles.chromeText, styles.metallicLarge]}>BlissClip</Text>
        </LinearGradient>
        <Text style={[styles.subtitle, { color: "#A8B0CC" }]}>
          Turn long videos into viral clips
        </Text>
      </View>

      {/* Pulse Glow Cards */}
      <View style={styles.cardsRow}>
        <PulseCard
          pulse={pulse1}
          icon={<Zap size={28} color="#FFB822" />}
          title="Swarm Agents"
          body="Deploy multiple AI agents in parallel to test hooks, captions, and thumbnails."
        />
        <PulseCard
          pulse={pulse2}
          icon={<Bot size={28} color="#22BDB4" />}
          title="Smart Scheduling"
          body="Auto-post at optimal times for each platform. Set it and forget it."
        />
        <PulseCard
          pulse={pulse1}
          icon={<Film size={28} color="#FF4FD4" />}
          title="Earnings Dashboard"
          body="Track views, watch time, and estimated revenue across all platforms."
        />
      </View>

      {/* CTA */}
      <Pressable style={[styles.ctaButton, { backgroundColor: "#FF4FD4" }]} onPress={() => router.push("/(auth)/welcome")}>
        <Text style={styles.ctaText}>Start Creating</Text>
        <ChevronRight size={20} color="#fff" />
      </Pressable>
    </View>
  );
}

/* ═══════════════════════════════════════════════════════════════
   CONCEPT 3 — "VOID RINGS"
   React Bits: Orbital rings + glitch titles + holographic cards
   ═══════════════════════════════════════════════════════════════ */
function ConceptThree() {
  const rotation = useRef(new Animated.Value(0)).current;
  const glitch = useRef(new Animated.Value(0)).current;
  const router = useRouter();

  useEffect(() => {
    const spin = Animated.loop(
      Animated.timing(rotation, {
        toValue: 1,
        duration: 20000,
        useNativeDriver: true,
      })
    );
    const glitchLoop = Animated.loop(
      Animated.sequence([
        Animated.delay(3000),
        Animated.timing(glitch, { toValue: 1, duration: 150, useNativeDriver: true }),
        Animated.timing(glitch, { toValue: 0, duration: 50, useNativeDriver: true }),
        Animated.timing(glitch, { toValue: 1, duration: 100, useNativeDriver: true }),
        Animated.timing(glitch, { toValue: 0, duration: 50, useNativeDriver: true }),
      ])
    );
    spin.start();
    glitchLoop.start();
    return () => {
      spin.stop();
      glitchLoop.stop();
    };
  }, []);

  const spinDeg = rotation.interpolate({
    inputRange: [0, 1],
    outputRange: ["0deg", "360deg"],
  });

  const glitchX = glitch.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: [0, -3, 3],
  });

  return (
    <View style={[styles.conceptRoot, { backgroundColor: "#020408" }]}>
      {/* Orbital Rings */}
      <OrbitalRings spinDeg={spinDeg} />

      {/* Glitch Title */}
      <View style={styles.titleBlock}>
        <Animated.View style={{ transform: [{ translateX: glitchX }] }}>
          <Text style={[styles.glitchBase, styles.metallicLarge]}>BLISSCLIP</Text>
        </Animated.View>
        <Text style={styles.glitchShadow}>BLISSCLIP</Text>
        <Text style={[styles.subtitle, { color: "#6B7494" }]}>
          Autonomous video clipping for creators
        </Text>
      </View>

      {/* Holographic Cards */}
      <View style={styles.cardsRow}>
        <HoloCard
          icon={<Sparkles size={28} color="#00F0FF" />}
          title="Auto-Clip"
          body="AI finds the best moments and cuts vertical clips automatically."
          tint="#00F0FF"
        />
        <HoloCard
          icon={<Share2 size={28} color="#FF0055" />}
          title="Multi-Post"
          body="Simultaneous posting to all major platforms with optimized captions."
          tint="#FF0055"
        />
        <HoloCard
          icon={<Star size={28} color="#FFD700" />}
          title="Analytics"
          body="Real-time metrics across platforms. Track what works and double down."
          tint="#FFD700"
        />
      </View>

      {/* CTA */}
      <Pressable
        style={[styles.ctaButton, { backgroundColor: "transparent", borderWidth: 2, borderColor: "#00F0FF" }]}
        onPress={() => router.push("/(auth)/welcome")}
      >
        <Text style={[styles.ctaText, { color: "#00F0FF" }]}>Enter the App</Text>
        <ChevronRight size={20} color="#00F0FF" />
      </Pressable>
    </View>
  );
}

/* ─── Sub-components ─── */

function ThreadsBackground() {
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      <LinearGradient
        colors={["#0A0E1A", "#10162A", "#1D2645", "#0A0E1A"]}
        locations={[0, 0.3, 0.7, 1]}
        style={StyleSheet.absoluteFill}
      />
      {/* Animated thread lines */}
      {Array.from({ length: 6 }).map((_, i) => (
        <AnimatedThread key={i} index={i} />
      ))}
    </View>
  );
}

function AnimatedThread({ index }: { index: number }) {
  const anim = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    const loop = Animated.loop(
      Animated.timing(anim, {
        toValue: 1,
        duration: 4000 + index * 800,
        useNativeDriver: true,
      })
    );
    loop.start();
    return () => loop.stop();
  }, []);

  const opacity = anim.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: [0.1, 0.3, 0.1],
  });

  const top = `${10 + index * 15}%`;
  const rotate = `${-20 + index * 8}deg`;

  return (
    <Animated.View
      style={[
        styles.thread,
        {
          top,
          transform: [{ rotate }],
          opacity,
          backgroundColor: index % 2 === 0 ? "#5B7CFF" : "#22BDB4",
        },
      ]}
    />
  );
}

function AuroraMesh() {
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      <LinearGradient
        colors={["#050810", "#0a0a1a", "#120820", "#050810"]}
        style={StyleSheet.absoluteFill}
      />
      {/* Aurora blobs */}
      <View style={[styles.auroraBlob, { top: "10%", left: "-10%", backgroundColor: "rgba(91,114,255,0.15)" }]} />
      <View style={[styles.auroraBlob, { top: "40%", right: "-15%", backgroundColor: "rgba(255,79,212,0.12)" }]} />
      <View style={[styles.auroraBlob, { bottom: "20%", left: "20%", backgroundColor: "rgba(34,189,180,0.1)" }]} />
    </View>
  );
}

function OrbitalRings({ spinDeg }: { spinDeg: Animated.AnimatedInterpolation<string> }) {
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      <View style={styles.orbitalCenter}>
        <Animated.View style={[styles.orbitalRing, { transform: [{ rotate: spinDeg }] }]}>
          <View style={[styles.orbitalDot, { top: -4, left: "50%" }]} />
        </Animated.View>
        <Animated.View
          style={[
            styles.orbitalRing,
            {
              width: 200,
              height: 200,
              transform: [{ rotate: Animated.multiply(spinDeg, -1.5) }],
            },
          ]}
        >
          <View style={[styles.orbitalDot, { bottom: -4, left: "30%", backgroundColor: "#FF0055" }]} />
        </Animated.View>
        <Animated.View
          style={[
            styles.orbitalRing,
            {
              width: 280,
              height: 280,
              transform: [{ rotate: Animated.multiply(spinDeg, 0.8) }],
            },
          ]}
        >
          <View style={[styles.orbitalDot, { top: "60%", right: -4, backgroundColor: "#00F0FF" }]} />
        </Animated.View>
      </View>
    </View>
  );
}

function StarCard({ icon, title, body }: { icon: React.ReactNode; title: string; body: string }) {
  const [active, setActive] = useState(false);
  const scale = useRef(new Animated.Value(1)).current;

  const handlePressIn = () => {
    setActive(true);
    Animated.spring(scale, { toValue: 0.96, useNativeDriver: true }).start();
  };
  const handlePressOut = () => {
    setActive(false);
    Animated.spring(scale, { toValue: 1, useNativeDriver: true }).start();
  };

  return (
    <Pressable onPressIn={handlePressIn} onPressOut={handlePressOut}>
      <Animated.View style={[styles.starCard, { transform: [{ scale }] }]}>
        {/* Star border effect */}
        <View style={[styles.starBorder, active && styles.starBorderActive]}>
          {Array.from({ length: 20 }).map((_, i) => (
            <View
              key={i}
              style={[
                styles.starSegment,
                {
                  transform: [{ rotate: `${i * 18}deg` }],
                  opacity: active ? 1 : 0.4,
                },
              ]}
            />
          ))}
        </View>
        <View style={styles.starCardInner}>
          <View style={styles.starIcon}>{icon}</View>
          <Text style={styles.starTitle}>{title}</Text>
          <Text style={styles.starBody}>{body}</Text>
        </View>
      </Animated.View>
    </Pressable>
  );
}

function PulseCard({
  pulse,
  icon,
  title,
  body,
}: {
  pulse: Animated.Value;
  icon: React.ReactNode;
  title: string;
  body: string;
}) {
  return (
    <View style={styles.pulseCardWrapper}>
      <Animated.View
        style={[
          styles.pulseGlow,
          {
            transform: [{ scale: pulse }],
            opacity: pulse.interpolate({
              inputRange: [1, 1.15],
              outputRange: [0.3, 0],
            }),
          },
        ]}
      />
      <View style={styles.pulseCard}>
        <View style={styles.pulseIcon}>{icon}</View>
        <Text style={styles.pulseTitle}>{title}</Text>
        <Text style={styles.pulseBody}>{body}</Text>
      </View>
    </View>
  );
}

function HoloCard({
  icon,
  title,
  body,
  tint,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
  tint: string;
}) {
  const shimmer = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    const loop = Animated.loop(
      Animated.timing(shimmer, { toValue: 1, duration: 2500, useNativeDriver: false })
    );
    loop.start();
    return () => loop.stop();
  }, []);

  const shimmerX = shimmer.interpolate({
    inputRange: [0, 1],
    outputRange: ["-100%", "100%"],
  });

  return (
    <View style={[styles.holoCard, { borderColor: `${tint}40` }]}>
      <Animated.View style={[styles.holoShimmer, { transform: [{ translateX: shimmerX }] }]}>
        <LinearGradient
          colors={["transparent", `${tint}30`, "transparent"]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 0 }}
          style={StyleSheet.absoluteFill}
        />
      </Animated.View>
      <View style={styles.holoIcon}>{icon}</View>
      <Text style={[styles.holoTitle, { color: tint }]}>{title}</Text>
      <Text style={styles.holoBody}>{body}</Text>
    </View>
  );
}

/* ─── Styles ─── */
const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#0A0E1A" },
  rootContent: { flexGrow: 1 },

  // Switcher
  switcher: {
    flexDirection: "row",
    justifyContent: "center",
    gap: 12,
    paddingVertical: 16,
    backgroundColor: "#0A0E1A",
    zIndex: 10,
  },
  switcherDesktop: {
    position: "absolute",
    top: 24,
    right: 24,
    paddingVertical: 0,
  },
  switcherBtn: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: "#161D38",
    borderWidth: 1,
    borderColor: "#1F2747",
  },
  switcherBtnActive: {
    backgroundColor: "#5B7CFF",
    borderColor: "#5B7CFF",
  },
  switcherText: { color: "#A8B0CC", fontSize: 14, fontWeight: "600" },
  switcherTextActive: { color: "#fff" },

  // Concept root
  conceptRoot: {
    flex: 1,
    minHeight: 800,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 24,
    paddingVertical: 48,
    gap: 32,
    overflow: "hidden",
  },

  // Title block
  titleBlock: { alignItems: "center", gap: 8, zIndex: 2 },
  metallicWrapper: { position: "relative", overflow: "hidden" },
  metallicBase: {
    color: "#F4F6FF",
    fontWeight: "900",
    letterSpacing: -1,
    textShadowColor: "rgba(91,124,255,0.5)",
    textShadowOffset: { width: 0, height: 4 },
    textShadowRadius: 20,
  },
  metallicLarge: { fontSize: 64 },
  shimmerOverlay: {
    ...StyleSheet.absoluteFillObject,
    width: "50%",
  },
  subtitle: {
    color: "#6B7494",
    fontSize: 18,
    fontWeight: "500",
    letterSpacing: 0.5,
  },

  chromeGradient: {
    paddingHorizontal: 8,
    borderRadius: 8,
  },
  chromeText: {
    backgroundColor: "transparent",
    color: "#fff",
  },

  glitchBase: {
    color: "#F4F6FF",
    fontWeight: "900",
    letterSpacing: 4,
  },
  glitchShadow: {
    position: "absolute",
    color: "#FF0055",
    opacity: 0.3,
    fontSize: 64,
    fontWeight: "900",
    letterSpacing: 4,
    top: 4,
    left: 4,
  },

  // Cards
  cardsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "center",
    gap: 16,
    zIndex: 2,
    maxWidth: 1200,
  },

  // Star Card
  starCard: {
    width: 280,
    minHeight: 180,
    position: "relative",
    alignItems: "center",
    justifyContent: "center",
  },
  starBorder: {
    ...StyleSheet.absoluteFillObject,
    alignItems: "center",
    justifyContent: "center",
  },
  starBorderActive: {},
  starSegment: {
    position: "absolute",
    width: 4,
    height: 8,
    backgroundColor: "#5B7CFF",
    borderRadius: 2,
    top: 0,
  },
  starCardInner: {
    backgroundColor: "#10162A",
    borderRadius: 16,
    padding: 24,
    alignItems: "center",
    gap: 12,
    borderWidth: 1,
    borderColor: "#1F2747",
    width: "92%",
    height: "92%",
  },
  starIcon: {
    width: 48,
    height: 48,
    borderRadius: 12,
    backgroundColor: "#1D2645",
    alignItems: "center",
    justifyContent: "center",
  },
  starTitle: {
    color: "#F4F6FF",
    fontSize: 18,
    fontWeight: "700",
  },
  starBody: {
    color: "#A8B0CC",
    fontSize: 14,
    textAlign: "center",
    lineHeight: 20,
  },

  // Pulse Card
  pulseCardWrapper: {
    width: 280,
    minHeight: 180,
    alignItems: "center",
    justifyContent: "center",
    position: "relative",
  },
  pulseGlow: {
    position: "absolute",
    width: 260,
    height: 170,
    borderRadius: 20,
    backgroundColor: "#5B72FF",
  },
  pulseCard: {
    backgroundColor: "#10162A",
    borderRadius: 16,
    padding: 24,
    alignItems: "center",
    gap: 12,
    borderWidth: 1,
    borderColor: "#1F2747",
    width: "100%",
    height: "100%",
    zIndex: 2,
  },
  pulseIcon: {
    width: 48,
    height: 48,
    borderRadius: 12,
    backgroundColor: "#1D2645",
    alignItems: "center",
    justifyContent: "center",
  },
  pulseTitle: {
    color: "#F4F6FF",
    fontSize: 18,
    fontWeight: "700",
  },
  pulseBody: {
    color: "#A8B0CC",
    fontSize: 14,
    textAlign: "center",
    lineHeight: 20,
  },

  // Holographic Card
  holoCard: {
    width: 280,
    minHeight: 180,
    backgroundColor: "#0a0a12",
    borderRadius: 16,
    padding: 24,
    alignItems: "center",
    gap: 12,
    borderWidth: 1,
    overflow: "hidden",
    position: "relative",
  },
  holoShimmer: {
    position: "absolute",
    top: 0,
    left: 0,
    width: "100%",
    height: "100%",
    zIndex: 1,
  },
  holoIcon: {
    width: 48,
    height: 48,
    borderRadius: 12,
    backgroundColor: "#161D38",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 2,
  },
  holoTitle: {
    fontSize: 18,
    fontWeight: "700",
    zIndex: 2,
  },
  holoBody: {
    color: "#A8B0CC",
    fontSize: 14,
    textAlign: "center",
    lineHeight: 20,
    zIndex: 2,
  },

  // Threads
  thread: {
    position: "absolute",
    width: "120%",
    height: 1,
    left: "-10%",
    opacity: 0.2,
  },

  // Aurora
  auroraBlob: {
    position: "absolute",
    width: 300,
    height: 300,
    borderRadius: 150,
    filter: "blur(80px)",
  },

  // Orbital
  orbitalCenter: {
    position: "absolute",
    top: "30%",
    left: "50%",
    marginLeft: -140,
    width: 280,
    height: 280,
    alignItems: "center",
    justifyContent: "center",
  },
  orbitalRing: {
    position: "absolute",
    width: 140,
    height: 140,
    borderRadius: 70,
    borderWidth: 1,
    borderColor: "rgba(91,114,255,0.2)",
  },
  orbitalDot: {
    position: "absolute",
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#5B7CFF",
    shadowColor: "#5B7CFF",
    shadowRadius: 8,
    shadowOpacity: 0.8,
  },

  // CTA
  ctaButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: "#5B7CFF",
    paddingHorizontal: 32,
    paddingVertical: 16,
    borderRadius: 12,
    zIndex: 2,
  },
  ctaText: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "700",
  },
});
