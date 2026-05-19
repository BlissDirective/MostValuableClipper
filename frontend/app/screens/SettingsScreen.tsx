import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, Switch, Alert } from 'react-native';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { api } from '@/lib/api';

export default function SettingsScreen() {
  const router = useRouter();
  const [notifications, setNotifications] = useState(true);
  const [darkMode, setDarkMode] = useState(true);
  const [autoPost, setAutoPost] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleLogout = async () => {
    Alert.alert('Log Out', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Log Out',
        style: 'destructive',
        onPress: async () => {
          await AsyncStorage.multiRemove(['auth_token', 'user']);
          router.replace('/auth');
        },
      },
    ]);
  };

  const handleDeleteAccount = () => {
    Alert.alert(
      'Delete Account',
      'This permanently deletes all your data. Are you sure?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await api.delete('/users/me');
              await AsyncStorage.multiRemove(['auth_token', 'user']);
              router.replace('/auth');
            } catch (err) {
              Alert.alert('Error', 'Could not delete account');
            }
          },
        },
      ]
    );
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Preferences</Text>
        <View style={styles.row}>
          <Text style={styles.label}>Push Notifications</Text>
          <Switch value={notifications} onValueChange={setNotifications} />
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>Dark Mode</Text>
          <Switch value={darkMode} onValueChange={setDarkMode} />
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>Auto-Post Approved Clips</Text>
          <Switch value={autoPost} onValueChange={setAutoPost} />
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Swarm & AI</Text>
        <TouchableOpacity style={styles.buttonRow} onPress={() => router.push('/profile/swarm')}>
          <Text style={styles.buttonLabel}>Agent Allocation</Text>
          <Text style={styles.chevron}>›</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.buttonRow} onPress={() => router.push('/profile/behavior')}>
          <Text style={styles.buttonLabel}>Agent Behavior</Text>
          <Text style={styles.chevron}>›</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Account</Text>
        <TouchableOpacity style={styles.buttonRow} onPress={() => router.push('/subscription')}>
          <Text style={styles.buttonLabel}>Subscription & Billing</Text>
          <Text style={styles.chevron}>›</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.buttonRow} onPress={() => router.push('/social-accounts')}>
          <Text style={styles.buttonLabel}>Connected Platforms</Text>
          <Text style={styles.chevron}>›</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.buttonRow} onPress={() => router.push('/earnings')}>
          <Text style={styles.buttonLabel}>Earnings & Analytics</Text>
          <Text style={styles.chevron}>›</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Legal</Text>
        <TouchableOpacity style={styles.buttonRow} onPress={() => router.push('/legal?tab=privacy')}>
          <Text style={styles.buttonLabel}>Privacy Policy</Text>
          <Text style={styles.chevron}>›</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.buttonRow} onPress={() => router.push('/legal?tab=terms')}>
          <Text style={styles.buttonLabel}>Terms of Service</Text>
          <Text style={styles.chevron}>›</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.buttonRow} onPress={() => router.push('/legal?tab=dmca')}>
          <Text style={styles.buttonLabel}>DMCA / Copyright</Text>
          <Text style={styles.chevron}>›</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Danger Zone</Text>
        <TouchableOpacity style={[styles.buttonRow, styles.danger]} onPress={handleLogout}>
          <Text style={[styles.buttonLabel, styles.dangerText]}>Log Out</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.buttonRow, styles.danger]} onPress={handleDeleteAccount}>
          <Text style={[styles.buttonLabel, styles.dangerText]}>Delete Account</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f0f0f',
  },
  section: {
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    margin: 16,
    marginBottom: 8,
    padding: 16,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: '#6366f1',
    textTransform: 'uppercase',
    marginBottom: 12,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2a2a',
  },
  label: {
    fontSize: 15,
    color: '#fff',
  },
  buttonRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2a2a',
  },
  buttonLabel: {
    fontSize: 15,
    color: '#fff',
  },
  chevron: {
    fontSize: 18,
    color: '#888',
  },
  danger: {
    borderBottomColor: '#3a1a1a',
  },
  dangerText: {
    color: '#ef4444',
  },
});