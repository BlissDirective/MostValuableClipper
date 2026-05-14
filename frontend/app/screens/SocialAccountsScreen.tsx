import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, Alert, ActivityIndicator } from 'react-native';
import { api } from '@/lib/api';

type Platform = 'tiktok' | 'instagram' | 'youtube' | 'facebook';

interface SocialAccount {
  id: string;
  platform: Platform;
  handle: string | null;
  follower_count: number;
  eligible_for_program: boolean;
  connected_at: string;
}

const platformInfo: Record<Platform, { name: string; color: string; icon: string }> = {
  tiktok: { name: 'TikTok', color: '#ff0050', icon: '🎵' },
  instagram: { name: 'Instagram', color: '#e1306c', icon: '📸' },
  youtube: { name: 'YouTube', color: '#ff0000', icon: '🎬' },
  facebook: { name: 'Facebook', color: '#1877f2', icon: '👥' },
};

export default function SocialAccountsScreen() {
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState<Platform | null>(null);

  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    try {
      const data = await api.get<SocialAccount[]>('/social-accounts');
      setAccounts(data);
    } catch {
      // No accounts yet
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async (platform: Platform) => {
    setConnecting(platform);
    try {
      const { auth_url } = await api.post<{ auth_url: string }>('/social-accounts/connect', {
        platform,
        redirect_uri: 'mvc-app://callback',
      });
      // Open auth_url in browser / WebView
      Alert.alert('Connect', `Open this URL to connect ${platformInfo[platform].name}:\n\n${auth_url}`, [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Done', onPress: fetchAccounts },
      ]);
    } catch (err: any) {
      Alert.alert('Error', err.message || `Could not connect ${platformInfo[platform].name}`);
    } finally {
      setConnecting(null);
    }
  };

  const handleDisconnect = (accountId: string, platform: Platform) => {
    Alert.alert(
      `Disconnect ${platformInfo[platform].name}`,
      'Are you sure? This will stop posting to this platform.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Disconnect',
          style: 'destructive',
          onPress: async () => {
            try {
              await api.delete(`/social-accounts/${accountId}`);
              setAccounts(accounts.filter((a) => a.id !== accountId));
            } catch {
              Alert.alert('Error', 'Could not disconnect account');
            }
          },
        },
      ]
    );
  };

  const isConnected = (platform: Platform) => accounts.find((a) => a.platform === platform);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#6366f1" />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.header}>Connected Platforms</Text>
      <Text style={styles.subheader}>Link your social accounts to auto-post clips</Text>

      {(Object.keys(platformInfo) as Platform[]).map((platform) => {
        const account = isConnected(platform);
        const info = platformInfo[platform];
        return (
          <View key={platform} style={[styles.card, account && { borderColor: info.color, borderWidth: 1 }]}>
            <View style={styles.row}>
              <Text style={styles.icon}>{info.icon}</Text>
              <View style={styles.info}>
                <Text style={styles.name}>{info.name}</Text>
                {account ? (
                  <>
                    <Text style={styles.handle}>@{account.handle || 'connected'}</Text>
                    <Text style={styles.meta}>
                      {account.follower_count.toLocaleString()} followers •
                      {account.eligible_for_program ? ' ✅ Monetized' : ' ⏳ Not eligible'}
                    </Text>
                  </>
                ) : (
                  <Text style={styles.notConnected}>Not connected</Text>
                )}
              </View>
            </View>

            {account ? (
              <TouchableOpacity
                style={[styles.button, { borderColor: '#ef4444' }]}
                onPress={() => handleDisconnect(account.id, platform)}
              >
                <Text style={[styles.buttonText, { color: '#ef4444' }]}>Disconnect</Text>
              </TouchableOpacity>
            ) : (
              <TouchableOpacity
                style={[styles.button, { backgroundColor: info.color }]}
                onPress={() => handleConnect(platform)}
                disabled={connecting === platform}
              >
                <Text style={styles.buttonText}>
                  {connecting === platform ? 'Connecting...' : `Connect ${info.name}`}
                </Text>
              </TouchableOpacity>
            )}
          </View>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f0f0f',
    padding: 16,
  },
  center: {
    flex: 1,
    backgroundColor: '#0f0f0f',
    justifyContent: 'center',
    alignItems: 'center',
  },
  header: {
    fontSize: 24,
    fontWeight: '700',
    color: '#fff',
    marginTop: 16,
  },
  subheader: {
    fontSize: 14,
    color: '#888',
    marginBottom: 20,
    marginTop: 4,
  },
  card: {
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    padding: 20,
    marginBottom: 12,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  icon: {
    fontSize: 32,
    marginRight: 16,
  },
  info: {
    flex: 1,
  },
  name: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
  },
  handle: {
    fontSize: 14,
    color: '#6366f1',
    marginTop: 2,
  },
  meta: {
    fontSize: 13,
    color: '#888',
    marginTop: 4,
  },
  notConnected: {
    fontSize: 14,
    color: '#666',
    marginTop: 2,
  },
  button: {
    borderRadius: 12,
    padding: 14,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'transparent',
  },
  buttonText: {
    fontWeight: '600',
    fontSize: 15,
  },
});
