// Экран списка чатов
import React, { useEffect, useState } from 'react';
import {
  View, Text, FlatList, TouchableOpacity,
  StyleSheet, ActivityIndicator, RefreshControl, Alert
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { getDialogs } from '../api';

export default function ChatsScreen({ navigation }) {
  const [chats, setChats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadChats();
  }, []);

  async function loadChats() {
    try {
      const data = await getDialogs();
      setChats(data);
    } catch (e) {
      Alert.alert('Ошибка', e.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  function openChat(chat) {
    if (chat.is_blocked) {
      Alert.alert(
        '🚫 Доступ закрыт',
        'Родитель заблокировал этот чат',
        [{ text: 'Понятно' }]
      );
      return;
    }
    navigation.navigate('Messages', { chatId: chat.id, chatName: chat.name });
  }

  function renderChat({ item }) {
    return (
      <TouchableOpacity
        style={[styles.chatItem, item.is_blocked && styles.blockedItem]}
        onPress={() => openChat(item)}
      >
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>
            {(item.name || '?')[0].toUpperCase()}
          </Text>
        </View>
        <View style={styles.chatInfo}>
          <Text style={styles.chatName}>{item.name}</Text>
          <Text style={styles.chatType}>
            {item.type === 'bot' ? '🤖 Бот' : '💬 Чат'}
          </Text>
        </View>
        {item.is_blocked ? (
          <Icon name="block" size={20} color="#e53935" />
        ) : item.unread_count > 0 ? (
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{item.unread_count}</Text>
          </View>
        ) : null}
      </TouchableOpacity>
    );
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#5288c1" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={chats}
        keyExtractor={item => String(item.id)}
        renderItem={renderChat}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => { setRefreshing(true); loadChats(); }}
            tintColor="#5288c1"
          />
        }
        ListEmptyComponent={
          <Text style={styles.empty}>Нет чатов</Text>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#17212b' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#17212b' },
  chatItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderBottomWidth: 0.5,
    borderBottomColor: '#2b3a4a',
  },
  blockedItem: { opacity: 0.5 },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#5288c1',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  avatarText: { color: '#fff', fontSize: 20, fontWeight: 'bold' },
  chatInfo: { flex: 1 },
  chatName: { color: '#ffffff', fontSize: 16, fontWeight: '500' },
  chatType: { color: '#aaaaaa', fontSize: 12, marginTop: 2 },
  badge: {
    backgroundColor: '#5288c1',
    borderRadius: 12,
    minWidth: 24,
    height: 24,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 6,
  },
  badgeText: { color: '#fff', fontSize: 12, fontWeight: 'bold' },
  empty: { color: '#aaaaaa', textAlign: 'center', marginTop: 40 },
});
