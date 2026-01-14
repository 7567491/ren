import { defineStore } from 'pinia';

export interface TaskAnalytics {
  textLength?: number;
  videoStageSeconds?: number;
  perCharSeconds?: number;
}

export interface TaskHistoryItem {
  id: string;
  status: string;
  message: string;
  createdAt: number;
  updatedAt: number;
  costEstimate?: number;
  assets?: Record<string, any>;
  snapshot?: Record<string, any>;
  textLength?: number;
  analytics?: TaskAnalytics;
}

interface DashboardState {
  apiKey: string;
  tasks: TaskHistoryItem[];
  selectedTaskId: string | null;
  selectionRevision: number;
  bucketRoot: string;
  bucketUserDir: string;
  errors: Record<string, string>;
}

const STORAGE_KEY = 'digital-human-dashboard';
const LEGACY_API_KEY_STORAGE = 'wavespeed_api_key';
const TERMINAL_STATUSES = new Set(['finished', 'failed']);

function isTaskStillActive(task?: TaskHistoryItem | null) {
  if (!task) return false;
  return !TERMINAL_STATUSES.has(task.status);
}

function loadPersisted(): Partial<DashboardState> {
  if (typeof window === 'undefined') return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : {};
    if (!parsed.apiKey) {
      const legacyKey = window.localStorage.getItem(LEGACY_API_KEY_STORAGE);
      if (legacyKey && legacyKey.trim()) {
        parsed.apiKey = legacyKey.trim();
      }
    }
    return parsed;
  } catch (err) {
    console.warn('failed to load dashboard storage', err);
    return {};
  }
}

function persist(partial: Partial<DashboardState>) {
  if (typeof window === 'undefined') return;
  try {
    const current = loadPersisted();
    const next = { ...current, ...partial };
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    if ('apiKey' in partial) {
      const trimmed = (partial.apiKey || '').trim();
      if (trimmed) {
        window.localStorage.setItem(LEGACY_API_KEY_STORAGE, trimmed);
      } else {
        window.localStorage.removeItem(LEGACY_API_KEY_STORAGE);
      }
    }
  } catch (err) {
    console.warn('failed to persist dashboard storage', err);
  }
}

export const useDashboardStore = defineStore('dashboard', {
  state: (): DashboardState => {
    const persisted = loadPersisted();
    const tasks = persisted.tasks || [];
    const selectedFromStorage = persisted.selectedTaskId || null;
    const selectedTask = tasks.find((task) => task.id === selectedFromStorage);
    return {
      apiKey: persisted.apiKey || '',
      tasks,
      selectedTaskId: isTaskStillActive(selectedTask) ? selectedFromStorage : null,
      selectionRevision: persisted.selectionRevision || 0,
      bucketRoot: '/mnt/www',
      bucketUserDir: 'ren',
      errors: {}
    };
  },
  getters: {
    currentTask(state): TaskHistoryItem | null {
      return state.tasks.find((task) => task.id === state.selectedTaskId) || null;
    },
    sortedTasks(state): TaskHistoryItem[] {
      return [...state.tasks].sort((a, b) => b.updatedAt - a.updatedAt);
    }
  },
  actions: {
    setApiKey(value: string) {
      const trimmed = value.trim();
      if (this.apiKey === trimmed && trimmed.length > 0) {
        return;
      }
      this.apiKey = trimmed;
      persist({ apiKey: this.apiKey });
    },
    clearApiKey() {
      this.setApiKey('');
    },
    upsertTask(payload: TaskHistoryItem) {
      const idx = this.tasks.findIndex((item) => item.id === payload.id);
      if (idx >= 0) {
        this.tasks[idx] = { ...this.tasks[idx], ...payload, updatedAt: payload.updatedAt };
      } else {
        this.tasks.push(payload);
      }
      persist({
        apiKey: this.apiKey,
        tasks: this.tasks,
        selectedTaskId: this.selectedTaskId,
        selectionRevision: this.selectionRevision
      });
    },
    selectTask(id: string | null) {
      this.selectedTaskId = id;
      this.selectionRevision += 1;
      persist({
        apiKey: this.apiKey,
        tasks: this.tasks,
        selectedTaskId: this.selectedTaskId,
        selectionRevision: this.selectionRevision
      });
    },
    removeTask(id: string) {
      this.tasks = this.tasks.filter((task) => task.id !== id);
      if (this.selectedTaskId === id) {
        this.selectedTaskId = null;
        this.selectionRevision += 1;
      }
      persist({
        apiKey: this.apiKey,
        tasks: this.tasks,
        selectedTaskId: this.selectedTaskId,
        selectionRevision: this.selectionRevision
      });
    },
    setError(key: string, message: string) {
      this.errors = { ...this.errors, [key]: message };
    },
    clearError(key: string) {
      if (!(key in this.errors)) return;
      const next = { ...this.errors };
      delete next[key];
      this.errors = next;
    },
    clearAllErrors() {
      this.errors = {};
    }
  }
});
