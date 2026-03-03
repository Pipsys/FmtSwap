import { Link, NavLink, Outlet } from 'react-router-dom'
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
              <summary className={styles.profileTrigger}>
                Профиль
                {/* <span className={styles.dropdownCaret}>▾</span> */}
              </summary>
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

      <main className={styles.main}>
        <Outlet />
      </main>

      <footer className={styles.footer}>
        <span>fmtSwap · конвертация документов</span>
      </footer>
    </div>
  )
}
