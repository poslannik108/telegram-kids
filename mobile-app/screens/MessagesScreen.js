// Экран сообщений
import React, { useEffect, useState, useRef } from 'react';
import {
  View, Text, FlatList, TextInput, TouchableOpacity,
  StyleSheet, ActivityIndicator, Alert, KeyboardAvoidingView, Platform
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { getMessages, sendMessage } from '../api';

export default function MessagesScreen({ route }) {
  const { chatId, chatName } = route.params;
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const flatListRef = useRef(null);

  useEffect(() => {
    loadMessages();
    // Обновляем каждые 5 секунд
    const interval = setInterval(loadMessages, 5000);
    return () => clearInterval(interval);
  }, []);

  async function loadMessages() {
    try {
      const data = await getMessages(chatId);
      setMessages(data.reverse()); // Новые снизу
    } catch (e) {
      if (e.message.includes('blocked')) {
        Alert.alert('🚫 Чат заблокирован', 'Родитель закрыл доступ к этому чату');
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleSend() {
    if (!text.trim()) return;
    setSending(true);
    try {
      await sendMessage(chatId, text.trim());
      setText('');
      await loadMessages();
    } catch (e) {
      Alert.alert('Ошибка', e.message);
    } finally {
      setSending(false);
    }
  }

  function renderMessage({ item }) {
    return (
      <View style={[styles.msgRow, item.out && styles.msgRowOut]}>
        <View style={[styles.bubble, item.out ? styles.bubbleOut : styles.bubbleIn]}>
          <Text style={styles.msgText}>{item.text}</Text>
          <Text style={styles.msgTime}>
            {new Date(item.date).toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' })}
          </Text>
        </View>
      </View>
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
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={90}
    >
      <FlatList
        ref={flatListRef}
        data={messages}
        keyExtractor={item => String(item.id)}
        renderItem={renderMessage}
        onContentSizeChange={() => flatListRef.current?.scrollToEnd()}
        style={styles.list}
      />
      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          value={text}
          onChangeText={setText}
          placeholder="Сообщение..."
          placeholderTextColor="#666"
          multiline
        />
        <TouchableOpacity
          style={styles.sendBtn}
          onPress={handleSend}
          disabled={sending || !text.trim()}
        >
          {sending
            ? <ActivityIndicator size="small" color="#fff" />
            : <Icon name="send" size={22} color="#fff" />
          }
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0e1621' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0e1621' },
  list: { flex: 1, padding: 8 },
  msgRow: { marginVertical: 2, alignItems: 'flex-start' },
  msgRowOut: { alignItems: 'flex-end' },
  bubble: {
    maxWidth: '80%',
    padding: 10,
    borderRadius: 12,
  },
  bubbleIn: { backgroundColor: '#182533', borderBottomLeftRadius: 2 },
  bubbleOut: { backgroundColor: '#2b5278', borderBottomRightRadius: 2 },
  msgText: { color: '#ffffff', fontSize: 15 },
  msgTime: { color: '#aaaaaa', fontSize: 11, marginTop: 4, textAlign: 'right' },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    padding: 8,
    backgroundColor: '#17212b',
    borderTopWidth: 0.5,
    borderTopColor: '#2b3a4a',
  },
  input: {
    flex: 1,
    backgroundColor: '#242f3d',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    color: '#ffffff',
    fontSize: 15,
    maxHeight: 120,
    marginRight: 8,
  },
  sendBtn: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: '#5288c1',
    justifyContent: 'center',
    alignItems: 'center',
  },
});
