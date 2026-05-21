import React, { useEffect } from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { checkLinkStatus } from '../api';

// Показывается после логина, пока родитель не привязал ребёнка через бота.
// Каждые 10 секунд проверяет, появился ли статус linked.
export default function AwaitingLinkScreen({ navigation }) {
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const data = await checkLinkStatus();
        if (data.is_linked) {
          clearInterval(interval);
          navigation.replace('Main');
        }
      } catch (_) {}
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color="#5288c1" style={styles.spinner} />
      <Text style={styles.title}>Ожидаем подтверждения</Text>
      <Text style={styles.subtitle}>
        Попроси родителя открыть бота{'\n'}Telegram Kids и добавить тебя.{'\n\n'}
        После привязки приложение откроется автоматически.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#17212b',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  spinner: { marginBottom: 32 },
  title: {
    color: '#ffffff',
    fontSize: 22,
    fontWeight: '600',
    marginBottom: 16,
    textAlign: 'center',
  },
  subtitle: {
    color: '#aaaaaa',
    fontSize: 15,
    textAlign: 'center',
    lineHeight: 22,
  },
});
