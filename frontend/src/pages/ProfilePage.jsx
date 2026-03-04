import { useEffect, useState } from 'react'
import { authApi } from '../api/client'
import HistoryList from '../components/HistoryList'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import styles from './ProfilePage.module.css'

export default function ProfilePage() {
  const { user, setUser } = useAuth()
  const { theme, setTheme, canUseDarkTheme } = useTheme()

  const [emailValue, setEmailValue] = useState('')
  const [emailPassword, setEmailPassword] = useState('')
  const [emailError, setEmailError] = useState('')
  const [emailSuccess, setEmailSuccess] = useState('')
  const [emailSaving, setEmailSaving] = useState(false)

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [passwordSuccess, setPasswordSuccess] = useState('')
  const [passwordSaving, setPasswordSaving] = useState(false)

  const [setupPassword, setSetupPassword] = useState('')
  const [setupSecret, setSetupSecret] = useState('')
  const [setupUri, setSetupUri] = useState('')
  const [enableCode, setEnableCode] = useState('')
  const [twofaError, setTwofaError] = useState('')
  const [twofaSuccess, setTwofaSuccess] = useState('')
  const [twofaLoading, setTwofaLoading] = useState(false)

  const [disablePassword, setDisablePassword] = useState('')
  const [disableCode, setDisableCode] = useState('')

  useEffect(() => {
    setEmailValue(user?.email || '')
  }, [user?.email])

  const handleEmailSubmit = async (e) => {
    e.preventDefault()
    setEmailError('')
    setEmailSuccess('')
    setEmailSaving(true)

    try {
      const res = await authApi.changeEmail(emailValue.trim(), emailPassword)
      setUser(res.data.user)
      setEmailPassword('')
      setEmailSuccess('Почта успешно обновлена')
    } catch (err) {
      setEmailError(err.response?.data?.detail || 'Не удалось обновить почту')
    } finally {
      setEmailSaving(false)
    }
  }

  const handlePasswordSubmit = async (e) => {
    e.preventDefault()
    setPasswordError('')
    setPasswordSuccess('')

    if (newPassword !== confirmPassword) {
      setPasswordError('Подтверждение пароля не совпадает')
      return
    }

    setPasswordSaving(true)
    try {
      const res = await authApi.changePassword(currentPassword, newPassword)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setPasswordSuccess(res.data.message || 'Пароль изменен')
    } catch (err) {
      setPasswordError(err.response?.data?.detail || 'Не удалось изменить пароль')
    } finally {
      setPasswordSaving(false)
    }
  }

  const handleTwoFactorSetup = async (e) => {
    e.preventDefault()
    setTwofaError('')
    setTwofaSuccess('')
    setTwofaLoading(true)

    try {
      const res = await authApi.setupTwoFactor(setupPassword)
      setSetupSecret(res.data.secret)
      setSetupUri(res.data.otpauth_url)
      setEnableCode('')
      setTwofaSuccess('Секрет создан. Добавьте его в приложение-аутентификатор и подтвердите кодом.')
    } catch (err) {
      setTwofaError(err.response?.data?.detail || 'Не удалось начать настройку 2FA')
    } finally {
      setTwofaLoading(false)
    }
  }

  const handleTwoFactorEnable = async (e) => {
    e.preventDefault()
    setTwofaError('')
    setTwofaSuccess('')
    setTwofaLoading(true)

    try {
      const res = await authApi.enableTwoFactor(enableCode)
      setUser(res.data.user)
      setSetupPassword('')
      setSetupSecret('')
      setSetupUri('')
      setEnableCode('')
      setTwofaSuccess('Двухфакторная авторизация включена')
    } catch (err) {
      setTwofaError(err.response?.data?.detail || 'Не удалось включить 2FA')
    } finally {
      setTwofaLoading(false)
    }
  }

  const handleTwoFactorDisable = async (e) => {
    e.preventDefault()
    setTwofaError('')
    setTwofaSuccess('')
    setTwofaLoading(true)

    try {
      const res = await authApi.disableTwoFactor(disablePassword, disableCode)
      setUser(res.data.user)
      setDisablePassword('')
      setDisableCode('')
      setTwofaSuccess('Двухфакторная авторизация отключена')
    } catch (err) {
      setTwofaError(err.response?.data?.detail || 'Не удалось отключить 2FA')
    } finally {
      setTwofaLoading(false)
    }
  }

  const twofaEnabled = Boolean(user?.twofa_enabled)
  const userInitial = (user?.username?.[0] || '?').toUpperCase()

  return (
    <div className={styles.page}>
      <aside className={styles.summaryCard}>
        <div className={styles.profileIdentity}>
          <div className={styles.avatar}>{userInitial}</div>
          <div>
            <p className={styles.kicker}>Личный кабинет</p>
            <h1 className={styles.title}>@{user?.username}</h1>
            <p className={styles.email}>{user?.email}</p>
          </div>
        </div>

        {/* <div className={styles.badges}>
          <span className={`${styles.badge} ${twofaEnabled ? styles.badgeOn : styles.badgeOff}`}>
            2FA: {twofaEnabled ? 'включена' : 'выключена'}
          </span>
          <span className={styles.badge}>Тема: {theme === 'dark' ? 'тёмная' : 'светлая'}</span>
        </div> */}

        {/* <p className={styles.summaryText}>
          Здесь вы можете безопасно управлять почтой, паролем, двухфакторной авторизацией и историей загруженных файлов.
        </p> */}

        <nav className={styles.quickNav} aria-label="Быстрый переход по профилю">
          <a href="#account" className={styles.quickLink}>
            Аккаунт
          </a>
          <a href="#security" className={styles.quickLink}>
            Безопасность
          </a>
          <a href="#interface" className={styles.quickLink}>
            Интерфейс
          </a>
          <a href="#history" className={styles.quickLink}>
            История файлов
          </a>
        </nav>
      </aside>

      <div className={styles.content}>
        <section className={styles.panel} id="account">
          <header className={styles.panelHead}>
            <h2 className={styles.sectionTitle}>Аккаунт</h2>
            <p className={styles.sectionSub}>Обновите данные для входа, чтобы сохранить доступ к аккаунту.</p>
          </header>

          <div className={styles.gridTwo}>
            <form className={styles.formCard} onSubmit={handleEmailSubmit}>
              <h3 className={styles.formTitle}>Смена почты</h3>
              <p className={styles.formHint}>Новая почта будет использоваться для входа и уведомлений.</p>

              <label className={styles.field}>
                <span className={styles.fieldLabel}>Новая почта</span>
                <input
                  className={styles.input}
                  type="email"
                  value={emailValue}
                  onChange={(e) => setEmailValue(e.target.value)}
                  placeholder="user@example.com"
                  required
                />
              </label>

              <label className={styles.field}>
                <span className={styles.fieldLabel}>Текущий пароль</span>
                <input
                  className={styles.input}
                  type="password"
                  value={emailPassword}
                  onChange={(e) => setEmailPassword(e.target.value)}
                  placeholder="Введите пароль"
                  required
                />
              </label>

              <button type="submit" className="btn-primary" disabled={emailSaving}>
                {emailSaving ? 'Сохраняем...' : 'Сменить почту'}
              </button>

              {emailError ? <p className="error-msg">{emailError}</p> : null}
              {emailSuccess ? <p className={styles.success}>{emailSuccess}</p> : null}
            </form>

            <form className={styles.formCard} onSubmit={handlePasswordSubmit}>
              <h3 className={styles.formTitle}>Смена пароля</h3>
              <p className={styles.formHint}>Используйте сложный пароль длиной не менее 8 символов.</p>

              <label className={styles.field}>
                <span className={styles.fieldLabel}>Текущий пароль</span>
                <input
                  className={styles.input}
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="Введите текущий пароль"
                  required
                />
              </label>

              <label className={styles.field}>
                <span className={styles.fieldLabel}>Новый пароль</span>
                <input
                  className={styles.input}
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Минимум 8 символов"
                  required
                  minLength={8}
                />
              </label>

              <label className={styles.field}>
                <span className={styles.fieldLabel}>Подтверждение нового пароля</span>
                <input
                  className={styles.input}
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Повторите новый пароль"
                  required
                  minLength={8}
                />
              </label>

              <button type="submit" className="btn-primary" disabled={passwordSaving}>
                {passwordSaving ? 'Сохраняем...' : 'Сменить пароль'}
              </button>

              {passwordError ? <p className="error-msg">{passwordError}</p> : null}
              {passwordSuccess ? <p className={styles.success}>{passwordSuccess}</p> : null}
            </form>
          </div>
        </section>

        <section className={styles.panel} id="security">
          <header className={styles.panelHead}>
            <h2 className={styles.sectionTitle}>Безопасность</h2>
            <p className={styles.sectionSub}>Добавьте второй уровень защиты входа через код из приложения.</p>
          </header>

          <p className={styles.statusLine}>
            Текущий статус:
            <span className={`${styles.statusBadge} ${twofaEnabled ? styles.badgeOn : styles.badgeOff}`}>
              {twofaEnabled ? 'Включена' : 'Выключена'}
            </span>
          </p>

          {!twofaEnabled ? (
            <div className={styles.gridTwo}>
              <form className={styles.formCard} onSubmit={handleTwoFactorSetup}>
                <h3 className={styles.formTitle}>Шаг 1. Создать секрет</h3>
                <p className={styles.formHint}>Подтвердите текущий пароль, чтобы получить секретный ключ.</p>

                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Текущий пароль</span>
                  <input
                    className={styles.input}
                    type="password"
                    value={setupPassword}
                    onChange={(e) => setSetupPassword(e.target.value)}
                    placeholder="Введите пароль"
                    required
                  />
                </label>

                <button type="submit" className="btn-primary" disabled={twofaLoading}>
                  {twofaLoading ? 'Создаем...' : 'Начать настройку 2FA'}
                </button>
              </form>

              <form className={styles.formCard} onSubmit={handleTwoFactorEnable}>
                <h3 className={styles.formTitle}>Шаг 2. Подтвердить код</h3>
                <p className={styles.formHint}>Добавьте ключ в приложение-аутентификатор и введите 6-значный код.</p>

                {setupSecret ? (
                  <>
                    <div className={styles.secretBox}>Секрет: {setupSecret}</div>
                    <a href={setupUri} className={styles.uri} target="_blank" rel="noreferrer">
                      Открыть ссылку для приложения-аутентификатора
                    </a>
                  </>
                ) : (
                  <p className={styles.helper}>Сначала выполните шаг 1 и получите секрет.</p>
                )}

                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Код из приложения (6 цифр)</span>
                  <input
                    className={styles.input}
                    type="text"
                    value={enableCode}
                    onChange={(e) => setEnableCode(e.target.value)}
                    placeholder="123456"
                    required
                  />
                </label>

                <button type="submit" className="btn-primary" disabled={!setupSecret || twofaLoading}>
                  {twofaLoading ? 'Подтверждаем...' : 'Подтвердить и включить 2FA'}
                </button>
              </form>
            </div>
          ) : (
            <form className={styles.formCard} onSubmit={handleTwoFactorDisable}>
              <h3 className={styles.formTitle}>Отключение 2FA</h3>

              <label className={styles.field}>
                <span className={styles.fieldLabel}>Текущий пароль</span>
                <input
                  className={styles.input}
                  type="password"
                  value={disablePassword}
                  onChange={(e) => setDisablePassword(e.target.value)}
                  placeholder="Введите пароль"
                  required
                />
              </label>

              <label className={styles.field}>
                <span className={styles.fieldLabel}>Код из приложения</span>
                <input
                  className={styles.input}
                  type="text"
                  value={disableCode}
                  onChange={(e) => setDisableCode(e.target.value)}
                  placeholder="123456"
                  required
                />
              </label>

              <button type="submit" className="btn-danger" disabled={twofaLoading}>
                {twofaLoading ? 'Отключаем...' : 'Отключить 2FA'}
              </button>
            </form>
          )}

          {twofaError ? <p className="error-msg">{twofaError}</p> : null}
          {twofaSuccess ? <p className={styles.success}>{twofaSuccess}</p> : null}
        </section>

        <section className={styles.panel} id="interface">
          <header className={styles.panelHead}>
            <h2 className={styles.sectionTitle}>Интерфейс</h2>
            <p className={styles.sectionSub}>Выберите удобную тему оформления.</p>
          </header>

          <div className={styles.themeGrid}>
            <label className={`${styles.option} ${theme === 'light' ? styles.optionActive : ''}`}>
              <input
                type="radio"
                name="theme"
                value="light"
                checked={theme === 'light'}
                onChange={() => setTheme('light')}
              />
              <div className={styles.optionBody}>
                <span className={`${styles.themeChip} ${styles.themeChipLight}`} />
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
              <div className={styles.optionBody}>
                <span className={`${styles.themeChip} ${styles.themeChipDark}`} />
                <p className={styles.optionTitle}>Тёмная</p>
                <p className={styles.optionDesc}>Классическая тёмная тема приложения.</p>
              </div>
            </label>
          </div>
        </section>

        <section className={styles.panel} id="history">
          <header className={styles.panelHead}>
            <h2 className={styles.sectionTitle}>История всех загруженных файлов</h2>
            <p className={styles.sectionSub}>Быстрый поиск по имени файла и типу конвертации.</p>
          </header>

          <HistoryList
            refreshKey={0}
            conversionType=""
            enableSearch
            searchPlaceholder="Поиск по имени файла или типу конвертации"
          />
        </section>
      </div>
    </div>
  )
}
