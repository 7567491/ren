<template>
  <section class="panel monitor-panel card">
    <header class="panel-header">
      <div>
        <p class="panel-eyebrow">监控</p>
        <h2>任务进度与素材</h2>
        <p class="panel-subtitle">实时阶段、日志、播放器与素材目录</p>
      </div>
      <div class="step-pill">Step 3</div>
    </header>

    <div class="monitor-toolbar">
      <div class="polling-indicator" :class="{ active: pollingActive }">
        <span class="dot"></span>
        {{ pollingActive ? '轮询中' : '轮询已暂停' }}
      </div>
      <div class="toolbar-actions">
        <button type="button" class="btn-secondary" :disabled="!currentJobId" @click="$emit('refresh-task')">刷新任务</button>
        <button type="button" class="btn-secondary" :disabled="!currentJobId" @click="$emit('toggle-polling')">
          {{ pollingActive ? '暂停轮询' : '恢复轮询' }}
        </button>
      </div>
    </div>

    <div class="progress-headline">
      <div v-if="currentJobId" class="task-info">任务 ID：<code>{{ currentJobId }}</code></div>
      <div class="progress-meter" role="progressbar" :aria-valuenow="overallProgressPercent" aria-valuemin="0" aria-valuemax="100">
        <div class="progress-meter__fill" :style="{ width: overallProgressLabel }"></div>
        <span class="progress-meter__label">{{ overallProgressLabel }}</span>
      </div>
    </div>

    <ul class="stage-pipeline">
      <li v-for="definition in stageDefinitions" :key="definition.id" :class="['stage', stageStatus[definition.id].state]">
        <div class="stage-icon" :style="{ borderColor: definition.color }">
          <span class="stage-base">{{ definition.icon }}</span>
          <span class="stage-state">{{ stageStateIcon(stageStatus[definition.id].state) }}</span>
        </div>
        <div>
          <p class="stage-text">{{ definition.label }}</p>
          <p class="stage-desc">{{ stageStatus[definition.id].description }}</p>
        </div>
      </li>
    </ul>

    <div class="status-card" :class="statusAccent">
      <p class="status-text">{{ statusMessage }}</p>
      <p v-if="traceId" class="trace-tag">
        Trace ID：<code>{{ traceId }}</code>
      </p>
    </div>
    <div v-if="countdownVisible" class="countdown-hint">
      ⏱️ 预计剩余 <strong>{{ countdownLabel }}</strong>
      <span v-if="countdownSource" class="countdown-source">（{{ countdownSource }}）</span>
    </div>

    <div v-if="costEstimateValue !== null" class="cost-estimate">
      预计成本：<strong>${{ costEstimateValue?.toFixed(2) }}</strong>
      <small>{{ costEstimateDesc }}</small>
    </div>

    <section class="asset-preview">
      <div v-if="avatarUrl" class="asset-card">
        <p class="asset-title">头像预览</p>
        <img :src="avatarUrl" alt="生成头像" class="asset-image" />
      </div>
      <div v-if="audioUrl" class="asset-card">
        <p class="asset-title">语音试听</p>
        <audio :src="audioUrl" controls></audio>
      </div>
    </section>

    <div v-if="taskStatus === 'failed'" class="error-message">
      <strong>❌ 生成失败</strong>
      <p>{{ errorMessage }}</p>
    </div>

    <ResultAssetSection
      :current-job-id="currentJobId"
      :task-status="taskStatus"
      :result-video-url="resultVideoUrl"
      :total-cost="totalCost"
      :billing-summary="billingSummary"
      :material-items="materialItems"
      :collapsed="resultSectionCollapsed"
      :has-path-warning="materialWarning"
      @download-video="$emit('download-video')"
      @copy-video-link="$emit('copy-video-link')"
      @copy-local-path="$emit('copy-local-path', $event)"
      @copy-public-link="$emit('copy-public-link', $event)"
      @open-public-link="$emit('open-public-link', $event)"
      @toggle-collapsed="$emit('toggle-result-section', $event)"
    />
  </section>
</template>

<script setup lang="ts">
import type { StageDefinition, StageViewState, StageKey } from '@/types/stages';
import type { MaterialEntry } from '@/types/material';
import ResultAssetSection from './ResultAssetSection.vue';

const props = defineProps<{
  currentJobId: string | null;
  taskStatus: 'idle' | 'running' | 'finished' | 'failed';
  overallProgressPercent: number;
  overallProgressLabel: string;
  stageDefinitions: StageDefinition[];
  stageStatus: Record<StageKey, StageViewState>;
  statusMessage: string;
  statusAccent: Record<string, boolean>;
  traceId?: string;
  countdownVisible: boolean;
  countdownLabel: string;
  countdownSource: string;
  costEstimateValue: number | null;
  costEstimateDesc: string;
  avatarUrl: string;
  audioUrl: string;
  resultVideoUrl: string;
  totalCost: number;
  billingSummary: string;
  errorMessage: string;
  materialItems: MaterialEntry[];
  pollingActive: boolean;
  resultSectionCollapsed: boolean;
  materialWarning: boolean;
}>();

defineEmits<{
  (event: 'download-video'): void;
  (event: 'copy-video-link'): void;
  (event: 'copy-local-path', path: string): void;
  (event: 'copy-public-link', url: string): void;
  (event: 'open-public-link', url: string): void;
  (event: 'refresh-task'): void;
  (event: 'toggle-polling'): void;
  (event: 'toggle-result-section', collapsed: boolean): void;
}>();

function stageStateIcon(state: StageViewState['state']) {
  if (state === 'done') return '✅';
  if (state === 'active') return '⚙️';
  if (state === 'failed') return '⚠️';
  return '⏳';
}
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
  background: rgba(34, 197, 94, 0.2);
  border: 1px solid rgba(34, 197, 94, 0.4);
  font-weight: 600;
  font-size: 0.85rem;
}

.progress-headline {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.progress-meter {
  position: relative;
  width: 100%;
  background: rgba(15, 23, 42, 0.15);
  border-radius: 999px;
  padding: 0.35rem;
  overflow: hidden;
  border: 1px solid rgba(15, 23, 42, 0.25);
}

.progress-meter__fill {
  height: 8px;
  border-radius: 999px;
  background: linear-gradient(90deg, #34d399, #0ea5e9);
  transition: width 0.3s ease;
}

.progress-meter__label {
  position: absolute;
  right: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.85rem;
  color: #0f172a;
  font-weight: 600;
}

.stage-pipeline {
  list-style: none;
  padding: 0;
  margin: 0.5rem 0 0;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.stage {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  padding: 0.6rem;
  border-radius: 12px;
  border: 1px dashed rgba(148, 163, 184, 0.3);
}

.stage.active {
  border-color: rgba(56, 189, 248, 0.8);
  background: rgba(14, 165, 233, 0.12);
}

.stage.done {
  border-color: rgba(16, 185, 129, 0.5);
  background: rgba(16, 185, 129, 0.1);
}

.stage.failed {
  border-color: rgba(248, 113, 113, 0.7);
  background: rgba(248, 113, 113, 0.12);
}

.stage-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  border: 2px solid rgba(148, 163, 184, 0.45);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.15rem;
  padding: 0.3rem 0.4rem;
  font-size: 1.35rem;
}

.monitor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.polling-indicator {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0.8rem;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.4);
  font-size: 0.85rem;
  color: rgba(226, 232, 240, 0.85);
}

.polling-indicator .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(248, 113, 113, 0.85);
  display: inline-block;
}

.polling-indicator.active .dot {
  background: rgba(74, 222, 128, 0.95);
  box-shadow: 0 0 6px rgba(74, 222, 128, 0.65);
}

.toolbar-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.status-card {
  margin-top: 0.75rem;
  padding: 0.9rem 1rem;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid rgba(148, 163, 184, 0.35);
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.status-text {
  margin: 0;
  font-weight: 600;
}

.trace-tag {
  margin: 0;
  font-size: 0.85rem;
  color: rgba(226, 232, 240, 0.75);
}

.trace-tag code {
  font-size: 0.85rem;
  color: #cbd5f5;
}

.countdown-hint {
  margin-top: 0.35rem;
  font-size: 0.95rem;
  color: #0f172a;
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.cost-estimate {
  background: rgba(36, 195, 142, 0.08);
  border: 1px solid rgba(36, 195, 142, 0.5);
  border-radius: 12px;
  padding: 0.8rem 1rem;
  color: var(--color-info);
}

.asset-preview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
}

.asset-card {
  padding: 0.75rem;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.4);
}

.result-container {
  margin-top: 1rem;
}

.material-card {
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 16px;
  padding: 1rem;
  background: rgba(15, 23, 42, 0.35);
}

.material-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.material-actions {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
}
</style>
