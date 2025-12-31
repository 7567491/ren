import { onBeforeUnmount, onMounted, ref, watchEffect } from 'vue';

export function useMediaQuery(query: string, options: { defaultState?: boolean } = {}) {
  const state = ref(Boolean(options.defaultState));
  let mediaQuery: MediaQueryList | null = null;

  const cleanup = () => {
    if (mediaQuery) {
      mediaQuery.removeEventListener('change', handleChange);
    }
    mediaQuery = null;
  };

  const handleChange = (event: MediaQueryListEvent) => {
    state.value = event.matches;
  };

  onMounted(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return;
    }
    mediaQuery = window.matchMedia(query);
    state.value = mediaQuery.matches;
    mediaQuery.addEventListener('change', handleChange);
  });

  onBeforeUnmount(() => {
    cleanup();
  });

  watchEffect((onInvalidate) => {
    onInvalidate(() => {
      cleanup();
    });
  });

  return state;
}

