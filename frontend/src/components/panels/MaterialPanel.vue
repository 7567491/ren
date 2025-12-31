<template>
  <section class="material-panel">
    <div v-if="!currentJobId" class="empty-state">未选择任务，暂无法展示素材。</div>
    <div v-else>
      <p class="bucket-path">当前任务目录：<code>{{ currentBucketDir }}</code></p>
      <section v-if="audioUrl || showVideoPreview" class="material-preview">
        <div v-if="audioUrl" class="material-audio">
          <p class="asset-title">语音素材</p>
          <audio :src="audioUrl" controls></audio>
        </div>
        <div v-if="showVideoPreview" class="material-video">
          <p class="asset-title">视频素材</p>
          <video :src="resultVideoUrl" controls playsinline></video>
        </div>
      </section>
      <ul v-if="materialItems.length" class="material-list">
        <li v-for="item in materialItems" :key="item.id">
          <div class="material-meta">
            <strong>{{ item.label }}</strong>
            <span class="material-tag" :class="item.type">{{ item.type }}</span>
          </div>
          <p v-if="item.description" class="material-desc">{{ item.description }}</p>
          <p v-if="item.localPath" class="material-path">本地：<code>{{ item.localPath }}</code></p>
          <p v-if="item.publicUrl" class="material-path">公网：<code>{{ item.publicUrl }}</code></p>
          <div class="material-actions">
            <button v-if="item.localPath" type="button" class="btn-text" @click="copyLocalPath(item.localPath)">
              复制本地
            </button>
            <button v-if="item.publicUrl" type="button" class="btn-text" @click="copyPublicLink(item.publicUrl)">
              复制公网
            </button>
            <button v-if="item.publicUrl" type="button" class="btn-text" @click="openPublicLink(item.publicUrl)">
              打开
            </button>
          </div>
        </li>
      </ul>
      <div v-else class="empty-state">暂无素材文件，等待任务产出。</div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { MaterialEntry } from '@/types/dashboard';

interface Props {
  currentJobId: string | null;
  currentBucketDir: string;
  audioUrl?: string;
  resultVideoUrl?: string;
  taskStatus: 'idle' | 'running' | 'finished' | 'failed';
  materialItems: MaterialEntry[];
  copyLocalPath: (path: string) => void;
  copyPublicLink: (url: string) => void;
  openPublicLink: (url: string) => void;
}

const props = defineProps<Props>();

const showVideoPreview = computed(() => props.taskStatus === 'finished' && Boolean(props.resultVideoUrl));
</script>

<style scoped>
.material-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.bucket-path {
  font-size: 0.9rem;
  color: rgba(229, 231, 235, 0.8);
}

.bucket-path code {
  font-size: 0.85rem;
  color: #cbd5f5;
}

.empty-state {
  padding: 1rem;
  border: 1px dashed rgba(148, 163, 184, 0.4);
  border-radius: 12px;
  font-size: 0.95rem;
  color: rgba(226, 232, 240, 0.7);
}

.material-preview {
  display: grid;
  gap: 0.75rem;
  margin: 0.75rem 0 0.5rem;
}

.material-preview video,
.material-preview audio {
  width: 100%;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.35);
}

.material-list {
  list-style: none;
  padding: 0;
  margin: 1rem 0 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.material-list li {
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 12px;
  padding: 0.85rem;
}

.material-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.material-tag {
  padding: 0.1rem 0.55rem;
  border-radius: 999px;
  font-size: 0.75rem;
  text-transform: uppercase;
  background: rgba(148, 163, 184, 0.2);
  border: 1px solid rgba(148, 163, 184, 0.3);
}

.material-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: 0.5rem;
}

.material-path code {
  font-size: 0.85rem;
  color: #cbd5f5;
}

.btn-text {
  border: none;
  background: none;
  color: #60a5fa;
  cursor: pointer;
  padding: 0.2rem 0.4rem;
  font-size: 0.9rem;
}
</style>
