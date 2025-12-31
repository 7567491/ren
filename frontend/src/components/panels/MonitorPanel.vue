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

    <div class="status-message" :class="statusAccent">
      {{ statusMessage }}
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

    <section v-if="taskStatus === 'finished' && resultVideoUrl" class="result-container">
      <p class="asset-title">最终视频</p>
      <video ref="videoPlayerEl" class="video-player video-js vjs-default-skin" playsinline data-setup="{}"></video>
      <div class="cost-display">
        总成本: ${{ totalCost.toFixed(2) }}
        <small v-if="billingSummary">{{ billingSummary }}</small>
      </div>
      <div class="result-actions">
        <button class="btn-download" @click="$emit('download-video')">📥 下载视频</button>
        <button class="btn-share" @click="$emit('copy-video-link')">🔗 复制链接</button>
      </div>
    </section>

    <div v-if="taskStatus === 'failed'" class="error-message">
      <strong>❌ 生成失败</strong>
      <p>{{ errorMessage }}</p>
    </div>

    <section class="material-card">
      <header>
        <h3>素材目录</h3>
        <a href="/doc/frontend_task_flow.md" target="_blank" rel="noreferrer" class="link">任务流说明</a>
      </header>
      <div v-if="!currentJobId" class="empty-state">未选择任务，暂无法展示素材。</div>
      <div v-else>
        <ul v-if="materialItems.length" class="material-list">
          <li v-for="item in materialItems" :key="item.id">
            <div class="material-meta">
              <strong>{{ item.label }}</strong>
              <span class="material-tag" :class="item.type">{{ item.type }}</span>
            </div>
            <p v-if="item.description" class="material-desc">{{ item.description }}</p>
            <p v-if="item.publicUrl" class="material-path">公网：<code>{{ item.publicUrl }}</code></p>
            <details v-if="item.localPath" class="material-details">
              <summary>技术详情</summary>
              <p class="material-path">本地：<code>{{ item.localPath }}</code></p>
            </details>
            <div class="material-actions">
              <button v-if="item.localPath" type="button" class="btn-text" @click="$emit('copy-local-path', item.localPath)">复制本地</button>
              <button v-if="item.publicUrl" type="button" class="btn-text" @click="$emit('copy-public-link', item.publicUrl)">复制公网</button>
              <button v-if="item.publicUrl" type="button" class="btn-text" @click="$emit('open-public-link', item.publicUrl)">打开</button>
            </div>
          </li>
        </ul>
        <div v-else class="empty-state">暂无素材文件，等待任务产出。</div>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue';
import videojs from 'video.js';
import type { StageDefinition, StageViewState, StageKey } from '@/types/stages';
import type { MaterialEntry } from '@/types/material';

const props = defineProps<{
  currentJobId: string | null;
  taskStatus: 'idle' | 'running' | 'finished' | 'failed';
  overallProgressPercent: number;
  overallProgressLabel: string;
  stageDefinitions: StageDefinition[];
  stageStatus: Record<StageKey, StageViewState>;
  statusMessage: string;
  statusAccent: Record<string, boolean>;
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
}>();

defineEmits<{
  (event: 'download-video'): void;
  (event: 'copy-video-link'): void;
  (event: 'copy-local-path', path: string): void;
  (event: 'copy-public-link', url: string): void;
  (event: 'open-public-link', url: string): void;
}>();

const videoPlayerEl = ref<HTMLVideoElement | null>(null);
let videoPlayerInstance: videojs.Player | null = null;

watch(
  () => props.resultVideoUrl,
  (url) => {
    if (videoPlayerInstance) {
      videoPlayerInstance.dispose();
      videoPlayerInstance = null;
    }
    if (url) {
      queueMicrotask(() => {
        if (!videoPlayerEl.value) return;
        videoPlayerInstance = videojs(videoPlayerEl.value, {
          controls: true,
          preload: 'auto',
          sources: [{ src: url, type: 'video/mp4' }]
        });
      });
    }
  }
);

onBeforeUnmount(() => {
  if (videoPlayerInstance) {
    videoPlayerInstance.dispose();
    videoPlayerInstance = null;
  }
});

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

.status-message {
  padding: 0.9rem 1rem;
  border-radius: 10px;
  background: rgba(57, 64, 77, 0.8);
  border-left: 4px solid var(--color-info);
  margin-bottom: 0.5rem;
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
