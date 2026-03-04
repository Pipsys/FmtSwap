import { useCallback, useMemo, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import styles from './FileUploader.module.css'

function formatSize(size) {
  if (!Number.isFinite(size) || size <= 0) return '0 Б'
  const units = ['Б', 'КБ', 'МБ', 'ГБ']
  const idx = Math.min(units.length - 1, Math.floor(Math.log(size) / Math.log(1024)))
  const value = size / 1024 ** idx
  return `${value.toFixed(idx === 0 ? 0 : 1)} ${units[idx]}`
}

export default function FileUploader({ uploading, progress, onUpload }) {
  const [selectedFiles, setSelectedFiles] = useState([])

  const onDrop = useCallback((acceptedFiles) => {
    if (!acceptedFiles?.length) return
    setSelectedFiles((prev) => [...prev, ...acceptedFiles])
  }, [])

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    noClick: true,
    multiple: true,
    disabled: uploading,
  })

  const totalSize = useMemo(
    () => selectedFiles.reduce((sum, file) => sum + (file?.size || 0), 0),
    [selectedFiles],
  )

  const handleUpload = async () => {
    if (!selectedFiles.length || uploading) return
    await onUpload(selectedFiles)
    setSelectedFiles([])
  }

  return (
    <section className={styles.card}>
      <div
        {...getRootProps()}
        className={`${styles.dropzone} ${isDragActive ? styles.dragActive : ''} ${uploading ? styles.disabled : ''}`}
      >
        <input {...getInputProps()} />
        <p className={styles.dropTitle}>Перетащите файлы сюда</p>
        <p className={styles.dropSub}>или выберите через кнопку</p>
        <button type="button" className="btn-ghost" onClick={open} disabled={uploading}>
          Выбрать файлы
        </button>
      </div>

      <div className={styles.actions}>
        <p className={styles.meta}>
          Выбрано: <b>{selectedFiles.length}</b> · Общий размер: <b>{formatSize(totalSize)}</b>
        </p>
        <div className={styles.buttons}>
          <button type="button" className="btn-ghost" onClick={() => setSelectedFiles([])} disabled={uploading}>
            Очистить
          </button>
          <button type="button" className="btn-primary" onClick={handleUpload} disabled={uploading || !selectedFiles.length}>
            {uploading ? `Загрузка ${progress}%` : 'Загрузить'}
          </button>
        </div>
      </div>

      {uploading && (
        <div className="progress-bar">
          <div className="progress-bar__fill" style={{ width: `${progress}%` }} />
        </div>
      )}
    </section>
  )
}
