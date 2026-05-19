import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Modal,
  Pressable,
  ScrollView,
} from 'react-native';
import {
  Bot,
  Sparkles,
  Repeat,
  Shield,
  Music,
  Image,
  BarChart3,
  Scissors,
  Activity,
  Layers,
  X,
  Zap,
  Settings,
  Play,
} from 'lucide-react-native';

interface SwarmAction {
  id: string;
  label: string;
  description: string;
  icon: React.ComponentType<any>;
  color: string;
  category: string;
}

const SWARM_ACTIONS: SwarmAction[] = [
  // Generate
  {
    id: 'hook',
    label: 'Hook Generation',
    description: 'Generate multiple hook variations with different personas',
    icon: Sparkles,
    color: '#6366f1',
    category: 'Generate',
  },
  {
    id: 'thumbnail',
    label: 'Thumbnail Generation',
    description: 'Create thumbnails with different style strategies',
    icon: Image,
    color: '#8b5cf6',
    category: 'Generate',
  },
  // Edit
  {
    id: 'remix',
    label: 'Remix Clip',
    description: 'Generate AI-powered remix variants',
    icon: Repeat,
    color: '#10b981',
    category: 'Edit',
  },
  {
    id: 'edit',
    label: 'Edit Recipe',
    description: 'Apply automated edit recipes (cuts, captions, zoom)',
    icon: Scissors,
    color: '#06b6d4',
    category: 'Edit',
  },
  {
    id: 'segment_analyze',
    label: 'Segment Analysis',
    description: 'Find best moments: energy peaks, faces, questions',
    icon: Layers,
    color: '#0ea5e9',
    category: 'Edit',
  },
  // Analyze
  {
    id: 'safety',
    label: 'Safety Check',
    description: 'Run multi-level safety screening (strict to permissive)',
    icon: Shield,
    color: '#f59e0b',
    category: 'Analyze',
  },
  {
    id: 'hooks_analysis',
    label: 'Hooks Analysis',
    description: 'Analyze historical hook performance patterns',
    icon: BarChart3,
    color: '#ec4899',
    category: 'Analyze',
  },
  {
    id: 'ab_test',
    label: 'A/B Test Analysis',
    description: 'Compare variants with different winner strategies',
    icon: Activity,
    color: '#f97316',
    category: 'Analyze',
  },
  // Enhance
  {
    id: 'music_match',
    label: 'Music Match',
    description: 'Match music tracks by energy, tempo, mood, or contrast',
    icon: Music,
    color: '#14b8a6',
    category: 'Enhance',
  },
  {
    id: 'post',
    label: 'Multi-Account Post',
    description: 'Post to all connected accounts simultaneously',
    icon: Zap,
    color: '#eab308',
    category: 'Post',
  },
];

const CATEGORIES = ['Generate', 'Edit', 'Analyze', 'Enhance', 'Post'];

interface SwarmActionSheetProps {
  visible: boolean;
  onClose: () => void;
  /** Called when user taps the main card to configure before executing */
  onConfigure: (actionId: string) => void;
  /** Called when user taps the quick-run play button */
  onQuickRun?: (actionId: string) => void;
  disabled?: boolean;
  filterCategory?: string[];
  title?: string;
}

export default function SwarmActionSheet({
  visible,
  onClose,
  onConfigure,
  onQuickRun,
  disabled = false,
  filterCategory,
  title = 'Run Swarm Agents',
}: SwarmActionSheetProps) {
  const actions = filterCategory
    ? SWARM_ACTIONS.filter((a) => filterCategory.includes(a.category))
    : SWARM_ACTIONS;

  const grouped = CATEGORIES.map((cat) => ({
    category: cat,
    actions: actions.filter((a) => a.category === cat),
  })).filter((g) => g.actions.length > 0);

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <Pressable style={styles.overlay} onPress={onClose}>
        <View style={styles.sheet}>
          <View style={styles.header}>
            <Bot size={20} color="#6366f1" />
            <Text style={styles.title}>{title}</Text>
            <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
              <X size={20} color="#888" />
            </TouchableOpacity>
          </View>

          <ScrollView style={styles.scroll} showsVerticalScrollIndicator={false}>
            {grouped.map((group) => (
              <View key={group.category} style={styles.categorySection}>
                <Text style={styles.categoryLabel}>{group.category}</Text>
                <View style={styles.actionsGrid}>
                  {group.actions.map((action) => {
                    const Icon = action.icon;
                    return (
                  <TouchableOpacity
                      key={action.id}
                      style={[
                        styles.actionCard,
                        disabled && styles.actionCardDisabled,
                      ]}
                      onPress={() => {
                        if (!disabled) {
                          onConfigure(action.id);
                        }
                      }}
                      disabled={disabled}
                      activeOpacity={0.7}
                    >
                      <View style={styles.actionCardTop}>
                        <View
                          style={[
                            styles.iconContainer,
                            { backgroundColor: action.color + '20' },
                          ]}
                        >
                          <Icon size={22} color={action.color} />
                        </View>
                        {onQuickRun && (
                          <TouchableOpacity
                            style={[styles.quickRunBtn, { backgroundColor: action.color + '30' }]}
                            onPress={(e) => {
                              e.stopPropagation();
                              if (!disabled) {
                                onQuickRun(action.id);
                                onClose();
                              }
                            }}
                            disabled={disabled}
                          >
                            <Play size={14} color={action.color} />
                          </TouchableOpacity>
                        )}
                      </View>
                      <Text style={styles.actionLabel}>{action.label}</Text>
                      <Text style={styles.actionDesc} numberOfLines={2}>
                        {action.description}
                      </Text>
                      <View style={styles.configureHint}>
                        <Settings size={12} color="#666" />
                        <Text style={styles.configureHintText}>Configure</Text>
                      </View>
                    </TouchableOpacity>
                    );
                  })}
                </View>
              </View>
            ))}
          </ScrollView>

          <View style={styles.footer}>
            <Text style={styles.footerText}>
              Each agent runs in parallel with a unique strategy
            </Text>
          </View>
        </View>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'flex-end',
  },
  sheet: {
    backgroundColor: '#1a1a1a',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '80%',
    paddingBottom: 24,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 12,
  },
  title: {
    fontSize: 17,
    fontWeight: '700',
    color: '#fff',
    flex: 1,
    marginLeft: 12,
  },
  closeBtn: {
    padding: 4,
  },
  scroll: {
    paddingHorizontal: 20,
  },
  categorySection: {
    marginBottom: 20,
  },
  categoryLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#666',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 12,
  },
  actionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  actionCard: {
    width: '47%',
    backgroundColor: '#252525',
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: '#333',
  },
  actionCardDisabled: {
    opacity: 0.4,
  },
  iconContainer: {
    width: 40,
    height: 40,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 10,
  },
  actionLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 4,
  },
  actionDesc: {
    fontSize: 11,
    color: '#888',
    lineHeight: 16,
  },
  footer: {
    paddingHorizontal: 20,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#2a2a2a',
  },
  footerText: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
    fontStyle: 'italic',
  },
  actionCardTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 10,
  },
  quickRunBtn: {
    width: 28,
    height: 28,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  configureHint: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 8,
  },
  configureHintText: {
    fontSize: 11,
    color: '#666',
  },
});
