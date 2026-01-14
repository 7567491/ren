interface AnalyticsPayload {
  [key: string]: string | number | boolean | null | undefined;
}

interface AnalyticsRecord {
  event: string;
  payload?: AnalyticsPayload;
  ts?: number;
}

export function useAnalytics() {
  async function track(event: string, payload: AnalyticsPayload = {}) {
    const record: AnalyticsRecord = {
      event,
      payload,
      ts: Date.now()
    };
    try {
      await fetch('/api/analytics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(record)
      });
    } catch (error) {
      if (import.meta.env?.DEV) {
        console.info('[analytics]', record, error);
      }
    }
  }

  return { track };
}
