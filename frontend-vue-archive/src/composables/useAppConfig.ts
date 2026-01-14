import type { FrontendAppConfig } from '../types/app-config';

const FALLBACK_CONFIG: FrontendAppConfig = {
  API_BASE: 'http://127.0.0.1:18005',
  API_TIMEOUT: 30000,
  POLL_INTERVAL: 2000,
  DEBUG: true
};

export function useAppConfig(): FrontendAppConfig {
  if (typeof window === 'undefined') {
    return FALLBACK_CONFIG;
  }

  const runtimeConfig = window.APP_CONFIG ?? {};
  return {
    ...FALLBACK_CONFIG,
    ...runtimeConfig
  } as FrontendAppConfig;
}
