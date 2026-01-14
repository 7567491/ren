<template>
  <section class="section-card section-collapsible">
    <summary class="section-summary">
      <div>
        <p class="section-eyebrow">角色与头像</p>
        <h3>角色管理</h3>
      </div>
      <p class="section-status">{{ statusText }}</p>
    </summary>
    <div class="section-body">
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
        <button type="button" class="btn-text" :disabled="characterLoading" @click="$emit('refresh-characters')">
          {{ characterLoading ? '刷新中…' : '重新载入' }}
        </button>
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
            <input
              type="text"
              :value="newCharacterForm.name"
              placeholder="如：产品代言人 Lisa"
              @input="$emit('update:new-character-form', { ...newCharacterForm, name: ($event.target as HTMLInputElement).value })"
            />
            <label>形象描述（中文）</label>
            <textarea
              :value="newCharacterForm.appearanceZh"
              rows="3"
              @input="$emit('update:new-character-form', { ...newCharacterForm, appearanceZh: ($event.target as HTMLTextAreaElement).value })"
            ></textarea>
            <label>形象描述（英文，可选）</label>
            <textarea
              :value="newCharacterForm.appearanceEn"
              rows="2"
              @input="$emit('update:new-character-form', { ...newCharacterForm, appearanceEn: ($event.target as HTMLTextAreaElement).value })"
            ></textarea>
            <label>声音提示（中文，可选）</label>
            <textarea
              :value="newCharacterForm.voiceZh"
              rows="2"
              @input="$emit('update:new-character-form', { ...newCharacterForm, voiceZh: ($event.target as HTMLTextAreaElement).value })"
            ></textarea>
            <label>声音提示（英文/Prompt，可选）</label>
            <textarea
              :value="newCharacterForm.voicePrompt"
              rows="2"
              @input="$emit('update:new-character-form', { ...newCharacterForm, voicePrompt: ($event.target as HTMLTextAreaElement).value })"
            ></textarea>
            <label>推荐音色 ID（可选）</label>
            <input
              type="text"
              :value="newCharacterForm.voiceId"
              @input="$emit('update:new-character-form', { ...newCharacterForm, voiceId: ($event.target as HTMLInputElement).value })"
            />
            <label>上传头像</label>
            <input type="file" accept="image/*" @change="$emit('new-character-file-change', $event)" />
            <small>支持 PNG/JPG，最大 10MB</small>
            <button type="button" class="btn-secondary" :disabled="creatingCharacter" @click="$emit('submit-new-character')">
              {{ creatingCharacter ? '上传中...' : '保存角色' }}
            </button>
          </div>
        </details>
      </section>
    </div>
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
}>();

defineEmits<{
  (event: 'update:avatar-mode', value: 'character' | 'prompt' | 'upload'): void;
  (event: 'update:avatar-prompt', value: string): void;
  (event: 'refresh-characters'): void;
  (event: 'update:selected-character-id', id: string): void;
  (event: 'clear-character-selection'): void;
  (event: 'avatar-files-change', files: Array<{ file?: File }>): void;
  (event: 'update:new-character-form', value: Record<string, string>): void;
  (event: 'new-character-file-change', event: Event): void;
  (event: 'submit-new-character'): void;
}>();

const avatarPond = ref<any>(null);

const statusText = computed(() => {
  if (props.avatarMode === 'character' && props.selectedCharacter?.name) {
    return `已选 ${props.selectedCharacter.name}`;
  }
  if (props.avatarMode === 'prompt' && props.avatarPrompt.trim()) {
    return `AI 描述 · ${props.avatarPrompt.trim().slice(0, 12)}`;
  }
  if (props.avatarMode === 'upload') {
    return '等待头像上传';
  }
  return '尚未配置';
});

defineExpose({
  clearAvatarUpload() {
    avatarPond.value?.removeFiles();
  }
});
</script>
