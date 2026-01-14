<template>
  <section class="card config-card">
    <header>
      <p class="eyebrow">{{ subtitle }}</p>
      <h2>{{ title }}</h2>
    </header>
    <dl>
      <div class="row">
        <dt>API Base URL</dt>
        <dd><code>{{ config.API_BASE }}</code></dd>
      </div>
      <div class="row">
        <dt>Timeout</dt>
        <dd>{{ (config.API_TIMEOUT / 1000).toFixed(0) }} 秒</dd>
      </div>
      <div class="row">
        <dt>轮询间隔</dt>
        <dd>{{ (config.POLL_INTERVAL / 1000).toFixed(1) }} 秒</dd>
      </div>
      <div class="row">
        <dt>调试模式</dt>
        <dd>
          <span :class="['badge', config.DEBUG ? 'badge--on' : 'badge--off']">
            {{ config.DEBUG ? '开启' : '关闭' }}
          </span>
        </dd>
      </div>
    </dl>
  </section>
</template>

<script setup lang="ts">
import type { FrontendAppConfig } from '@/types/app-config';

interface Props {
  config: FrontendAppConfig;
  title: string;
  subtitle: string;
}

defineProps<Props>();
</script>

<style scoped>
.config-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

dl {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.row:last-child {
  border-bottom: none;
}

dt {
  color: rgba(255, 255, 255, 0.75);
  font-size: 0.9rem;
}

dd {
  margin: 0;
  font-weight: 600;
}

code {
  background: rgba(0, 0, 0, 0.2);
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  font-size: 0.85rem;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 0.1rem 0.6rem;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 600;
}

.badge--on {
  background: rgba(46, 204, 113, 0.2);
  color: #2ecc71;
}

.badge--off {
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
}

.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.6);
}
</style>
