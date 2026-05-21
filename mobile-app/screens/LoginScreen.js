import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, ActivityIndicator, Alert,
  KeyboardAvoidingView, Platform, ScrollView,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { requestCode, verifyCode } from '../api';

export default function LoginScreen({ navigation }) {
  const [step, setStep] = useState('phone'); // 'phone' | 'code'
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [phoneCodeHash, setPhoneCodeHash] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSendCode() {
    const trimmed = phone.trim();
    if (!trimmed) return;
    setLoading(true);
    try {
      const result = await requestCode(trimmed);
      setPhoneCodeHash(result.phone_code_hash);
      setStep('code');
    } catch (e) {
      Alert.alert('Ошибка', e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyCode() {
    const trimmedCode = code.trim();
    if (!trimmedCode) return;
    setLoading(true);
    try {
      const result = await verifyCode(phone.trim(), trimmedCode, phoneCodeHash);
      await AsyncStorage.setItem('child_token', result.token);
      await AsyncStorage.setItem('child_phone', phone.trim());
      if (result.is_linked) {
        navigation.replace('Main');
      } else {
        navigation.replace('AwaitingLink');
      }
    } catch (e) {
      Alert.alert('Неверный код', e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.inner} keyboardShouldPersistTaps="handled">
        <Text style={styles.logo}>Telegram Kids</Text>

        {step === 'phone' ? (
          <>
            <Text style={styles.title}>Введи номер телефона</Text>
            <Text style={styles.subtitle}>
              На твой Telegram придёт код подтверждения
            </Text>
            <TextInput
              style={styles.input}
              value={phone}
              onChangeText={setPhone}
              placeholder="+7 900 000 00 00"
              placeholderTextColor="#555"
              keyboardType="phone-pad"
              autoFocus
              returnKeyType="done"
              onSubmitEditing={handleSendCode}
            />
            <TouchableOpacity
              style={[styles.btn, (!phone.trim() || loading) && styles.btnDisabled]}
              onPress={handleSendCode}
              disabled={!phone.trim() || loading}
            >
              {loading
                ? <ActivityIndicator color="#fff" />
                : <Text style={styles.btnText}>Получить код</Text>
              }
            </TouchableOpacity>
          </>
        ) : (
          <>
            <Text style={styles.title}>Введи код из Telegram</Text>
            <Text style={styles.subtitle}>
              Код отправлен на номер{'\n'}{phone}
            </Text>
            <TextInput
              style={[styles.input, styles.codeInput]}
              value={code}
              onChangeText={setCode}
              placeholder="12345"
              placeholderTextColor="#555"
              keyboardType="number-pad"
              maxLength={6}
              autoFocus
              returnKeyType="done"
              onSubmitEditing={handleVerifyCode}
            />
            <TouchableOpacity
              style={[styles.btn, (!code.trim() || loading) && styles.btnDisabled]}
              onPress={handleVerifyCode}
              disabled={!code.trim() || loading}
            >
              {loading
                ? <ActivityIndicator color="#fff" />
                : <Text style={styles.btnText}>Войти</Text>
              }
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.backBtn}
              onPress={() => { setStep('phone'); setCode(''); }}
            >
              <Text style={styles.backText}>Изменить номер</Text>
            </TouchableOpacity>
          </>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#17212b' },
  inner: {
    flexGrow: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  logo: {
    color: '#5288c1',
    fontSize: 28,
    fontWeight: 'bold',
    marginBottom: 48,
    letterSpacing: 0.5,
  },
  title: {
    color: '#ffffff',
    fontSize: 22,
    fontWeight: '600',
    marginBottom: 10,
    textAlign: 'center',
  },
  subtitle: {
    color: '#aaaaaa',
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 28,
    lineHeight: 20,
  },
  input: {
    width: '100%',
    backgroundColor: '#242f3d',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    color: '#ffffff',
    fontSize: 17,
    marginBottom: 16,
  },
  codeInput: {
    textAlign: 'center',
    fontSize: 28,
    letterSpacing: 8,
  },
  btn: {
    width: '100%',
    backgroundColor: '#5288c1',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginBottom: 12,
  },
  btnDisabled: { opacity: 0.45 },
  btnText: { color: '#ffffff', fontSize: 16, fontWeight: '600' },
  backBtn: { paddingVertical: 10 },
  backText: { color: '#5288c1', fontSize: 14 },
});
