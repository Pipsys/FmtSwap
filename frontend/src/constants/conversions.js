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
    featureChips: [],
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
    featureChips: [],
  },
  {
    type: 'jpg_to_pdf',
    route: '/jpg-to-pdf',
    shortTitle: 'JPG → PDF',
    title: 'JPG → PDF',
    description:
      'Загрузите один или несколько JPG/JPEG и получите единый PDF в правильном порядке.',
    inputLabel: 'JPG/JPEG',
    inputExtensions: ['.jpg', '.jpeg', '.jfif'],
    inputAccept: '.jpg,.jpeg,.jfif,image/jpeg',
    allowMultiple: true,
    outputLabel: 'Скачать PDF',
    outputHint: 'PDF',
    featureChips: [
      // { icon: 'Ml', label: 'Несколько изображений в один PDF' },
      // { icon: 'Ord', label: 'Порядок по имени файла' },
    ],
  },
  {
    type: 'word_to_pdf',
    route: '/word-to-pdf',
    shortTitle: 'WORD → PDF',
    title: 'WORD → PDF',
    description:
      'Преобразуйте документы Word (.docx/.doc/.docm) в PDF с максимально точным сохранением структуры.',
    inputLabel: 'DOC/DOCX',
    inputExtensions: ['.docx', '.doc', '.docm'],
    inputAccept:
      '.doc,.docx,.docm,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    outputLabel: 'Скачать PDF',
    outputHint: 'PDF',
    featureChips: [
      // { icon: 'Wd', label: 'Поддержка DOCX/DOC/DOCM' },
      // { icon: 'St', label: 'Сохранение структуры' },
      // { icon: 'Pr', label: 'Готово к печати' },
    ],
  },
]

export const CONVERSION_MAP = Object.fromEntries(
  CONVERSION_OPTIONS.map((option) => [option.type, option]),
)

export function findConversionByRoute(pathname) {
  return CONVERSION_OPTIONS.find((option) => option.route === pathname)
}
