import { useCallback, useEffect, useState } from 'react'
import { hostingApi } from '../api/client'
import HostedFilesList from '../components/HostedFilesList'
import FileUploader from '../components/FileUploader'
import { useAuth } from '../context/AuthContext'
import styles from './FilesPage.module.css'

export default function FilesPage() {
  const { user } = useAuth()

  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [deletingId, setDeletingId] = useState(null)
  const [statsLoadingId, setStatsLoadingId] = useState(null)
  const [statsById, setStatsById] = useState({})

  const [uploadLifetime, setUploadLifetime] = useState('1d')
  const [uploadDescription, setUploadDescription] = useState('')
  const [uploadPassword, setUploadPassword] = useState('')

  const loadFiles = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await hostingApi.list()
      setItems(res.data.items || [])
    } catch (err) {
      setItems([])
      setError(err.response?.data?.detail || 'Не удалось загрузить список файлов')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadFiles()
  }, [loadFiles])

  const handleUpload = async (selectedFiles) => {
    setUploading(true)
    setProgress(0)
    setError('')
    try {
      await hostingApi.upload(
        selectedFiles,
        {
          lifetime: uploadLifetime,
          description: uploadDescription,
          password: uploadPassword,
        },
        setProgress,
      )
      setUploadPassword('')
      await loadFiles()
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка загрузки файлов')
    } finally {
      setUploading(false)
      setProgress(0)
    }
  }

  const handleDelete = async (fileId) => {
    setDeletingId(fileId)
    setError('')
    try {
      await hostingApi.remove(fileId)
      await loadFiles()
    } catch (err) {
      setError(err.response?.data?.detail || 'Не удалось удалить файл')
    } finally {
      setDeletingId(null)
    }
  }

  const handleUpdate = async (fileId, payload) => {
    setError('')
    try {
      await hostingApi.update(fileId, payload)
      await loadFiles()
    } catch (err) {
      setError(err.response?.data?.detail || 'Не удалось обновить параметры файла')
    }
  }

  const handleLoadStats = async (fileId, days = 7) => {
    setStatsLoadingId(fileId)
    setError('')
    try {
      const res = await hostingApi.stats(fileId, days)
      setStatsById((prev) => ({ ...prev, [fileId]: res.data }))
    } catch (err) {
      setError(err.response?.data?.detail || 'Не удалось загрузить статистику')
    } finally {
      setStatsLoadingId(null)
    }
  }

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <h1 className={styles.title}>Файловый хостинг</h1>
        <p className={styles.desc}>
          Загружайте файлы, защищайте ссылку паролем, задавайте срок хранения и делитесь ссылкой.
        </p>
        <div className={styles.badges}>
          <span className={styles.badge}>
            {user ? 'Авторизован: можно хранить бессрочно или задать срок действия' : 'Гость: хранение 15 минут'}
          </span>
          <span className={styles.badge}>{user ? 'Лимит: до 300 МБ на файл' : 'Лимит: до 100 МБ на файл'}</span>
        </div>
      </section>

      <section className={styles.optionsCard}>
        <h2 className={styles.optionsTitle}>Параметры загрузки</h2>
        <div className={styles.optionsGrid}>
          <label className={styles.optionField}>
            <span>Описание файла</span>
            <input
              type="text"
              value={uploadDescription}
              onChange={(e) => setUploadDescription(e.target.value)}
              placeholder="Например: Финальный отчёт для команды"
              maxLength={1000}
            />
          </label>

          <label className={styles.optionField}>
            <span>Пароль на ссылку (опционально)</span>
            <input
              type="password"
              value={uploadPassword}
              onChange={(e) => setUploadPassword(e.target.value)}
              placeholder="Минимум 4 символа"
            />
          </label>

          <label className={styles.optionField}>
            <span>Срок действия ссылки</span>
            <select
              value={uploadLifetime}
              onChange={(e) => setUploadLifetime(e.target.value)}
              disabled={!user}
              title={!user ? 'Для гостей фиксированный срок хранения 15 минут' : ''}
            >
              <option value="1h">1 час</option>
              <option value="1d">1 день</option>
              <option value="1w">1 неделя</option>
              <option value="forever">Бессрочно</option>
            </select>
          </label>
        </div>
        {!user && <p className={styles.note}>Для гостей срок действия устанавливается автоматически: 15 минут.</p>}
      </section>

      <FileUploader uploading={uploading} progress={progress} onUpload={handleUpload} />

      <section className={styles.listCard}>
        <header className={styles.listHead}>
          <h2 className={styles.sectionTitle}>Ваши файлы</h2>
          <p className={styles.sectionSub}>
            {user ? 'Отображаются все ваши загруженные файлы.' : 'Отображаются файлы текущей гостевой сессии.'}
          </p>
        </header>

        {loading ? (
          <p className={styles.dim}>Загрузка списка...</p>
        ) : (
          <HostedFilesList
            items={items}
            isAuthenticated={Boolean(user)}
            deletingId={deletingId}
            onDelete={handleDelete}
            onNeedRefresh={loadFiles}
            onUpdate={handleUpdate}
            onLoadStats={handleLoadStats}
            statsById={statsById}
            statsLoadingId={statsLoadingId}
          />
        )}
      </section>

      {error ? <p className="error-msg">{error}</p> : null}
    </div>
  )
}
