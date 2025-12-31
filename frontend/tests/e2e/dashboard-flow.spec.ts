import { beforeEach, describe, expect, it, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import App from '@/App.vue';

function mockResponse(body: any, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body
  } as Response;
}

describe('Dashboard flow', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
    (window as any).APP_CONFIG = {
      API_BASE: 'http://127.0.0.1:18005',
      API_TIMEOUT: 30000,
      POLL_INTERVAL: 50,
      DEBUG: true
    };
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('creates task, polls progress and renders materials', async () => {
    const pollSnapshots = [
      {
        status: 'avatar_generating',
        message: '头像生成中',
        assets: {}
      },
      {
        status: 'speech_ready',
        message: '语音完成',
        avatar_url: 'https://cdn/avatar.png',
        audio_url: 'https://cdn/audio.mp3',
        assets: {
          avatar_local_path: '/mnt/www/ren/aka-001/avatar.png',
          audio_local_path: '/mnt/www/ren/aka-001/speech.mp3'
        }
      },
      {
        status: 'finished',
        message: '完成',
        avatar_url: 'https://cdn/avatar.png',
        audio_url: 'https://cdn/audio.mp3',
        assets: {
          local_video_url: '/output/aka-001/digital_human.mp4'
        },
        cost: 0.8
      }
    ];
    let pollCount = 0;

    const fetchMock = vi.fn(async (input: RequestInfo, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : input.url;
      if (url.endsWith('/api/characters') && (!init || init.method === 'GET')) {
        return mockResponse([{ id: 'char-mai', name: '默认角色' }]);
      }
      if (url.endsWith('/api/tasks') && init?.method === 'POST') {
        return mockResponse({ job_id: 'aka-001', cost_estimate: { total: 0.5 }, assets: {} });
      }
      if (url.endsWith('/api/tasks/aka-001')) {
        const body = pollSnapshots[Math.min(pollCount, pollSnapshots.length - 1)];
        pollCount += 1;
        return mockResponse(body);
      }
      return mockResponse({ detail: 'not found' }, 404);
    });

    vi.stubGlobal('fetch', fetchMock);

    const wrapper = mount(App);
    await flushPromises();

    // 提交任务
    await wrapper.find('form').trigger('submit.prevent');
    await flushPromises();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/tasks'), expect.objectContaining({ method: 'POST' }));

    // 驱动轮询
    for (let i = 0; i < pollSnapshots.length; i += 1) {
      vi.advanceTimersByTime(60);
      await flushPromises();
    }

    expect(wrapper.find('.result-container').exists()).toBe(true);
    expect(wrapper.findAll('.stage.done').length).toBeGreaterThanOrEqual(2);
    expect(wrapper.find('.material-list li').exists()).toBe(true);
  });
});
