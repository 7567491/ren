import { beforeAll, afterEach, vi } from 'vitest';
import { config } from '@vue/test-utils';
import { defineComponent, h } from 'vue';

config.global.stubs = {
  transition: false,
  'transition-group': false
};

vi.mock('video.js', () => {
  return {
    default: vi.fn(() => ({
      dispose: vi.fn()
    }))
  };
});

vi.mock('vue-filepond', () => {
  return {
    default: () =>
      defineComponent({
        name: 'FilePondStub',
        emits: ['updatefiles'],
        setup(_, { emit, expose }) {
          expose({
            removeFiles: vi.fn()
          });
          return () =>
            h('div', {
              class: 'filepond-stub',
              onClick: () => emit('updatefiles', [])
            });
        }
      })
  };
});

beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => {
      return {
        media: query,
        matches: false,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn()
      };
    }
  });

  Object.defineProperty(navigator, 'clipboard', {
    writable: true,
    value: {
      writeText: vi.fn().mockResolvedValue(undefined)
    }
  });
});

afterEach(() => {
  vi.clearAllMocks();
});
