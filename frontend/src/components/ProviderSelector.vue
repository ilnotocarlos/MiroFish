<template>
  <div class="provider-selector">
    <button
      class="provider-btn"
      :class="{ active: provider === 'lm-studio' }"
      @click="setProvider('lm-studio')"
      :disabled="switching"
      title="LM Studio (locale)"
    >
      Locale
    </button>
    <button
      class="provider-btn"
      :class="{ active: provider === 'anthropic' }"
      @click="setProvider('anthropic')"
      :disabled="switching"
      title="Anthropic Claude (cloud)"
    >
      Cloud
    </button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import service from '../api/index.js'

const provider = ref('lm-studio')
const switching = ref(false)

const fetchProvider = async () => {
  try {
    const res = await service.get('/api/config/provider')
    provider.value = res.provider || 'lm-studio'
  } catch {
    // Il backend potrebbe non essere raggiungibile; default locale
    provider.value = 'lm-studio'
  }
}

const setProvider = async (value) => {
  if (provider.value === value || switching.value) return
  switching.value = true
  try {
    await service.post('/api/config/provider', { provider: value })
    provider.value = value
  } catch (err) {
    console.error('Errore cambio provider:', err)
  } finally {
    switching.value = false
  }
}

onMounted(fetchProvider)
</script>

<style scoped>
.provider-selector {
  display: flex;
  gap: 0;
  margin-left: 12px;
}

.provider-btn {
  background: transparent;
  border: 1px solid currentColor;
  color: inherit;
  padding: 4px 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1px;
  cursor: pointer;
  transition: all 0.2s;
  opacity: 0.5;
}

.provider-btn:first-child {
  border-radius: 3px 0 0 3px;
  border-right: none;
}

.provider-btn:last-child {
  border-radius: 0 3px 3px 0;
}

.provider-btn.active {
  opacity: 1;
  background: rgba(255, 255, 255, 0.15);
}

.provider-btn:hover:not(:disabled) {
  opacity: 0.85;
}

.provider-btn:disabled {
  cursor: wait;
}
</style>
