<template>
  <section class="preparation-panel">
    <div class="balance-card" :class="{ 'balance-card--loading': balanceLoading }">
      <div class="balance-chip" role="group" aria-label="Wavespeed 余额与密钥">
        <button
          type="button"
          class="balance-refresh-btn"
          :disabled="balanceLoading"
          @click="emit('refresh-balance')"
        >
          <span class="balance-info">
            <span class="balance-label">余额</span>
            <span class="balance-amount" :title="balanceDisplay">{{ balanceDisplay }}</span>
          </span>
        </button>
        <button
          type="button"
          class="balance-toggle"
          :aria-expanded="apiFormExpanded"
          @click="toggleApiForm"
        >
          密钥 <span class="toggle-arrow">{{ apiFormExpanded ? '▲' : '▼' }}</span>
        </button>
      </div>

      <transition name="api-panel">
        <div v-show="apiFormExpanded" class="api-input-panel" aria-live="polite">
          <label for="preparation_api_key">Wavespeed API 密钥</label>
          <div class="api-inline-row">
            <input
              id="preparation_api_key"
              :type="apiKeyVisible ? 'text' : 'password'"
              :value="apiKeyValue"
              placeholder="输入 Wavespeed API Key"
              autocomplete="off"
              @input="onInput"
              @blur="emit('validate-api-key')"
            />
            <button type="button" class="btn-icon" @click="toggleVisibility">
              {{ apiKeyVisible ? '🙈' : '👁️' }}
            </button>
            <button type="button" class="btn-icon" @click="emit('save-api-key')" :disabled="!isApiKeyValid">
              💾
            </button>
            <button type="button" class="btn-icon" @click="emit('clear-api-key')" :disabled="!hasStoredKey">
              ✖️
            </button>
          </div>
          <p v-if="apiKeyError" class="input-error">{{ apiKeyError }}</p>
          <p class="api-hint">密钥仅保存在本地浏览器，可随时折叠隐藏</p>
        </div>
      </transition>
    </div>

    <CardContainer
      class="task-card"
      title="任务管理"
      subtitle="多任务、一键切换"
      :collapsible="true"
      :initially-collapsed="false"
      persist-key="task-card"
      :error="taskError"
    >
      <template #actions>
        <div class="task-card-actions">
          <button type="button" class="btn-text" :disabled="!currentJobId" @click="emit('refresh-selected-task')">
            刷新
          </button>
          <button type="button" class="btn-text" :disabled="!currentJobId" @click="emit('toggle-polling')">
            {{ pollingActive ? '暂停轮询' : '恢复轮询' }}
          </button>
        </div>
      </template>
      <TaskList
        :tasks="taskHistory"
        :current-task-id="currentJobId"
        :describe-status="describeStatus"
        :format-timestamp="formatTimestamp"
        @select-task="emit('select-task', $event)"
        @remove-task="emit('remove-task', $event)"
      />
    </CardContainer>

    <CardContainer
      class="history-card"
      title="历史视频"
      subtitle="挂载网盘最近生成的产物"
      :collapsible="true"
      :initially-collapsed="false"
      persist-key="history-video-card"
    >
      <HistoryVideoList
        :items="historyVideos"
        :loading="historyLoading"
        :error="historyError"
        @refresh="emit('refresh-history')"
      />
    </CardContainer>

    <CardContainer
      class="settings-card"
      title="全局设置"
      subtitle="调试模式 · 轮询策略"
      :collapsible="true"
      :initially-collapsed="false"
      persist-key="preparation-settings-card"
    >
      <div class="settings-card__grid">
        <div class="settings-card__row">
          <div>
            <p class="settings-card__label">调试模式</p>
            <p class="settings-card__desc">{{ debugHint }}</p>
          </div>
          <label class="switch">
            <input type="checkbox" :checked="debugMode" @change="onDebugToggle" />
            <span class="switch__track"></span>
          </label>
        </div>
        <dl class="settings-card__meta">
          <div>
            <dt>API Base</dt>
            <dd><code>{{ appConfig.API_BASE }}</code></dd>
          </div>
          <div>
            <dt>轮询间隔</dt>
            <dd>{{ pollIntervalLabel }}</dd>
          </div>
          <div>
            <dt>请求超时</dt>
            <dd>{{ timeoutLabel }}</dd>
          </div>
        </dl>
      </div>
    </CardContainer>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import CardContainer from '@/layout/CardContainer.vue';
import TaskList from './TaskList.vue';
import type { TaskHistoryItem } from '@/stores/dashboard';
import type { FrontendAppConfig } from '@/types/app-config';
import HistoryVideoList from './HistoryVideoList.vue';
import type { HistoryVideoItem } from '@/types/history';

const props = defineProps<{
  isMobile: boolean;
  apiKeyValue: string;
  apiKeyVisible: boolean;
  apiKeyError: string;
  isApiKeyValid: boolean;
  hasStoredKey: boolean;
  balanceDisplay: string;
  balanceLoading: boolean;
  debugMode: boolean;
  debugHint: string;
  appConfig: FrontendAppConfig;
  errorMessage?: string | null;
  taskError?: string | null;
  taskHistory: TaskHistoryItem[];
  currentJobId: string | null;
  pollingActive: boolean;
  describeStatus: (status: string) => string;
  formatTimestamp: (timestamp: number) => string;
  historyVideos: HistoryVideoItem[];
  historyLoading: boolean;
  historyError: string;
}>();

const emit = defineEmits<{
  (event: 'update:apiKeyValue', value: string): void;
  (event: 'update:apiKeyVisible', value: boolean): void;
  (event: 'validate-api-key'): void;
  (event: 'save-api-key'): void;
  (event: 'clear-api-key'): void;
  (event: 'refresh-balance'): void;
  (event: 'refresh-selected-task'): void;
  (event: 'toggle-polling'): void;
  (event: 'select-task', value: string): void;
  (event: 'remove-task', value: string): void;
  (event: 'update:debug-mode', value: boolean): void;
  (event: 'refresh-history'): void;
}>();

function onInput(event: Event) {
  const target = event.target as HTMLInputElement;
  emit('update:apiKeyValue', target.value);
}

function toggleVisibility() {
  emit('update:apiKeyVisible', !props.apiKeyVisible);
}

const apiFormExpanded = ref(!props.hasStoredKey);
const pollIntervalLabel = computed(() => `${(props.appConfig.POLL_INTERVAL / 1000).toFixed(1)} 秒`);
const timeoutLabel = computed(() => `${(props.appConfig.API_TIMEOUT / 1000).toFixed(0)} 秒`);

watch(
  () => props.hasStoredKey,
  (hasKey) => {
    if (!hasKey) {
      apiFormExpanded.value = true;
    }
  }
);

function toggleApiForm() {
  apiFormExpanded.value = !apiFormExpanded.value;
}

function onDebugToggle(event: Event) {
  const target = event.target as HTMLInputElement;
  emit('update:debug-mode', target.checked);
}
</script>

<style scoped>
.preparation-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.preparation-panel__hero {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 20px;
  padding: 1.25rem;
  color: #e2e8f0;
}

.preparation-panel__eyebrow {
  text-transform: uppercase;
  font-size: 0.8rem;
  letter-spacing: 0.15em;
  color: rgba(191, 219, 254, 0.9);
  margin-bottom: 0.35rem;
}

.preparation-panel__hero h2 {
  margin: 0;
  font-size: 1.35rem;
}

.preparation-panel__hero p {
  margin: 0.35rem 0 0;
  font-size: 0.95rem;
  color: rgba(226, 232, 240, 0.85);
}

.preparation-panel__stack {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.preparation-panel__card {
  width: 100%;
  max-width: none;
}

.key-card {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.key-chip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.8rem 0.95rem;
  border-radius: 14px;
  border: 1px solid rgba(59, 130, 246, 0.25);
  background: linear-gradient(90deg, rgba(37, 99, 235, 0.25), rgba(15, 23, 42, 0.8));
}

.key-chip__info {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}

.key-chip__label {
  margin: 0;
  font-size: 0.8rem;
  letter-spacing: 0.08em;
  color: rgba(191, 219, 254, 0.9);
  text-transform: uppercase;
}

.key-chip__balance {
  margin: 0;
  font-size: 1rem;
  color: #e2e8f0;
  white-space: nowrap;
}

.key-chip__actions {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-shrink: 0;
}

.chip-btn {
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.4);
  background: rgba(37, 99, 235, 0.2);
  color: #dbeafe;
  padding: 0.4rem 0.9rem;
  font-size: 0.9rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.chip-btn.ghost {
  background: rgba(15, 23, 42, 0.65);
  border-color: rgba(148, 163, 184, 0.35);
  color: #cbd5e1;
}

.chip-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chip-btn .arrow {
  font-size: 0.8rem;
}

.btn-icon {
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(15, 23, 42, 0.7);
  color: #e5e7eb;
  border-radius: 10px;
  padding: 0.35rem 0.45rem;
  cursor: pointer;
}

.btn-text {
  border: none;
  background: none;
  color: #60a5fa;
  cursor: pointer;
}

.btn-text.danger {
  color: #f87171;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
}

.api-panel {
  border-top: 1px solid rgba(148, 163, 184, 0.25);
  padding-top: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.api-mini-row {
  display: flex;
  gap: 0.4rem;
  align-items: center;
}

.api-mini-row input {
  flex: 1;
  padding: 0.85rem;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(2, 6, 23, 0.85);
  color: #e2e8f0;
}

.api-hint {
  margin: 0;
  color: rgba(148, 163, 184, 0.95);
  font-size: 0.85rem;
}

.api-panel-enter-active,
.api-panel-leave-active {
  transition: opacity 0.2s ease, max-height 0.2s ease;
}

.api-panel-enter-from,
.api-panel-leave-to {
  opacity: 0;
  max-height: 0;
}

.task-card-actions {
  display: flex;
  gap: 0.5rem;
}

.settings-card__grid {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.settings-card__row {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: center;
}

.settings-card__label {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
}

.settings-card__desc {
  margin: 0.25rem 0 0;
  color: rgba(148, 163, 184, 0.95);
  font-size: 0.85rem;
}

.settings-card__meta {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.settings-card__meta div {
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 12px;
  padding: 0.65rem 0.85rem;
  background: rgba(15, 23, 42, 0.35);
}

.settings-card__meta dt {
  margin: 0;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: rgba(148, 163, 184, 0.9);
}

.settings-card__meta dd {
  margin: 0.35rem 0 0;
  font-weight: 600;
  font-size: 0.95rem;
  color: #e2e8f0;
}

.settings-card__meta code {
  font-size: 0.85rem;
  word-break: break-all;
}

.switch {
  position: relative;
  display: inline-flex;
  align-items: center;
  width: 48px;
  height: 26px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.switch__track {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(100, 116, 139, 0.6);
  border-radius: 999px;
  transition: background-color 0.2s ease;
}

.switch__track::after {
  content: '';
  position: absolute;
  height: 20px;
  width: 20px;
  left: 4px;
  top: 3px;
  background: #0f172a;
  border-radius: 50%;
  transition: transform 0.2s ease;
}

.switch input:checked + .switch__track {
  background-color: rgba(56, 189, 248, 0.85);
}

.switch input:checked + .switch__track::after {
  transform: translateX(18px);
}

@media (max-width: 640px) {
  .settings-card__meta {
    grid-template-columns: 1fr;
  }
}
</style>
