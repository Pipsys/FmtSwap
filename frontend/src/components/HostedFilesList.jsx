import { useState } from 'react'
import { Link } from 'react-router-dom'
import FileCountdown from './FileCountdown'
import styles from './HostedFilesList.module.css'

function formatSize(size) {
  if (!Number.isFinite(size) || size <= 0) return '0 Б'
  const units = ['Б', 'КБ', 'МБ', 'ГБ']
  const idx = Math.min(units.length - 1, Math.floor(Math.log(size) / Math.log(1024)))
  const value = size / 1024 ** idx
  return `${value.toFixed(idx === 0 ? 0 : 1)} ${units[idx]}`
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('ru-RU', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function HostedFilesList({
  items,
  isAuthenticated,
  deletingId,
  onDelete,
  onNeedRefresh,
  onUpdate,
  onLoadStats,
  statsById = {},
  statsLoadingId = null,
}) {
  const [copiedId, setCopiedId] = useState('')
  const [descById, setDescById] = useState({})
  const [pwdById, setPwdById] = useState({})
  const [lifetimeById, setLifetimeById] = useState({})
  const [openDescriptionById, setOpenDescriptionById] = useState({})
  const [openEditDescriptionById, setOpenEditDescriptionById] = useState({})
  const [openStatsById, setOpenStatsById] = useState({})

  const toggleById = (setter, id) => {
    setter((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  const handleCopy = async (item) => {
    try {
      await navigator.clipboard.writeText(item.share_url)
      setCopiedId(String(item.id))
      setTimeout(() => setCopiedId(''), 1200)
    } catch (_) {
      setCopiedId('')
    }
  }

  const saveDescription = async (item) => {
    await onUpdate(item.id, {
      description: descById[item.id] ?? item.description ?? '',
    })
  }

  const setPassword = async (item) => {
    await onUpdate(item.id, {
      password: pwdById[item.id] ?? '',
    })
    setPwdById((prev) => ({ ...prev, [item.id]: '' }))
  }

  const removePassword = async (item) => {
    await onUpdate(item.id, { remove_password: true })
  }

  const extendLifetime = async (item) => {
    await onUpdate(item.id, {
      lifetime: lifetimeById[item.id] || '1d',
    })
  }

  if (!items.length) {
    return <p className={styles.empty}>Файлов пока нет. Загрузите первый файл выше.</p>
  }

  return (
    <div className={styles.list}>
      {items.map((item) => {
        const stats = statsById[item.id]
        const maxPoint = stats?.points?.reduce((max, point) => Math.max(max, point.views + point.downloads), 0) || 0

        return (
          <article key={item.id} className={styles.row}>
            <div className={styles.info}>
              <p className={styles.name} title={item.original_filename}>
                {item.original_filename}
              </p>
              <p className={styles.meta}>
                {formatSize(item.size_bytes)} · загружен {formatDate(item.created_at)}
              </p>
              <p className={styles.meta}>
                Скачиваний: <b>{item.download_count || 0}</b> · Последнее: <b>{formatDate(item.last_downloaded_at)}</b>
              </p>

              {item.description ? (
                <div className={styles.compactSection}>
                  <button
                    type="button"
                    className={styles.compactToggle}
                    onClick={() => toggleById(setOpenDescriptionById, item.id)}
                    aria-expanded={Boolean(openDescriptionById[item.id])}
                  >
                    Описание
                    <span className={styles.toggleIcon} aria-hidden="true">
                      {openDescriptionById[item.id] ? '▾' : '▸'}
                    </span>
                  </button>
                  {openDescriptionById[item.id] ? <p className={styles.desc}>{item.description}</p> : null}
                </div>
              ) : null}

              {item.is_password_protected ? <p className={styles.protected}>Ссылка защищена паролем</p> : null}

              {!isAuthenticated && item.expires_at && (
                <p className={styles.timer}>
                  До удаления: <b><FileCountdown expiresAt={item.expires_at} onExpire={onNeedRefresh} /></b>
                </p>
              )}
            </div>

            <div className={styles.actions}>
              <Link to={`/share/${item.token}`} className={styles.linkBtn}>
                Открыть ссылку
              </Link>
              <button type="button" className={styles.linkBtn} onClick={() => handleCopy(item)}>
                {copiedId === String(item.id) ? 'Скопировано' : 'Копировать ссылку'}
              </button>
              {isAuthenticated && (
                <>
                  <button type="button" className={styles.linkBtn} onClick={() => onLoadStats(item.id, 7)}>
                    {statsLoadingId === item.id ? 'Загрузка...' : 'Статистика'}
                  </button>
                  <button
                    type="button"
                    className={styles.deleteBtn}
                    onClick={() => onDelete(item.id)}
                    disabled={deletingId === item.id}
                  >
                    {deletingId === item.id ? 'Удаляем...' : 'Удалить'}
                  </button>
                </>
              )}
            </div>

            {isAuthenticated && (
              <div className={styles.manage}>
                <div className={styles.manageGroup}>
                  <button
                    type="button"
                    className={styles.manageToggle}
                    onClick={() => toggleById(setOpenEditDescriptionById, item.id)}
                    aria-expanded={Boolean(openEditDescriptionById[item.id])}
                  >
                    Описание
                    <span className={styles.toggleIcon} aria-hidden="true">
                      {openEditDescriptionById[item.id] ? '▾' : '▸'}
                    </span>
                  </button>
                  {openEditDescriptionById[item.id] ? (
                    <div className={styles.inline}>
                      <input
                        type="text"
                        value={descById[item.id] ?? item.description ?? ''}
                        onChange={(e) => setDescById((prev) => ({ ...prev, [item.id]: e.target.value }))}
                        placeholder="Комментарий к файлу"
                      />
                      <button type="button" className={styles.linkBtn} onClick={() => saveDescription(item)}>
                        Сохранить
                      </button>
                    </div>
                  ) : null}
                </div>

                <div className={styles.manageGroup}>
                  <label>Пароль ссылки</label>
                  <div className={styles.inline}>
                    <input
                      type="password"
                      value={pwdById[item.id] ?? ''}
                      onChange={(e) => setPwdById((prev) => ({ ...prev, [item.id]: e.target.value }))}
                      placeholder="Новый пароль"
                    />
                    <button type="button" className={styles.linkBtn} onClick={() => setPassword(item)}>
                      Установить
                    </button>
                    {item.is_password_protected && (
                      <button type="button" className={styles.linkBtn} onClick={() => removePassword(item)}>
                        Снять
                      </button>
                    )}
                  </div>
                </div>

                <div className={styles.manageGroup}>
                  <label>Продлить срок</label>
                  <div className={styles.inline}>
                    <select
                      value={lifetimeById[item.id] || '1d'}
                      onChange={(e) => setLifetimeById((prev) => ({ ...prev, [item.id]: e.target.value }))}
                    >
                      <option value="1h">1 час</option>
                      <option value="1d">1 день</option>
                      <option value="1w">1 неделя</option>
                      <option value="forever">Бессрочно</option>
                    </select>
                    <button type="button" className={styles.linkBtn} onClick={() => extendLifetime(item)}>
                      Применить
                    </button>
                  </div>
                </div>
              </div>
            )}

            {stats && (
              <div className={styles.statsSection}>
                <button
                  type="button"
                  className={styles.statsToggle}
                  onClick={() => toggleById(setOpenStatsById, item.id)}
                  aria-expanded={Boolean(openStatsById[item.id])}
                >
                  Переходы за 7 дней: просмотры и скачивания
                  <span className={styles.toggleIcon} aria-hidden="true">
                    {openStatsById[item.id] ? '▾' : '▸'}
                  </span>
                </button>
                {openStatsById[item.id] ? (
                  <div className={styles.stats}>
                    <div className={styles.chart}>
                      {stats.points.map((point) => {
                        const height = maxPoint > 0 ? Math.max(8, ((point.views + point.downloads) / maxPoint) * 68) : 8
                        return (
                          <div key={point.date} className={styles.barCol} title={`${point.date}: ${point.views}/${point.downloads}`}>
                            <div className={styles.bar} style={{ height: `${height}px` }}>
                              <span className={styles.barView} style={{ height: `${(point.views / Math.max(1, point.views + point.downloads)) * 100}%` }} />
                              <span className={styles.barDownload} style={{ height: `${(point.downloads / Math.max(1, point.views + point.downloads)) * 100}%` }} />
                            </div>
                            <span className={styles.barLabel}>{point.date.slice(5)}</span>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </article>
        )
      })}
    </div>
  )
}
