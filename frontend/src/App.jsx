import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { useAuth } from './context/AuthContext'
import { CONVERSION_OPTIONS } from './constants/conversions'
import AboutPage from './pages/AboutPage'
import ConversionPage from './pages/ConversionPage'
import FAQPage from './pages/FAQPage'
import FilesPage from './pages/FilesPage'
import LegalPage from './pages/LegalPage'
import LoginPage from './pages/LoginPage'
import ProfilePage from './pages/ProfilePage'
import RegisterPage from './pages/RegisterPage'
import SharePage from './pages/SharePage'

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
        <Route path="/terms" element={<LegalPage documentType="terms" />} />
        <Route path="/privacy" element={<LegalPage documentType="privacy" />} />
        <Route path="/program-rules" element={<LegalPage documentType="program_rules" />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/faq" element={<FAQPage />} />
        <Route path="/files" element={<FilesPage />} />
        <Route path="/share/:token" element={<SharePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
