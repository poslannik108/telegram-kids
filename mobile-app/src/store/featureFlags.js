import { create } from 'zustand';
import { MMKV } from 'react-native-mmkv';
import { BASE_URL } from '../../config';

const storage = new MMKV();
const FLAGS_CACHE_KEY = 'feature_flags_v1';

const DEFAULT_FLAGS = {
  stories: false,
  video_notes: false,
  reactions: false,
  calls: false,
  stickers_animated: false,
  voice_messages: true,
  file_sharing: true,
  search_global: false,
};

function loadCachedFlags() {
  const raw = storage.getString(FLAGS_CACHE_KEY);
  if (!raw) return DEFAULT_FLAGS;
  try {
    return { ...DEFAULT_FLAGS, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_FLAGS;
  }
}

export const useFeatureFlagsStore = create(set => ({
  flags: loadCachedFlags(),
  fetchFlags: async () => {
    try {
      const res = await fetch(`${BASE_URL}/feature-flags`);
      const data = await res.json();
      storage.set(FLAGS_CACHE_KEY, JSON.stringify(data));
      set({ flags: { ...DEFAULT_FLAGS, ...data } });
    } catch {
      // оставляем кэш/дефолт
    }
  },
}));
