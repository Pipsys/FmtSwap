import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import styles from './Layout.module.css'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <Link to="/" className={styles.logo}>
          <span className={styles.logo__icon}>⟆</span>
          <span>FMT<span className={styles.logo__arrow}>→</span>SWAP</span>
        </Link>
        <nav className={styles.nav}>
          {user ? (
            <>
              <span className={styles.username}>@{user.username}</span>
              <button className="btn-danger" onClick={handleLogout}>Выйти</button>
            </>
          ) : (
            <>
              <Link to="/login" className="btn-ghost" style={{ padding: '8px 18px', borderRadius: 'var(--radius)', border: '1px solid var(--border)', color: 'var(--text-dim)', fontFamily: 'var(--font-sans)', fontWeight: 700, fontSize: 13, letterSpacing: '.06em', textTransform: 'uppercase', textDecoration: 'none' }}>Войти</Link>
              <Link to="/register" className="btn-primary" style={{ padding: '8px 18px', borderRadius: 'var(--radius)', background: 'var(--accent)', color: '#080810', fontFamily: 'var(--font-sans)', fontWeight: 700, fontSize: 13, letterSpacing: '.06em', textTransform: 'uppercase', textDecoration: 'none' }}>Регистрация</Link>
            </>
          )}
        </nav>
      </header>
      <main className={styles.main}>
        <Outlet />
      </main>
      <footer className={styles.footer}>
        <span>fmtSwap Converter · Secure · Fast</span>
      </footer>
    </div>
  )
}
