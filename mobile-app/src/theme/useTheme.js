import { useContext } from 'react';
import { ThemeContext_ } from './ThemeProvider';

// Единая точка входа для темы во всех компонентах.
// Использование: const { colors, fonts, radii } = useTheme()
export const useTheme = () => useContext(ThemeContext_);
