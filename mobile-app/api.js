// Telegram Kids API Client

import AsyncStorage from '@react-native-async-storage/async-storage';

const BASE_URL = 'http://YOUR_SERVER_IP:8000';
const API_SECRET = 'change_this_to_random_string'; // совпадает с .env

// После логина используем токен ребёнка вместо общего секрета
async function getHeaders() {
  const token = await AsyncStorage.getItem('child_token');
  return {
    'Content-Type': 'application/json',
    'x-api-key': token || API_SECRET,
  };
}

// ============================================================
// АВТОРИЗАЦИЯ
// ============================================================

export async function requestCode(phone) {
  const h = await getHeaders();
  const res = await fetch(`${BASE_URL}/auth/request-code`, {
    method: 'POST',
    headers: h,
    body: JSON.stringify({ phone }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Не удалось отправить код');
  }
  return res.json();
}

export async function verifyCode(phone, code, phoneCodeHash) {
  const h = await getHeaders();
  const res = await fetch(`${BASE_URL}/auth/verify-code`, {
    method: 'POST',
    headers: h,
    body: JSON.stringify({ phone, code, phone_code_hash: phoneCodeHash }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Неверный код');
  }
  return res.json();
}

// ============================================================
// ЧАТЫ
// ============================================================

export async function getDialogs() {
  const h = await getHeaders();
  const res = await fetch(`${BASE_URL}/dialogs`, { headers: h });
  if (!res.ok) throw new Error('Ошибка загрузки чатов');
  return res.json();
}

export async function getMessages(chatId, limit = 30) {
  const h = await getHeaders();
  const res = await fetch(`${BASE_URL}/messages/${chatId}?limit=${limit}`, { headers: h });
  if (!res.ok) throw new Error('Ошибка загрузки сообщений');
  return res.json();
}

export async function sendMessage(chatId, text) {
  const h = await getHeaders();
  const res = await fetch(`${BASE_URL}/send-message`, {
    method: 'POST',
    headers: h,
    body: JSON.stringify({ chat_id: chatId, text }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Ошибка отправки');
  }
  return res.json();
}

// ============================================================
// ЗАПРОСЫ НА РАЗРЕШЕНИЕ
// ============================================================

export async function requestJoinChat(chatIdentifier) {
  const h = await getHeaders();
  const res = await fetch(`${BASE_URL}/join-chat`, {
    method: 'POST',
    headers: h,
    body: JSON.stringify({ chat_identifier: chatIdentifier }),
  });
  return res.json();
}

export async function requestUseBot(botUsername) {
  const h = await getHeaders();
  const res = await fetch(`${BASE_URL}/use-bot`, {
    method: 'POST',
    headers: h,
    body: JSON.stringify({ bot_username: botUsername }),
  });
  return res.json();
}

// ============================================================
// БЛОКИРОВКИ
// ============================================================

export async function getBlocked() {
  const h = await getHeaders();
  const res = await fetch(`${BASE_URL}/blocked`, { headers: h });
  return res.json();
}

// ============================================================
// КОНТАКТЫ
// ============================================================

export async function getContacts() {
  const h = await getHeaders();
  const res = await fetch(`${BASE_URL}/contacts`, { headers: h });
  if (!res.ok) throw new Error('Ошибка загрузки контактов');
  return res.json();
}

export async function checkLinkStatus() {
  const h = await getHeaders();
  const res = await fetch(`${BASE_URL}/auth/status`, { headers: h });
  if (!res.ok) return { is_linked: false };
  return res.json();
}
