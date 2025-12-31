<template>
  <section class="card flow-card">
    <header>
      <p class="eyebrow">{{ subtitle }}</p>
      <h2>{{ title }}</h2>
    </header>
    <ol>
      <li v-for="step in steps" :key="step.id">
        <div class="icon">{{ step.icon }}</div>
        <div>
          <p class="step-title">{{ step.title }}</p>
          <p class="step-detail">{{ step.detail }}</p>
        </div>
      </li>
    </ol>
  </section>
</template>

<script setup lang="ts">
export interface TaskFlowStep {
  id: string;
  title: string;
  detail: string;
  icon?: string;
}

interface Props {
  title: string;
  subtitle: string;
  steps: TaskFlowStep[];
}

defineProps<Props>();
</script>

<style scoped>
.flow-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

ol {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

li {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
  padding: 0.75rem 0;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.12);
}

li:last-child {
  border-bottom: none;
}

.icon {
  font-size: 1.4rem;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
}

.step-title {
  font-weight: 600;
}

.step-detail {
  margin-top: 0.15rem;
  color: rgba(255, 255, 255, 0.75);
  font-size: 0.9rem;
}
</style>
