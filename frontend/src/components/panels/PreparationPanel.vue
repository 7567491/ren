<template>
  <section class="panel preparation-panel card">
    <header class="panel-header">
      <div>
        <p class="panel-eyebrow">准备</p>
        <h2>API Key & 任务</h2>
        <p class="panel-subtitle">绑定 Wavespeed API、管理任务清单</p>
      </div>
      <div class="step-pill">Step 1</div>
    </header>

    <div class="api-tools">
      <div class="api-input">
        <label class="sr-only" for="prep_api_key">Wavespeed API Key</label>
        <input
          id="prep_api_key"
          :type="apiKeyVisible ? 'text' : 'password'"
          :value="apiKeyInput"
          placeholder="输入或粘贴 Wavespeed API Key"
          @input="$emit('update:api-key-input', ($event.target as HTMLInputElement).value)"
          @blur="$emit('validate-api-key')"
        />
        <button type="button" class="btn-icon" @click="$emit('toggle-api-key-visibility')">
          {{ apiKeyVisible ? '🙈' : '👁️' }}
        </button>
      </div>
      <div class="api-actions">
        <button type="button" class="btn-secondary" :disabled="!isApiKeyValid" @click="$emit('save-api-key')">保存</button>
        <button type="button" class="btn-secondary ghost" :disabled="!hasApiKey" @click="$emit('clear-api-key')">清除</button>
        <button type="button" class="btn-secondary ghost" :disabled="balanceLoading" @click="$emit('refresh-balance')">
          {{ balanceLoading ? '查询中…' : '刷新余额' }}
        </button>
      </div>
      <p v-if="apiKeyError" class="input-error">{{ apiKeyError }}</p>
      <p class="balance-display">{{ balanceDisplay }}</p>
    </div>

    <footer class="task-toolbar">
      <div>
        <strong>任务队列</strong>
        <p>最近 10 个任务，点击即可切换</p>
      </div>
      <div class="toolbar-actions">
        <button type="button" class="btn-text" :disabled="!currentJobId" @click="$emit('refresh-selected-task')">刷新</button>
        <button type="button" class="btn-text" :disabled="!currentJobId" @click="$emit('toggle-polling')">
          {{ pollingActive ? '暂停轮询' : '恢复轮询' }}
        </button>
      </div>
    </footer>

    <div v-if="!taskHistory.length" class="empty-state">
      暂无任务，点击下方「创建新任务」开始吧。
    </div>
    <ul v-else class="task-list">
      <li v-for="task in taskHistory" :key="task.id" :class="{ active: task.id === currentJobId }">
        <div class="task-meta">
          <strong>{{ task.id }}</strong>
          <span class="status-badge" :class="task.status">{{ describeStatus(task.status) }}</span>
        </div>
        <div class="task-info-row">
          <span>{{ formatTimestamp(task.updatedAt) }}</span>
          <span class="task-message">{{ task.message }}</span>
        </div>
        <div class="task-actions">
          <button type="button" class="btn-text" @click="$emit('select-task', task.id)">查看</button>
          <button type="button" class="btn-text danger" @click="$emit('remove-task', task.id)">移除</button>
        </div>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import type { TaskHistoryItem } from '@/stores/dashboard';

defineProps<{
  apiKeyInput: string;
  apiKeyVisible: boolean;
  apiKeyError: string;
  isApiKeyValid: boolean;
  balanceDisplay: string;
  balanceLoading: boolean;
  hasApiKey: boolean;
  taskHistory: TaskHistoryItem[];
  currentJobId: string | null;
  pollingActive: boolean;
  describeStatus: (status: string) => string;
  formatTimestamp: (timestamp: number) => string;
}>();

defineEmits<{
  (event: 'update:api-key-input', value: string): void;
  (event: 'validate-api-key'): void;
  (event: 'toggle-api-key-visibility'): void;
  (event: 'save-api-key'): void;
  (event: 'clear-api-key'): void;
  (event: 'refresh-balance'): void;
  (event: 'refresh-selected-task'): void;
  (event: 'toggle-polling'): void;
  (event: 'select-task', id: string): void;
  (event: 'remove-task', id: string): void;
}>();
</script>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
}

.panel-eyebrow {
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.6);
  margin: 0 0 0.15rem;
}

.panel-subtitle {
  margin: 0.15rem 0 0;
  color: rgba(226, 232, 240, 0.7);
  font-size: 0.9rem;
}

.step-pill {
  border-radius: 999px;
  padding: 0.2rem 0.65rem;
  background: rgba(59, 130, 246, 0.2);
  border: 1px solid rgba(59, 130, 246, 0.4);
  font-weight: 600;
  font-size: 0.85rem;
}

.api-tools {
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 16px;
  padding: 1rem;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.api-input {
  display: flex;
  gap: 0.4rem;
  align-items: center;
}

.api-input input {
  flex: 1;
  padding: 0.85rem;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(2, 6, 23, 0.85);
  color: #e2e8f0;
}

.api-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.btn-secondary {
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.4);
  background: rgba(37, 99, 235, 0.2);
  color: #dbeafe;
  padding: 0.45rem 0.9rem;
  font-size: 0.9rem;
  cursor: pointer;
}

.btn-secondary.ghost {
  background: transparent;
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-icon {
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(15, 23, 42, 0.7);
  color: #e5e7eb;
  border-radius: 10px;
  padding: 0.35rem 0.45rem;
  cursor: pointer;
}

.balance-display {
  margin: 0;
  color: rgba(226, 232, 240, 0.85);
  font-size: 0.9rem;
}

.task-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid rgba(148, 163, 184, 0.25);
}

.toolbar-actions {
  display: flex;
  gap: 0.35rem;
}

.task-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.task-list li {
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 12px;
  padding: 0.85rem;
}

.task-list li.active {
  border-color: rgba(59, 130, 246, 0.6);
  background: rgba(37, 99, 235, 0.08);
}

.task-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}

.task-message {
  color: rgba(248, 250, 252, 0.85);
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
</style>
