import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import { getLocales } from 'react-native-localize';
import { MMKV } from 'react-native-mmkv';
import { BASE_URL } from '../../config';

// Встроенные переводы — fallback когда сервер недоступен
import ruCommon from './locales/ru/common.json';
import ruAuth from './locales/ru/auth.json';
import ruChats from './locales/ru/chats.json';
import ruSettings from './locales/ru/settings.json';
import enCommon from './locales/en/common.json';
import enAuth from './locales/en/auth.json';
import enChats from './locales/en/chats.json';
import enSettings from './locales/en/settings.json';

const storage = new MMKV();
const SUPPORTED_LANGS = ['ru', 'en'];
const NAMESPACES = ['common', 'auth', 'chats', 'settings'];

const BUNDLED = {
  ru: { common: ruCommon, auth: ruAuth, chats: ruChats, settings: ruSettings },
  en: { common: enCommon, auth: enAuth, chats: enChats, settings: enSettings },
};

function getDeviceLang() {
  const locales = getLocales();
  const code = locales[0]?.languageCode ?? 'ru';
  return SUPPORTED_LANGS.includes(code) ? code : 'ru';
}

function cacheKey(lang, ns) {
  return `i18n_${lang}_${ns}_v1`;
}

function loadCachedNs(lang, ns) {
  const raw = storage.getString(cacheKey(lang, ns));
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}

async function fetchNs(lang, ns) {
  const res = await fetch(`${BASE_URL}/translations/${lang}/${ns}`);
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

export async function initI18n() {
  if (i18n.isInitialized) return i18n;

  const lang = getDeviceLang();
  const resources = { ru: {}, en: {} };

  // Инициализируем из встроенных + кэша (синхронно, без сети)
  for (const l of SUPPORTED_LANGS) {
    for (const ns of NAMESPACES) {
      const cached = loadCachedNs(l, ns);
      resources[l][ns] = cached ?? BUNDLED[l]?.[ns] ?? {};
    }
  }

  await i18n.use(initReactI18next).init({
    resources,
    lng: lang,
    fallbackLng: 'ru',
    ns: NAMESPACES,
    defaultNS: 'common',
    interpolation: { escapeValue: false },
  });

  // Обновляем с сервера в фоне — не блокируем запуск
  Promise.all(
    NAMESPACES.map(ns =>
      fetchNs(lang, ns)
        .then(data => {
          storage.set(cacheKey(lang, ns), JSON.stringify(data));
          i18n.addResourceBundle(lang, ns, data, true, true);
        })
        .catch(() => {})
    )
  );

  return i18n;
}

export default i18n;
