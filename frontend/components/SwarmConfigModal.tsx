import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Modal,
  Pressable,
  Switch,
  Alert,
  ActivityIndicator,
  TextInput,
} from 'react-native';
import {
  X,
  Bot,
  ChevronDown,
  ChevronUp,
  Zap,
  DollarSign,
  Settings,
} from 'lucide-react-native';
import { tokens } from '@/constants/tokens';

// ── Types ───────────────────────────────────────────────────────────

export type SwarmPoolType =
  | 'hook'
  | 'remix'
  | 'post'
  | 'ab_test'
  | 'music_match'
  | 'thumbnail'
  | 'safety'
  | 'hooks_analysis'
  | 'segment_analyze'
  | 'edit';

export interface SwarmExecutionConfig {
  poolType: SwarmPoolType;
  agentCount: number;
  strategyFilter: string[];
  customOptions?: Record<string, any>;
}

interface SwarmConfigModalProps {
  visible: boolean;
  onClose: () => void;
  onExecute: (config: SwarmExecutionConfig) => void;
  poolType: SwarmPoolType;
  // Optional overrides for batch/reuse contexts
  title?: string;
  description?: string;
  agentCountLabel?: string;
  // Pool metadata (optional with defaults)
  poolLabel?: string;
  poolColor?: string;
  poolDescription?: string;
  category?: string;
  // User's current allocation (optional with defaults)
  userAllocation?: number;
  tierLimit?: number;
  availableAgents?: number;
  // Strategy options
  availableStrategies?: string[];
  strategyLabels?: Record<string, string>;
  strategyDescriptions?: Record<string, string>;
  // Cost info (optional with defaults)
  costPerAgent?: number;
  // Loading state
  isExecuting?: boolean;
}

// ── Strategy config metadata ──────────────────────────────────────

const STRATEGY_META: Record<SwarmPoolType, { strategies: string[]; labels: Record<string, string>; descriptions: Record<string, string>; costPerAgent: number }> = {
  hook: {
    strategies: ['punchy', 'aspirational', 'controversial', 'story', 'question', 'how_to'],
    labels: {
      punchy: 'Punchy',
      aspirational: 'Aspirational',
      controversial: 'Controversial',
      story: 'Story-driven',
      question: 'Question Hook',
      how_to: 'How-To',
    },
    descriptions: {
      punchy: 'Short, impactful hooks that grab attention immediately',
      aspirational: 'Hooks that inspire and motivate the viewer',
      controversial: 'Hooks that challenge assumptions or spark debate',
      story: 'Narrative-driven hooks that draw viewers in',
      question: 'Curiosity-driven question-based hooks',
      how_to: 'Educational hooks promising value',
    },
    costPerAgent: 5,
  },
  remix: {
    strategies: ['energy_max', 'face_presence', 'hook_quality', 'music_sync', 'caption_heavy', 'fast_cuts'],
    labels: {
      energy_max: 'Energy Max',
      face_presence: 'Face Focus',
      hook_quality: 'Hook Quality',
      music_sync: 'Music Sync',
      caption_heavy: 'Caption Heavy',
      fast_cuts: 'Fast Cuts',
    },
    descriptions: {
      energy_max: 'Maximize visual energy and dynamic movement',
      face_presence: 'Optimize for face visibility and expressions',
      hook_quality: 'Prioritize strongest hook moments',
      music_sync: 'Sync edits tightly to music beats',
      caption_heavy: 'Heavy caption overlay strategy',
      fast_cuts: 'Rapid-fire cut transitions',
    },
    costPerAgent: 20,
  },
  post: {
    strategies: ['optimal_time', 'hashtag_max', 'engagement_bait', 'cross_post', 'story_announce'],
    labels: {
      optimal_time: 'Optimal Time',
      hashtag_max: 'Hashtag Max',
      engagement_bait: 'Engagement Bait',
      cross_post: 'Cross Post',
      story_announce: 'Story Announce',
    },
    descriptions: {
      optimal_time: 'Post at algorithmically optimal times',
      hashtag_max: 'Maximum hashtag reach strategy',
      engagement_bait: 'CTAs designed to maximize comments/shares',
      cross_post: 'Synchronized multi-platform posting',
      story_announce: 'Story announcement + feed post combo',
    },
    costPerAgent: 1,
  },
  ab_test: {
    strategies: ['engagement_winner', 'retention_winner', 'composite_winner', 'views_winner', 'watch_time_winner'],
    labels: {
      engagement_winner: 'Engagement Winner',
      retention_winner: 'Retention Winner',
      composite_winner: 'Composite Winner',
      views_winner: 'Views Winner',
      watch_time_winner: 'Watch Time Winner',
    },
    descriptions: {
      engagement_winner: 'Pick variant with highest likes+comments+shares',
      retention_winner: 'Pick variant with best retention curve',
      composite_winner: 'Balanced scoring across all metrics',
      views_winner: 'Pick variant with highest view count',
      watch_time_winner: 'Pick variant with highest total watch time',
    },
    costPerAgent: 3,
  },
  music_match: {
    strategies: ['energy_match', 'contrast_boost', 'tempo_sync', 'mood_amplify', 'neutral_underscore'],
    labels: {
      energy_match: 'Energy Match',
      contrast_boost: 'Contrast Boost',
      tempo_sync: 'Tempo Sync',
      mood_amplify: 'Mood Amplify',
      neutral_underscore: 'Neutral Underscore',
    },
    descriptions: {
      energy_match: 'Match music energy to video energy',
      contrast_boost: 'Use contrasting energy for surprise',
      tempo_sync: 'Tight BPM synchronization',
      mood_amplify: 'Amplify emotional mood of content',
      neutral_underscore: 'Subtle background music',
    },
    costPerAgent: 2,
  },
  thumbnail: {
    strategies: ['face_focus', 'text_overlay', 'action_peak', 'color_pop', 'mid_shot'],
    labels: {
      face_focus: 'Face Focus',
      text_overlay: 'Text Overlay',
      action_peak: 'Action Peak',
      color_pop: 'Color Pop',
      mid_shot: 'Mid Shot',
    },
    descriptions: {
      face_focus: 'Close-up face expressions for emotional connection',
      text_overlay: 'Bold text overlay for context',
      action_peak: 'Capture peak action moment',
      color_pop: 'Vibrant color contrast strategy',
      mid_shot: 'Balanced mid-frame composition',
    },
    costPerAgent: 1,
  },
  safety: {
    strategies: ['strict', 'standard', 'permissive', 'brand_safe', 'kids_safe'],
    labels: {
      strict: 'Strict',
      standard: 'Standard',
      permissive: 'Permissive',
      brand_safe: 'Brand Safe',
      kids_safe: 'Kids Safe',
    },
    descriptions: {
      strict: 'Conservative screening, flag any risk',
      standard: 'Balanced safety evaluation',
      permissive: 'Lenient, only flag clear violations',
      brand_safe: 'Brand partnership safety level',
      kids_safe: 'Child-appropriate content screening',
    },
    costPerAgent: 1,
  },
  hooks_analysis: {
    strategies: ['recent_7d', 'recent_30d', 'all_time', 'per_platform', 'by_archetype'],
    labels: {
      recent_7d: 'Recent 7 Days',
      recent_30d: 'Recent 30 Days',
      all_time: 'All Time',
      per_platform: 'Per Platform',
      by_archetype: 'By Archetype',
    },
    descriptions: {
      recent_7d: 'Analyze hook performance from last 7 days',
      recent_30d: 'Analyze hook performance from last 30 days',
      all_time: 'Full historical hook analysis',
      per_platform: 'Platform-specific hook breakdown',
      by_archetype: 'Analyze by hook archetype patterns',
    },
    costPerAgent: 8,
  },
  segment_analyze: {
    strategies: ['energy_peak', 'face_presence', 'hook_potential', 'question_moment', 'silence_break'],
    labels: {
      energy_peak: 'Energy Peak',
      face_presence: 'Face Presence',
      hook_potential: 'Hook Potential',
      question_moment: 'Question Moment',
      silence_break: 'Silence Break',
    },
    descriptions: {
      energy_peak: 'Find high-energy visual moments',
      face_presence: 'Find segments with strong face visibility',
      hook_potential: 'Identify potential hook moments',
      question_moment: 'Find question/curiosity peaks',
      silence_break: 'Find dramatic silence-to-sound transitions',
    },
    costPerAgent: 5,
  },
  edit: {
    strategies: ['fast_cuts', 'caption_heavy', 'zoom_pulse', 'clean_trim', 'reaction_focus'],
    labels: {
      fast_cuts: 'Fast Cuts',
      caption_heavy: 'Caption Heavy',
      zoom_pulse: 'Zoom Pulse',
      clean_trim: 'Clean Trim',
      reaction_focus: 'Reaction Focus',
    },
    descriptions: {
      fast_cuts: 'Rapid jump cuts for high energy',
      caption_heavy: 'Dense caption overlay strategy',
      zoom_pulse: 'Subtle zoom pulses for emphasis',
      clean_trim: 'Minimal, clean trimming only',
      reaction_focus: 'Focus on reaction moments',
    },
    costPerAgent: 15,
  },
};

// ── Component ─────────────────────────────────────────────────────

export default function SwarmConfigModal({
  visible,
  onClose,
  onExecute,
  poolType,
  poolLabel,
  poolColor,
  poolDescription,
  category,
  userAllocation,
  tierLimit,
  availableAgents,
  availableStrategies: _availableStrategies,
  strategyLabels: _strategyLabels,
  strategyDescriptions: _strategyDescriptions,
  costPerAgent: _costPerAgent,
  isExecuting = false,
  title,
  description: _description,
  agentCountLabel,
}: SwarmConfigModalProps) {
  // Use built-in metadata as defaults
  const meta = STRATEGY_META[poolType];
  const strategies = ((_availableStrategies?.length ?? 0) > 0) ? _availableStrategies! : meta.strategies;
  const labels = (Object.keys(_strategyLabels || {}).length > 0) ? (_strategyLabels ?? meta.labels) : meta.labels;
  const descriptions = (Object.keys(_strategyDescriptions || {}).length > 0) ? (_strategyDescriptions ?? meta.descriptions) : meta.descriptions;
  const perAgentCost = (_costPerAgent ?? 0) > 0 ? _costPerAgent! : meta.costPerAgent;

  const [agentCount, setAgentCount] = useState(1);
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([]);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [customOptions, setCustomOptions] = useState<Record<string, any>>({});
  const [concurrencyLimit, setConcurrencyLimit] = useState(5);
  const [enableRetry, setEnableRetry] = useState(true);
  const [saveAsTemplate, setSaveAsTemplate] = useState(false);
  const [templateName, setTemplateName] = useState('');

  // Defaults for optional pool metadata
  const displayLabel = poolLabel || meta.labels[meta.strategies[0]] || poolType;
  const displayColor = poolColor || tokens.color.accent.primary;
  const displayDescription = _description || poolDescription || `${poolType} swarm`;
  const displayCategory = category || 'Generate';
  const displayTitle = title || `${displayLabel} Swarm`;

  // Reset state when modal opens
  useEffect(() => {
    if (visible) {
      setAgentCount(Math.min(1, userAllocation || 5));
      setSelectedStrategies([]);
      setShowAdvanced(false);
      setCustomOptions({});
    }
  }, [visible, userAllocation]);

  const maxAgents = Math.min(userAllocation || 5, tierLimit || 10);
  const canIncrement = agentCount < maxAgents;
  const canDecrement = agentCount > 1;

  const estimatedCost = agentCount * perAgentCost;

  const toggleStrategy = useCallback((strategy: string) => {
    setSelectedStrategies((prev) => {
      if (prev.includes(strategy)) {
        return prev.filter((s) => s !== strategy);
      }
      // Limit to agent count (1 strategy per agent)
      if (prev.length >= agentCount) {
        return [...prev.slice(1), strategy];
      }
      return [...prev, strategy];
    });
  }, [agentCount]);

  const handleExecute = () => {
    if (agentCount <= 0) {
      Alert.alert('Invalid', 'Allocate at least 1 agent');
      return;
    }

    const finalOptions = {
      ...customOptions,
      concurrencyLimit,
      enableRetry,
    };

    onExecute({
      poolType,
      agentCount,
      strategyFilter: selectedStrategies.length > 0 ? selectedStrategies : strategies.slice(0, agentCount),
      customOptions: finalOptions,
    });
  };

  const getCategoryLabel = (cat: string) => {
    switch (cat) {
      case 'Generate': return '✨ Generate';
      case 'Edit': return '✂️ Edit';
      case 'Analyze': return '📊 Analyze';
      case 'Enhance': return '🔧 Enhance';
      case 'Post': return '🚀 Post';
      default: return cat;
    }
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <Pressable style={styles.overlay} onPress={onClose}>
        <View style={styles.sheet} onStartShouldSetResponder={() => true}>
          {/* Header */}
          <View style={styles.header}>
            <View style={[styles.iconBadge, { backgroundColor: displayColor + '20' }]}>
              <Bot size={20} color={displayColor} />
            </View>
            <View style={styles.headerText}>
              <Text style={styles.title}>{displayTitle}</Text>
              <Text style={styles.categoryLabel}>{getCategoryLabel(displayCategory)}</Text>
            </View>
            <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
              <X size={20} color="#888" />
            </TouchableOpacity>
          </View>

          <ScrollView style={styles.scroll} showsVerticalScrollIndicator={false}>
            {/* Description */}
            <Text style={styles.description}>{displayDescription}</Text>

            {/* Agent Count Control */}
            <View style={styles.section}>
              <View style={styles.sectionHeader}>
                <Zap size={16} color="#6366f1" />
                <Text style={styles.sectionTitle}>{agentCountLabel || 'Agent Count'}</Text>
              </View>
              <Text style={styles.sectionSubtext}>
                You have <Text style={styles.highlight}>{userAllocation || 1}</Text> agents allocated to this pool
                (tier limit: {tierLimit || 10})
              </Text>

              <View style={styles.agentControlRow}>
                <TouchableOpacity
                  style={[styles.agentBtn, !canDecrement && styles.agentBtnDisabled]}
                  onPress={() => canDecrement && setAgentCount((c) => c - 1)}
                  disabled={!canDecrement}
                >
                  <Text style={styles.agentBtnText}>−</Text>
                </TouchableOpacity>

                <View style={styles.agentCountDisplay}>
                  <Text style={styles.agentCountNumber}>{agentCount}</Text>
                  <Text style={styles.agentCountLabel}>agent{agentCount !== 1 ? 's' : ''}</Text>
                </View>

                <TouchableOpacity
                  style={[styles.agentBtn, !canIncrement && styles.agentBtnDisabled]}
                  onPress={() => canIncrement && setAgentCount((c) => c + 1)}
                  disabled={!canIncrement}
                >
                  <Text style={styles.agentBtnText}>+</Text>
                </TouchableOpacity>
              </View>

              {/* Visual bar */}
              <View style={styles.agentBarContainer}>
                <View style={styles.agentBarBg}>
                  <View
                    style={[
                      styles.agentBarFill,
                      { width: `${(agentCount / Math.max(maxAgents, 1)) * 100}%`, backgroundColor: displayColor },
                    ]}
                  />
                </View>
                <Text style={styles.agentBarText}>
                  {agentCount} / {maxAgents} agents
                </Text>
              </View>
            </View>

            {/* Strategy Selection */}
            <View style={styles.section}>
              <View style={styles.sectionHeader}>
                <Settings size={16} color="#10b981" />
                <Text style={styles.sectionTitle}>Strategies</Text>
              </View>
              <Text style={styles.sectionSubtext}>
                Select up to <Text style={styles.highlight}>{agentCount}</Text> strategy{agentCount !== 1 ? 'ies' : 'y'} 
                (one per agent). {selectedStrategies.length > 0 && `(${selectedStrategies.length} selected)`}
              </Text>

              <View style={styles.strategyGrid}>
                {strategies.map((strategy) => {
                  const isSelected = selectedStrategies.includes(strategy);
                  const isDisabled = !isSelected && selectedStrategies.length >= agentCount;

                  return (
                    <TouchableOpacity
                      key={strategy}
                      style={[
                        styles.strategyChip,
                        isSelected && { backgroundColor: poolColor + '25', borderColor: poolColor },
                        isDisabled && styles.strategyChipDisabled,
                      ]}
                      onPress={() => !isDisabled && toggleStrategy(strategy)}
                      disabled={isDisabled}
                      activeOpacity={0.7}
                    >
                      <Text
                        style={[
                          styles.strategyChipText,
                          isSelected && { color: poolColor, fontWeight: '700' },
                          isDisabled && styles.strategyChipTextDisabled,
                        ]}
                      >
                        {labels[strategy] || strategy}
                      </Text>
                      {isSelected && <View style={[styles.strategyDot, { backgroundColor: poolColor }]} />}
                    </TouchableOpacity>
                  );
                })}
              </View>

              {/* Strategy descriptions */}
              {selectedStrategies.length > 0 && (
                <View style={styles.selectedStrategiesInfo}>
                  <Text style={styles.selectedStrategiesTitle}>Selected Strategies:</Text>
                  {selectedStrategies.map((s) => (
                    <View key={s} style={styles.strategyInfoRow}>
                      <View style={[styles.strategyInfoDot, { backgroundColor: poolColor }]} />
                      <Text style={styles.strategyInfoText}>
                        <Text style={{ fontWeight: '700' }}>{labels[s] || s}</Text>
                        {' — '}{descriptions[s] || 'No description'}
                      </Text>
                    </View>
                  ))}
                </View>
              )}
            </View>

            {/* Advanced Options */}
            <TouchableOpacity
              style={styles.advancedToggle}
              onPress={() => setShowAdvanced((v) => !v)}
            >
              <Text style={styles.advancedToggleText}>Advanced Options</Text>
              {showAdvanced ? (
                <ChevronUp size={16} color="#888" />
              ) : (
                <ChevronDown size={16} color="#888" />
              )}
            </TouchableOpacity>

            {showAdvanced && (
              <View style={styles.advancedSection}>
                <View style={styles.advancedRow}>
                  <View style={styles.advancedRowText}>
                    <Text style={styles.advancedLabel}>Force Sequential Execution</Text>
                    <Text style={styles.advancedSublabel}>
                      Run agents one after another instead of parallel
                    </Text>
                  </View>
                  <Switch
                    value={customOptions.sequential || false}
                    onValueChange={(v) => setCustomOptions((o) => ({ ...o, sequential: v }))}
                    trackColor={{ false: '#3a3a3a', true: poolColor }}
                  />
                </View>

                <View style={styles.advancedRow}>
                  <View style={styles.advancedRowText}>
                    <Text style={styles.advancedLabel}>Save Results to Library</Text>
                    <Text style={styles.advancedSublabel}>
                      Keep all variant outputs in your clip library
                    </Text>
                  </View>
                  <Switch
                    value={customOptions.saveToLibrary !== false}
                    onValueChange={(v) => setCustomOptions((o) => ({ ...o, saveToLibrary: v }))}
                    trackColor={{ false: '#3a3a3a', true: poolColor }}
                  />
                </View>

                {poolType === 'hook' && (
                  <View style={styles.advancedRow}>
                    <View style={styles.advancedRowText}>
                      <Text style={styles.advancedLabel}>Platform Target</Text>
                      <Text style={styles.advancedSublabel}>
                        Optimize hooks for specific platform
                      </Text>
                    </View>
                    <View style={styles.platformSelector}>
                      {['tiktok', 'instagram', 'youtube'].map((p) => (
                        <TouchableOpacity
                          key={p}
                          style={[
                            styles.platformChip,
                            (customOptions.platform || 'tiktok') === p && { backgroundColor: poolColor + '30', borderColor: poolColor },
                          ]}
                          onPress={() => setCustomOptions((o) => ({ ...o, platform: p }))}
                        >
                          <Text
                            style={[
                              styles.platformChipText,
                              (customOptions.platform || 'tiktok') === p && { color: poolColor, fontWeight: '700' },
                            ]}
                          >
                            {p}
                          </Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  </View>
                )}

                {/* Concurrency Limit (batch mode) */}
                <View style={styles.advancedRow}>
                  <View style={styles.advancedRowText}>
                    <Text style={styles.advancedLabel}>Concurrency Limit</Text>
                    <Text style={styles.advancedSublabel}>
                      Max clips processed simultaneously: {concurrencyLimit}
                    </Text>
                  </View>
                  <View style={styles.sliderRow}>
                    <TouchableOpacity
                      style={[styles.sliderBtn, concurrencyLimit <= 1 && styles.sliderBtnDisabled]}
                      onPress={() => setConcurrencyLimit((c) => Math.max(1, c - 1))}
                      disabled={concurrencyLimit <= 1}
                    >
                      <Text style={styles.sliderBtnText}>−</Text>
                    </TouchableOpacity>
                    <Text style={styles.sliderValue}>{concurrencyLimit}</Text>
                    <TouchableOpacity
                      style={[styles.sliderBtn, concurrencyLimit >= 10 && styles.sliderBtnDisabled]}
                      onPress={() => setConcurrencyLimit((c) => Math.min(10, c + 1))}
                      disabled={concurrencyLimit >= 10}
                    >
                      <Text style={styles.sliderBtnText}>+</Text>
                    </TouchableOpacity>
                  </View>
                </View>

                {/* Retry Toggle */}
                <View style={styles.advancedRow}>
                  <View style={styles.advancedRowText}>
                    <Text style={styles.advancedLabel}>Auto-Retry Failed Clips</Text>
                    <Text style={styles.advancedSublabel}>
                      Automatically retry up to 2 times with backoff
                    </Text>
                  </View>
                  <Switch
                    value={enableRetry}
                    onValueChange={setEnableRetry}
                    trackColor={{ false: '#3a3a3a', true: poolColor }}
                  />
                </View>

                {/* Save as Template */}
                <View style={styles.advancedRow}>
                  <View style={styles.advancedRowText}>
                    <Text style={styles.advancedLabel}>Save as Template</Text>
                    <Text style={styles.advancedSublabel}>
                      Save this configuration for future use
                    </Text>
                  </View>
                  <Switch
                    value={saveAsTemplate}
                    onValueChange={setSaveAsTemplate}
                    trackColor={{ false: '#3a3a3a', true: poolColor }}
                  />
                </View>

                {saveAsTemplate && (
                  <View style={styles.templateInputRow}>
                    <Text style={styles.templateLabel}>Template Name</Text>
                    <TextInput
                      style={styles.templateInput}
                      value={templateName}
                      onChangeText={setTemplateName}
                      placeholder="e.g., Fast Hook Batch"
                      placeholderTextColor="#666"
                    />
                  </View>
                )}
              </View>
            )}

            {/* Cost Estimate */}
            <View style={styles.costSection}>
              <View style={styles.costHeader}>
                <DollarSign size={16} color="#10b981" />
                <Text style={styles.costTitle}>Cost Estimate</Text>
              </View>
              <View style={styles.costBreakdown}>
                <View style={styles.costRow}>
                  <Text style={styles.costLabel}>Base cost per agent</Text>
                  <Text style={styles.costValue}>{perAgentCost}¢</Text>
                </View>
                <View style={styles.costRow}>
                  <Text style={styles.costLabel}>Agents</Text>
                  <Text style={styles.costValue}>× {agentCount}</Text>
                </View>
                <View style={styles.costDivider} />
                <View style={styles.costRow}>
                  <Text style={styles.costTotalLabel}>Total estimated cost</Text>
                  <Text style={[styles.costTotalValue, { color: '#10b981' }]}>{estimatedCost}¢</Text>
                </View>
              </View>
            </View>
          </ScrollView>

          {/* Footer Actions */}
          <View style={styles.footer}>
            {isExecuting ? (
              <View style={[styles.executeBtn, { backgroundColor: poolColor + '80' }]}>
                <ActivityIndicator size="small" color="#fff" />
                <Text style={styles.executeBtnText}>Dispatching Agents...</Text>
              </View>
            ) : (
              <TouchableOpacity
                style={[styles.executeBtn, { backgroundColor: displayColor }]}
                activeOpacity={0.8}
              >
                <Zap size={18} color="#fff" />
                <Text style={styles.executeBtnText}>
                  Execute with {agentCount} Agent{agentCount !== 1 ? 's' : ''}
                </Text>
              </TouchableOpacity>
            )}
            <TouchableOpacity style={styles.cancelBtn} onPress={onClose} disabled={isExecuting}>
              <Text style={styles.cancelBtnText}>Cancel</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Pressable>
    </Modal>
  );
}

// ── Styles ────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'flex-end',
  },
  sheet: {
    backgroundColor: '#1a1a1a',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '92%',
    paddingBottom: 24,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2a2a',
  },
  iconBadge: {
    width: 44,
    height: 44,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 14,
  },
  headerText: {
    flex: 1,
  },
  title: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
  },
  categoryLabel: {
    fontSize: 12,
    color: '#888',
    marginTop: 2,
  },
  closeBtn: {
    padding: 4,
  },
  scroll: {
    paddingHorizontal: 20,
    paddingTop: 16,
  },
  description: {
    fontSize: 14,
    color: '#aaa',
    lineHeight: 20,
    marginBottom: 20,
  },
  section: {
    marginBottom: 24,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  sectionTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: '#fff',
  },
  sectionSubtext: {
    fontSize: 13,
    color: '#888',
    marginBottom: 14,
    lineHeight: 18,
  },
  highlight: {
    color: '#fff',
    fontWeight: '600',
  },
  agentControlRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 20,
    marginBottom: 16,
  },
  agentBtn: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#2a2a2a',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#3a3a3a',
  },
  agentBtnDisabled: {
    opacity: 0.3,
  },
  agentBtnText: {
    color: '#fff',
    fontSize: 24,
    fontWeight: '600',
    lineHeight: 28,
  },
  agentCountDisplay: {
    alignItems: 'center',
    minWidth: 80,
  },
  agentCountNumber: {
    fontSize: 32,
    fontWeight: '800',
    color: '#fff',
  },
  agentCountLabel: {
    fontSize: 13,
    color: '#888',
    marginTop: 2,
  },
  agentBarContainer: {
    marginTop: 4,
  },
  agentBarBg: {
    height: 8,
    backgroundColor: '#2a2a2a',
    borderRadius: 4,
    overflow: 'hidden',
  },
  agentBarFill: {
    height: '100%',
    borderRadius: 4,
  },
  agentBarText: {
    fontSize: 12,
    color: '#666',
    marginTop: 6,
    textAlign: 'center',
  },
  strategyGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  strategyChip: {
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: '#252525',
    borderWidth: 1,
    borderColor: '#333',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  strategyChipDisabled: {
    opacity: 0.35,
  },
  strategyChipText: {
    fontSize: 13,
    color: '#ccc',
    fontWeight: '500',
  },
  strategyChipTextDisabled: {
    color: '#555',
  },
  strategyDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  selectedStrategiesInfo: {
    marginTop: 16,
    backgroundColor: '#252525',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: '#333',
  },
  selectedStrategiesTitle: {
    fontSize: 12,
    fontWeight: '600',
    color: '#888',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 10,
  },
  strategyInfoRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    marginBottom: 8,
  },
  strategyInfoDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginTop: 6,
  },
  strategyInfoText: {
    flex: 1,
    fontSize: 13,
    color: '#bbb',
    lineHeight: 18,
  },
  advancedToggle: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 12,
    borderTopWidth: 1,
    borderTopColor: '#2a2a2a',
    marginBottom: 12,
  },
  advancedToggleText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#888',
  },
  advancedSection: {
    gap: 16,
    marginBottom: 20,
  },
  advancedRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  advancedRowText: {
    flex: 1,
    marginRight: 12,
  },
  advancedLabel: {
    fontSize: 14,
    color: '#fff',
    marginBottom: 2,
  },
  advancedSublabel: {
    fontSize: 12,
    color: '#666',
  },
  platformSelector: {
    flexDirection: 'row',
    gap: 8,
  },
  platformChip: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
    backgroundColor: '#252525',
    borderWidth: 1,
    borderColor: '#333',
  },
  platformChipText: {
    fontSize: 11,
    color: '#888',
    textTransform: 'uppercase',
  },
  costSection: {
    backgroundColor: '#252525',
    borderRadius: 14,
    padding: 16,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: '#333',
  },
  costHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  costTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
  },
  costBreakdown: {
    gap: 8,
  },
  costRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  costLabel: {
    fontSize: 13,
    color: '#aaa',
  },
  costValue: {
    fontSize: 13,
    color: '#fff',
    fontWeight: '500',
  },
  costDivider: {
    height: 1,
    backgroundColor: '#3a3a3a',
    marginVertical: 4,
  },
  costTotalLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
  },
  costTotalValue: {
    fontSize: 16,
    fontWeight: '700',
    color: '#10b981',
  },
  templateInputRow: {
    marginTop: 8,
    gap: 8,
  },
  templateLabel: {
    fontSize: 13,
    color: '#888',
    marginBottom: 4,
  },
  templateInput: {
    backgroundColor: '#252525',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    color: '#fff',
    fontSize: 14,
    borderWidth: 1,
    borderColor: '#333',
  },
  sliderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  sliderBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#2a2a2a',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#3a3a3a',
  },
  sliderBtnDisabled: {
    opacity: 0.3,
  },
  sliderBtnText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
    lineHeight: 22,
  },
  sliderValue: {
    fontSize: 16,
    fontWeight: '700',
    color: '#fff',
    minWidth: 24,
    textAlign: 'center',
  },
  footer: {
    paddingHorizontal: 20,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#2a2a2a',
    gap: 10,
  },
  executeBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    paddingVertical: 16,
    borderRadius: 14,
  },
  executeBtnText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '700',
  },
  cancelBtn: {
    alignItems: 'center',
    paddingVertical: 12,
  },
  cancelBtnText: {
    color: '#888',
    fontSize: 14,
    fontWeight: '500',
  },
});
