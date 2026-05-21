import React, { useEffect, useState } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, Alert,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Icon from 'react-native-vector-icons/MaterialIcons';

export default function SettingsScreen({ navigation }) {
  const [phone, setPhone] = useState('');

  useEffect(() => {
    AsyncStorage.getItem('child_phone').then(p => setPhone(p || '—'));
  }, []);

  function handleLogout() {
    Alert.alert(
      'Выход',
      'Выйти из аккаунта?',
      [
        { text: 'Отмена', style: 'cancel' },
        {
          text: 'Выйти',
          style: 'destructive',
          onPress: async () => {
            await AsyncStorage.multiRemove(['child_token', 'child_phone']);
            navigation.replace('Login');
          },
        },
      ]
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Аккаунт</Text>
        <View style={styles.row}>
          <Icon name="phone" size={20} color="#5288c1" style={styles.rowIcon} />
          <View>
            <Text style={styles.rowLabel}>Номер телефона</Text>
            <Text style={styles.rowValue}>{phone}</Text>
          </View>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Приложение</Text>
        <View style={styles.row}>
          <Icon name="info-outline" size={20} color="#5288c1" style={styles.rowIcon} />
          <View>
            <Text style={styles.rowLabel}>Версия</Text>
            <Text style={styles.rowValue}>1.0.0</Text>
          </View>
        </View>
        <View style={styles.row}>
          <Icon name="shield" size={20} color="#5288c1" style={styles.rowIcon} />
          <View>
            <Text style={styles.rowLabel}>Режим</Text>
            <Text style={styles.rowValue}>Родительский контроль активен</Text>
          </View>
        </View>
      </View>

      <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
        <Icon name="logout" size={20} color="#e53935" style={{ marginRight: 8 }} />
        <Text style={styles.logoutText}>Выйти из аккаунта</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#17212b', padding: 16 },
  section: {
    backgroundColor: '#1e2d3d',
    borderRadius: 12,
    marginBottom: 16,
    overflow: 'hidden',
  },
  sectionTitle: {
    color: '#5288c1',
    fontSize: 12,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 6,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderTopWidth: 0.5,
    borderTopColor: '#2b3a4a',
  },
  rowIcon: { marginRight: 14 },
  rowLabel: { color: '#aaaaaa', fontSize: 12, marginBottom: 2 },
  rowValue: { color: '#ffffff', fontSize: 15 },
  logoutBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#1e2d3d',
    borderRadius: 12,
    paddingVertical: 14,
  },
  logoutText: { color: '#e53935', fontSize: 16, fontWeight: '500' },
});
