import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { useAuth } from './context/AuthContext'
import { CONVERSION_OPTIONS } from './constants/conversions'
import ConversionPage from './pages/ConversionPage'
import LoginPage from './pages/LoginPage'
import ProfilePage from './pages/ProfilePage'
import RegisterPage from './pages/RegisterPage'

function RequireAuth({ children }) {
  const { user, loading } = useAuth()

  if (loading) {
    return <div style={{ padding: 24, color: 'var(--text-dim)' }}>Загрузка...</div>
  }

  return user ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        {CONVERSION_OPTIONS.map((option) => (
          <Route
            key={option.type}
            path={option.route}
            element={<ConversionPage conversionType={option.type} />}
          />
        ))}

        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route
          path="/profile"
          element={
            <RequireAuth>
              <ProfilePage />
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
