import { defineStore } from 'pinia';

export type CreationSectionKey = 'avatar' | 'script' | 'advanced';

export interface LayoutPrefs {
  heroStepTooltipShown: boolean;
  creationSections: Record<CreationSectionKey, boolean>;
  resultSectionCollapsed: boolean;
  lastGuideTs?: number;
}

const STORAGE_KEY = 'digital-human-layout-prefs';

function getDefaultState(): LayoutPrefs {
  return {
    heroStepTooltipShown: false,
    creationSections: {
      avatar: true,
      script: true,
      advanced: false
    },
    resultSectionCollapsed: false,
    lastGuideTs: undefined
  };
}

function loadPersisted(): LayoutPrefs {
  if (typeof window === 'undefined') return getDefaultState();
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return getDefaultState();
    const parsed = JSON.parse(raw);
    return {
      ...getDefaultState(),
      ...parsed,
      creationSections: {
        ...getDefaultState().creationSections,
        ...(parsed?.creationSections || {})
      }
    };
  } catch (error) {
    console.warn('failed to load layout prefs', error);
    return getDefaultState();
  }
}

function persistState(state: LayoutPrefs) {
  if (typeof window === 'undefined') return;
  const payload = JSON.stringify({
    heroStepTooltipShown: state.heroStepTooltipShown,
    creationSections: state.creationSections,
    resultSectionCollapsed: state.resultSectionCollapsed,
    lastGuideTs: state.lastGuideTs
  });
  const writer = () => {
    try {
      window.localStorage.setItem(STORAGE_KEY, payload);
    } catch (error) {
      console.warn('failed to persist layout prefs', error);
    }
  };
  if (typeof window.requestIdleCallback === 'function') {
    window.requestIdleCallback(writer);
  } else {
    window.setTimeout(writer, 0);
  }
}

export const useLayoutPrefsStore = defineStore('layoutPrefs', {
  state: (): LayoutPrefs => loadPersisted(),
  actions: {
    markHeroTooltipSeen() {
      if (this.heroStepTooltipShown) return;
      this.heroStepTooltipShown = true;
      persistState(this.$state);
    },
    setCreationSection(id: CreationSectionKey, value: boolean) {
      if (this.creationSections[id] === value) return;
      this.creationSections = {
        ...this.creationSections,
        [id]: value
      };
      persistState(this.$state);
    },
    toggleCreationSection(id: CreationSectionKey) {
      this.setCreationSection(id, !this.creationSections[id]);
    },
    setResultSectionCollapsed(value: boolean) {
      if (this.resultSectionCollapsed === value) return;
      this.resultSectionCollapsed = value;
      persistState(this.$state);
    },
    resetPrefs() {
      Object.assign(this.$state, getDefaultState());
      persistState(this.$state);
    },
    touchGuide(timestamp: number) {
      this.lastGuideTs = timestamp;
      persistState(this.$state);
    }
  }
});
