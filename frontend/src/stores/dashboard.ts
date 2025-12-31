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
  bucketRoot: string;
  bucketUserDir: string;
  errors: Record<string, string>;
}

const STORAGE_KEY = 'digital-human-dashboard';

function loadPersisted(): Partial<DashboardState> {
  if (typeof window === 'undefined') return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch (err) {
    console.warn('failed to load dashboard storage', err);
    return {};
  }
}

function persist(state: Partial<DashboardState>) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (err) {
    console.warn('failed to persist dashboard storage', err);
  }
}

export const useDashboardStore = defineStore('dashboard', {
  state: (): DashboardState => {
    const persisted = loadPersisted();
    return {
      apiKey: persisted.apiKey || '',
      tasks: persisted.tasks || [],
      selectedTaskId: persisted.selectedTaskId || null,
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
      this.apiKey = value;
      persist({ apiKey: this.apiKey, tasks: this.tasks, selectedTaskId: this.selectedTaskId });
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
      persist({ apiKey: this.apiKey, tasks: this.tasks, selectedTaskId: this.selectedTaskId });
    },
    selectTask(id: string | null) {
      this.selectedTaskId = id;
      persist({ apiKey: this.apiKey, tasks: this.tasks, selectedTaskId: this.selectedTaskId });
    },
    removeTask(id: string) {
      this.tasks = this.tasks.filter((task) => task.id !== id);
      if (this.selectedTaskId === id) {
        this.selectedTaskId = null;
      }
      persist({ apiKey: this.apiKey, tasks: this.tasks, selectedTaskId: this.selectedTaskId });
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
