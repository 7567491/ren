<template>
  <section class="cost-badge" :class="{ 'cost-badge--sticky': sticky }">
    <header>
      <p class="label">实时预估</p>
      <strong>{{ charCount }} 字</strong>
    </header>
    <dl>
      <div>
        <dt>时长</dt>
        <dd>{{ estimatedDuration }} 秒</dd>
      </div>
      <div>
        <dt>费用</dt>
        <dd>${{ estimatedCost.toFixed(2) }}</dd>
      </div>
    </dl>
    <p class="hint">超过 1000 字请拆分任务，避免生成失败。</p>
  </section>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    charCount: number;
    estimatedDuration: number;
    estimatedCost: number;
    sticky?: boolean;
  }>(),
  { sticky: false }
);
</script>

<style scoped>
.cost-badge {
  border: 1px solid rgba(45, 212, 191, 0.35);
  border-radius: 16px;
  padding: 0.9rem 1rem;
  background: radial-gradient(circle at top, rgba(13, 148, 136, 0.35), rgba(6, 95, 70, 0.35));
  color: #ecfeff;
  box-shadow: inset 0 0 0 1px rgba(45, 212, 191, 0.15);
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 220px;
}

.cost-badge--sticky {
  position: sticky;
  top: 1rem;
}

header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.label {
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.75rem;
  color: rgba(224, 231, 255, 0.7);
}

dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(80px, 1fr));
  gap: 0.75rem;
  margin: 0.25rem 0;
}

dt {
  margin: 0;
  font-size: 0.8rem;
  color: rgba(224, 231, 255, 0.75);
}

dd {
  margin: 0.15rem 0 0;
  font-size: 1.15rem;
  font-weight: 600;
}

.hint {
  margin: 0;
  font-size: 0.8rem;
  color: rgba(224, 231, 255, 0.75);
}

@media (max-width: 768px) {
  .cost-badge {
    position: static;
    width: 100%;
  }
}
</style>
