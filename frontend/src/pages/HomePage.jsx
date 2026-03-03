import { useState } from 'react'
import DropZone from '../components/DropZone'
import ConversionStatus from '../components/ConversionStatus'
import HistoryList from '../components/HistoryList'
import styles from './HomePage.module.css'

export default function HomePage() {
  // Active (in-progress) conversions shown above the dropzone
  const [active, setActive] = useState([])
  // Bump this to trigger history reload
  const [historyKey, setHistoryKey] = useState(0)

  const handleConversionStarted = (taskId, filename) => {
    setActive((prev) => [...prev, { taskId, filename }])
  }

  const handleDone = () => {
    // Refresh history list when any conversion completes
    setHistoryKey((k) => k + 1)
  }

  return (
    <div className={styles.page}>
      {/* Hero */}
      <section className={styles.hero}>
        <h1 className={styles.title}>
          PDF <span className={styles.arrow}>→</span> DOCX
        </h1>
        <p className={styles.desc}>
          Конвертируйте PDF-документы в редактируемый формат Word.<br/>
          Сохраняются текст, форматирование, таблицы и структура.
        </p>
      </section>

      {/* Upload zone */}
      <section className={styles.section}>
        <DropZone onConversionStarted={handleConversionStarted} />

        {/* Active conversions */}
        {active.map((item) => (
          <ConversionStatus
            key={item.taskId}
            taskId={item.taskId}
            filename={item.filename}
            onDone={handleDone}
          />
        ))}
      </section>

      {/* Feature chips */}
      <section className={styles.features}>
        {[
          { icon: '⟆', label: 'Текст и шрифты' },
          { icon: '⊞', label: 'Таблицы' },
          { icon: '≡', label: 'Списки' },
          { icon: '⊕', label: 'Изображения' },
          { icon: '⚿', label: 'JWT + httpOnly' },
          { icon: '⊘', label: 'CSRF защита' },
        ].map(({ icon, label }) => (
          <div key={label} className={styles.chip}>
            <span className={styles.chipIcon}>{icon}</span>
            <span>{label}</span>
          </div>
        ))}
      </section>

      {/* History */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>История конвертаций</h2>
        <HistoryList refreshKey={historyKey} />
      </section>
    </div>
  )
}
