<template>
  <section class="panel creation-panel card">
    <header class="panel-header">
      <div>
        <p class="panel-eyebrow">创作</p>
        <h2>配置数字人任务</h2>
        <p class="panel-subtitle">形象、台词、音色一屏完成</p>
      </div>
    </header>

    <div v-if="formAlert.message" class="form-alert" :class="{ info: formAlert.type === 'info' }">
      {{ formAlert.message }}
    </div>

    <form @submit.prevent="$emit('submit')">
      <details class="section-card section-collapsible" :open="creationSections.avatar" @toggle="handleSectionToggle('avatar', $event)">
        <AvatarConfigurator
          ref="avatarConfiguratorRef"
          :avatar-mode="avatarMode"
          :avatar-prompt="avatarPrompt"
          :accepted-avatar-types="acceptedAvatarTypes"
          :max-avatar-size-label="maxAvatarSizeLabel"
          :pond-label="pondLabel"
          :avatar-file-error="avatarFileError"
          :characters="characters"
          :character-loading="characterLoading"
          :character-error="characterError"
          :selected-character-id="selectedCharacterId"
          :selected-character="selectedCharacter"
          :character-preview-url="characterPreviewUrl"
          :new-character-form="newCharacterForm"
          :new-character-alert="newCharacterAlert"
          :creating-character="creatingCharacter"
          @update:avatar-mode="$emit('update:avatar-mode', $event)"
          @update:avatar-prompt="$emit('update:avatar-prompt', $event)"
          @refresh-characters="$emit('refresh-characters')"
          @update:selected-character-id="$emit('update:selected-character-id', $event)"
          @clear-character-selection="$emit('clear-character-selection')"
          @avatar-files-change="$emit('avatar-files-change', $event)"
          @update:new-character-form="$emit('update:new-character-form', $event)"
          @new-character-file-change="$emit('new-character-file-change', $event)"
          @submit-new-character="$emit('submit-new-character')"
        />
      </details>

      <details class="section-card section-collapsible" :open="creationSections.script" @toggle="handleSectionToggle('script', $event)">
        <ScriptEditor
          :speech-text="speechText"
          :char-count="charCount"
          :estimated-duration="estimatedDuration"
          :estimated-cost="estimatedCost"
          :is-mobile="isMobile"
          :voice-id="voiceId"
          :speed="speed"
          :pitch="pitch"
          :emotion="emotion"
          @update:speech-text="$emit('update:speech-text', $event)"
          @update:voice-id="$emit('update:voice-id', $event)"
          @update:speed="$emit('update:speed', $event)"
          @update:pitch="$emit('update:pitch', $event)"
          @update:emotion="$emit('update:emotion', $event)"
        />
      </details>

      <details
        class="section-card section-collapsible advanced-options"
        :open="creationSections.advanced"
        @toggle="handleSectionToggle('advanced', $event)"
      >
        <summary class="section-summary">
          <div>
            <p class="section-eyebrow">⚙️ 高级参数</p>
            <h3>画质与随机种子</h3>
          </div>
          <p class="section-status">{{ advancedSummary }}</p>
        </summary>
        <div class="section-body">
          <div class="form-group">
            <label for="resolution">分辨率</label>
            <select id="resolution" :value="resolution" @change="$emit('update:resolution', ($event.target as HTMLSelectElement).value)">
              <option value="720p">720p ($0.06/秒)</option>
              <option value="1080p">1080p ($0.12/秒)</option>
            </select>
          </div>
          <div class="form-group">
            <label for="seed">随机种子（可选）</label>
            <input id="seed" type="text" :value="seed" placeholder="留空则由服务端随机生成" @input="$emit('update:seed', ($event.target as HTMLInputElement).value)" />
          </div>
        </div>
      </details>

      <button type="submit" class="btn" :disabled="submitting">
        {{ submitting ? '⏳ 正在创建任务...' : '🚀 生成数字人视频' }}
      </button>
    </form>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { CharacterRecord } from '@/types/characters';
import type { CreationSectionKey } from '@/stores/layoutPrefs';
import AvatarConfigurator from './AvatarConfigurator.vue';
import ScriptEditor from './ScriptEditor.vue';

const props = defineProps<{
  isMobile: boolean;
  avatarMode: 'character' | 'prompt' | 'upload';
  avatarPrompt: string;
  speechText: string;
  voiceId: string;
  resolution: '720p' | '1080p';
  speed: number;
  pitch: number;
  emotion: string;
  seed: string;
  formAlert: { message: string; type: 'info' | 'error' | '' };
  submitting: boolean;
  acceptedAvatarTypes: string[];
  maxAvatarSizeLabel: string;
  pondLabel: string;
  avatarFileError: string;
  characters: CharacterRecord[];
  characterLoading: boolean;
  characterError: string;
  selectedCharacterId: string;
  selectedCharacter: CharacterRecord | null;
  characterPreviewUrl: string;
  newCharacterForm: {
    name: string;
    appearanceZh: string;
    appearanceEn: string;
    voiceZh: string;
    voicePrompt: string;
    voiceId: string;
  };
  newCharacterAlert: { message: string; type: 'error' | 'success' | '' };
  creatingCharacter: boolean;
  charCount: number;
  estimatedDuration: number;
  estimatedCost: number;
  creationSections: Record<CreationSectionKey, boolean>;
}>();

const emit = defineEmits<{
  (event: 'update:avatar-mode', value: 'character' | 'prompt' | 'upload'): void;
  (event: 'update:avatar-prompt', value: string): void;
  (event: 'update:speech-text', value: string): void;
  (event: 'update:voice-id', value: string): void;
  (event: 'update:resolution', value: '720p' | '1080p'): void;
  (event: 'update:speed', value: number): void;
  (event: 'update:pitch', value: number): void;
  (event: 'update:emotion', value: string): void;
  (event: 'update:seed', value: string): void;
  (event: 'refresh-characters'): void;
  (event: 'update:selected-character-id', id: string): void;
  (event: 'clear-character-selection'): void;
  (event: 'avatar-files-change', files: Array<{ file?: File }>): void;
  (event: 'update:new-character-form', value: Record<string, string>): void;
  (event: 'new-character-file-change', event: Event): void;
  (event: 'submit-new-character'): void;
  (event: 'submit'): void;
  (event: 'toggle-section', payload: { id: CreationSectionKey; value: boolean }): void;
}>();

const avatarConfiguratorRef = ref<InstanceType<typeof AvatarConfigurator> | null>(null);
const advancedSummary = computed(() => `${props.resolution.toUpperCase()} · 种子${props.seed ? '已填' : '自动'}`);

function handleSectionToggle(id: CreationSectionKey, event: Event) {
  const target = event.currentTarget as HTMLDetailsElement | null;
  emit('toggle-section', { id, value: Boolean(target?.open) });
}

defineExpose({
  clearAvatarUpload() {
    avatarConfiguratorRef.value?.clearAvatarUpload?.();
  }
});
</script>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
}

.panel-eyebrow {
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.6);
  margin: 0 0 0.15rem;
}

.panel-subtitle {
  margin: 0.15rem 0 0;
  color: rgba(226, 232, 240, 0.7);
  font-size: 0.9rem;
}

.section-card {
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 18px;
  padding: 1rem;
  background: rgba(15, 23, 42, 0.45);
  margin-bottom: 1rem;
}

.section-collapsible summary::-webkit-details-marker {
  display: none;
}

.section-summary {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
  cursor: pointer;
  list-style: none;
}

.section-summary:focus-visible {
  outline: 2px solid #22d3ee;
  border-radius: 12px;
}

.section-body {
  margin-top: 0.85rem;
}

.section-eyebrow {
  margin: 0;
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.6);
  text-transform: uppercase;
}

.section-status {
  margin: 0;
  color: rgba(224, 231, 255, 0.75);
  font-size: 0.9rem;
}

.character-library {
  border: 1px solid rgba(99, 102, 241, 0.3);
  padding: 1rem;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.92), rgba(30, 64, 175, 0.65));
  color: #e5e7eb;
}

.character-select {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.75rem;
}

.character-select select {
  flex: 1;
  padding: 0.4rem 0.5rem;
}

.character-detail {
  display: flex;
  gap: 1rem;
  align-items: center;
  margin-bottom: 1rem;
}

.character-image {
  width: 140px;
  height: 140px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.link-btn {
  border: none;
  background: none;
  color: #60a5fa;
  cursor: pointer;
}

.script-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(200px, 0.45fr);
  gap: 1rem;
  align-items: flex-start;
}

.script-side {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.script-field label {
  font-weight: 600;
  display: block;
  margin-bottom: 0.5rem;
}

.script-templates {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin: 0 0 0.5rem;
}

.template-btn {
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 999px;
  padding: 0.35rem 0.8rem;
  background: rgba(15, 23, 42, 0.6);
  color: rgba(226, 232, 240, 0.9);
  cursor: pointer;
  font-size: 0.85rem;
}

.template-btn:hover {
  border-color: rgba(59, 130, 246, 0.6);
  color: #f8fafc;
}

.section-card textarea {
  width: 100%;
}

.script-estimate {
  align-self: stretch;
}

.voice-card {
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 14px;
  padding: 0.85rem;
  background: rgba(2, 6, 23, 0.7);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.slider-container {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.slider-container input {
  flex: 1;
}

.slider-value {
  min-width: 46px;
  text-align: right;
  font-weight: 600;
  color: rgba(226, 232, 240, 0.8);
}

@media (max-width: 960px) {
  .script-layout {
    grid-template-columns: 1fr;
  }
}

.advanced-options {
  border: 1px dashed rgba(148, 163, 184, 0.35);
  background: rgba(15, 23, 42, 0.3);
}
</style>
