import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { hostingApi } from '../api/client'
import styles from './SharePage.module.css'

function formatSize(size) {
  if (!Number.isFinite(size) || size <= 0) return '0 Б'
  const units = ['Б', 'КБ', 'МБ', 'ГБ']
  const idx = Math.min(units.length - 1, Math.floor(Math.log(size) / Math.log(1024)))
  const value = size / 1024 ** idx
  return `${value.toFixed(idx === 0 ? 0 : 1)} ${units[idx]}`
}

function extractErrorMessage(err, fallback) {
  if (err?.response?.data?.detail) return err.response.data.detail
  return fallback
}

export default function SharePage() {
  const { token = '' } = useParams()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [downloadError, setDownloadError] = useState('')
  const [data, setData] = useState(null)
  const [password, setPassword] = useState('')
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    if (!token) return
    setLoading(true)
    setError('')

    hostingApi
      .shareInfo(token)
      .then((res) => setData(res.data))
      .catch((err) => {
        setData(null)
        setError(extractErrorMessage(err, 'Файл не найден или срок хранения истёк'))
      })
      .finally(() => setLoading(false))
  }, [token])

  const handleDownload = async () => {
    if (!data) return
    if (data.is_password_protected && !password.trim()) {
      setDownloadError('Введите пароль для скачивания файла')
      return
    }

    setDownloadError('')
    setDownloading(true)
    try {
      const res = await hostingApi.downloadBlob(token, password.trim())
      const blob = new Blob([res.data], { type: res.headers['content-type'] || 'application/octet-stream' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = data.original_filename || 'file'
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      if (err?.response?.data instanceof Blob) {
        try {
          const parsed = JSON.parse(await err.response.data.text())
          setDownloadError(parsed.detail || 'Не удалось скачать файл')
        } catch (_) {
          setDownloadError('Не удалось скачать файл')
        }
      } else {
        setDownloadError(extractErrorMessage(err, 'Не удалось скачать файл'))
      }
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className={styles.page}>
      <article className={styles.card}>
        <p className={styles.kicker}>Публичная ссылка</p>
        <h1 className={styles.title}>Скачивание файла</h1>

        {loading && <p className={styles.dim}>Проверяем ссылку...</p>}

        {!loading && error && (
          <div className={styles.errorBox}>
            <p>{error}</p>
            <Link to="/files" className={styles.back}>
              Перейти в хостинг
            </Link>
          </div>
        )}

        {!loading && !error && data && (
          <div className={styles.info}>
            <p>
              <b>Имя файла:</b> {data.original_filename}
            </p>
            <p>
              <b>Размер:</b> {formatSize(data.size_bytes)}
            </p>
            <p>
              <b>Загружен:</b>{' '}
              {new Date(data.created_at).toLocaleString('ru-RU', {
                day: '2-digit',
                month: 'long',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </p>
            {data.description ? (
              <p>
                <b>Комментарий:</b> {data.description}
              </p>
            ) : null}
            {data.expires_at ? (
              <p>
                <b>Удалится:</b>{' '}
                {new Date(data.expires_at).toLocaleString('ru-RU', {
                  day: '2-digit',
                  month: 'long',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </p>
            ) : (
              <p>
                <b>Срок хранения:</b> бессрочно
              </p>
            )}

            {data.is_password_protected && (
              <label className={styles.passField}>
                <span>Пароль к файлу</span>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Введите пароль"
                />
              </label>
            )}

            <button type="button" className={styles.downloadBtn} onClick={handleDownload} disabled={downloading}>
              {downloading ? 'Подготавливаем...' : 'Скачать файл'}
            </button>
            {downloadError ? <p className="error-msg">{downloadError}</p> : null}
          </div>
        )}
      </article>
    </div>
  )
}
