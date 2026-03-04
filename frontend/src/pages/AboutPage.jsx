import styles from './AboutPage.module.css'

export default function AboutPage() {
  return (
    <div className={styles.page}>
      <article className={styles.card}>
        <p className={styles.kicker}>О сервисе</p>
        <h1 className={styles.title}>О нас</h1>
        <p className={styles.lead}>
          fmtSwap - онлайн-сервис для быстрой конвертации документов, изображений, видео и архивов в популярные форматы.
        </p>

        <div className={styles.grid}>
          <section className={styles.block}>
            <h2 className={styles.blockTitle}>Что мы делаем</h2>
            <p>
              Мы объединяем разные инструменты конвертации в одном интерфейсе, чтобы пользователь мог выполнять задачи
              без установки сложного ПО.
            </p>
          </section>

          <section className={styles.block}>
            <h2 className={styles.blockTitle}>Наш фокус</h2>
            <p>
              Скорость, понятный интерфейс, поддержка популярных форматов и аккуратная обработка файлов с сохранением
              качества результата.
            </p>
          </section>
        </div>
      </article>
    </div>
  )
}
