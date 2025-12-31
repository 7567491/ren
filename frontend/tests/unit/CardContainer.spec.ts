import { mount } from '@vue/test-utils';
import { describe, expect, it, beforeEach } from 'vitest';
import CardContainer from '@/layout/CardContainer.vue';

describe('CardContainer', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('renders title and toggles collapse', async () => {
    const wrapper = mount(CardContainer, {
      props: {
        title: 'API Key',
        collapsible: true
      },
      slots: {
        default: '<p class="body">content</p>'
      }
    });
    expect(wrapper.text()).toContain('content');
    await wrapper.find('.collapse-btn').trigger('click');
    expect(wrapper.find('.body').isVisible()).toBe(false);
    await wrapper.find('.collapse-btn').trigger('click');
    expect(wrapper.find('.body').isVisible()).toBe(true);
  });

  it('persists collapse state via persistKey', async () => {
    const persistKey = 'card-test';
    const wrapper = mount(CardContainer, {
      props: {
        title: 'Persist',
        collapsible: true,
        persistKey
      },
      slots: {
        default: 'persisted-body'
      }
    });
    await wrapper.find('.collapse-btn').trigger('click');
    expect(window.localStorage.getItem(`card-state:${persistKey}`)).toBe('collapsed');
    await wrapper.find('.collapse-btn').trigger('click');
    expect(window.localStorage.getItem(`card-state:${persistKey}`)).toBe('expanded');
  });

  it('displays error banner when error prop is provided', () => {
    const wrapper = mount(CardContainer, {
      props: {
        title: 'Error Card',
        error: '发生异常',
        collapsible: true
      },
      slots: {
        default: 'body'
      }
    });
    expect(wrapper.text()).toContain('发生异常');
    expect(wrapper.find('.card-shell__error').exists()).toBe(true);
  });
});

