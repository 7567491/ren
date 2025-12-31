<template>
  <section class="panel creation-panel card">
    <header class="panel-header">
      <div>
        <p class="panel-eyebrow">创作</p>
        <h2>配置数字人任务</h2>
        <p class="panel-subtitle">角色、脚本、音色与高级参数</p>
      </div>
      <div class="step-pill">Step 2</div>
    </header>

    <div v-if="formAlert.message" class="form-alert" :class="{ info: formAlert.type === 'info' }">
      {{ formAlert.message }}
    </div>

    <form @submit.prevent="$emit('submit')">
      <article class="section-card">
        <header class="section-header">
          <div>
            <p class="section-eyebrow">头像模式</p>
            <h3>角色管理</h3>
          </div>
          <button type="button" class="btn-text" :disabled="characterLoading" @click="$emit('refresh-characters')">
            {{ characterLoading ? '刷新中…' : '重新载入' }}
          </button>
        </header>
        <div class="radio-group">
          <label>
            <input type="radio" value="character" :checked="avatarMode === 'character'" @change="$emit('update:avatar-mode', 'character')" />
            预制人物
          </label>
          <label>
            <input type="radio" value="prompt" :checked="avatarMode === 'prompt'" @change="$emit('update:avatar-mode', 'prompt')" />
            AI 生成头像
          </label>
          <label>
            <input type="radio" value="upload" :checked="avatarMode === 'upload'" @change="$emit('update:avatar-mode', 'upload')" />
            上传头像
          </label>
        </div>
        <section v-show="avatarMode === 'prompt'" class="form-group mode-content active">
          <label for="avatar_prompt">头像描述</label>
          <input
            id="avatar_prompt"
            type="text"
            :value="avatarPrompt"
            placeholder="例如：专业女性播音员，商务装"
            @input="$emit('update:avatar-prompt', ($event.target as HTMLInputElement).value)"
          />
        </section>
        <section v-show="avatarMode === 'upload'" class="form-group mode-content active">
          <label for="avatar_upload">上传头像</label>
          <FilePond
            ref="avatarPond"
            :allow-multiple="false"
            :accepted-file-types="acceptedAvatarTypes"
            :max-file-size="maxAvatarSizeLabel"
            :instant-upload="false"
            :label-idle="pondLabel"
            @updatefiles="(files) => $emit('avatar-files-change', files)"
          />
          <small>支持 PNG/JPG，最大 5MB</small>
          <p v-if="avatarFileError" class="input-error">{{ avatarFileError }}</p>
        </section>
        <section v-show="avatarMode === 'character'" class="form-group character-library">
          <p class="hint">选择角色即默认使用其头像与声音设定。</p>
          <div v-if="characterError" class="input-error">{{ characterError }}</div>
          <div class="character-select">
            <select :value="selectedCharacterId" @change="$emit('update:selected-character-id', ($event.target as HTMLSelectElement).value)">
              <option disabled value="">{{ characterLoading ? '加载中...' : '请选择人物' }}</option>
              <option v-for="char in characters" :key="char.id" :value="char.id">
                {{ char.name }}
              </option>
            </select>
            <button type="button" class="link-btn" v-if="selectedCharacterId" @click="$emit('clear-character-selection')">清除选择</button>
          </div>
          <div v-if="selectedCharacter" class="character-detail">
            <img :src="characterPreviewUrl" :alt="selectedCharacter.name" class="character-image" />
            <div class="character-meta">
              <strong>{{ selectedCharacter.name }}</strong>
              <p class="character-desc">
                {{ selectedCharacter.appearance?.zh || selectedCharacter.appearance?.en }}
              </p>
              <p class="character-desc" v-if="selectedCharacter.voice?.zh">
                语音：{{ selectedCharacter.voice.zh }}
              </p>
              <p class="character-desc" v-if="selectedCharacter.voice?.voice_id">
                推荐音色 ID：{{ selectedCharacter.voice.voice_id }}
              </p>
            </div>
          </div>
          <details class="character-upload">
            <summary>上传新人物</summary>
            <div class="upload-form">
              <div v-if="newCharacterAlert.message" class="input-error" :class="{ success: newCharacterAlert.type === 'success' }">
                {{ newCharacterAlert.message }}
              </div>
              <label>名称</label>
              <input type="text" :value="newCharacterForm.name" placeholder="如：产品代言人 Lisa" @input="$emit('update:new-character-form', { ...newCharacterForm, name: ($event.target as HTMLInputElement).value })" />
              <label>形象描述（中文）</label>
              <textarea :value="newCharacterForm.appearanceZh" rows="3" @input="$emit('update:new-character-form', { ...newCharacterForm, appearanceZh: ($event.target as HTMLTextAreaElement).value })"></textarea>
              <label>形象描述（英文，可选）</label>
              <textarea :value="newCharacterForm.appearanceEn" rows="2" @input="$emit('update:new-character-form', { ...newCharacterForm, appearanceEn: ($event.target as HTMLTextAreaElement).value })"></textarea>
              <label>声音提示（中文，可选）</label>
              <textarea :value="newCharacterForm.voiceZh" rows="2" @input="$emit('update:new-character-form', { ...newCharacterForm, voiceZh: ($event.target as HTMLTextAreaElement).value })"></textarea>
              <label>声音提示（英文/Prompt，可选）</label>
              <textarea :value="newCharacterForm.voicePrompt" rows="2" @input="$emit('update:new-character-form', { ...newCharacterForm, voicePrompt: ($event.target as HTMLTextAreaElement).value })"></textarea>
              <label>推荐音色 ID（可选）</label>
              <input type="text" :value="newCharacterForm.voiceId" @input="$emit('update:new-character-form', { ...newCharacterForm, voiceId: ($event.target as HTMLInputElement).value })" />
              <label>上传头像</label>
              <input type="file" accept="image/*" @change="$emit('new-character-file-change', $event)" />
              <small>支持 PNG/JPG，最大 10MB</small>
              <button type="button" class="btn-secondary" :disabled="creatingCharacter" @click="$emit('submit-new-character')">
                {{ creatingCharacter ? '上传中...' : '保存角色' }}
              </button>
            </div>
          </details>
        </section>
      </article>

      <article class="section-card">
        <header class="section-header">
          <div>
            <p class="section-eyebrow">脚本与音色</p>
            <h3>播报内容</h3>
          </div>
          <div class="estimates">
            <span>{{ charCount }} / 1000 字</span>
            <span>预估 {{ estimatedDuration }} 秒</span>
            <span>${{ estimatedCost.toFixed(2) }}</span>
          </div>
        </header>
        <div class="form-group">
          <label for="speech_text">播报文本</label>
          <textarea
            id="speech_text"
            :value="speechText"
            maxlength="1000"
            rows="5"
            placeholder="请输入数字人要播报的内容..."
            @input="$emit('update:speech-text', ($event.target as HTMLTextAreaElement).value)"
          ></textarea>
        </div>
        <div class="form-group">
          <label for="voice_id">音色</label>
          <select id="voice_id" :value="voiceId" @change="$emit('update:voice-id', ($event.target as HTMLSelectElement).value)">
            <option value="female-shaonv">女声 - 少女</option>
            <option value="female-yujie">女声 - 御姐</option>
            <option value="male-qn-qingse">男声 - 青涩</option>
            <option value="male-qn-jingying">男声 - 精英</option>
          </select>
        </div>
      </article>

      <details class="section-card advanced-options" open>
        <summary>⚙️ 高级选项</summary>
        <div class="form-group">
          <label for="resolution">分辨率</label>
          <select id="resolution" :value="resolution" @change="$emit('update:resolution', ($event.target as HTMLSelectElement).value)">
            <option value="720p">720p ($0.06/秒)</option>
            <option value="1080p">1080p ($0.12/秒)</option>
          </select>
        </div>
        <div class="form-group">
          <label for="speed">语速</label>
          <div class="slider-container">
            <input id="speed" type="range" min="0.5" max="2" step="0.1" :value="speed" @input="$emit('update:speed', Number(($event.target as HTMLInputElement).value))" />
            <span class="slider-value">{{ speed.toFixed(1) }}</span>
          </div>
        </div>
        <div class="form-group">
          <label for="pitch">音调</label>
          <div class="slider-container">
            <input id="pitch" type="range" min="-12" max="12" step="1" :value="pitch" @input="$emit('update:pitch', Number(($event.target as HTMLInputElement).value))" />
            <span class="slider-value">{{ pitch }}</span>
          </div>
        </div>
        <div class="form-group">
          <label for="emotion">情绪</label>
          <select id="emotion" :value="emotion" @change="$emit('update:emotion', ($event.target as HTMLSelectElement).value)">
            <option value="neutral">中性</option>
            <option value="happy">开心</option>
            <option value="sad">悲伤</option>
            <option value="angry">愤怒</option>
          </select>
        </div>
        <div class="form-group">
          <label for="seed">随机种子（可选）</label>
          <input id="seed" type="text" :value="seed" placeholder="留空则由服务端随机生成" @input="$emit('update:seed', ($event.target as HTMLInputElement).value)" />
        </div>
      </details>

      <section class="form-group debug-toggle">
        <label>
          <input type="checkbox" :checked="debugMode" @change="$emit('update:debug-mode', ($event.target as HTMLInputElement).checked)" />
          启用调试模式
        </label>
        <small>{{ debugHint }}</small>
      </section>

      <button type="submit" class="btn" :disabled="submitting">
        {{ submitting ? '⏳ 正在创建任务...' : '🚀 生成数字人视频' }}
      </button>
    </form>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import vueFilePond from 'vue-filepond';
import FilePondPluginImagePreview from 'filepond-plugin-image-preview';
import FilePondPluginFileValidateType from 'filepond-plugin-file-validate-type';
import FilePondPluginFileValidateSize from 'filepond-plugin-file-validate-size';
import type { CharacterRecord } from '@/types/characters';

const FilePond = vueFilePond(FilePondPluginImagePreview, FilePondPluginFileValidateType, FilePondPluginFileValidateSize);

const props = defineProps<{
  avatarMode: 'character' | 'prompt' | 'upload';
  avatarPrompt: string;
  speechText: string;
  voiceId: string;
  resolution: '720p' | '1080p';
  speed: number;
  pitch: number;
  emotion: string;
  seed: string;
  debugMode: boolean;
  debugHint: string;
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
  (event: 'update:debug-mode', value: boolean): void;
  (event: 'refresh-characters'): void;
  (event: 'update:selected-character-id', id: string): void;
  (event: 'clear-character-selection'): void;
  (event: 'avatar-files-change', files: Array<{ file?: File }>): void;
  (event: 'update:new-character-form', value: Record<string, string>): void;
  (event: 'new-character-file-change', event: Event): void;
  (event: 'submit-new-character'): void;
  (event: 'submit'): void;
}>();

const avatarPond = ref<any>(null);

defineExpose({
  clearAvatarUpload() {
    avatarPond.value?.removeFiles();
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

.step-pill {
  border-radius: 999px;
  padding: 0.2rem 0.65rem;
  background: rgba(14, 165, 233, 0.2);
  border: 1px solid rgba(14, 165, 233, 0.4);
  font-weight: 600;
  font-size: 0.85rem;
}

.section-card {
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 18px;
  padding: 1rem;
  background: rgba(15, 23, 42, 0.45);
  margin-bottom: 1rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.section-eyebrow {
  margin: 0;
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.6);
  text-transform: uppercase;
}

.estimates {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  font-size: 0.85rem;
  color: rgba(226, 232, 240, 0.8);
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

.section-card textarea {
  width: 100%;
}

.advanced-options {
  border: 1px dashed rgba(148, 163, 184, 0.35);
  background: rgba(15, 23, 42, 0.3);
}
</style>
