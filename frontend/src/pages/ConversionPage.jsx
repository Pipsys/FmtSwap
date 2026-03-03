import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import DropZone from '../components/DropZone'
import ConversionStatus from '../components/ConversionStatus'
import HistoryList from '../components/HistoryList'
import { CONVERSION_MAP } from '../constants/conversions'
import styles from './ConversionPage.module.css'

export default function ConversionPage({ conversionType }) {
  const config = CONVERSION_MAP[conversionType]
  const { user } = useAuth()
  const [active, setActive] = useState([])
  const [historyKey, setHistoryKey] = useState(0)

  if (!config) return <Navigate to="/" replace />

  const handleConversionStarted = (taskId, filename) => {
    setActive((prev) => [...prev, { taskId, filename }])
  }

  const handleDone = () => {
    setHistoryKey((k) => k + 1)
  }

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        {/* <p className={styles.kicker}>Добро пожаловать в fmtSwap</p> */}
        <h1 className={styles.title}>{config.title}</h1>
        <p className={styles.desc}>{config.description}</p>
        <div className={styles.meta}>
          <span className={styles.metaPill}>Без регистрации</span>
          <span className={styles.metaPill}>До 50 МБ</span>
          {user ? <span className={styles.metaPill}>История включена</span> : null}
        </div>
      </section>

      <section className={styles.section}>
        <DropZone
          conversionType={config.type}
          acceptedLabel={config.inputLabel}
          acceptedExtensions={config.inputExtensions}
          accept={config.inputAccept}
          onConversionStarted={handleConversionStarted}
        />

        {active.map((item) => (
          <ConversionStatus
            key={item.taskId}
            taskId={item.taskId}
            filename={item.filename}
            outputLabel={config.outputLabel}
            onDone={handleDone}
          />
        ))}
      </section>

      <section className={styles.features}>
        {config.featureChips.map(({ icon, label }) => (
          <div key={label} className={styles.chip}>
            <span className={styles.chipIcon}>{icon}</span>
            <span>{label}</span>
          </div>
        ))}
      </section>

      {user && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>История конвертаций</h2>
          <HistoryList refreshKey={historyKey} />
        </section>
      )}
    </div>
  )
}
