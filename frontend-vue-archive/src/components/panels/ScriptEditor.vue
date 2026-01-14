<template>
  <section class="section-card section-collapsible">
    <summary class="section-summary">
      <div>
        <p class="section-eyebrow">脚本与音色</p>
        <h3>播报内容</h3>
      </div>
      <p class="section-status">{{ summaryText }}</p>
    </summary>
    <div class="section-body script-layout">
      <div class="script-field">
        <label for="speech_text">播报文本</label>
        <div class="script-templates">
          <button
            v-for="template in templates"
            :key="template.id"
            type="button"
            class="template-btn"
            @click="$emit('update:speech-text', template.content)"
          >
            {{ template.label }}
          </button>
        </div>
        <textarea
          id="speech_text"
          :value="speechText"
          maxlength="1000"
          rows="6"
          placeholder="请输入数字人要播报的内容..."
          @input="$emit('update:speech-text', ($event.target as HTMLTextAreaElement).value)"
        ></textarea>
      </div>
      <div class="script-side">
        <CostEstimateBadge
          class="script-estimate"
          :char-count="charCount"
          :estimated-duration="estimatedDuration"
          :estimated-cost="estimatedCost"
          :sticky="!isMobile"
        />
        <div class="voice-card">
          <div class="form-group">
            <label for="voice_id">音色</label>
            <select id="voice_id" :value="voiceId" @change="$emit('update:voice-id', ($event.target as HTMLSelectElement).value)">
              <option value="Chinese (Mandarin)_Reliable_Executive">普通话 · 稳重高管男声</option>
              <option value="Chinese (Mandarin)_News_Anchor">普通话 · 新闻女主播</option>
              <option value="Chinese (Mandarin)_Warm_Bestie">普通话 · 温暖闺蜜</option>
              <option value="Chinese (Mandarin)_Gentleman">普通话 · 绅士男声</option>
              <option value="Chinese (Mandarin)_Warm_Girl">普通话 · 暖心女声</option>
              <option value="Chinese (Mandarin)_Male_Announcer">普通话 · 男播音员</option>
              <option value="Chinese (Mandarin)_Gentle_Youth">普通话 · 温柔青年</option>
              <option value="Chinese (Mandarin)_Cute_Spirit">普通话 · 可爱精灵</option>
              <option value="Cantonese_GentleLady">粤语 · 温柔女士</option>
              <option value="Cantonese_Narrator">粤语 · 叙述男声</option>
              <option value="English_magnetic_voiced_man">English · Magnetic Male</option>
              <option value="English_radiant_girl">English · Radiant Girl</option>
              <option value="English_captivating_female1">English · Captivating Female</option>
              <option value="English_Upbeat_Woman">English · Upbeat Woman</option>
              <option value="English_Trustworth_Man">English · Trustworthy Male</option>
              <option value="English_CalmWoman">English · Calm Woman</option>
            </select>
          </div>
          <div class="form-group">
            <label for="speed">语速</label>
            <div class="slider-container">
              <input id="speed" type="range" min="0.5" max="2" step="0.1" :value="speed" @input="$emit('update:speed', Number(($event.target as HTMLInputElement).value))" />
              <span class="slider-value">{{ speed.toFixed(1) }}x</span>
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
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import CostEstimateBadge from './CostEstimateBadge.vue';

const templates = [
  {
    id: 'product',
    label: '新品介绍',
    content: '大家好，我是您的数字讲解员。今天为您带来全新的智能助手，只需一句话即可生成宣传视频，欢迎体验。'
  },
  {
    id: 'education',
    label: '课程提示',
    content: '同学们好，接下来我们将进入人工智能基础课程，请准备好笔记，我们从数字人工作流开始。'
  },
  {
    id: 'event',
    label: '活动预热',
    content: '欢迎来到本周的线上发布会，稍后数字人将为您分享产品亮点与限时福利，敬请期待。'
  }
];

const props = defineProps<{
  speechText: string;
  charCount: number;
  estimatedDuration: number;
  estimatedCost: number;
  isMobile: boolean;
  voiceId: string;
  speed: number;
  pitch: number;
  emotion: string;
}>();

defineEmits<{
  (event: 'update:speech-text', value: string): void;
  (event: 'update:voice-id', value: string): void;
  (event: 'update:speed', value: number): void;
  (event: 'update:pitch', value: number): void;
  (event: 'update:emotion', value: string): void;
}>();

const summaryText = computed(() => {
  const base = props.charCount ? `${props.charCount} / 1000 字` : '未输入脚本';
  return `${base} · ${voiceLabels[props.voiceId] || '默认音色'}`;
});

const voiceLabels: Record<string, string> = {
  'Chinese (Mandarin)_Reliable_Executive': '普通话 · 稳重高管男声',
  'Chinese (Mandarin)_News_Anchor': '普通话 · 新闻女主播',
  'Chinese (Mandarin)_Warm_Bestie': '普通话 · 温暖闺蜜',
  'Chinese (Mandarin)_Gentleman': '普通话 · 绅士男声',
  'Chinese (Mandarin)_Warm_Girl': '普通话 · 暖心女声',
  'Chinese (Mandarin)_Male_Announcer': '普通话 · 男播音员',
  'Chinese (Mandarin)_Gentle_Youth': '普通话 · 温柔青年',
  'Chinese (Mandarin)_Cute_Spirit': '普通话 · 可爱精灵',
  Cantonese_GentleLady: '粤语 · 温柔女士',
  Cantonese_Narrator: '粤语 · 叙述男声',
  English_magnetic_voiced_man: 'English · Magnetic Male',
  English_radiant_girl: 'English · Radiant Girl',
  English_captivating_female1: 'English · Captivating Female',
  English_Upbeat_Woman: 'English · Upbeat Woman',
  English_Trustworth_Man: 'English · Trustworthy Male',
  English_CalmWoman: 'English · Calm Woman'
};
</script>

<style scoped>
.script-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, 0.45fr);
  gap: 1rem;
  align-items: flex-start;
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

.script-side {
  display: flex;
  flex-direction: column;
  gap: 1rem;
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
</style>
