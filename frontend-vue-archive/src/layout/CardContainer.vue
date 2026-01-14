<template>
  <article :class="['card', 'card-shell', { collapsed: isCollapsed }]">
    <header class="card-shell__header">
      <div class="card-shell__title">
        <p v-if="eyebrow" class="card-shell__eyebrow">{{ eyebrow }}</p>
        <h2>{{ title }}</h2>
        <p v-if="subtitle" class="card-shell__subtitle">{{ subtitle }}</p>
      </div>
      <div class="card-shell__meta">
        <slot name="status" />
        <slot name="actions" />
        <button
          v-if="collapsible"
          type="button"
          class="collapse-btn"
          @click="toggleCollapse"
          :aria-expanded="!isCollapsed"
        >
          {{ isCollapsed ? '展开' : '收起' }}
        </button>
      </div>
    </header>
    <div v-if="error" class="card-shell__error">{{ error }}</div>
    <transition name="card-collapse">
      <section v-show="!isCollapsed" class="card-shell__body">
        <slot />
      </section>
    </transition>
    <footer v-if="$slots.footer && !isCollapsed" class="card-shell__footer">
      <slot name="footer" />
    </footer>
  </article>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';

interface Props {
  title: string;
  subtitle?: string;
  eyebrow?: string;
  collapsible?: boolean;
  initiallyCollapsed?: boolean;
  persistKey?: string;
  error?: string;
}

const props = withDefaults(defineProps<Props>(), {
  collapsible: false,
  initiallyCollapsed: false,
  error: ''
});

const emit = defineEmits<{ (event: 'toggle', collapsed: boolean): void }>();

const isCollapsed = ref(Boolean(props.initiallyCollapsed));
const userInteracted = ref(false);

const storageKey = computed(() => (props.persistKey ? `card-state:${props.persistKey}` : ''));

if (typeof window !== 'undefined' && storageKey.value) {
  try {
    const stored = window.localStorage.getItem(storageKey.value);
    if (stored === 'collapsed') {
      isCollapsed.value = true;
    } else if (stored === 'expanded') {
      isCollapsed.value = false;
    }
  } catch {
    // ignore
  }
}

watch(
  () => props.initiallyCollapsed,
  (value) => {
    if (userInteracted.value) return;
    isCollapsed.value = Boolean(value);
  }
);

function toggleCollapse() {
  if (!props.collapsible) return;
  userInteracted.value = true;
  isCollapsed.value = !isCollapsed.value;
  emit('toggle', isCollapsed.value);
  if (storageKey.value && typeof window !== 'undefined') {
    try {
      window.localStorage.setItem(storageKey.value, isCollapsed.value ? 'collapsed' : 'expanded');
    } catch {
      // ignore
    }
  }
}
</script>

<style scoped>
.card-shell__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
}

.card-shell__title h2 {
  margin: 0;
  font-size: 1.35rem;
}

.card-shell__subtitle {
  margin: 0.15rem 0 0;
  color: rgba(255, 255, 255, 0.65);
  font-size: 0.9rem;
}

.card-shell__eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 0 0 0.25rem;
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.6);
}

.card-shell__meta {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.card-shell__body {
  margin-top: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.card-shell__footer {
  margin-top: 1rem;
}

.card-shell__error {
  margin-top: 0.75rem;
  padding: 0.75rem;
  border-radius: 10px;
  background: rgba(231, 76, 60, 0.15);
  border: 1px solid rgba(231, 76, 60, 0.5);
  color: #ffcdd2;
  font-size: 0.9rem;
}

.collapse-btn {
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(15, 23, 42, 0.7);
  color: #e5e7eb;
  border-radius: 10px;
  padding: 0.35rem 0.75rem;
  cursor: pointer;
  font-size: 0.85rem;
}

.card-shell.collapsed {
  opacity: 0.92;
}

.card-collapse-enter-active,
.card-collapse-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.card-collapse-enter-from,
.card-collapse-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

@media (max-width: 768px) {
  .card-shell__header {
    flex-direction: column;
  }
  .card-shell__meta {
    justify-content: flex-start;
  }
}
</style>

