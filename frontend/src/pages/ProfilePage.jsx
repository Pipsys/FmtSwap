import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import styles from './ProfilePage.module.css'

export default function ProfilePage() {
  const { user } = useAuth()
  const { theme, setTheme, canUseDarkTheme } = useTheme()

  return (
    <div className={styles.page}>
      <section className={styles.card}>
        <p className={styles.kicker}>Профиль пользователя</p>
        <h1 className={styles.title}>@{user?.username}</h1>
        <p className={styles.sub}>Здесь можно настроить отображение интерфейса.</p>

        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Тема интерфейса</h2>

          <label className={`${styles.option} ${theme === 'light' ? styles.optionActive : ''}`}>
            <input
              type="radio"
              name="theme"
              value="light"
              checked={theme === 'light'}
              onChange={() => setTheme('light')}
            />
            <div>
              <p className={styles.optionTitle}>Светлая</p>
              <p className={styles.optionDesc}>Тема по умолчанию: светлый фон, бирюзовые акценты и сетка.</p>
            </div>
          </label>

          <label
            className={`${styles.option} ${theme === 'dark' ? styles.optionActive : ''} ${!canUseDarkTheme ? styles.optionDisabled : ''}`}
          >
            <input
              type="radio"
              name="theme"
              value="dark"
              checked={theme === 'dark'}
              onChange={() => setTheme('dark')}
              disabled={!canUseDarkTheme}
            />
            <div>
              <p className={styles.optionTitle}>Тёмная</p>
              <p className={styles.optionDesc}>Классическая тёмная тема приложения.</p>
            </div>
          </label>
        </div>
      </section>
    </div>
  )
}
