<template>
  <section class="panel result-section card">
    <header class="result-header">
      <div>
        <p class="section-eyebrow">结果与素材</p>
        <h3>播放器 / 下载 / 目录</h3>
      </div>
      <div class="result-actions">
        <button type="button" class="btn-secondary" @click="toggleCollapse">
          {{ collapsed ? '展开' : '收起' }}
        </button>
      </div>
    </header>
    <p v-if="hasPathWarning" class="result-warning">⚠️ 本地视频路径异常，请确认是否为 /output/{{ currentJobLabel }}/digital_human.mp4。</p>

    <transition name="result-collapse">
      <div v-show="!collapsed" class="result-body">
        <section v-if="canShowVideo" class="result-container">
          <p class="asset-title">最终视频</p>
          <video ref="videoPlayerEl" class="video-player video-js vjs-default-skin" playsinline data-setup="{}"></video>
          <div class="player-actions">
            <button type="button" class="btn-primary" :disabled="!canShowVideo" @click="$emit('download-video')">下载本地视频</button>
            <button
              type="button"
              class="btn-text"
              :disabled="!resultVideoUrl"
              @click="$emit('copy-video-link')"
            >
              备用 CDN 链接
            </button>
          </div>
          <div class="cost-display">
            总成本: ${{ totalCost.toFixed(2) }}
            <small v-if="billingSummary">{{ billingSummary }}</small>
          </div>
        </section>
        <p v-else class="empty-state">
          {{ taskStatus === 'finished' ? '暂无可播放视频，请检查素材目录。' : '任务完成后将自动展示播放器与素材。' }}
        </p>

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
      </div>
    </transition>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import videojs from 'video.js';
import type { MaterialEntry } from '@/types/material';

const props = defineProps<{
  currentJobId: string | null;
  taskStatus: 'idle' | 'running' | 'finished' | 'failed';
  resultVideoUrl: string;
  totalCost: number;
  billingSummary: string;
  materialItems: MaterialEntry[];
  collapsed: boolean;
  hasPathWarning: boolean;
}>();

const emit = defineEmits<{
  (event: 'download-video'): void;
  (event: 'copy-video-link'): void;
  (event: 'copy-local-path', path: string): void;
  (event: 'copy-public-link', url: string): void;
  (event: 'open-public-link', url: string): void;
  (event: 'toggle-collapsed', value: boolean): void;
}>();

const videoPlayerEl = ref<HTMLVideoElement | null>(null);
let videoPlayerInstance: videojs.Player | null = null;

const canShowVideo = computed(() => props.taskStatus === 'finished' && Boolean(props.resultVideoUrl));
const currentJobLabel = computed(() => props.currentJobId || 'job');

watch(
  () => props.resultVideoUrl,
  (url) => {
    if (videoPlayerInstance) {
      videoPlayerInstance.dispose();
      videoPlayerInstance = null;
    }
    if (url && !props.collapsed) {
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

watch(
  () => props.collapsed,
  (collapsed) => {
    if (collapsed && videoPlayerInstance) {
      videoPlayerInstance.pause();
    } else if (!collapsed && props.resultVideoUrl && !videoPlayerInstance) {
      queueMicrotask(() => {
        if (!videoPlayerEl.value) return;
        videoPlayerInstance = videojs(videoPlayerEl.value, {
          controls: true,
          preload: 'auto',
          sources: [{ src: props.resultVideoUrl, type: 'video/mp4' }]
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

function toggleCollapse() {
  emit('toggle-collapsed', !props.collapsed);
}
</script>

<style scoped>
.result-section {
  margin-top: 1.5rem;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.result-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.result-warning {
  margin: 0 0 0.75rem;
  padding: 0.6rem 0.9rem;
  border-radius: 12px;
  border: 1px solid rgba(248, 113, 113, 0.6);
  background: rgba(248, 113, 113, 0.12);
  color: #fecaca;
}

.result-body {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.material-card {
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 18px;
  padding: 1rem;
  background: rgba(15, 23, 42, 0.35);
}

.material-card header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.player-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin: 0.75rem 0;
}

.player-actions .btn-primary {
  border: none;
  border-radius: 10px;
  padding: 0.65rem 1.1rem;
  font-weight: 600;
  background: linear-gradient(120deg, #22d3ee, #0ea5e9);
  color: #0f172a;
  cursor: pointer;
  box-shadow: 0 12px 24px rgba(14, 165, 233, 0.35);
}

.player-actions .btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}

.result-collapse-enter-active,
.result-collapse-leave-active {
  transition: all 0.2s ease;
}

.result-collapse-enter-from,
.result-collapse-leave-to {
  opacity: 0;
  transform: translateY(-0.5rem);
}
</style>
.player-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin: 0.75rem 0;
}
