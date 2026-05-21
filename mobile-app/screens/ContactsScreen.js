import React, { useEffect, useState, useMemo } from 'react';
import {
  View, Text, FlatList, TextInput, TouchableOpacity,
  StyleSheet, ActivityIndicator, RefreshControl, Linking,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { getContacts } from '../api';

export default function ContactsScreen({ navigation }) {
  const [contacts, setContacts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [query, setQuery] = useState('');

  useEffect(() => { load(); }, []);

  async function load() {
    try {
      const data = await getContacts();
      // Сортируем по имени
      data.sort((a, b) => a.name.localeCompare(b.name, 'ru'));
      setContacts(data);
    } catch (_) {
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return contacts;
    return contacts.filter(c =>
      c.name.toLowerCase().includes(q) ||
      c.username.toLowerCase().includes(q)
    );
  }, [contacts, query]);

  function openChat(contact) {
    navigation.navigate('Messages', {
      chatId: contact.id,
      chatName: contact.name,
    });
  }

  function renderContact({ item }) {
    const initials = item.name
      .split(' ')
      .map(w => w[0])
      .join('')
      .slice(0, 2)
      .toUpperCase();

    return (
      <TouchableOpacity style={styles.row} onPress={() => openChat(item)}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{initials || '?'}</Text>
        </View>
        <View style={styles.info}>
          <Text style={styles.name}>{item.name}</Text>
          {item.username ? (
            <Text style={styles.sub}>@{item.username}</Text>
          ) : item.phone ? (
            <Text style={styles.sub}>{item.phone}</Text>
          ) : null}
        </View>
        <Icon name="chat-bubble-outline" size={20} color="#5288c1" />
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
      <View style={styles.searchBox}>
        <Icon name="search" size={20} color="#666" style={styles.searchIcon} />
        <TextInput
          style={styles.searchInput}
          value={query}
          onChangeText={setQuery}
          placeholder="Поиск по контактам..."
          placeholderTextColor="#555"
          clearButtonMode="while-editing"
        />
        {query.length > 0 && (
          <TouchableOpacity onPress={() => setQuery('')}>
            <Icon name="close" size={20} color="#666" />
          </TouchableOpacity>
        )}
      </View>

      <FlatList
        data={filtered}
        keyExtractor={item => String(item.id)}
        renderItem={renderContact}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => { setRefreshing(true); load(); }}
            tintColor="#5288c1"
          />
        }
        ListEmptyComponent={
          <Text style={styles.empty}>
            {query ? 'Ничего не найдено' : 'Контактов нет'}
          </Text>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#17212b' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#17212b' },
  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#242f3d',
    margin: 10,
    borderRadius: 10,
    paddingHorizontal: 10,
  },
  searchIcon: { marginRight: 6 },
  searchInput: {
    flex: 1,
    color: '#ffffff',
    fontSize: 15,
    paddingVertical: 10,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderBottomWidth: 0.5,
    borderBottomColor: '#2b3a4a',
  },
  avatar: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: '#5288c1',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  avatarText: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
  info: { flex: 1 },
  name: { color: '#ffffff', fontSize: 16, fontWeight: '500' },
  sub: { color: '#aaaaaa', fontSize: 13, marginTop: 2 },
  empty: { color: '#aaaaaa', textAlign: 'center', marginTop: 40 },
});
