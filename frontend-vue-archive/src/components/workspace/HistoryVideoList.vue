<template>
  <div class="history-video">
    <div class="history-video__header">
      <span class="history-video__hint">
        最近 {{ items.length }} 条记录
      </span>
      <button type="button" class="btn-text" :disabled="loading" @click="$emit('refresh')">
        {{ loading ? '刷新中...' : '刷新' }}
      </button>
    </div>
    <p v-if="error" class="history-video__error">{{ error }}</p>
    <p v-else-if="loading && !items.length" class="history-video__muted">加载中...</p>
    <p v-else-if="!items.length" class="history-video__muted">暂无历史视频</p>
    <ul v-else class="history-video__list">
      <li v-for="item in items" :key="item.job_id + (item.published_at || '')">
        <div class="history-video__row">
          <div>
            <div class="history-video__title">
              <strong>{{ item.job_id }}</strong>
              <span class="status-badge" :class="item.status">{{ describeStatus(item.status) }}</span>
            </div>
            <small class="history-video__time">{{ formatPublishedAt(item.published_at) }}</small>
          </div>
          <div class="history-video__actions">
            <a
              v-if="item.video_url"
              class="btn-text"
              :href="item.video_url"
              target="_blank"
              rel="noopener"
            >
              播放 / 下载
            </a>
            <span v-else class="history-video__muted">暂无链接</span>
          </div>
        </div>
        <p class="history-video__message">{{ item.message || '点击“播放”即可访问挂载网盘中的视频' }}</p>
        <dl class="history-video__meta">
          <div v-if="item.duration">
            <dt>时长</dt>
            <dd>{{ formatDuration(item.duration) }}</dd>
          </div>
          <div v-if="item.file_size">
            <dt>大小</dt>
            <dd>{{ formatSize(item.file_size) }}</dd>
          </div>
          <div v-if="item.local_video_url">
            <dt>本地</dt>
            <dd><code>{{ item.local_video_url }}</code></dd>
          </div>
        </dl>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import type { HistoryVideoItem } from '@/types/history';

defineProps<{
  items: HistoryVideoItem[];
  loading: boolean;
  error: string;
}>();

defineEmits<{
  (event: 'refresh'): void;
}>();

function describeStatus(status: string) {
  const map: Record<string, string> = {
    finished: '已完成',
    failed: '失败',
    running: '执行中',
    pending: '排队中'
  };
  return map[status] || status || '未知';
}

function formatPublishedAt(value?: string | null) {
  if (!value) return '时间未知';
  const time = Date.parse(value);
  if (Number.isNaN(time)) {
    return value;
  }
  return new Date(time).toLocaleString('zh-CN', { hour12: false });
}

function formatDuration(seconds?: number | null) {
  if (!seconds || !Number.isFinite(seconds)) return '';
  const value = Math.max(0, Math.round(seconds));
  const mins = Math.floor(value / 60);
  const secs = value % 60;
  if (!mins) return `${secs} 秒`;
  return `${mins} 分 ${secs.toString().padStart(2, '0')} 秒`;
}

function formatSize(size?: number | null) {
  if (!size || size <= 0) return '';
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}
</script>

<style scoped>
.history-video {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.history-video__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.history-video__hint {
  font-size: 0.85rem;
  color: rgba(148, 163, 184, 0.9);
}

.history-video__error {
  color: #f87171;
  font-size: 0.9rem;
}

.history-video__muted {
  color: rgba(148, 163, 184, 0.9);
  font-size: 0.9rem;
}

.history-video__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.history-video__list li {
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 12px;
  padding: 0.75rem;
  background: rgba(15, 23, 42, 0.45);
}

.history-video__row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.5rem;
}

.history-video__title {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.history-video__time {
  display: block;
  color: rgba(148, 163, 184, 0.9);
}

.history-video__message {
  margin: 0.35rem 0;
  font-size: 0.9rem;
  color: rgba(226, 232, 240, 0.92);
}

.history-video__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin: 0;
}

.history-video__meta div {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.history-video__meta dt {
  font-size: 0.75rem;
  color: rgba(148, 163, 184, 0.9);
}

.history-video__meta dd {
  margin: 0;
  font-size: 0.85rem;
  color: rgba(248, 250, 252, 0.95);
}

.history-video__meta code {
  word-break: break-all;
  font-size: 0.8rem;
}
</style>
