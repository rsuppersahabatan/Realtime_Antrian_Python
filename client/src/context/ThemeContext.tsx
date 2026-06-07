import React, {
  useState,
  useEffect,
  useRef,
  useLayoutEffect,
  useMemo,
  ReactNode,
  Dispatch,
  SetStateAction,
} from 'react';

type Theme = string;

function usePrevious(theme: Theme): Theme | undefined {
  const ref = useRef<Theme | undefined>(undefined);
  useEffect(() => {
    ref.current = theme;
  });
  return ref.current;
}

function useStorageTheme(key: string): [Theme, Dispatch<SetStateAction<Theme>>] {
  const userPreference =
    !!window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;

  const [theme, setTheme] = useState<Theme>(
    localStorage.getItem(key) || (userPreference ? 'dark' : 'light')
  );

  useEffect(() => {
    localStorage.setItem(key, theme);
  }, [theme, key]);

  return [theme, setTheme];
}

type ThemeContextValue = {
  theme: Theme;
  toggleTheme: () => void;
};

export const ThemeContext = React.createContext<ThemeContextValue | undefined>(undefined);

type ThemeProviderProps = {
  children: ReactNode;
};

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  const [theme, setTheme] = useStorageTheme('theme');

  const oldTheme = usePrevious(theme);
  useLayoutEffect(() => {
    if (oldTheme) {
      document.documentElement.classList.remove(`theme-${oldTheme}`);
    }
    document.documentElement.classList.add(`theme-${theme}`);
  }, [theme, oldTheme]);

  function toggleTheme(): void {
    if (theme === 'light') setTheme('dark');
    else setTheme('light');
  }

  const value = useMemo<ThemeContextValue>(
    () => ({
      theme,
      toggleTheme,
    }),
    [theme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};
