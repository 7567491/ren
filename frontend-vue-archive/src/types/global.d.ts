import type { FrontendAppConfig } from './app-config';

declare global {
  interface Window {
    APP_CONFIG?: Partial<FrontendAppConfig>;
  }
}

export {};
