import React, { createContext, useContext, useEffect, useState } from 'react';
import { MMKV } from 'react-native-mmkv';
import { BASE_URL } from '../../config';

const storage = new MMKV();
const THEME_CACHE_KEY = 'app_theme_v1';

const DEFAULT_THEME = {
  colors: {
    bg: '#17212b',
    bgSecondary: '#0e1621',
    bgElement: '#1e2d3d',
    accent: '#2E86AB',
    bubbleIn: '#182533',
    bubbleOut: '#1B5E8A',
    text: '#ffffff',
    textSecondary: '#aaaaaa',
    divider: '#2b3a4a',
    danger: '#e53935',
    success: '#4caf50',
  },
  fonts: {
    sizeBase: 14,
    sizeSmall: 12,
    sizeLarge: 16,
    weightNormal: '400',
    weightBold: '600',
  },
  radii: {
    bubble: 18,
    button: 8,
    avatar: 50,
  },
  iconSet: 'material',
};

const ThemeContext = createContext(DEFAULT_THEME);

function loadCachedTheme() {
  const raw = storage.getString(THEME_CACHE_KEY);
  if (!raw) return DEFAULT_THEME;
  try {
    return JSON.parse(raw);
  } catch {
    return DEFAULT_THEME;
  }
}

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(loadCachedTheme);

  useEffect(() => {
    fetch(`${BASE_URL}/theme`)
      .then(r => r.json())
      .then(data => {
        storage.set(THEME_CACHE_KEY, JSON.stringify(data));
        setTheme(data);
      })
      .catch(() => {});
  }, []);

  return <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>;
}

export const ThemeContext_ = ThemeContext;
