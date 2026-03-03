import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { findConversionByRoute, CONVERSION_OPTIONS } from '../constants/conversions'
import styles from './Layout.module.css'

export default function Layout() {
  const { user, logout } = useAuth()
  const location = useLocation()

  const activeConversion = findConversionByRoute(location.pathname)

  const handleLogout = async () => {
    await logout()
  }

  const closeDropdown = (event) => {
    event.currentTarget.closest('details')?.removeAttribute('open')
  }

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <Link to="/" className={styles.logo}>
          <span>
            FMT<span className={styles.logoArrow}>→</span>SWAP
          </span>
        </Link>

        <nav className={styles.nav}>
          <details className={styles.dropdown}>
            <summary className={styles.dropdownTrigger}>
              {activeConversion?.shortTitle || 'Конвертация'}
              <span className={styles.dropdownCaret}>▾</span>
            </summary>
            <div className={styles.dropdownMenu}>
              {CONVERSION_OPTIONS.map((option) => (
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

          {user ? (
            <>
              <Link to="/profile" className={styles.profileLink}>
                Профиль
              </Link>
              <span className={styles.username}>@{user.username}</span>
              <button className="btn-danger" onClick={handleLogout}>
                Выйти
              </button>
            </>
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
