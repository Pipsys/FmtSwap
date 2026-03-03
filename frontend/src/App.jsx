import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import JpgToPdfPage from './pages/JpgToPdfPage'
import LoginPage from './pages/LoginPage'
import PdfToJpgPage from './pages/PdfToJpgPage'
import RegisterPage from './pages/RegisterPage'
import WordToPdfPage from './pages/WordToPdfPage'

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
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
