/**
 * Generic drag-and-drop upload zone.
 */
import { useCallback, useRef, useState } from 'react'
import { convertApi } from '../api/client'
import styles from './DropZone.module.css'

export default function DropZone({
  onConversionStarted,
  conversionType = 'pdf_to_docx',
  acceptedLabel = 'PDF',
  acceptedExtensions = ['.pdf'],
  accept = '.pdf,application/pdf',
  allowMultiple = false,
}) {
  const [dragging, setDragging] = useState(false)
  const [progress, setProgress] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef()

  const allowedExts = acceptedExtensions.map((item) => item.toLowerCase())
  const acceptsAnyExtension = allowedExts.includes('*')

  const handleFiles = useCallback(
    async (incoming) => {
      setError('')
      const fileList = Array.from(incoming || []).filter(Boolean)
      if (!fileList.length) return

      const selectedFiles = allowMultiple ? fileList : [fileList[0]]

      for (const file of selectedFiles) {
        const name = file.name.toLowerCase()
        const isAllowed = acceptsAnyExtension || allowedExts.some((ext) => name.endsWith(ext))
        if (!isAllowed) {
          const list = acceptedExtensions.map((ext) => ext.replace('.', '').toUpperCase()).join(', ')
          setError(`Выберите файл формата: ${list}`)
          return
        }

        if (file.size > 50 * 1024 * 1024) {
          setError(`Файл ${file.name} превышает ограничение 50 МБ`)
          return
        }
      }

      setUploading(true)
      setProgress(0)
      try {
        const payload = allowMultiple ? selectedFiles : selectedFiles[0]
        const res = await convertApi.upload(payload, conversionType, setProgress)

        const displayName =
          selectedFiles.length > 1
            ? `${selectedFiles[0].name} + ${selectedFiles.length - 1} файл(ов)`
            : selectedFiles[0].name

        onConversionStarted(res.data.task_id, displayName)
      } catch (err) {
        setError(err.response?.data?.detail || 'Ошибка загрузки файла')
      } finally {
        setUploading(false)
        setProgress(0)
      }
    },
    [acceptedExtensions, acceptsAnyExtension, allowMultiple, allowedExts, conversionType, onConversionStarted],
  )

  const onDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    handleFiles(e.dataTransfer.files)
  }

  return (
    <div
      className={`${styles.zone} ${dragging ? styles.dragging : ''} ${uploading ? styles.uploading : ''}`}
      onDragOver={(e) => {
        e.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      onClick={() => !uploading && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        multiple={allowMultiple}
        accept={accept}
        style={{ display: 'none' }}
        onChange={(e) => handleFiles(e.target.files)}
      />

      <div className={styles.icon}>
        {uploading ? (
          <span className={styles.spinner}>◌</span>
        ) : (
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14,2 14,8 20,8" />
            <line x1="12" y1="18" x2="12" y2="12" />
            <polyline points="9,15 12,12 15,15" />
          </svg>
        )}
      </div>

      <p className={styles.main}>
        {uploading
          ? `Загрузка... ${progress}%`
          : dragging
            ? 'Отпустите файл для загрузки'
            : allowMultiple
              ? `Перетащите ${acceptedLabel} файлы или нажмите для выбора`
              : `Перетащите ${acceptedLabel} или нажмите для выбора`}
      </p>
      <p className={styles.hint}>
        {acceptedLabel} · макс. 50 МБ{allowMultiple ? ' каждый' : ''}
      </p>

      <button
        type="button"
        className={`btn-primary ${styles.convertBtn}`}
        disabled={uploading}
        onClick={(e) => {
          e.stopPropagation()
          inputRef.current?.click()
        }}
      >
        {uploading ? 'Загрузка...' : 'Конвертировать'}
      </button>

      {uploading && (
        <div className="progress-bar" style={{ width: '80%', marginTop: 16 }}>
          <div className="progress-bar__fill" style={{ width: `${progress}%` }} />
        </div>
      )}

      {error && <p className="error-msg" style={{ marginTop: 12 }}>{error}</p>}
    </div>
  )
}
