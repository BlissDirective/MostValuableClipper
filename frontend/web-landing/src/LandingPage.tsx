import React, { useEffect, useState } from 'react';
import { ArrowRight, Sparkles, Wand2, Share2, BarChart3, Zap, Layers } from 'lucide-react';
import Threads from './components/Backgrounds/Threads';
import StarBorder from './components/Animations/StarBorder';
import SpotlightCard from './components/Components/SpotlightCard';
import AnimatedContent from './components/Animations/AnimatedContent';

const API_URL = import.meta.env.VITE_API_URL || 'https://mvc-backend.fly.dev';

const frames = [
  {
    id: 'hero',
    eyebrow: 'AI-Powered Video Clipping',
    title: 'Turn Long Videos Into\\nViral Moments',
    subtitle: 'BlissClip uses intelligent AI agents to analyze, remix, and publish your best content across every platform — automatically.',
    cta: 'Launch App',
    ctaLink: `${API_URL}/app`,
  },
  {
    id: 'analyze',
    eyebrow: 'Deep Analysis',
    title: 'Find The\\nGolden Seconds',
    subtitle: 'Our AI scans your content for engagement peaks, emotional hooks, and trending formats — then extracts the clips with highest viral potential.',
    features: ['Hook detection', 'Sentiment scoring', 'Trend matching'],
    accent: '#818cf8',
  },
  {
    id: 'remix',
    eyebrow: 'Smart Remixing',
    title: 'Auto-Edit\\nLike A Pro',
    subtitle: 'Captions, transitions, music sync, aspect ratios — BlissClip agents handle the entire post-production pipeline in seconds, not hours.',
    features: ['Auto-captions', 'Beat-matched cuts', 'Multi-format export'],
    accent: '#34d399',
  },
  {
    id: 'swarm',
    eyebrow: 'Agent Swarm',
    title: 'One Clip.\\nTwenty Posts.',
    subtitle: 'Deploy a swarm of specialized agents — each one optimizing for a different platform, audience, and content style. Scale without the team.',
    features: ['Platform-native formats', 'A/B title variants', 'Schedule optimization'],
    accent: '#f472b6',
  },
  {
    id: 'earnings',
    eyebrow: 'Monetization',
    title: 'Track What\\nPays You',
    subtitle: 'Unified earnings dashboard across YouTube, TikTok, Instagram, and more. See which clips drive revenue and double down.',
    features: ['Cross-platform revenue', 'Clip-level attribution', 'Payout scheduling'],
    accent: '#fbbf24',
  },
  {
    id: 'cta',
    eyebrow: 'Start Creating',
    title: 'Your Content\\nDeserves Bliss.',
    subtitle: 'Join creators who let AI handle the grind — so they can focus on what they do best.',
    cta: 'Get Started Free',
    ctaLink: `${API_URL}/app`,
  },
];

const LandingPage: React.FC = () => {
  const [activeFrame, setActiveFrame] = useState(0);
  const [scrollProgress, setScrollProgress] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const total = document.documentElement.scrollHeight - window.innerHeight;
      const progress = window.scrollY / total;
      setScrollProgress(progress);

      const frameHeight = window.innerHeight;
      const current = Math.min(
        Math.floor(window.scrollY / frameHeight),
        frames.length - 1
      );
      setActiveFrame(current);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="relative bg-black min-h-screen">
      {/* Fixed Threads Background */}
      <div className="fixed inset-0 z-0">
        <Threads
          color={[0.5, 0.35, 1]}
          amplitude={1.2}
          distance={0.2}
          enableMouseInteraction={true}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black/30 via-transparent to-black/80" />
      </div>

      {/* Progress Bar */}
      <div className="fixed top-0 left-0 right-0 h-1 z-50">
        <div
          className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 transition-all duration-150"
          style={{ width: `${scrollProgress * 100}%` }}
        />
      </div>

      {/* Frame Navigation Dots */}
      <div className="fixed right-6 top-1/2 -translate-y-1/2 z-50 flex flex-col gap-3">
        {frames.map((_, i) => (
          <button
            key={i}
            onClick={() => {
              window.scrollTo({
                top: i * window.innerHeight,
                behavior: 'smooth',
              });
            }}
            className={`w-2 h-2 rounded-full transition-all duration-300 ${
              i === activeFrame
                ? 'bg-white scale-125'
                : 'bg-white/30 hover:bg-white/50'
            }`}
          />
        ))}
      </div>

      {/* Cinematic Frames */}
      <main className="relative z-10">
        {frames.map((frame, index) => (
          <section
            key={frame.id}
            className="min-h-screen flex items-center justify-center px-6 md:px-12 lg:px-24 relative"
          >
            {/* Frame Border Effect */}
            <div className="absolute inset-8 md:inset-16 border border-white/5 rounded-3xl pointer-events-none" />
            <div
              className="absolute inset-8 md:inset-16 rounded-3xl pointer-events-none opacity-0 transition-opacity duration-1000"
              style={{
                opacity: activeFrame === index ? 0.5 : 0,
                boxShadow: frame.accent
                  ? `inset 0 0 80px ${frame.accent}15, 0 0 40px ${frame.accent}10`
                  : 'inset 0 0 80px rgba(129, 140, 248, 0.1), 0 0 40px rgba(129, 140, 248, 0.05)',
              }}
            />

            <div className="max-w-6xl w-full grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-20 items-center">
              {/* Text Content */}
              <AnimatedContent
                distance={60}
                direction="vertical"
                reverse={index % 2 === 1}
                duration={1}
                delay={0.1}
                className="space-y-6"
              >
                <span
                  className="inline-block text-sm font-medium tracking-widest uppercase"
                  style={{ color: frame.accent || '#818cf8' }}
                >
                  {frame.eyebrow}
                </span>

                <h2 className="text-5xl md:text-6xl lg:text-7xl font-bold text-white leading-[1.1] whitespace-pre-line">
                  {frame.title}
                </h2>

                <p className="text-lg md:text-xl text-gray-400 leading-relaxed max-w-lg">
                  {frame.subtitle}
                </p>

                {frame.cta && (
                  <a
                    href={frame.ctaLink}
                    className="inline-flex items-center gap-3 bg-white text-black px-8 py-4 rounded-full font-semibold text-lg hover:bg-gray-200 transition-colors group"
                  >
                    {frame.cta}
                    <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                  </a>
                )}

                {frame.features && (
                  <div className="flex flex-wrap gap-3 pt-4">
                    {frame.features.map((feat) => (
                      <span
                        key={feat}
                        className="px-4 py-2 rounded-full text-sm font-medium border"
                        style={{
                          borderColor: `${frame.accent}40`,
                          color: frame.accent,
                          backgroundColor: `${frame.accent}10`,
                        }}
                      >
                        {feat}
                      </span>
                    ))}
                  </div>
                )}
              </AnimatedContent>

              {/* Visual Card */}
              <AnimatedContent
                distance={80}
                direction="vertical"
                reverse={index % 2 === 0}
                duration={1.2}
                delay={0.3}
                className="flex justify-center"
              >
                <StarBorder
                  as="div"
                  color={frame.accent || '#818cf8'}
                  speed="8s"
                  thickness={2}
                  className="w-full max-w-md"
                >
                  <SpotlightCard
                    className="p-8 md:p-10"
                    spotlightColor={`rgba(${hexToRgb(frame.accent || '#818cf8')}, 0.3)`}
                  >
                    <FrameVisual frameId={frame.id} accent={frame.accent} />
                  </SpotlightCard>
                </StarBorder>
              </AnimatedContent>
            </div>

            {/* Scroll Indicator */}
            {index === 0 && (
              <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 animate-bounce">
                <span className="text-xs text-gray-500 uppercase tracking-widest">Scroll</span>
                <div className="w-px h-8 bg-gradient-to-b from-gray-500 to-transparent" />
              </div>
            )}
          </section>
        ))}
      </main>

      {/* Footer */}
      <footer className="relative z-10 py-12 px-6 border-t border-white/5">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-3">
            <Sparkles className="w-6 h-6 text-indigo-400" />
            <span className="text-xl font-bold text-white">BlissClip</span>
          </div>
          <div className="flex gap-8 text-sm text-gray-500">
            <a href={`${API_URL}/privacy`} className="hover:text-white transition-colors">Privacy</a>
            <a href={`${API_URL}/terms`} className="hover:text-white transition-colors">Terms</a>
            <a href={`${API_URL}/dmca`} className="hover:text-white transition-colors">DMCA</a>
          </div>
          <p className="text-sm text-gray-600">© 2026 BlissClip. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
};

/* Visual elements for each frame */
function FrameVisual({ frameId, accent = '#818cf8' }: { frameId: string; accent?: string }) {
  switch (frameId) {
    case 'hero':
      return (
        <div className="space-y-4">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-bold text-white">BlissClip</span>
          </div>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-2 rounded-full bg-gradient-to-r from-white/20 to-transparent"
                style={{ width: `${100 - i * 15}%` }}
              />
            ))}
          </div>
          <p className="text-sm text-gray-400 pt-2">AI-powered video intelligence platform</p>
        </div>
      );
    case 'analyze':
      return (
        <div className="space-y-4">
          <Wand2 className="w-10 h-10 mb-4" style={{ color: accent }} />
          <div className="grid grid-cols-3 gap-2">
            {[80, 95, 60, 90, 75, 85].map((score, i) => (
              <div
                key={i}
                className="h-16 rounded-lg flex items-end p-2"
                style={{ backgroundColor: `${accent}15` }}
              >
                <div
                  className="w-full rounded transition-all duration-1000"
                  style={{
                    height: `${score}%`,
                    backgroundColor: accent,
                    opacity: 0.6,
                  }}
                />
              </div>
            ))}
          </div>
          <p className="text-sm text-gray-400">Engagement scoring in real-time</p>
        </div>
      );
    case 'remix':
      return (
        <div className="space-y-4">
          <Zap className="w-10 h-10 mb-4" style={{ color: accent }} />
          <div className="flex gap-2">
            {['9:16', '1:1', '16:9'].map((ratio) => (
              <div
                key={ratio}
                className="flex-1 rounded-lg border border-white/10 p-3 text-center"
              >
                <div
                  className="mx-auto mb-2 rounded bg-white/10"
                  style={{
                    width: ratio === '1:1' ? '32px' : ratio === '9:16' ? '18px' : '32px',
                    height: ratio === '1:1' ? '32px' : ratio === '9:16' ? '32px' : '18px',
                  }}
                />
                <span className="text-xs text-gray-400">{ratio}</span>
              </div>
            ))}
          </div>
          <p className="text-sm text-gray-400">Auto-formatted for every platform</p>
        </div>
      );
    case 'swarm':
      return (
        <div className="space-y-4">
          <Layers className="w-10 h-10 mb-4" style={{ color: accent }} />
          <div className="relative h-24">
            {[0, 1, 2, 3].map((i) => (
              <div
                key={i}
                className="absolute w-10 h-10 rounded-full border-2 flex items-center justify-center text-xs font-bold"
                style={{
                  borderColor: accent,
                  backgroundColor: 'rgba(0,0,0,0.6)',
                  left: `${i * 25}%`,
                  top: `${Math.sin(i) * 20 + 20}px`,
                  color: accent,
                }}
              >
                {['YT', 'TT', 'IG', 'X'][i]}
              </div>
            ))}
          </div>
          <p className="text-sm text-gray-400">Multi-platform publishing swarm</p>
        </div>
      );
    case 'earnings':
      return (
        <div className="space-y-4">
          <BarChart3 className="w-10 h-10 mb-4" style={{ color: accent }} />
          <div className="space-y-2">
            {[
              { label: 'YouTube', value: 65 },
              { label: 'TikTok', value: 45 },
              { label: 'Instagram', value: 30 },
            ].map((item) => (
              <div key={item.label} className="flex items-center gap-3">
                <span className="text-xs text-gray-400 w-16">{item.label}</span>
                <div className="flex-1 h-2 rounded-full bg-white/10 overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${item.value}%`,
                      backgroundColor: accent,
                      opacity: 0.7,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
          <p className="text-sm text-gray-400">Revenue tracking across platforms</p>
        </div>
      );
    case 'cta':
      return (
        <div className="space-y-4 text-center">
          <Share2 className="w-10 h-10 mx-auto mb-4" style={{ color: accent }} />
          <div className="py-8">
            <p className="text-3xl font-bold text-white mb-2">Free to start</p>
            <p className="text-gray-400">No credit card required</p>
          </div>
        </div>
      );
    default:
      return null;
  }
}

function hexToRgb(hex: string): string {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!result) return '129, 140, 248';
  const r = parseInt(result[1], 16);
  const g = parseInt(result[2], 16);
  const b = parseInt(result[3], 16);
  return `${r}, ${g}, ${b}`;
}

export default LandingPage;
