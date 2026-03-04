import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  ARCHIVER_CONVERSION_OPTIONS,
  COMPRESSION_CONVERSION_OPTIONS,
  MEDIA_IMAGE_CONVERSION_OPTIONS,
  MEDIA_VIDEO_CONVERSION_OPTIONS,
  PDF_CONVERSION_OPTIONS,
} from '../constants/conversions'
import styles from './Layout.module.css'

export default function Layout() {
  const { user, logout } = useAuth()
  const location = useLocation()

  const handleLogout = async () => {
    await logout()
  }

  const handleLogoutFromMenu = async (event) => {
    closeDropdown(event)
    await handleLogout()
  }

  const closeDropdown = (event) => {
    event.currentTarget.closest('details')?.removeAttribute('open')
  }

  const handleDropdownToggle = (event) => {
    const current = event.currentTarget
    if (!current.open) return

    const container = current.parentElement
    container?.querySelectorAll('details[open]').forEach((item) => {
      if (item !== current) item.removeAttribute('open')
    })
  }

  const mediaImageOptions = MEDIA_IMAGE_CONVERSION_OPTIONS
  const mediaVideoOptions = MEDIA_VIDEO_CONVERSION_OPTIONS
  const isProfileRoute = location.pathname.startsWith('/profile')

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <Link to="/" className={styles.logo}>
            <span>
              FMT<span className={styles.logoArrow}>→</span>SWAP
            </span>
          </Link>

          <details className={styles.dropdown} onToggle={handleDropdownToggle}>
            <summary className={styles.dropdownTrigger}>
              Конвертация PDF
              <span className={styles.dropdownCaret}>▾</span>
            </summary>
            <div className={styles.dropdownMenu}>
              {PDF_CONVERSION_OPTIONS.map((option) => (
                <NavLink
                  key={option.type}
                  to={option.route}
                  end={option.route === '/'}
                  onClick={closeDropdown}
                  className={({ isActive }) =>
                    `${styles.dropdownItem} ${isActive ? styles.dropdownItemActive : ''}`.trim()
                  }
                >
                  {option.shortTitle}
                </NavLink>
              ))}
            </div>
          </details>

          <details className={styles.dropdown} onToggle={handleDropdownToggle}>
            <summary className={styles.dropdownTrigger}>
              Конвертация изображений
              <span className={styles.dropdownCaret}>▾</span>
            </summary>
            <div className={`${styles.dropdownMenu} ${styles.dropdownMenuWide}`}>
              {mediaImageOptions.map((option) => (
                <NavLink
                  key={option.type}
                  to={option.route}
                  onClick={closeDropdown}
                  className={({ isActive }) =>
                    `${styles.dropdownItem} ${isActive ? styles.dropdownItemActive : ''}`.trim()
                  }
                >
                  {option.shortTitle}
                </NavLink>
              ))}
            </div>
          </details>

          <details className={styles.dropdown} onToggle={handleDropdownToggle}>
            <summary className={styles.dropdownTrigger}>
              Видео и аудио
              <span className={styles.dropdownCaret}>▾</span>
            </summary>
            <div className={`${styles.dropdownMenu} ${styles.dropdownMenuWide}`}>
              {mediaVideoOptions.map((option) => (
                <NavLink
                  key={option.type}
                  to={option.route}
                  onClick={closeDropdown}
                  className={({ isActive }) =>
                    `${styles.dropdownItem} ${isActive ? styles.dropdownItemActive : ''}`.trim()
                  }
                >
                  {option.shortTitle}
                </NavLink>
              ))}
            </div>
          </details>

          <details className={styles.dropdown} onToggle={handleDropdownToggle}>
            <summary className={styles.dropdownTrigger}>
              Архиваторы
              <span className={styles.dropdownCaret}>▾</span>
            </summary>
            <div className={`${styles.dropdownMenu} ${styles.dropdownMenuWide}`}>
              {ARCHIVER_CONVERSION_OPTIONS.map((option) => (
                <NavLink
                  key={option.type}
                  to={option.route}
                  onClick={closeDropdown}
                  className={({ isActive }) =>
                    `${styles.dropdownItem} ${isActive ? styles.dropdownItemActive : ''}`.trim()
                  }
                >
                  {option.shortTitle}
                </NavLink>
              ))}
            </div>
          </details>

          <details className={styles.dropdown} onToggle={handleDropdownToggle}>
            <summary className={styles.dropdownTrigger}>
              Сжатия
              <span className={styles.dropdownCaret}>▾</span>
            </summary>
            <div className={`${styles.dropdownMenu} ${styles.dropdownMenuWide}`}>
              {COMPRESSION_CONVERSION_OPTIONS.map((option) => (
                <NavLink
                  key={option.type}
                  to={option.route}
                  onClick={closeDropdown}
                  className={({ isActive }) =>
                    `${styles.dropdownItem} ${isActive ? styles.dropdownItemActive : ''}`.trim()
                  }
                >
                  {option.shortTitle}
                </NavLink>
              ))}
            </div>
          </details>
        </div>

        <nav className={styles.nav}>
          {user ? (
            <details className={styles.dropdown} onToggle={handleDropdownToggle}>
              <summary className={styles.profileTrigger}>Профиль</summary>
              <div className={`${styles.dropdownMenu} ${styles.profileMenu}`}>
                <div className={styles.profileName}>@{user.username}</div>
                <Link to="/profile" className={styles.dropdownItem} onClick={closeDropdown}>
                  Перейти в профиль
                </Link>
                <button type="button" className={styles.profileLogoutBtn} onClick={handleLogoutFromMenu}>
                  Выйти из аккаунта
                </button>
              </div>
            </details>
          ) : (
            <>
              <Link to="/login" className={styles.authGhost}>
                Войти
              </Link>
              <Link to="/register" className={styles.authPrimary}>
                Регистрация
              </Link>
            </>
          )}
        </nav>
      </header>

      <main className={`${styles.main} ${isProfileRoute ? styles.mainWide : ''}`.trim()}>
        <Outlet />
      </main>

      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <div className={styles.footerBrand}>2026 © fmtswap.com</div>

          <nav className={styles.footerInline} aria-label="Нижние ссылки сайта">
            <Link to="/about" className={styles.footerLink}>
              О нас
            </Link>
            <span className={styles.footerSep}>·</span>
            <Link to="/terms" className={styles.footerLink}>
              Условия использования
            </Link>
            <span className={styles.footerSep}>·</span>
            <Link to="/privacy" className={styles.footerLink}>
              Конфиденциальность
            </Link>
            <span className={styles.footerSep}>·</span>
            <Link to="/program-rules" className={styles.footerLink}>
              Правила программы
            </Link>
            <span className={styles.footerSep}>·</span>
            <a href="mailto:contact@fmtswap.com" className={styles.footerLink}>
              Контакты
            </a>
            <span className={styles.footerSep}>·</span>
            <a href="mailto:support@fmtswap.com" className={styles.footerLink}>
              Поддержка
            </a>
            <span className={styles.footerSep}>·</span>
            <a href="https://t.me/fmtswap" target="_blank" rel="noreferrer" className={styles.footerLink}>
              Telegram
            </a>
            <span className={styles.footerSep}>·</span>
            <a href="https://github.com/fmtswap" target="_blank" rel="noreferrer" className={styles.footerLink}>
              GitHub
            </a>
          </nav>
        </div>
      </footer>
    </div>
  )
}
