/**
 * Displays authenticated user's conversion history.
 */
import { useEffect, useState } from 'react'
import { convertApi } from '../api/client'
import styles from './HistoryList.module.css'

const PAGE_SIZE = 10

function getDownloadLabel(outputFilename) {
  const ext = outputFilename?.split('.').pop()?.toUpperCase()
  if (!ext) return 'Файл'
  if (ext === 'ZIP') return 'ZIP'
  return ext
}

export default function HistoryList({
  refreshKey,
  conversionType,
  enableSearch = false,
  searchPlaceholder = 'Поиск по имени файла',
}) {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [reloadTick, setReloadTick] = useState(0)
  const [deletingId, setDeletingId] = useState('')
  const [deleteError, setDeleteError] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    const timer = setTimeout(() => setSearchQuery(searchInput.trim()), 250)
    return () => clearTimeout(timer)
  }, [searchInput])

  useEffect(() => {
    setPage(1)
  }, [conversionType, refreshKey, searchQuery])

  useEffect(() => {
    setLoading(true)
    convertApi
      .history(page, PAGE_SIZE, conversionType, searchQuery)
      .then((res) => {
        setTasks(res.data.items || [])
        setTotal(res.data.total || 0)
      })
      .catch(() => {
        setTasks([])
        setTotal(0)
      })
      .finally(() => setLoading(false))
  }, [conversionType, refreshKey, page, reloadTick, searchQuery])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages)
    }
  }, [page, totalPages])

  if (loading) return <p className={styles.dim}>Загрузка истории...</p>
  if (!tasks.length) return <p className={styles.dim}>Конвертаций пока нет.</p>

  const startPage = Math.max(1, page - 2)
  const endPage = Math.min(totalPages, startPage + 4)
  const visiblePages = []
  for (let p = startPage; p <= endPage; p += 1) visiblePages.push(p)

  const fmt = (iso) =>
    new Date(iso).toLocaleString('ru-RU', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    })

  const handleDelete = async (taskId) => {
    setDeleteError('')
    setDeletingId(taskId)
    try {
      await convertApi.deleteTask(taskId)
      setReloadTick((tick) => tick + 1)
    } catch (err) {
      setDeleteError(err.response?.data?.detail || 'Не удалось удалить запись')
    } finally {
      setDeletingId('')
    }
  }

  return (
    <div className={styles.wrap}>
      {enableSearch && (
        <div className={styles.searchRow}>
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder={searchPlaceholder}
            className={styles.searchInput}
          />
        </div>
      )}

      <div className={styles.list}>
        {tasks.map((t) => (
          <div key={t.task_id} className={styles.row}>
            <div className={styles.left}>
              <span className={styles.name}>{t.original_filename}</span>
              <span className={styles.date}>{fmt(t.created_at)}</span>
            </div>
            <div className={styles.right}>
              <span className={`badge badge--${t.status}`}>
                {{
                  pending: 'В очереди',
                  processing: 'Конвертация',
                  done: 'Готово',
                  failed: 'Ошибка',
                }[t.status]}
              </span>
              {t.status === 'done' && t.output_filename && (
                <a href={convertApi.downloadUrl(t.output_filename)} className={styles.dl} download>
                  ↓ {getDownloadLabel(t.output_filename)}
                </a>
              )}
              <button
                type="button"
                className={styles.deleteBtn}
                onClick={() => handleDelete(t.task_id)}
                disabled={deletingId === t.task_id || t.status === 'pending' || t.status === 'processing'}
                title={
                  t.status === 'pending' || t.status === 'processing'
                    ? 'Удаление доступно после завершения конвертации'
                    : 'Удалить из истории'
                }
              >
                {deletingId === t.task_id ? 'Удаляем...' : 'Удалить'}
              </button>
            </div>
          </div>
        ))}
      </div>

      {deleteError && <p className="error-msg">{deleteError}</p>}

      {totalPages > 1 && (
        <div className={styles.pager}>
          <button className={styles.pageBtn} onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>
            ← Назад
          </button>

          <div className={styles.pageNumbers}>
            {visiblePages.map((p) => (
              <button
                key={p}
                className={`${styles.pageBtn} ${p === page ? styles.pageBtnActive : ''}`}
                onClick={() => setPage(p)}
              >
                {p}
              </button>
            ))}
          </div>

          <button
            className={styles.pageBtn}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
          >
            Вперёд →
          </button>
        </div>
      )}
    </div>
  )
}
