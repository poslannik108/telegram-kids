import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity } from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { requestJoinChat, requestUseBot } from '../api';

// Статусы: waiting | approved | rejected | timeout | error
export default function PendingScreen({ route, navigation }) {
  const { type, identifier, name } = route.params;
  const [status, setStatus] = useState('waiting');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function ask() {
      setStatus('waiting');
      setErrorMsg('');
      try {
        const res = type === 'chat'
          ? await requestJoinChat(identifier)
          : await requestUseBot(identifier);

        if (cancelled) return;
        if (res.reason === 'timeout') {
          setStatus('timeout');
        } else {
          setStatus(res.allowed ? 'approved' : 'rejected');
        }
      } catch (e) {
        if (cancelled) return;
        setStatus('error');
        setErrorMsg(e.message || 'Нет соединения с сервером');
      }
    }
    ask();
    return () => { cancelled = true; };
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  function retry() {
    // Сброс + повторный запрос через новый useEffect
    setStatus('waiting');
    let cancelled = false;
    async function ask() {
      try {
        const res = type === 'chat'
          ? await requestJoinChat(identifier)
          : await requestUseBot(identifier);
        if (cancelled) return;
        if (res.reason === 'timeout') setStatus('timeout');
        else setStatus(res.allowed ? 'approved' : 'rejected');
      } catch (e) {
        if (cancelled) return;
        setStatus('error');
        setErrorMsg(e.message || 'Нет соединения с сервером');
      }
    }
    ask();
    return () => { cancelled = true; };
  }

  function goBack() {
    navigation.goBack();
  }

  return (
    <View style={styles.container}>
      {status === 'waiting' && (
        <>
          <ActivityIndicator size="large" color="#5288c1" style={styles.spinner} />
          <Icon
            name={type === 'chat' ? 'group' : 'smart-toy'}
            size={56}
            color="#5288c1"
            style={styles.icon}
          />
          <Text style={styles.title}>Ожидание разрешения</Text>
          <Text style={styles.sub}>
            {type === 'chat'
              ? `Ты хочешь вступить в\n«${name}»`
              : `Ты хочешь использовать\n«${name}»`}
          </Text>
          <Text style={styles.hint}>
            Родитель получил уведомление.{'\n'}Дождись его ответа.
          </Text>
          <TouchableOpacity style={styles.cancelBtn} onPress={goBack}>
            <Text style={styles.cancelText}>Отмена</Text>
          </TouchableOpacity>
        </>
      )}

      {status === 'approved' && (
        <>
          <Icon name="check-circle" size={80} color="#4caf50" style={styles.icon} />
          <Text style={[styles.title, { color: '#4caf50' }]}>Разрешено!</Text>
          <Text style={styles.sub}>Родитель разрешил это действие.</Text>
          <TouchableOpacity style={styles.btn} onPress={goBack}>
            <Text style={styles.btnText}>Закрыть</Text>
          </TouchableOpacity>
        </>
      )}

      {status === 'rejected' && (
        <>
          <Icon name="cancel" size={80} color="#e53935" style={styles.icon} />
          <Text style={[styles.title, { color: '#e53935' }]}>Запрещено</Text>
          <Text style={styles.sub}>Родитель не разрешил это действие.</Text>
          <TouchableOpacity style={styles.btn} onPress={goBack}>
            <Text style={styles.btnText}>Закрыть</Text>
          </TouchableOpacity>
        </>
      )}

      {status === 'timeout' && (
        <>
          <Icon name="timer-off" size={80} color="#ff9800" style={styles.icon} />
          <Text style={[styles.title, { color: '#ff9800' }]}>Время истекло</Text>
          <Text style={styles.sub}>Родитель не ответил в течение 10 минут.</Text>
          <TouchableOpacity style={styles.btn} onPress={retry}>
            <Text style={styles.btnText}>Повторить запрос</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.cancelBtn} onPress={goBack}>
            <Text style={styles.cancelText}>Отмена</Text>
          </TouchableOpacity>
        </>
      )}

      {status === 'error' && (
        <>
          <Icon name="wifi-off" size={80} color="#aaaaaa" style={styles.icon} />
          <Text style={[styles.title, { color: '#aaaaaa' }]}>Нет соединения</Text>
          <Text style={styles.sub}>{errorMsg}</Text>
          <TouchableOpacity style={styles.btn} onPress={retry}>
            <Text style={styles.btnText}>Повторить</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.cancelBtn} onPress={goBack}>
            <Text style={styles.cancelText}>Отмена</Text>
          </TouchableOpacity>
        </>
      )}
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
  spinner: { marginBottom: 16 },
  icon: { marginBottom: 20 },
  title: {
    color: '#ffffff',
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 12,
    textAlign: 'center',
  },
  sub: {
    color: '#cccccc',
    fontSize: 16,
    textAlign: 'center',
    marginBottom: 12,
    lineHeight: 22,
  },
  hint: {
    color: '#777777',
    fontSize: 13,
    textAlign: 'center',
    marginBottom: 36,
    lineHeight: 20,
  },
  btn: {
    backgroundColor: '#5288c1',
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 32,
    marginBottom: 12,
  },
  btnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  cancelBtn: { paddingVertical: 10 },
  cancelText: { color: '#5288c1', fontSize: 15 },
});
