import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import JpgToPdfPage from './pages/JpgToPdfPage'
import LoginPage from './pages/LoginPage'
import PdfToJpgPage from './pages/PdfToJpgPage'
import ProfilePage from './pages/ProfilePage'
import RegisterPage from './pages/RegisterPage'
import WordToPdfPage from './pages/WordToPdfPage'

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
        <Route path="/" element={<HomePage />} />
        <Route path="/pdf-to-jpg" element={<PdfToJpgPage />} />
        <Route path="/jpg-to-pdf" element={<JpgToPdfPage />} />
        <Route path="/word-to-pdf" element={<WordToPdfPage />} />
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
