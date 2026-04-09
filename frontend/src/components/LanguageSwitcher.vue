<template>
  <button class="lang-switch" @click="toggleLocale" :title="currentLabel">
    {{ currentFlag }}
  </button>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { locale, t } = useI18n()

const currentFlag = computed(() => {
  if (locale.value === 'it') return 'IT'
  if (locale.value === 'en') return 'EN'
  return 'ZH'
})

const currentLabel = computed(() => {
  if (locale.value === 'it') return t('langSwitcher.switchToEn')
  if (locale.value === 'en') return t('langSwitcher.switchToZh')
  return t('langSwitcher.switchToIt')
})

const toggleLocale = () => {
  let newLocale
  if (locale.value === 'it') newLocale = 'en'
  else if (locale.value === 'en') newLocale = 'zh'
  else newLocale = 'it'
  locale.value = newLocale
  localStorage.setItem('mirofish-locale', newLocale)
}
</script>

<style scoped>
.lang-switch {
  background: transparent;
  border: 1px solid currentColor;
  color: inherit;
  padding: 4px 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1px;
  cursor: pointer;
  border-radius: 3px;
  transition: all 0.2s;
  opacity: 0.7;
}

.lang-switch:hover {
  opacity: 1;
}
</style>
