import { useFeatureFlagsStore } from '../store/featureFlags';

// Использование: const { isEnabled } = useFeatureFlag('stories')
// if (!isEnabled) return null
export function useFeatureFlag(name) {
  const flags = useFeatureFlagsStore(state => state.flags);
  return { isEnabled: flags[name] ?? false };
}
