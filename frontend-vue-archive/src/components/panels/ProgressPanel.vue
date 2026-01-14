<template>
  <section class="progress-panel">
    <div class="progress-headline">
      <div v-if="currentJobId" class="task-info">任务 ID：<code>{{ currentJobId }}</code></div>
      <div
        class="progress-meter"
        role="progressbar"
        :aria-valuenow="overallProgressPercent"
        aria-valuemin="0"
        aria-valuemax="100"
      >
        <div class="progress-meter__fill" :style="{ width: overallProgressLabel }"></div>
        <span class="progress-meter__label">{{ overallProgressLabel }}</span>
      </div>
    </div>
    <ul class="stage-pipeline">
      <li
        v-for="definition in stageDefinitions"
        :key="definition.id"
        :class="['stage', stageStatus[definition.id]?.state]"
      >
        <div class="stage-icon" :style="{ borderColor: definition.color }">
          <span class="stage-base">{{ definition.icon }}</span>
          <span class="stage-state">{{ stageStateIcon(definition.id) }}</span>
        </div>
        <div>
          <p class="stage-text">{{ definition.label }}</p>
          <p class="stage-desc">{{ stageStatus[definition.id]?.description }}</p>
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
      <video
        ref="videoElement"
        class="video-player video-js vjs-default-skin"
        playsinline
        data-setup="{}"
      ></video>
      <div class="cost-display">
        总成本: ${{ totalCost.toFixed(2) }}
        <small v-if="billingSummary">{{ billingSummary }}</small>
      </div>
      <div class="result-actions">
        <button class="btn-download" @click="downloadVideo">📥 下载视频</button>
        <button class="btn-share" @click="copyVideoLink">🔗 复制链接</button>
      </div>
    </section>

    <div v-if="taskStatus === 'failed'" class="error-message">
      <strong>❌ 生成失败</strong>
      <p>{{ errorMessage }}</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { Ref, ref, watchEffect } from 'vue';
import type { StageDefinition, StageViewState } from '@/types/dashboard';

interface Props {
  currentJobId: string | null;
  overallProgressLabel: string;
  overallProgressPercent: number;
  stageDefinitions: StageDefinition[];
  stageStatus: Record<StageDefinition['id'], StageViewState>;
  stageStateIcon: (stage: StageDefinition['id']) => string;
  statusAccent: Record<string, boolean>;
  statusMessage: string;
  countdownVisible: boolean;
  countdownLabel: string;
  countdownSource?: string;
  costEstimateValue: number | null;
  costEstimateDesc: string;
  avatarUrl?: string;
  audioUrl?: string;
  taskStatus: 'idle' | 'running' | 'finished' | 'failed';
  resultVideoUrl?: string;
  totalCost: number;
  billingSummary?: string;
  downloadVideo: () => void;
  copyVideoLink: () => void;
  errorMessage: string;
  videoPlayerRef?: Ref<HTMLVideoElement | null>;
}

const props = defineProps<Props>();

const videoElement = ref<HTMLVideoElement | null>(null);

watchEffect(() => {
  if (!props.videoPlayerRef) return;
  props.videoPlayerRef.value = videoElement.value;
});
</script>

<style scoped>
.progress-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
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

.stage-pipeline .stage {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  padding: 0.6rem;
  border-radius: 12px;
  border: 1px dashed rgba(148, 163, 184, 0.3);
  transition: border-color 0.2s ease, background-color 0.2s ease;
}

.stage-pipeline .stage.active {
  border-color: rgba(56, 189, 248, 0.8);
  background: rgba(14, 165, 233, 0.12);
}

.stage-pipeline .stage.done {
  border-color: rgba(16, 185, 129, 0.5);
  background: rgba(16, 185, 129, 0.1);
}

.stage-pipeline .stage.failed {
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

.stage-base {
  flex: 1;
  text-align: left;
}

.stage-state {
  font-size: 0.95rem;
}

.stage-desc {
  margin: 0.05rem 0 0;
  font-size: 0.85rem;
  color: rgba(15, 23, 42, 0.7);
}

.countdown-hint {
  font-size: 0.95rem;
  color: #0f172a;
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.countdown-hint strong {
  font-size: 1.05rem;
  color: #16a34a;
}

.countdown-source {
  color: #64748b;
  font-size: 0.85rem;
}
</style>
