export const CONVERSION_OPTIONS = [
  {
    type: 'pdf_to_docx',
    route: '/',
    shortTitle: 'PDF → DOCX',
    title: 'PDF → DOCX',
    description:
      'Конвертируйте PDF в редактируемый документ Word. Подходит для отчётов, договоров и сканов с OCR.',
    inputLabel: 'PDF',
    inputExtensions: ['.pdf'],
    inputAccept: '.pdf,application/pdf',
    outputLabel: 'Скачать DOCX',
    outputHint: 'DOCX',
    featureChips: [
      // { icon: 'Tt', label: 'Текст и шрифты' },
      // { icon: 'Tb', label: 'Таблицы' },
      // { icon: 'Ls', label: 'Списки' },
      // { icon: 'Im', label: 'Изображения' },
    ],
  },
  {
    type: 'pdf_to_jpg',
    route: '/pdf-to-jpg',
    shortTitle: 'PDF → JPG',
    title: 'PDF → JPG',
    description:
      'Преобразуйте страницы PDF в JPG-изображения. На выходе вы получите ZIP-архив с изображениями страниц.',
    inputLabel: 'PDF',
    inputExtensions: ['.pdf'],
    inputAccept: '.pdf,application/pdf',
    outputLabel: 'Скачать ZIP (JPG)',
    outputHint: 'ZIP',
    featureChips: [
      // { icon: 'Pg', label: 'Каждая страница отдельным JPG' },
      // { icon: 'Hi', label: 'Высокая чёткость' },
      // { icon: 'Zip', label: 'Архив ZIP' },
      // { icon: 'Sh', label: 'Удобно для шаринга' },
    ],
  },
  {
    type: 'jpg_to_pdf',
    route: '/jpg-to-pdf',
    shortTitle: 'JPG → PDF',
    title: 'JPG → PDF',
    description:
      'Соберите JPG в PDF для отправки, печати или хранения. Поддерживаются файлы .jpg и .jpeg.',
    inputLabel: 'JPG',
    inputExtensions: ['.jpg', '.jpeg'],
    inputAccept: '.jpg,.jpeg,image/jpeg',
    outputLabel: 'Скачать PDF',
    outputHint: 'PDF',
    featureChips: [
      // { icon: 'Jpg', label: 'JPG/JPEG' },
      // { icon: 'Pdf', label: 'Один PDF-файл' },
      // { icon: 'Pr', label: 'Готово к печати' },
      // { icon: 'St', label: 'Быстрое сохранение' },
    ],
  },
  {
    type: 'word_to_pdf',
    route: '/word-to-pdf',
    shortTitle: 'WORD → PDF',
    title: 'WORD → PDF',
    description:
      'Преобразуйте документ Word в PDF-формат для стабильного просмотра и отправки без изменений структуры.',
    inputLabel: 'DOCX',
    inputExtensions: ['.docx'],
    inputAccept:
      '.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    outputLabel: 'Скачать PDF',
    outputHint: 'PDF',
    featureChips: [
      // { icon: 'Doc', label: 'Word DOCX' },
      // { icon: 'Fix', label: 'Фиксированный формат' },
      // { icon: 'Mail', label: 'Удобно отправлять' },
      // { icon: 'Safe', label: 'Чистый PDF' },
    ],
  },
]

export const CONVERSION_MAP = Object.fromEntries(
  CONVERSION_OPTIONS.map((option) => [option.type, option]),
)

export function findConversionByRoute(pathname) {
  return CONVERSION_OPTIONS.find((option) => option.route === pathname)
}
