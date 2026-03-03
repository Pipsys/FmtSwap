/**
 * Displays the user's past conversions, fetched from /convert/history.
 */
import { useState, useEffect } from 'react'
import { convertApi } from '../api/client'
import styles from './HistoryList.module.css'

export default function HistoryList({ refreshKey }) {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    convertApi.history()
      .then((res) => setTasks(res.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [refreshKey])

  if (loading) return <p className={styles.dim}>Загрузка истории…</p>
  if (!tasks.length) return <p className={styles.dim}>Конвертаций пока нет.</p>

  const fmt = (iso) =>
    new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })

  return (
    <div className={styles.list}>
      {tasks.map((t) => (
        <div key={t.task_id} className={styles.row}>
          <div className={styles.left}>
            <span className={styles.name}>{t.original_filename}</span>
            <span className={styles.date}>{fmt(t.created_at)}</span>
          </div>
          <div className={styles.right}>
            <span className={`badge badge--${t.status}`}>
              {{ pending:'В очереди', processing:'Конвертация', done:'Готово', failed:'Ошибка' }[t.status]}
            </span>
            {t.status === 'done' && t.output_filename && (
              <a
                href={convertApi.downloadUrl(t.output_filename)}
                className={styles.dl}
                download
              >↓ DOCX</a>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
