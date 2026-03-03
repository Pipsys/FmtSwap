/**
 * Polls the /convert/:taskId endpoint every 2 seconds
 * and shows current status + download link when done.
 */
import { useState, useEffect, useRef } from 'react'
import { convertApi } from '../api/client'
import styles from './ConversionStatus.module.css'

export default function ConversionStatus({ taskId, filename, onDone }) {
  const [status, setStatus] = useState('pending')
  const [outputFilename, setOutputFilename] = useState(null)
  const [error, setError] = useState('')
  const intervalRef = useRef(null)

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await convertApi.status(taskId)
        const { status: s, output_filename, error_message } = res.data
        setStatus(s)
        if (s === 'done') {
          setOutputFilename(output_filename)
          clearInterval(intervalRef.current)
          onDone?.()
        }
        if (s === 'failed') {
          setError(error_message || 'Конвертация не удалась')
          clearInterval(intervalRef.current)
        }
      } catch {
        // ignore transient errors
      }
    }

    poll()
    intervalRef.current = setInterval(poll, 2000)
    return () => clearInterval(intervalRef.current)
  }, [taskId])

  const statusLabel = {
    pending: 'В очереди',
    processing: 'Конвертация…',
    done: 'Готово',
    failed: 'Ошибка',
  }[status] || status

  return (
    <div className={styles.card}>
      <div className={styles.row}>
        <div className={styles.info}>
          <span className={styles.filename}>{filename}</span>
          <span className={`badge badge--${status}`}>{statusLabel}</span>
        </div>
        {status === 'processing' && (
          <div className={styles.spinner}>⟳</div>
        )}
      </div>

      {(status === 'pending' || status === 'processing') && (
        <div className="progress-bar">
          <div
            className="progress-bar__fill"
            style={{ width: status === 'processing' ? '60%' : '20%', transition: 'width 2s ease' }}
          />
        </div>
      )}

      {status === 'done' && outputFilename && (
        <a
          href={convertApi.downloadUrl(outputFilename)}
          className={styles.download}
          download
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          Скачать DOCX
        </a>
      )}

      {status === 'failed' && (
        <p className="error-msg">{error}</p>
      )}
    </div>
  )
}
