import { createI18n } from 'vue-i18n';
import zhCN from '../locales/zh-CN.json';

export function setupI18n() {
  return createI18n({
    legacy: false,
    locale: 'zh-CN',
    fallbackLocale: 'zh-CN',
    messages: {
      'zh-CN': zhCN
    }
  });
}
