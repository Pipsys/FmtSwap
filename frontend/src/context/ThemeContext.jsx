import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { useAuth } from './AuthContext'

const ThemeContext = createContext(null)
const STORAGE_KEY = 'fmtswap_theme'

function resolveInitialTheme(user) {
  if (!user) return 'light'

  const saved = window.localStorage.getItem(STORAGE_KEY)
  if (saved === 'dark' || saved === 'light') {
    return saved
  }

  return 'light'
}

export function ThemeProvider({ children }) {
  const { user } = useAuth()
  const [theme, setThemeState] = useState('light')

  useEffect(() => {
    setThemeState(resolveInitialTheme(user))
  }, [user])

  useEffect(() => {
    document.body.setAttribute('data-theme', theme)
  }, [theme])

  const setTheme = useCallback(
    (nextTheme) => {
      if (nextTheme !== 'light' && nextTheme !== 'dark') return
      if (nextTheme === 'dark' && !user) return

      setThemeState(nextTheme)
      window.localStorage.setItem(STORAGE_KEY, nextTheme)
    },
    [user],
  )

  const value = {
    theme,
    setTheme,
    canUseDarkTheme: Boolean(user),
  }

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  return useContext(ThemeContext)
}
