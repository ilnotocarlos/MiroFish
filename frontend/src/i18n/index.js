import { createI18n } from 'vue-i18n'
import it from './locales/it.json'
import en from './locales/en.json'
import zh from './locales/zh.json'

const savedLocale = localStorage.getItem('mirofish-locale') || 'it'

const i18n = createI18n({
  legacy: false,
  locale: savedLocale,
  fallbackLocale: 'zh',
  messages: { it, en, zh }
})

export default i18n
