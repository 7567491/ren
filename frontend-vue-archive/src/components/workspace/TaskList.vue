<template>
  <div class="task-list-panel">
    <div class="task-filters">
      <button
        v-for="filter in filterOptions"
        :key="filter.value"
        type="button"
        class="filter-btn"
        :class="{ active: activeFilter === filter.value }"
        @click="setFilter(filter.value)"
      >
        <span>{{ filter.label }}</span>
        <small>{{ filter.count }}</small>
      </button>
    </div>

    <div v-if="!filteredTasks.length" class="empty-state">没有符合条件的任务。</div>
    <ul v-else class="task-list">
      <li v-for="task in filteredTasks" :key="task.id" :class="{ active: task.id === currentTaskId }">
        <div class="task-head">
          <div class="task-id">
            <strong>{{ task.id }}</strong>
            <span class="status-badge" :class="task.status">{{ describeStatus(task.status) }}</span>
          </div>
          <span class="task-time">{{ formatTimestamp(task.updatedAt) }}</span>
        </div>
        <p class="task-message" :title="task.message">{{ task.message || '暂无消息' }}</p>
        <div class="task-actions">
          <button type="button" class="btn-text" @click="$emit('select-task', task.id)">查看</button>
          <button
            type="button"
            class="btn-text"
            :disabled="!getTraceId(task)"
            @click="copyTraceId(task)"
          >
            {{ copiedTaskId === task.id ? 'Trace 已复制' : '复制 Trace' }}
          </button>
          <button type="button" class="btn-text danger" @click="$emit('remove-task', task.id)">移除</button>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue';
import type { TaskHistoryItem } from '@/stores/dashboard';

type FilterValue = 'all' | 'running' | 'finished' | 'failed';

const props = defineProps<{
  tasks: TaskHistoryItem[];
  currentTaskId: string | null;
  describeStatus: (status: string) => string;
  formatTimestamp: (timestamp: number) => string;
}>();

const emit = defineEmits<{
  (event: 'select-task', id: string): void;
  (event: 'remove-task', id: string): void;
}>();

const activeFilter = ref<FilterValue>('all');
const copiedTaskId = ref<string | null>(null);
let copyTimer: number | null = null;

const filterStats = computed(() => {
  const stats: Record<FilterValue, number> = {
    all: props.tasks.length,
    running: 0,
    finished: 0,
    failed: 0
  };
  props.tasks.forEach((task) => {
    if (task.status === 'finished') stats.finished += 1;
    else if (task.status === 'failed') stats.failed += 1;
    else stats.running += 1;
  });
  return stats;
});

const filterOptions = computed(() => [
  { value: 'all' as FilterValue, label: '全部', count: filterStats.value.all },
  { value: 'running' as FilterValue, label: '执行中', count: filterStats.value.running },
  { value: 'finished' as FilterValue, label: '已完成', count: filterStats.value.finished },
  { value: 'failed' as FilterValue, label: '失败', count: filterStats.value.failed }
]);

const filteredTasks = computed(() =>
  props.tasks.filter((task) => {
    if (activeFilter.value === 'all') return true;
    if (activeFilter.value === 'running') {
      return task.status !== 'finished' && task.status !== 'failed';
    }
    return task.status === activeFilter.value;
  })
);

function setFilter(value: FilterValue) {
  activeFilter.value = value;
}

function getTraceId(task: TaskHistoryItem) {
  return (task.snapshot as { trace_id?: string } | undefined)?.trace_id || '';
}

async function copyTraceId(task: TaskHistoryItem) {
  const traceId = getTraceId(task);
  if (!traceId || typeof navigator === 'undefined') return;
  try {
    await navigator.clipboard.writeText(traceId);
    copiedTaskId.value = task.id;
    if (copyTimer) window.clearTimeout(copyTimer);
    copyTimer = window.setTimeout(() => {
      copiedTaskId.value = null;
    }, 1500);
  } catch (error) {
    console.warn('无法复制 trace id', error);
  }
}

onBeforeUnmount(() => {
  if (copyTimer) {
    window.clearTimeout(copyTimer);
    copyTimer = null;
  }
});
</script>

<style scoped>
.task-list-panel {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.task-filters {
  display: flex;
  gap: 0.45rem;
  flex-wrap: wrap;
}

.filter-btn {
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(15, 23, 42, 0.6);
  color: rgba(226, 232, 240, 0.9);
  border-radius: 999px;
  padding: 0.35rem 0.8rem;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  cursor: pointer;
  font-size: 0.85rem;
}

.filter-btn.active {
  background: rgba(59, 130, 246, 0.18);
  border-color: rgba(59, 130, 246, 0.55);
}

.filter-btn small {
  font-weight: 600;
  color: rgba(248, 250, 252, 0.95);
}

.task-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.task-list li {
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 14px;
  padding: 0.8rem;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.task-list li.active {
  border-color: rgba(59, 130, 246, 0.65);
  box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.3);
}

.task-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}

.task-id {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.task-time {
  font-size: 0.8rem;
  color: rgba(226, 232, 240, 0.75);
}

.task-message {
  margin: 0;
  font-size: 0.9rem;
  color: rgba(248, 250, 252, 0.85);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-actions {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.status-badge {
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  font-size: 0.75rem;
  text-transform: uppercase;
  background: rgba(148, 163, 184, 0.2);
  border: 1px solid rgba(148, 163, 184, 0.3);
}

.status-badge.finished {
  background: rgba(16, 185, 129, 0.2);
  border-color: rgba(16, 185, 129, 0.5);
}

.status-badge.failed {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.45);
}

.status-badge.running {
  background: rgba(59, 130, 246, 0.15);
  border-color: rgba(59, 130, 246, 0.4);
}
</style>
