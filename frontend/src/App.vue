<template>
  <main class="page">
    <header class="hero">
      <div class="hero-main">
        <h1>🎭 数字人空间</h1>
        <p>Linode+WavespeedAI数字人空间</p>
      </div>
    </header>

    <DashboardGrid>
      <CardContainer
        class="api-card"
        title="Wavespeed API Key"
        subtitle="安全存储、余额提醒"
        :collapsible="true"
        :initially-collapsed="isMobile"
        persist-key="api-card"
        :error="dashboardStore.errors.apiKey"
      >
        <div class="api-mini-row">
          <label class="sr-only" for="api_key">Wavespeed API Key</label>
          <input
            id="api_key"
            :type="apiKeyVisible ? 'text' : 'password'"
            v-model="apiKeyInput"
            placeholder="Wavespeed API Key"
            @blur="validateApiKey"
          />
          <button type="button" class="btn-icon" @click="apiKeyVisible = !apiKeyVisible">
            {{ apiKeyVisible ? '🙈' : '👁️' }}
          </button>
          <button type="button" class="btn-icon" @click="saveApiKeySetting" :disabled="!isApiKeyValid">
            💾
          </button>
          <button type="button" class="btn-icon" @click="clearApiKeySetting" :disabled="!dashboardStore.apiKey">
            ✖️
          </button>
        </div>
        <p v-if="apiKeyError" class="input-error">{{ apiKeyError }}</p>
        <div class="api-mini-row meta">
          <span class="balance-label">{{ balanceDisplay }}</span>
          <button type="button" class="btn-text" @click="refreshBalance" :disabled="balanceLoading">
            {{ balanceLoading ? '查询中…' : '刷新余额' }}
          </button>
        </div>
      </CardContainer>

      <CardContainer
        class="task-card"
        title="任务管理"
        subtitle="多任务、一键切换"
        :collapsible="true"
        :initially-collapsed="false"
        persist-key="task-card"
        :error="dashboardStore.errors.tasks"
      >
        <template #actions>
          <div class="task-card-actions">
            <button type="button" class="btn-text" :disabled="!currentJobId" @click="refreshSelectedTask">刷新</button>
            <button type="button" class="btn-text" :disabled="!currentJobId" @click="togglePolling">
              {{ pollingActive ? '暂停轮询' : '恢复轮询' }}
            </button>
          </div>
        </template>
        <section class="task-list-section">
          <div v-if="!taskHistory.length" class="empty-state">暂无任务，快来创建第一个任务。</div>
          <ul v-else class="task-list">
            <li v-for="task in taskHistory" :key="task.id" :class="{ active: task.id === currentJobId }">
              <div class="task-meta">
                <strong>{{ task.id }}</strong>
                <span class="status-badge" :class="task.status">{{ describeStatus(task.status) }}</span>
              </div>
              <div class="task-info-row">
                <span>{{ formatTimestamp(task.updatedAt) }}</span>
                <span class="task-message">{{ task.message }}</span>
              </div>
              <div class="task-actions">
                <button type="button" class="btn-text" @click="handleTaskSelection(task.id)">查看</button>
                <button type="button" class="btn-text danger" @click="removeTaskFromHistory(task.id)">移除</button>
              </div>
            </li>
          </ul>
        </section>

        <section class="form-wrapper">
          <h2>创建数字人任务</h2>
          <form @submit.prevent="handleSubmit">
            <div v-if="formAlert.message" class="form-alert" :class="{ info: formAlert.type === 'info' }">
              {{ formAlert.message }}
            </div>

            <section class="form-group">
              <label>头像模式</label>
              <div class="radio-group">
                <label>
                  <input type="radio" value="character" v-model="avatarMode" />
                  预制人物
                </label>
                <label>
                  <input type="radio" value="prompt" v-model="avatarMode" />
                  AI 生成头像
                </label>
                <label>
                  <input type="radio" value="upload" v-model="avatarMode" />
                  上传头像
                </label>
              </div>
            </section>

            <section v-show="avatarMode === 'prompt'" class="form-group mode-content active">
              <label for="avatar_prompt">头像描述</label>
              <input
                id="avatar_prompt"
                type="text"
                v-model.trim="avatarPrompt"
                placeholder="例如：一位专业的女性播音员，微笑，正面照，商务装"
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
                @updatefiles="handleAvatarFiles"
              />
              <small>支持 PNG/JPG，最大 5MB</small>
              <p v-if="avatarFileError" class="input-error">{{ avatarFileError }}</p>
            </section>

            <section v-show="avatarMode === 'character'" class="form-group character-library">
              <div class="section-header">
                <label>🎭 预制人物</label>
                <button type="button" class="link-btn" @click="refreshCharacters" :disabled="characterLoading">
                  {{ characterLoading ? '刷新中...' : '重新载入' }}
                </button>
              </div>
              <p class="hint">选择角色即默认使用其头像与声音设定，省去上传步骤。</p>
              <div v-if="characterError" class="input-error">{{ characterError }}</div>
              <div class="character-select">
                <select v-model="selectedCharacterId">
                  <option disabled value="">{{ characterLoading ? '加载中...' : '请选择人物' }}</option>
                  <option v-for="char in characters" :key="char.id" :value="char.id">
                    {{ char.name }}
                  </option>
                </select>
                <button type="button" class="link-btn" v-if="selectedCharacterId" @click="clearCharacterSelection">清除选择</button>
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
                  <input type="text" v-model.trim="newCharacterForm.name" placeholder="如：产品代言人 Lisa" />
                  <label>形象描述（中文）</label>
                  <textarea v-model.trim="newCharacterForm.appearanceZh" rows="3" placeholder="角色的造型、服装等细节"></textarea>
                  <label>形象描述（英文，可选）</label>
                  <textarea v-model.trim="newCharacterForm.appearanceEn" rows="2" placeholder="可选的英文描述"></textarea>
                  <label>声音提示（中文，可选）</label>
                  <textarea v-model.trim="newCharacterForm.voiceZh" rows="2" placeholder="如：男声，沉稳有磁性"></textarea>
                  <label>声音提示（英文/Prompt，可选）</label>
                  <textarea v-model.trim="newCharacterForm.voicePrompt" rows="2" placeholder="English voice prompt"></textarea>
                  <label>推荐音色 ID（可选）</label>
                  <input type="text" v-model.trim="newCharacterForm.voiceId" placeholder="如：male-qn-jingying" />
                  <label>上传头像</label>
                  <input type="file" accept="image/*" @change="handleNewCharacterFile" />
                  <small>支持 PNG/JPG，最大 10MB</small>
                  <button type="button" class="btn-secondary" :disabled="creatingCharacter" @click="submitNewCharacter">
                    {{ creatingCharacter ? '上传中...' : '保存角色' }}
                  </button>
                </div>
              </details>
            </section>

            <section class="form-group">
              <label for="speech_text">播报文本</label>
              <textarea
                id="speech_text"
                v-model="speechText"
                maxlength="1000"
                rows="5"
                placeholder="请输入数字人要播报的内容..."
              ></textarea>
              <div class="char-count">
                {{ charCount }} / 1000 字 | 预估时长: {{ estimatedDuration }} 秒 | 预估成本: ${{ estimatedCost.toFixed(2) }}
              </div>
            </section>

            <section class="form-group">
              <label for="voice_id">音色</label>
              <select id="voice_id" v-model="voiceId">
                <option value="female-shaonv">女声 - 少女</option>
                <option value="female-yujie">女声 - 御姐</option>
                <option value="male-qn-qingse">男声 - 青涩</option>
                <option value="male-qn-jingying">男声 - 精英</option>
              </select>
            </section>

            <details class="advanced-options">
              <summary>⚙️ 高级选项</summary>

              <div class="form-group">
                <label for="resolution">分辨率</label>
                <select id="resolution" v-model="resolution">
                  <option value="720p">720p ($0.06/秒)</option>
                  <option value="1080p">1080p ($0.12/秒)</option>
                </select>
              </div>

              <div class="form-group">
                <label for="speed">语速</label>
                <div class="slider-container">
                  <input id="speed" type="range" min="0.5" max="2" step="0.1" v-model.number="speed" />
                  <span class="slider-value">{{ speed.toFixed(1) }}</span>
                </div>
              </div>

              <div class="form-group">
                <label for="pitch">音调</label>
                <div class="slider-container">
                  <input id="pitch" type="range" min="-12" max="12" step="1" v-model.number="pitch" />
                  <span class="slider-value">{{ pitch }}</span>
                </div>
              </div>

              <div class="form-group">
                <label for="emotion">情绪</label>
                <select id="emotion" v-model="emotion">
                  <option value="neutral">中性</option>
                  <option value="happy">开心</option>
                  <option value="sad">悲伤</option>
                  <option value="angry">愤怒</option>
                </select>
              </div>

              <div class="form-group">
                <label for="seed">随机种子（可选）</label>
                <input id="seed" type="text" v-model="seed" placeholder="留空则由服务端随机生成" />
              </div>
            </details>

            <section class="form-group debug-toggle">
              <label>
                <input type="checkbox" v-model="debugMode" />
                启用调试模式
              </label>
              <small>{{ debugHint }}</small>
            </section>

            <button type="submit" class="btn" :disabled="submitting">
              {{ submitting ? '⏳ 正在创建任务...' : '🚀 生成数字人视频' }}
            </button>
          </form>
        </section>
      </CardContainer>

      <CardContainer
        class="progress-card"
        title="任务进度"
        subtitle="实时进展、日志与播放器"
        :collapsible="true"
        :initially-collapsed="isMobile"
        persist-key="progress-card"
        :error="dashboardStore.errors.progress"
      >
        <template #actions>
          <a href="/doc/frontend_task_flow.md" target="_blank" rel="noreferrer" class="link">任务流说明</a>
        </template>
        <div class="progress-headline">
          <div v-if="currentJobId" class="task-info">任务 ID：<code>{{ currentJobId }}</code></div>
          <div class="progress-meter" role="progressbar" :aria-valuenow="overallProgressPercent" aria-valuemin="0" aria-valuemax="100">
            <div class="progress-meter__fill" :style="{ width: overallProgressLabel }"></div>
            <span class="progress-meter__label">{{ overallProgressLabel }}</span>
          </div>
        </div>
        <ul class="stage-pipeline">
          <li
            v-for="definition in stageDefinitions"
            :key="definition.id"
            :class="['stage', stageStatus[definition.id].state]"
          >
            <div class="stage-icon" :style="{ borderColor: definition.color }">
              <span class="stage-base">{{ definition.icon }}</span>
              <span class="stage-state">{{ stageStateIcon(definition.id) }}</span>
            </div>
            <div>
              <p class="stage-text">{{ definition.label }}</p>
              <p class="stage-desc">{{ stageStatus[definition.id].description }}</p>
            </div>
          </li>
        </ul>

        <div class="status-message" :class="statusAccent">
          {{ statusMessage }}
        </div>
        <div v-if="countdownVisible" class="countdown-hint">
          ⏱️ 预计剩余 <strong>{{ countdownLabel }}</strong>
          <span v-if="countdownSource" class="countdown-source">（{{ countdownSource }}）</span>
        </div>

        <div v-if="costEstimateValue !== null" class="cost-estimate">
          预计成本：<strong>${{ costEstimateValue?.toFixed(2) }}</strong>
          <small>{{ costEstimateDesc }}</small>
        </div>

        <section class="asset-preview">
          <div v-if="avatarUrl" class="asset-card">
            <p class="asset-title">头像预览</p>
            <img :src="avatarUrl" alt="生成头像" class="asset-image" />
          </div>

          <div v-if="audioUrl" class="asset-card">
            <p class="asset-title">语音试听</p>
            <audio :src="audioUrl" controls></audio>
          </div>
        </section>

        <section v-if="taskStatus === 'finished' && resultVideoUrl" class="result-container">
          <p class="asset-title">最终视频</p>
          <video
            ref="videoPlayerEl"
            class="video-player video-js vjs-default-skin"
            playsinline
            data-setup="{}"
          ></video>
          <div class="cost-display">
            总成本: ${{ totalCost.toFixed(2) }}
            <small v-if="billingSummary">{{ billingSummary }}</small>
          </div>
          <div class="result-actions">
            <button class="btn-download" @click="downloadVideo">📥 下载视频</button>
            <button class="btn-share" @click="copyVideoLink">🔗 复制链接</button>
          </div>
        </section>

        <div v-if="taskStatus === 'failed'" class="error-message">
          <strong>❌ 生成失败</strong>
          <p>{{ errorMessage }}</p>
        </div>
      </CardContainer>

      <CardContainer
        class="material-card"
        title="素材目录"
        subtitle="桶内路径与公网映射"
        :collapsible="true"
        :initially-collapsed="isMobile"
        persist-key="material-card"
        :error="dashboardStore.errors.material"
      >
        <div v-if="!currentJobId" class="empty-state">未选择任务，暂无法展示素材。</div>
        <div v-else>
          <p class="bucket-path">当前任务目录：<code>{{ currentBucketDir }}</code></p>
          <section v-if="audioUrl || (taskStatus === 'finished' && resultVideoUrl)" class="material-preview">
            <div v-if="audioUrl" class="material-audio">
              <p class="asset-title">语音素材</p>
              <audio :src="audioUrl" controls></audio>
            </div>
            <div v-if="taskStatus === 'finished' && resultVideoUrl" class="material-video">
              <p class="asset-title">视频素材</p>
              <video :src="resultVideoUrl" controls playsinline></video>
            </div>
          </section>
          <ul v-if="materialItems.length" class="material-list">
            <li v-for="item in materialItems" :key="item.id">
              <div class="material-meta">
                <strong>{{ item.label }}</strong>
                <span class="material-tag" :class="item.type">{{ item.type }}</span>
              </div>
              <p v-if="item.description" class="material-desc">{{ item.description }}</p>
              <p v-if="item.localPath" class="material-path">本地：<code>{{ item.localPath }}</code></p>
              <p v-if="item.publicUrl" class="material-path">公网：<code>{{ item.publicUrl }}</code></p>
              <div class="material-actions">
                <button v-if="item.localPath" type="button" class="btn-text" @click="copyLocalPath(item.localPath)">
                  复制本地
                </button>
                <button v-if="item.publicUrl" type="button" class="btn-text" @click="copyPublicLink(item.publicUrl)">
                  复制公网
                </button>
                <button v-if="item.publicUrl" type="button" class="btn-text" @click="openPublicLink(item.publicUrl)">
                  打开
                </button>
              </div>
            </li>
          </ul>
          <div v-else class="empty-state">暂无素材文件，等待任务产出。</div>
        </div>
      </CardContainer>
    </DashboardGrid>
  </main>

  <div v-if="toastMessage" class="toast">{{ toastMessage }}</div>

  <div v-if="errorDialogVisible" class="error-overlay">
    <div class="error-dialog">
      <h3>{{ errorDialogTitle }}</h3>
      <p>{{ errorDialogMessage }}</p>
      <pre>{{ errorDialogDetail }}</pre>
      <button type="button" @click="closeErrorDialog">关闭</button>
    </div>
  </div>
</template>


<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import vueFilePond from 'vue-filepond';
import FilePondPluginImagePreview from 'filepond-plugin-image-preview';
import FilePondPluginFileValidateType from 'filepond-plugin-file-validate-type';
import FilePondPluginFileValidateSize from 'filepond-plugin-file-validate-size';
import videojs from 'video.js';
import { useAppConfig } from '@/composables/useAppConfig';
import { useMediaQuery } from '@/composables/useMediaQuery';
import DashboardGrid from '@/layout/DashboardGrid.vue';
import CardContainer from '@/layout/CardContainer.vue';
import { useDashboardStore } from '@/stores/dashboard';

interface BillingInfo {
  balance_before?: number;
  balance_after?: number;
  actual_cost?: number;
  currency?: string;
  updated_at?: string;
}

interface TaskResponse {
  job_id?: string;
  status: string;
  message?: string;
  billing?: BillingInfo;
  avatar_url?: string;
  audio_url?: string;
  video_url?: string;
  assets?: Record<string, any>;
  cost_estimate?: number | CostEstimate;
  cost?: number;
  duration?: number;
  error_code?: string;
  trace_id?: string;
  logs?: string[];
}

interface CostEstimate {
  total?: number;
  avatar?: number;
  speech?: number;
  video?: number;
}

interface CharacterRecord {
  id: string;
  name: string;
  image_url?: string;
  thumbnail_url?: string;
  image_path?: string;
  appearance?: Record<string, string>;
  voice?: Record<string, any>;
  tags?: string[];
  source?: string;
  status?: string;
}

interface MaterialEntry {
  id: string;
  label: string;
  type: 'avatar' | 'audio' | 'video' | 'input' | 'log' | 'other';
  localPath: string;
  publicUrl: string;
  description?: string;
}

type StageKey = 'avatar' | 'speech' | 'video';

interface StageDefinition {
  id: StageKey;
  label: string;
  icon: string;
  color: string;
  weight: number;
}

interface StageViewState {
  state: 'pending' | 'active' | 'done' | 'failed';
  description: string;
}

const DEBUG_MAX_DURATION = 10;
const DEBUG_MAX_CHARS = DEBUG_MAX_DURATION * 5;
const MAX_AVATAR_SIZE = 5 * 1024 * 1024;
const MAX_CHARACTER_IMAGE_SIZE = 10 * 1024 * 1024;
const DEFAULT_CHARACTER_ID = 'char-mai';
const DEFAULT_VIDEO_SECONDS_PER_CHAR = 1.2;

const STAGE_PIPELINE: StageDefinition[] = [
  { id: 'avatar', label: '头像生成', icon: '🧑‍🎨', color: '#a855f7', weight: 0.2 },
  { id: 'speech', label: '语音生成', icon: '🎙️', color: '#0ea5e9', weight: 0.3 },
  { id: 'video', label: '唇形视频', icon: '🎬', color: '#22c55e', weight: 0.5 }
];

const FilePond = vueFilePond(
  FilePondPluginImagePreview,
  FilePondPluginFileValidateType,
  FilePondPluginFileValidateSize
);

const config = useAppConfig();
const isMobile = useMediaQuery('(max-width: 768px)', { defaultState: false });
const dashboardStore = useDashboardStore();
const { sortedTasks } = storeToRefs(dashboardStore);
const BUCKET_PUBLIC_BASE = 'https://s.linapp.fun';
const API_KEY_PATTERN = /^(?:sk|ws|pk)_[-A-Za-z0-9]{16,}$/i;
const stageDefinitions = STAGE_PIPELINE;

const apiKeyInput = ref(dashboardStore.apiKey);
const apiKeyVisible = ref(false);
const apiKeyError = ref('');
const isApiKeyValid = computed(() => {
  const value = apiKeyInput.value.trim();
  if (!value) {
    return false;
  }
  return API_KEY_PATTERN.test(value);
});
const balanceValue = ref<number | null>(null);
const balanceTimestamp = ref<number | null>(null);
const balanceError = ref('');
const balanceLoading = ref(false);
const toastMessage = ref('');
const toastTimer = ref<number | null>(null);
const latestTaskSnapshot = ref<TaskResponse | null>(null);
const taskHistory = computed(() => sortedTasks.value);
watch(
  () => dashboardStore.apiKey,
  (value) => {
    apiKeyInput.value = value;
    if (!value) {
      balanceValue.value = null;
      balanceTimestamp.value = null;
      balanceError.value = '';
    }
  }
);
watch(apiKeyInput, (value) => {
  if (!value.trim()) {
    apiKeyError.value = '';
    return;
  }
  validateApiKey();
});
const balanceDisplay = computed(() => {
  if (balanceLoading.value) return '余额查询中...';
  if (balanceError.value) return `余额：${balanceError.value}`;
  if (balanceValue.value !== null) {
    const time = balanceTimestamp.value
      ? new Date(balanceTimestamp.value).toLocaleTimeString('zh-CN', {
          hour: '2-digit',
          minute: '2-digit',
          hour12: false
        })
      : '';
    return `余额 $${balanceValue.value.toFixed(2)}${time ? ` · ${time}` : ''}`;
  }
  return '余额：未查询';
});

const avatarMode = ref<'character' | 'prompt' | 'upload'>('character');
const avatarPrompt = ref('一位专业的女性播音员，微笑，正面照');
const speechText = ref('你好啊！欢迎进入Linode+WavespeedAI数字人空间。');
const voiceId = ref('female-shaonv');
const resolution = ref<'720p' | '1080p'>('720p');
const speed = ref(1.0);
const pitch = ref(0);
const emotion = ref('neutral');
const seed = ref('');
const debugMode = ref(config.DEBUG);

const formAlert = reactive({ message: '', type: '' as 'info' | 'error' | '' });
const submitting = ref(false);
const avatarFileError = ref('');
const avatarPond = ref<any>(null);
const avatarFile = ref<File | null>(null);

const currentJobId = ref<string | null>(null);
const bucketBasePath = computed(() => {
  const root = dashboardStore.bucketRoot.replace(/\/+$/, '');
  return `${root}/${dashboardStore.bucketUserDir}`.replace(/\/+/g, '/');
});
const currentBucketDir = computed(() =>
  currentJobId.value ? `${bucketBasePath.value}/${currentJobId.value}` : ''
);
const taskStatus = ref<'idle' | 'running' | 'finished' | 'failed'>('idle');
const statusMessage = ref('尚未创建任务');
const avatarUrl = ref('');
const audioUrl = ref('');
const stageStatus = reactive<Record<StageKey, StageViewState>>({
  avatar: { state: 'pending', description: '等待调度' },
  speech: { state: 'pending', description: '等待调度' },
  video: { state: 'pending', description: '等待调度' }
});

const costEstimateValue = ref<number | null>(null);
const costEstimateDesc = ref('');
const resultVideoUrl = ref('');
const totalCost = ref(0);
const billingInfo = ref<BillingInfo | null>(null);
const billingSummary = computed(() => {
  const info = billingInfo.value;
  if (!info) return '';
  const hasBefore = typeof info.balance_before === 'number';
  const hasAfter = typeof info.balance_after === 'number';
  if (hasBefore && hasAfter) {
    return `余额 ${formatBalance(info.balance_before)} → ${formatBalance(info.balance_after)}`;
  }
  if (hasAfter) {
    return `余额剩余 ${formatBalance(info.balance_after)}`;
  }
  return '';
});
const errorMessage = ref('');

const errorDialogVisible = ref(false);
const errorDialogTitle = ref('');
const errorDialogMessage = ref('');
const errorDialogDetail = ref('');

const pollTimer = ref<number | null>(null);
const pollingActive = computed(() => Boolean(pollTimer.value));
const currentJobTextLength = ref<number | null>(null);
const videoStageStartAt = ref<number | null>(null);
const videoCountdownTimer = ref<number | null>(null);
const videoCountdown = reactive({
  total: 0,
  remaining: 0,
  source: '',
  samples: 0,
  active: false
});
const historicalStats = reactive({ secondsPerChar: 0, sampleSize: 0 });
const videoPlayerEl = ref<HTMLVideoElement | null>(null);
let videoPlayerInstance: videojs.Player | null = null;

const characters = ref<CharacterRecord[]>([]);
const characterLoading = ref(false);
const characterError = ref('');
const selectedCharacterId = ref('');
const characterPreviewUrl = computed(() =>
  selectedCharacter.value ? buildCharacterImageUrl(selectedCharacter.value) : ''
);
const newCharacterForm = reactive({
  name: '',
  appearanceZh: '',
  appearanceEn: '',
  voiceZh: '',
  voicePrompt: '',
  voiceId: ''
});
const newCharacterFile = ref<File | null>(null);
const creatingCharacter = ref(false);
const newCharacterAlert = reactive({ message: '', type: '' as 'error' | 'success' | '' });

const charCount = computed(() => speechText.value.length);
const estimatedDuration = computed(() => Math.ceil(charCount.value / 5) || 0);
const estimatedCost = computed(() => {
  const avatarCost = 0.03;
  const voiceCost = estimatedDuration.value / 60 * 0.02;
  const videoCost = estimatedDuration.value * (resolution.value === '720p' ? 0.06 : 0.12);
  return avatarCost + voiceCost + videoCost;
});

const acceptedAvatarTypes = ['image/png', 'image/jpeg'];
const maxAvatarSizeLabel = '5MB';
const pondLabel =
  "拖拽或 <span class='filepond--label-action'>点击</span> 上传头像";

const debugHint = computed(() =>
  debugMode.value
    ? `调试模式开启：限制 ${DEBUG_MAX_CHARS} 字以内（约 ${DEBUG_MAX_DURATION} 秒）。`
    : '调试模式关闭：可输入最多 1000 字生成正式视频。'
);

const statusAccent = computed(() => ({
  success: taskStatus.value === 'finished',
  danger: taskStatus.value === 'failed'
}));

const overallProgress = computed(() =>
  stageDefinitions.reduce((total, definition) => {
    const state = stageStatus[definition.id].state;
    if (state === 'done') {
      return total + definition.weight;
    }
    if (state === 'active') {
      return total + definition.weight * 0.5;
    }
    return total;
  }, 0)
);

const overallProgressPercent = computed(() => Math.round(overallProgress.value * 100));
const overallProgressLabel = computed(() => `${overallProgressPercent.value}%`);

const countdownVisible = computed(() => videoCountdown.active && videoCountdown.remaining > 0);
const countdownLabel = computed(() => formatDuration(videoCountdown.remaining));
const countdownSource = computed(() => videoCountdown.source);

const selectedCharacter = computed(() =>
  characters.value.find((item) => item.id === selectedCharacterId.value) || null
);

const materialItems = computed<MaterialEntry[]>(() => {
  if (!currentJobId.value) {
    dashboardStore.clearError('material');
    return [];
  }
  const jobId = currentJobId.value;
  const snapshot = latestTaskSnapshot.value;
  const assets = snapshot?.assets || {};
  const items: MaterialEntry[] = [];
  let hasPathError = false;

  if (currentBucketDir.value) {
    items.push({
      id: 'dir-root',
      label: '任务目录',
      type: 'other',
      localPath: currentBucketDir.value,
      publicUrl: bucketPathToPublicUrl(currentBucketDir.value),
      description: '桶内该任务的根目录'
    });
  }

  const pushItem = (
    idSuffix: string,
    label: string,
    type: MaterialEntry['type'],
    rawPath?: string,
    fallback?: string,
    description?: string
  ) => {
    const { localPath, publicUrl } = normalizeMaterialPath(rawPath || fallback || '', jobId);
    if (!localPath && !publicUrl) return;
    if (localPath && !localPath.startsWith(bucketBasePath.value)) {
      hasPathError = true;
      return;
    }
    items.push({
      id: `${type}-${idSuffix}`,
      label,
      type,
      localPath,
      publicUrl,
      description
    });
  };

  pushItem('avatar', '生成头像', 'avatar', assets.avatar_local_path || assets.avatar_path, avatarUrl.value);
  pushItem(
    'audio',
    '语音合成',
    'audio',
    assets.audio_local_path || assets.audio_path || assets.local_audio_url,
    audioUrl.value
  );
  const finalVideoPath =
    assets.local_video_url || assets.video_local_path || assets.video_path || resultVideoUrl.value;
  pushItem('video', '唇形视频', 'video', finalVideoPath, finalVideoPath);
  const logPath = currentBucketDir.value ? `${currentBucketDir.value}/log.txt` : '';
  if (logPath) {
    pushItem('log', '任务日志', 'log', logPath, logPath, '记录 trace id 与成本');
  }

  if (hasPathError) {
    dashboardStore.setError('material', '素材路径异常，请检查桶映射');
  } else {
    dashboardStore.clearError('material');
  }
  return items;
});

watch(avatarMode, (mode) => {
  if (mode === 'prompt') {
    clearAvatarFile();
    avatarFileError.value = '';
  }
  if (mode === 'character' && !selectedCharacterId.value && characters.value.length) {
    selectedCharacterId.value = characters.value[0].id;
  }
});

watch(selectedCharacterId, (id) => {
  const character = characters.value.find((item) => item.id === id) || null;
  if (id) {
    avatarMode.value = 'character';
    clearAvatarFile();
  }
  if (character?.voice?.voice_id) {
    voiceId.value = character.voice.voice_id;
  }
});

watch(resultVideoUrl, (url) => {
  if (videoPlayerInstance) {
    videoPlayerInstance.dispose();
    videoPlayerInstance = null;
  }
  if (url) {
    nextTick(() => {
      if (!videoPlayerEl.value) return;
      videoPlayerInstance = videojs(videoPlayerEl.value, {
        controls: true,
        preload: 'auto',
        sources: [{ src: url, type: 'video/mp4' }]
      });
    });
  }
});

watch(
  () => dashboardStore.selectedTaskId,
  (taskId) => {
    if (taskId === currentJobId.value) return;
    stopPolling();
    if (!taskId) {
      currentJobId.value = null;
      latestTaskSnapshot.value = null;
      resetProgress('idle');
      return;
    }
    currentJobId.value = taskId;
    const stored = dashboardStore.tasks.find((task) => task.id === taskId);
    if (stored?.snapshot) {
      applyTask(stored.snapshot as TaskResponse, { silent: true });
    }
    const status = (stored?.snapshot as TaskResponse | undefined)?.status || '';
    if (!status || (status !== 'finished' && status !== 'failed')) {
      fetchTaskStatus();
      startPolling();
    }
  },
  { immediate: true }
);

watch(
  () => currentJobId.value,
  () => {
    syncCurrentJobMetadata();
  }
);

watch(
  taskHistory,
  () => {
    syncCurrentJobMetadata();
    scheduleAnalyticsHydration();
    recomputeHistoricalStats();
  },
  { deep: true }
);

watch(
  () => historicalStats.secondsPerChar,
  () => {
    if (videoCountdown.active && latestTaskSnapshot.value?.status === 'video_rendering') {
      startVideoCountdown(latestTaskSnapshot.value);
    }
  }
);

onMounted(() => {
  fetchCharacters();
  scheduleAnalyticsHydration();
  recomputeHistoricalStats();
});

function saveApiKeySetting() {
  if (!validateApiKey()) {
    showToast('请检查 API Key 格式');
    return;
  }
  const trimmed = apiKeyInput.value.trim();
  dashboardStore.setApiKey(trimmed);
  showToast('API Key 已保存');
}

function clearApiKeySetting() {
  apiKeyInput.value = '';
  dashboardStore.clearApiKey();
  showToast('API Key 已清除');
  balanceValue.value = null;
  balanceTimestamp.value = null;
  balanceError.value = '';
  apiKeyError.value = '';
  dashboardStore.clearError('apiKey');
}

function validateApiKey() {
  const trimmed = apiKeyInput.value.trim();
  if (!trimmed) {
    apiKeyError.value = '';
    dashboardStore.clearError('apiKey');
    return false;
  }
  if (!API_KEY_PATTERN.test(trimmed)) {
    apiKeyError.value = 'Key 需以 sk_/ws_/pk_ 开头，长度不少于 20';
    dashboardStore.setError('apiKey', apiKeyError.value);
    return false;
  }
  apiKeyError.value = '';
  dashboardStore.clearError('apiKey');
  return true;
}

function handleTaskSelection(taskId: string) {
  if (taskId) {
    dashboardStore.selectTask(taskId);
  }
}

function togglePolling() {
  if (pollingActive.value) {
    stopPolling();
  } else {
    startPolling();
  }
}

function refreshSelectedTask() {
  fetchTaskStatus();
}

async function refreshBalance() {
  const key = apiKeyInput.value.trim() || dashboardStore.apiKey.trim();
  if (!key) {
    showToast('请先填写 Wavespeed API Key');
    return;
  }
  balanceLoading.value = true;
  balanceError.value = '';
  try {
    const response = await fetch(`${config.API_BASE}/api/wavespeed/balance`, {
      method: 'POST',
      headers: buildRequestHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ wavespeed_api_key: key })
    });
    if (!response.ok) {
      const error = await safeJson(response);
      throw new Error(error.detail || '查询失败');
    }
    const result = await response.json();
    balanceValue.value = typeof result.balance === 'number' ? Number(result.balance) : null;
    balanceTimestamp.value = Date.now();
    balanceError.value = '';
    if (!dashboardStore.apiKey && key) {
      dashboardStore.setApiKey(key);
    }
    if (balanceValue.value !== null) {
      showToast(`余额 $${balanceValue.value.toFixed(2)}`);
    }
  } catch (err) {
    balanceError.value = (err as Error).message || '查询失败';
    showToast(balanceError.value);
    dashboardStore.setError('apiKey', balanceError.value);
  } finally {
    if (!balanceError.value) {
      dashboardStore.clearError('apiKey');
    }
    balanceLoading.value = false;
  }
}

function removeTaskFromHistory(taskId: string) {
  dashboardStore.removeTask(taskId);
  if (dashboardStore.selectedTaskId === taskId) {
    resetProgress('idle');
  }
}

function showToast(message: string) {
  toastMessage.value = message;
  if (toastTimer.value) {
    clearTimeout(toastTimer.value);
  }
  toastTimer.value = window.setTimeout(() => {
    toastMessage.value = '';
    toastTimer.value = null;
  }, 4000);
}

async function copyText(value: string, successMessage: string) {
  if (!value) return;
  try {
    await navigator.clipboard.writeText(value);
    showToast(successMessage);
  } catch {
    const input = document.createElement('textarea');
    input.value = value;
    input.style.position = 'fixed';
    input.style.opacity = '0';
    document.body.appendChild(input);
    input.focus();
    input.select();
    try {
      document.execCommand('copy');
      showToast(successMessage);
    } catch {
      showFormAlert('复制失败，请手动复制');
    } finally {
      document.body.removeChild(input);
    }
  }
}

function copyLocalPath(path: string) {
  if (!path) return;
  copyText(path, '本地路径已复制');
}

function copyPublicLink(link: string) {
  if (!link) return;
  copyText(link, '公网链接已复制');
}

function openPublicLink(link: string) {
  if (!link) return;
  window.open(link, '_blank', 'noreferrer');
}

function formatTimestamp(timestamp: number) {
  if (!timestamp) return '';
  return new Date(timestamp).toLocaleString('zh-CN', {
    hour12: false,
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
}

function formatDuration(seconds: number) {
  if (!Number.isFinite(seconds) || seconds <= 0) return '不到 1 秒';
  const value = Math.max(0, Math.round(seconds));
  const mins = Math.floor(value / 60);
  const secs = value % 60;
  if (!mins) {
    return `${secs} 秒`;
  }
  return `${mins} 分 ${secs.toString().padStart(2, '0')} 秒`;
}

function extractTextLength(task?: TaskResponse | null) {
  if (!task) return null;
  const raw = (task.assets || {}).text_length ?? (task.assets || {}).speech_text_length;
  const parsed = Number(raw);
  if (Number.isFinite(parsed) && parsed > 0) {
    return Math.round(parsed);
  }
  return null;
}

function describeStatus(status: string) {
  const map: Record<string, string> = {
    finished: '已完成',
    failed: '失败',
    running: '执行中',
    created: '已创建',
    idle: '待执行',
    pending: '排队中'
  };
  return map[status] || status || '未知';
}

function buildRequestHeaders(extra: HeadersInit = {}) {
  const headers: HeadersInit = { ...extra };
  if (dashboardStore.apiKey) {
    headers['X-API-Key'] = dashboardStore.apiKey;
  }
  return headers;
}

async function handleSubmit() {
  clearFormAlert();

  if (avatarMode.value === 'prompt' && !avatarPrompt.value.trim()) {
    return showFormAlert('请输入头像描述');
  }

  if (avatarMode.value === 'character' && !selectedCharacterId.value) {
    return showFormAlert('请选择一个预制人物');
  }

  if (avatarMode.value === 'upload') {
    const file = getSelectedAvatarFile();
    if (!file) {
      return showFormAlert('请上传头像图片');
    }
    const validationError = validateAvatarFile(file);
    if (validationError) {
      avatarFileError.value = validationError;
      return showFormAlert(validationError);
    }
  }

  const trimmedSpeech = speechText.value.trim();
  if (!trimmedSpeech) {
    return showFormAlert('请输入播报文本');
  }

  if (debugMode.value && trimmedSpeech.length > DEBUG_MAX_CHARS) {
    return showFormAlert(`调试模式下最多输入 ${DEBUG_MAX_CHARS} 个字符。`);
  }

  let avatarUploadUrl: string | null = null;
  if (avatarMode.value === 'upload') {
    try {
      const file = getSelectedAvatarFile();
      if (!file) throw new Error('未选择头像文件');
      const validationError = validateAvatarFile(file);
      if (validationError) {
        avatarFileError.value = validationError;
        throw new Error(validationError);
      }
      avatarUploadUrl = await uploadAvatar(file);
    } catch (err) {
      return showFormAlert(`上传头像失败：${(err as Error).message}`);
    }
  }

  let parsedSeed: number | undefined;
  if (seed.value.trim()) {
    const seedNumber = Number(seed.value.trim());
    if (!Number.isInteger(seedNumber)) {
      return showFormAlert('随机种子必须为整数，例如 42 或 1001。');
    }
    parsedSeed = seedNumber;
  }

  const payload: Record<string, any> = {
    avatar_mode: avatarMode.value,
    avatar_prompt: avatarMode.value === 'prompt' ? avatarPrompt.value.trim() : null,
    avatar_upload_url: avatarUploadUrl,
    speech_text: trimmedSpeech,
    voice_id: voiceId.value,
    resolution: resolution.value,
    speed: speed.value,
    pitch: pitch.value,
    emotion: emotion.value,
    debug_mode: debugMode.value
  };

  if (typeof parsedSeed === 'number') {
    payload.seed = parsedSeed;
  }
  if (avatarMode.value === 'character' && selectedCharacterId.value) {
    payload.character_id = selectedCharacterId.value;
  }

  try {
    submitting.value = true;
    taskStatus.value = 'running';
    statusMessage.value = '⏳ 正在创建任务...';

    const response = await fetch(`${config.API_BASE}/api/tasks`, {
      method: 'POST',
      headers: buildRequestHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const error = await safeJson(response);
      showErrorDialog('创建任务失败', error);
      throw new Error(error.detail || '创建任务失败');
    }

    const result = await response.json();
    const jobId = result.job_id || result.task_id;
    currentJobId.value = jobId;
    dashboardStore.selectTask(jobId);
    const now = Date.now();
    const textLength = trimmedSpeech.length;
    const initialSnapshot: TaskResponse = {
      status: 'created',
      message: '任务已创建，正在调度...',
      cost_estimate: result.cost_estimate,
      assets: {
        ...(result.assets || {}),
        text_length: textLength
      }
    };
    latestTaskSnapshot.value = initialSnapshot;
    dashboardStore.upsertTask({
      id: jobId,
      status: 'created',
      message: '任务已创建，正在调度...',
      createdAt: now,
      updatedAt: now,
      costEstimate: extractCostValue(result.cost_estimate),
      assets: initialSnapshot.assets,
      snapshot: initialSnapshot,
      textLength
    });
    currentJobTextLength.value = textLength;
    statusMessage.value = '任务已创建，正在调度...';
    resetProgress('running');
    updateCostEstimate(result.cost_estimate, '来自任务创建的初步估算。');
    startPolling();
    dashboardStore.clearError('tasks');
  } catch (err) {
    showFormAlert((err as Error).message || '未知错误');
    dashboardStore.setError('tasks', (err as Error).message || '创建任务失败');
    taskStatus.value = 'idle';
  } finally {
    submitting.value = false;
  }
}

async function uploadAvatar(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch(`${config.API_BASE}/api/assets/upload`, {
    method: 'POST',
    headers: buildRequestHeaders(),
    body: formData
  });

  if (!response.ok) {
    const error = await safeJson(response);
    throw new Error(error.detail || '上传失败');
  }

  const result = await response.json();
  return result.url;
}

async function fetchCharacters() {
  characterLoading.value = true;
  characterError.value = '';
  try {
    const response = await fetch(`${config.API_BASE}/api/characters`, {
      headers: buildRequestHeaders()
    });
    if (!response.ok) {
      const error = await safeJson(response);
      throw new Error(error.detail || '加载角色失败');
    }
    characters.value = await response.json();
    applyDefaultCharacterSelection(characters.value);
  } catch (err) {
    characterError.value = (err as Error).message;
    characters.value = [];
    selectedCharacterId.value = '';
  } finally {
    characterLoading.value = false;
  }
}

function refreshCharacters() {
  fetchCharacters();
}

function clearCharacterSelection() {
  selectedCharacterId.value = '';
}

function handleNewCharacterFile(event: Event) {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) {
    newCharacterFile.value = null;
    return;
  }
  if (file.size > MAX_CHARACTER_IMAGE_SIZE) {
    newCharacterAlert.message = '角色图片需小于 10MB';
    newCharacterAlert.type = 'error';
    newCharacterFile.value = null;
    return;
  }
  newCharacterAlert.message = '';
  newCharacterAlert.type = '';
  newCharacterFile.value = file;
}

function resetNewCharacterForm() {
  newCharacterForm.name = '';
  newCharacterForm.appearanceZh = '';
  newCharacterForm.appearanceEn = '';
  newCharacterForm.voiceZh = '';
  newCharacterForm.voicePrompt = '';
  newCharacterForm.voiceId = '';
  newCharacterFile.value = null;
}

async function submitNewCharacter() {
  if (!newCharacterForm.name.trim() || !newCharacterForm.appearanceZh.trim()) {
    newCharacterAlert.message = '名称与中文描述为必填项';
    newCharacterAlert.type = 'error';
    return;
  }
  if (!newCharacterFile.value) {
    newCharacterAlert.message = '请上传人物图片';
    newCharacterAlert.type = 'error';
    return;
  }
  const formData = new FormData();
  formData.append('name', newCharacterForm.name.trim());
  formData.append('appearance_zh', newCharacterForm.appearanceZh.trim());
  if (newCharacterForm.appearanceEn.trim()) {
    formData.append('appearance_en', newCharacterForm.appearanceEn.trim());
  }
  if (newCharacterForm.voiceZh.trim()) {
    formData.append('voice_zh', newCharacterForm.voiceZh.trim());
  }
  if (newCharacterForm.voicePrompt.trim()) {
    formData.append('voice_prompt', newCharacterForm.voicePrompt.trim());
  }
  if (newCharacterForm.voiceId.trim()) {
    formData.append('voice_id', newCharacterForm.voiceId.trim());
  }
  formData.append('file', newCharacterFile.value);

  try {
    creatingCharacter.value = true;
    const response = await fetch(`${config.API_BASE}/api/characters`, {
      method: 'POST',
      headers: buildRequestHeaders(),
      body: formData
    });
    if (!response.ok) {
      const error = await safeJson(response);
      throw new Error(error.detail || '上传失败');
    }
    const record: CharacterRecord = await response.json();
    newCharacterAlert.message = '角色上传成功';
    newCharacterAlert.type = 'success';
    await fetchCharacters();
    selectedCharacterId.value = record.id;
    resetNewCharacterForm();
  } catch (err) {
    newCharacterAlert.message = (err as Error).message;
    newCharacterAlert.type = 'error';
  } finally {
    creatingCharacter.value = false;
  }
}

function applyDefaultCharacterSelection(list: CharacterRecord[]) {
  if (!list.length) {
    selectedCharacterId.value = '';
    return;
  }
  if (selectedCharacterId.value && list.some((item) => item.id === selectedCharacterId.value)) {
    return;
  }
  const preferred = list.find((item) => item.id === DEFAULT_CHARACTER_ID);
  selectedCharacterId.value = (preferred || list[0]).id;
}

function buildCharacterImageUrl(record: CharacterRecord | null): string {
  if (!record || !record.image_url) return '';
  if (record.image_url.startsWith('http')) return record.image_url;
  return `${config.API_BASE}${record.image_url}`;
}

function startPolling() {
  if (!currentJobId.value) return;
  stopPolling();
  fetchTaskStatus();
  pollTimer.value = window.setInterval(fetchTaskStatus, config.POLL_INTERVAL);
}

function stopPolling() {
  if (pollTimer.value) {
    clearInterval(pollTimer.value);
    pollTimer.value = null;
  }
}

async function fetchTaskStatus() {
  if (!currentJobId.value) return;
  try {
    const response = await fetch(`${config.API_BASE}/api/tasks/${currentJobId.value}`, {
      headers: buildRequestHeaders()
    });
    if (!response.ok) {
      const error = await safeJson(response);
      showErrorDialog('查询任务失败', error);
      throw new Error(error.detail || '查询任务失败');
    }
    const task: TaskResponse = await response.json();
    applyTask(task);
    dashboardStore.clearError('progress');
  } catch (err) {
    console.error('轮询错误:', err);
    dashboardStore.setError('progress', (err as Error).message || '轮询失败');
  }
}

function applyTask(task: TaskResponse, options: { silent?: boolean } = {}) {
  latestTaskSnapshot.value = task;
  const jobId = task.job_id || currentJobId.value;
  const detectedTextLength = extractTextLength(task);
  if (detectedTextLength && jobId && jobId === currentJobId.value) {
    currentJobTextLength.value = detectedTextLength;
  }
  if (task.status === 'video_rendering') {
    startVideoCountdown(task);
  } else {
    stopVideoCountdown();
  }
  statusMessage.value = task.message || task.status || '执行中';
  billingInfo.value = task.billing || null;
  updateStages(task);
  updateCostEstimate(task.cost_estimate, '执行中估算（含头像/语音/视频）。');
  if (task.avatar_url) {
    avatarUrl.value = task.avatar_url;
  }
  if (task.audio_url) {
    audioUrl.value = task.audio_url;
  }
  const resolvedVideo = resolveVideoUrl(task);
  if (resolvedVideo && task.status !== 'failed') {
    resultVideoUrl.value = resolvedVideo;
  }

  if (!options.silent) {
    trackTaskHistory(task);
  }

  if (task.status === 'finished' || task.status === 'failed') {
    stopPolling();
    handleCompletion(task);
    if (task.status === 'finished' && jobId) {
      void hydrateTaskAnalytics(jobId, task);
    }
  }
}

function trackTaskHistory(task: TaskResponse) {
  if (!currentJobId.value) return;
  const now = Date.now();
  const existing = dashboardStore.tasks.find((item) => item.id === currentJobId.value);
  const resolvedTextLength = extractTextLength(task) ?? existing?.textLength ?? currentJobTextLength.value ?? undefined;
  dashboardStore.upsertTask({
    id: currentJobId.value,
    status: task.status || existing?.status || 'running',
    message: task.message || existing?.message || '',
    createdAt: existing?.createdAt || now,
    updatedAt: now,
    costEstimate: extractCostValue(task.cost_estimate) ?? existing?.costEstimate,
    assets: task.assets || existing?.assets,
    snapshot: task,
    textLength: resolvedTextLength,
    analytics: existing?.analytics
  });
}

function updateStages(task: TaskResponse) {
  const status = task.status || '';
  const finished = status === 'finished';
  const failed = status === 'failed';
  const activeStage = inferStageFromStatus(status);

  stageDefinitions.forEach((definition, index) => {
    const current = stageStatus[definition.id];
    const doneByAsset = isStageAssetReady(definition.id, task);

    if (finished || doneByAsset) {
      current.state = 'done';
      current.description = '已完成';
      return;
    }

    if (failed && activeStage === definition.id) {
      current.state = 'failed';
      current.description = task.message || stageActiveDescription(definition.id);
      return;
    }

    if (activeStage) {
      const activeIndex = stageDefinitions.findIndex((item) => item.id === activeStage);
      if (index < activeIndex) {
        current.state = 'done';
        current.description = '已完成';
      } else if (index === activeIndex) {
        current.state = 'active';
        current.description = stageActiveDescription(definition.id);
      } else {
        current.state = 'pending';
        current.description = '等待调度';
      }
      return;
    }

    current.state = 'pending';
    current.description = '等待调度';
  });
}

function resolveVideoUrl(task: TaskResponse) {
  if (task.assets?.local_video_url) {
    return task.assets.local_video_url;
  }
  if (task.video_url) {
    return task.video_url;
  }
  if (task.assets?.video_url) {
    return task.assets.video_url;
  }
  return '';
}

function inferStageFromStatus(status: string | undefined | null): StageKey | null {
  if (!status) return null;
  if (status.includes('video')) return 'video';
  if (status.includes('speech')) return 'speech';
  if (status.includes('avatar')) return 'avatar';
  return null;
}

function isStageAssetReady(stage: StageKey, task: TaskResponse) {
  if (stage === 'avatar') {
    return Boolean(task.avatar_url || task.assets?.avatar_local_path);
  }
  if (stage === 'speech') {
    return Boolean(task.audio_url || task.assets?.audio_local_path || task.assets?.local_audio_url);
  }
  if (stage === 'video') {
    return Boolean(resolveVideoUrl(task));
  }
  return false;
}

function stageActiveDescription(stage: StageKey) {
  if (stage === 'avatar') return '头像生成中';
  if (stage === 'speech') return '语音合成中';
  return '唇形渲染中';
}

function normalizeMaterialPath(raw: string, jobId?: string) {
  if (!raw) {
    return { localPath: '', publicUrl: '' };
  }
  const trimmed = raw.trim();
  if (!trimmed) {
    return { localPath: '', publicUrl: '' };
  }
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return { localPath: '', publicUrl: trimmed };
  }
  if (trimmed.startsWith('/mnt/www')) {
    return { localPath: trimmed, publicUrl: bucketPathToPublicUrl(trimmed) };
  }
  const normalizedJobId = jobId || currentJobId.value || '';
  let relative = trimmed.replace(/^\.\/?/, '');
  if (relative.startsWith('/')) {
    relative = relative.slice(1);
  }
  if (relative.startsWith('output/')) {
    const localPath = `${bucketBasePath.value}/${relative}`.replace(/\\/g, '/');
    return { localPath, publicUrl: bucketPathToPublicUrl(localPath) };
  }
  const suffix = normalizedJobId ? `${normalizedJobId}/${relative}` : relative;
  const localPath = `${bucketBasePath.value}/${suffix}`.replace(/\\/g, '/');
  return { localPath, publicUrl: bucketPathToPublicUrl(localPath) };
}

function bucketPathToPublicUrl(localPath: string) {
  if (!localPath) return '';
  if (localPath.startsWith('http://') || localPath.startsWith('https://')) {
    return localPath;
  }
  if (!localPath.startsWith('/mnt/www')) {
    return '';
  }
  const relative = localPath.replace(/^\/mnt\/www\/?/, '');
  try {
    const url = new URL(`${BUCKET_PUBLIC_BASE.replace(/\/$/, '')}/${relative}`);
    return url.toString();
  } catch {
    return `${BUCKET_PUBLIC_BASE}/${relative}`;
  }
}

const processedAnalytics = new Set<string>();
let analyticsHydrationRunning = false;

function syncCurrentJobMetadata() {
  if (!currentJobId.value) {
    currentJobTextLength.value = null;
    stopVideoCountdown();
    return;
  }
  const entry = dashboardStore.tasks.find((task) => task.id === currentJobId.value);
  const snapshot = (entry?.snapshot as TaskResponse | undefined) || latestTaskSnapshot.value;
  const length = entry?.textLength ?? extractTextLength(snapshot);
  currentJobTextLength.value = length ?? null;
  if (entry && length && entry.textLength !== length) {
    dashboardStore.upsertTask({ ...entry, textLength: length, updatedAt: entry.updatedAt ?? Date.now() });
  }
}

function startVideoCountdown(task?: TaskResponse | null) {
  if (!currentJobId.value) return;
  const textLength = currentJobTextLength.value || extractTextLength(task) || null;
  if (!textLength) {
    stopVideoCountdown();
    return;
  }
  const secondsPerChar = resolveSecondsPerChar();
  const estimatedTotal = Math.max(Math.round(textLength * secondsPerChar), 5);
  const stageStart = resolveVideoStageStart(task) ?? videoStageStartAt.value ?? Date.now();
  videoStageStartAt.value = stageStart;
  videoCountdown.total = estimatedTotal;
  videoCountdown.active = true;
  videoCountdown.source =
    historicalStats.sampleSize > 0
      ? `基于 ${historicalStats.sampleSize} 个历史样本`
      : '经验估算';
  videoCountdown.samples = historicalStats.sampleSize;
  updateVideoCountdownRemaining();
  if (!videoCountdownTimer.value) {
    videoCountdownTimer.value = window.setInterval(updateVideoCountdownRemaining, 1000);
  }
}

function stopVideoCountdown() {
  videoCountdown.active = false;
  videoCountdown.remaining = 0;
  videoStageStartAt.value = null;
  if (videoCountdownTimer.value) {
    clearInterval(videoCountdownTimer.value);
    videoCountdownTimer.value = null;
  }
}

function updateVideoCountdownRemaining() {
  if (!videoCountdown.active || videoStageStartAt.value === null) {
    videoCountdown.remaining = 0;
    return;
  }
  const elapsed = (Date.now() - videoStageStartAt.value) / 1000;
  const remaining = Math.max(videoCountdown.total - elapsed, 0);
  videoCountdown.remaining = remaining;
  if (remaining <= 0.1) {
    stopVideoCountdown();
  }
}

function resolveVideoStageStart(task?: TaskResponse | null) {
  if (!task) return null;
  const iso = (task.assets || {}).video_stage_started_at;
  if (typeof iso === 'string') {
    const parsed = Date.parse(iso);
    if (!Number.isNaN(parsed)) {
      return parsed;
    }
  }
  return null;
}

function resolveSecondsPerChar() {
  if (historicalStats.secondsPerChar > 0) {
    return historicalStats.secondsPerChar;
  }
  return DEFAULT_VIDEO_SECONDS_PER_CHAR;
}

function scheduleAnalyticsHydration() {
  void hydrateFinishedTaskAnalytics();
}

async function hydrateFinishedTaskAnalytics() {
  if (analyticsHydrationRunning) return;
  analyticsHydrationRunning = true;
  try {
    const finished = dashboardStore.tasks.filter((task) => task.status === 'finished');
    for (const entry of finished) {
      await hydrateTaskAnalytics(entry.id, entry.snapshot as TaskResponse | undefined);
    }
    recomputeHistoricalStats();
  } finally {
    analyticsHydrationRunning = false;
  }
}

async function hydrateTaskAnalytics(jobId: string, snapshot?: TaskResponse) {
  if (processedAnalytics.has(jobId)) return;
  const entry = dashboardStore.tasks.find((task) => task.id === jobId);
  if (!entry) return;
  if (entry.analytics?.perCharSeconds && entry.textLength) {
    processedAnalytics.add(jobId);
    return;
  }
  const textLength = entry.textLength ?? extractTextLength(snapshot);
  if (!textLength) return;
  let seconds = snapshot?.assets?.video_stage_seconds;
  if (seconds == null) {
    seconds = await fetchVideoStageSecondsFromLog(jobId);
    if (seconds == null && typeof snapshot?.duration === 'number') {
      seconds = snapshot.duration;
    }
  }
  if (seconds == null || seconds <= 0) return;
  const analytics = {
    textLength,
    videoStageSeconds: seconds,
    perCharSeconds: seconds / textLength
  };
  const updatedAt = entry.updatedAt || Date.now();
  dashboardStore.upsertTask({ ...entry, analytics, textLength, updatedAt });
  processedAnalytics.add(jobId);
}

async function fetchVideoStageSecondsFromLog(jobId: string) {
  if (!jobId) return null;
  try {
    const response = await fetch(`${config.API_BASE}/output/${jobId}/log.txt`);
    if (!response.ok) {
      return null;
    }
    const text = await response.text();
    return parseVideoStageDuration(text);
  } catch {
    return null;
  }
}

function parseVideoStageDuration(logText: string) {
  if (!logText) return null;
  const lines = logText.split(/\r?\n/);
  const regex = /^\[(?<time>[^\]]+)\]\s+\[[^\]]+\](?:\s+\[[^\]]+\])?\s+(?<message>.*)$/;
  let start: number | null = null;
  for (const line of lines) {
    const match = regex.exec(line.trim());
    if (!match || !match.groups) continue;
    const { time, message } = match.groups;
    if (!time || !message) continue;
    if (start === null && message.includes('正在生成数字人视频')) {
      const parsed = Date.parse(time);
      if (!Number.isNaN(parsed)) {
        start = parsed;
      }
      continue;
    }
    if (start !== null && message.includes('数字人视频生成完成')) {
      const end = Date.parse(time);
      if (!Number.isNaN(end)) {
        return Math.max((end - start) / 1000, 0);
      }
    }
  }
  return null;
}

function recomputeHistoricalStats() {
  const samples = dashboardStore.tasks
    .map((task) => task.analytics?.perCharSeconds)
    .filter((value): value is number => typeof value === 'number' && Number.isFinite(value) && value > 0);
  if (!samples.length) {
    historicalStats.secondsPerChar = 0;
    historicalStats.sampleSize = 0;
    return;
  }
  const avg = samples.reduce((sum, item) => sum + item, 0) / samples.length;
  historicalStats.secondsPerChar = avg;
  historicalStats.sampleSize = samples.length;
}

function formatBalance(value?: number | null) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '';
  }
  return `$${value.toFixed(2)}`;
}

function handleCompletion(task: TaskResponse) {
  if (task.status === 'finished') {
    taskStatus.value = 'finished';
    resultVideoUrl.value = resolveVideoUrl(task);
    totalCost.value = resolveActualCost(task);
    statusMessage.value = '✅ 数字人视频生成完成！';
  } else {
    taskStatus.value = 'failed';
    errorMessage.value = task.message || '任务执行失败';
    showErrorDialog('任务执行失败', task);
  }
}

function resolveActualCost(task: TaskResponse) {
  if (typeof task.billing?.actual_cost === 'number') {
    return task.billing.actual_cost;
  }
  if (typeof task.cost === 'number') {
    return task.cost;
  }
  const extracted = extractCostValue(task.cost_estimate);
  if (typeof extracted === 'number') {
    return extracted;
  }
  return estimatedCost.value;
}

function resetProgress(state: 'idle' | 'running' = 'running') {
  stageDefinitions.forEach((definition) => {
    stageStatus[definition.id].state = 'pending';
    stageStatus[definition.id].description = '等待调度';
  });
  taskStatus.value = state;
  avatarUrl.value = '';
  audioUrl.value = '';
  resultVideoUrl.value = '';
  totalCost.value = 0;
  billingInfo.value = null;
  errorMessage.value = '';
  costEstimateValue.value = null;
  costEstimateDesc.value = '';
  dashboardStore.clearError('progress');
}

function updateCostEstimate(value: TaskResponse['cost_estimate'], fallbackDesc = '') {
  if (typeof value === 'number') {
    costEstimateValue.value = value;
    costEstimateDesc.value = fallbackDesc;
    return;
  }

  if (value) {
    const total = extractCostValue(value);
    costEstimateValue.value = typeof total === 'number' ? Number(total) : null;
    const parts = [
      value.avatar ? `头像 $${value.avatar.toFixed(2)}` : null,
      value.speech ? `语音 $${value.speech.toFixed(2)}` : null,
      value.video ? `视频 $${value.video.toFixed(2)}` : null
    ]
      .filter(Boolean)
      .join(' / ');
    costEstimateDesc.value = parts || fallbackDesc;
    return;
  }

  costEstimateValue.value = null;
  costEstimateDesc.value = '';
}

function extractCostValue(value: TaskResponse['cost_estimate']) {
  if (typeof value === 'number') {
    return value;
  }
  if (value) {
    return value.total ?? (value.avatar ?? 0) + (value.speech ?? 0) + (value.video ?? 0);
  }
  return undefined;
}

function stageStateIcon(stage: StageKey) {
  const state = stageStatus[stage].state;
  if (state === 'done') return '✅';
  if (state === 'active') return '⚙️';
  if (state === 'failed') return '⚠️';
  return '⏳';
}

function downloadVideo() {
  if (!resultVideoUrl.value) return;
  const link = document.createElement('a');
  link.href = resultVideoUrl.value;
  link.download = `digital_human_${currentJobId.value ?? ''}.mp4`;
  link.click();
}

async function copyVideoLink() {
  if (!resultVideoUrl.value) return;
  try {
    await navigator.clipboard.writeText(resultVideoUrl.value);
    showFormAlert('链接已复制到剪贴板', 'info');
  } catch {
    showFormAlert('复制失败，请手动复制链接');
  }
}

function showFormAlert(message: string, type: 'info' | 'error' = 'error') {
  formAlert.message = message;
  formAlert.type = type;
}

function clearFormAlert() {
  formAlert.message = '';
  formAlert.type = '';
}

function showErrorDialog(title: string, payload: { detail?: string; error_code?: string; trace_id?: string }) {
  errorDialogTitle.value = title;
  errorDialogMessage.value = payload.detail || '';
  const meta = [
    payload.error_code ? `错误码: ${payload.error_code}` : null,
    payload.trace_id ? `Trace ID: ${payload.trace_id}` : null
  ]
    .filter(Boolean)
    .join('\n');
  errorDialogDetail.value = meta || '暂无更多信息';
  errorDialogVisible.value = true;
}

function closeErrorDialog() {
  errorDialogVisible.value = false;
  errorDialogTitle.value = '';
  errorDialogMessage.value = '';
  errorDialogDetail.value = '';
}

async function safeJson(response: Response) {
  try {
    return await response.json();
  } catch {
    const status = response.status || 0;
    const text = (response.statusText || '').trim();
    if (status && text) {
      return { detail: `HTTP ${status} ${text}` };
    }
    if (status) {
      return { detail: `HTTP ${status}` };
    }
    return { detail: text || '未知错误' };
  }
}

function getSelectedAvatarFile() {
  return avatarFile.value;
}

function validateAvatarFile(file: File) {
  if (!file.type.startsWith('image/')) {
    return '仅支持 PNG/JPG 等图片格式';
  }
  if (file.size > MAX_AVATAR_SIZE) {
    return '头像文件不能超过 5MB';
  }
  return null;
}

function handleAvatarFiles(files: Array<{ file?: File }>) {
  if (!files.length) {
    avatarFile.value = null;
    avatarFileError.value = '';
    return;
  }
  const file = files[0].file ?? null;
  if (!file) {
    avatarFile.value = null;
    return;
  }
  const validationError = validateAvatarFile(file);
  if (validationError) {
    avatarFileError.value = validationError;
    avatarFile.value = null;
    return;
  }
  avatarFileError.value = '';
  avatarFile.value = file;
}

function clearAvatarFile() {
  avatarFile.value = null;
  avatarFileError.value = '';
  if (avatarPond.value) {
    avatarPond.value.removeFiles();
  }
}

onBeforeUnmount(() => {
  stopPolling();
  if (videoPlayerInstance) {
    videoPlayerInstance.dispose();
    videoPlayerInstance = null;
  }
});
</script>

<style scoped>
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 1.5rem;
}

.status-message {
  margin-top: 0.75rem;
  font-size: 1rem;
  font-weight: 600;
  color: #0f172a;
}

.progress-headline {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.progress-meter {
  position: relative;
  width: 100%;
  background: rgba(15, 23, 42, 0.15);
  border-radius: 999px;
  padding: 0.35rem;
  overflow: hidden;
  border: 1px solid rgba(15, 23, 42, 0.25);
}

.progress-meter__fill {
  height: 8px;
  border-radius: 999px;
  background: linear-gradient(90deg, #34d399, #0ea5e9);
  transition: width 0.3s ease;
}

.progress-meter__label {
  position: absolute;
  right: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.85rem;
  color: #0f172a;
  font-weight: 600;
}

.stage-pipeline {
  list-style: none;
  padding: 0;
  margin: 0.5rem 0 0;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.stage-pipeline .stage {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  padding: 0.6rem;
  border-radius: 12px;
  border: 1px dashed rgba(148, 163, 184, 0.3);
  transition: border-color 0.2s ease, background-color 0.2s ease;
}

.stage-pipeline .stage.active {
  border-color: rgba(56, 189, 248, 0.8);
  background: rgba(14, 165, 233, 0.12);
}

.stage-pipeline .stage.done {
  border-color: rgba(16, 185, 129, 0.5);
  background: rgba(16, 185, 129, 0.1);
}

.stage-pipeline .stage.failed {
  border-color: rgba(248, 113, 113, 0.7);
  background: rgba(248, 113, 113, 0.12);
}

.stage-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  border: 2px solid rgba(148, 163, 184, 0.45);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.15rem;
  padding: 0.3rem 0.4rem;
  font-size: 1.35rem;
}

.stage-base {
  flex: 1;
  text-align: left;
}

.stage-state {
  font-size: 0.95rem;
}

.stage-desc {
  margin: 0.05rem 0 0;
  font-size: 0.85rem;
  color: rgba(15, 23, 42, 0.7);
}

.countdown-hint {
  margin-top: 0.35rem;
  font-size: 0.95rem;
  color: #0f172a;
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.countdown-hint strong {
  font-size: 1.05rem;
  color: #16a34a;
}

.countdown-source {
  color: #64748b;
  font-size: 0.85rem;
}

.api-card {
  gap: 0.25rem;
  padding: 0.75rem 1rem;
  max-width: 320px;
  width: 100%;
  justify-self: start;
}

.api-mini-row {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  min-height: 40px;
}

.api-mini-row.meta {
  justify-content: space-between;
  color: rgba(226, 232, 240, 0.9);
  font-size: 0.9rem;
}

.balance-label {
  font-weight: 600;
  color: #cbd5f5;
}

.btn-icon {
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(15, 23, 42, 0.7);
  color: #e5e7eb;
  border-radius: 10px;
  padding: 0.35rem 0.45rem;
  cursor: pointer;
}

.btn-icon:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.card-subtitle {
  margin: 0.15rem 0 0;
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.65);
}

.api-input-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.api-input-row input {
  flex: 1;
}

.api-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.bucket-note,
.bucket-path {
  font-size: 0.9rem;
  color: rgba(229, 231, 235, 0.8);
}

.task-list-section {
  margin-bottom: 1.25rem;
}

.task-list {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  margin: 0;
}

.task-list li {
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 12px;
  padding: 0.85rem;
  transition: border-color 0.2s ease, background-color 0.2s ease;
}

.task-list li.active {
  border-color: rgba(59, 130, 246, 0.6);
  background: rgba(37, 99, 235, 0.08);
}

.task-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.status-badge {
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  font-size: 0.75rem;
  text-transform: uppercase;
  background: rgba(148, 163, 184, 0.2);
  border: 1px solid rgba(148, 163, 184, 0.3);
}

.status-badge.finished {
  background: rgba(16, 185, 129, 0.2);
  border-color: rgba(16, 185, 129, 0.5);
}

.status-badge.failed {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.45);
}

.status-badge.running {
  background: rgba(59, 130, 246, 0.15);
  border-color: rgba(59, 130, 246, 0.4);
}

.task-info-row {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  margin: 0.5rem 0;
  color: rgba(226, 232, 240, 0.8);
  font-size: 0.9rem;
}

.task-message {
  color: rgba(248, 250, 252, 0.85);
}

.task-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.task-card-actions {
  display: flex;
  gap: 0.5rem;
}

.form-wrapper {
  border-top: 1px solid rgba(148, 163, 184, 0.25);
  padding-top: 1.25rem;
}

.empty-state {
  padding: 1rem;
  border: 1px dashed rgba(148, 163, 184, 0.4);
  border-radius: 12px;
  font-size: 0.95rem;
  color: rgba(226, 232, 240, 0.7);
}

.material-list {
  list-style: none;
  padding: 0;
  margin: 1rem 0 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.material-list li {
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 12px;
  padding: 0.85rem;
}

.material-preview {
  display: grid;
  gap: 0.75rem;
  margin: 0.75rem 0 0.5rem;
}

.material-preview video,
.material-preview audio {
  width: 100%;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.35);
}

.material-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.material-tag {
  padding: 0.1rem 0.55rem;
  border-radius: 999px;
  font-size: 0.75rem;
  text-transform: uppercase;
  background: rgba(148, 163, 184, 0.2);
  border: 1px solid rgba(148, 163, 184, 0.3);
}

.material-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: 0.5rem;
}

.btn-text {
  border: none;
  background: none;
  color: #60a5fa;
  cursor: pointer;
  padding: 0.2rem 0.4rem;
  font-size: 0.9rem;
}

.btn-text.danger {
  color: #f87171;
}

.toast {
  position: fixed;
  bottom: 1.5rem;
  right: 1.5rem;
  background: rgba(15, 118, 110, 0.9);
  color: #fff;
  padding: 0.75rem 1.25rem;
  border-radius: 999px;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.35);
  font-size: 0.95rem;
}

.material-path code,
.bucket-path code,
.bucket-note code {
  font-size: 0.85rem;
  color: #cbd5f5;
}

@media (max-width: 768px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }

  .task-card-actions {
    flex-wrap: wrap;
    justify-content: flex-end;
  }
}

.character-library {
  border: 1px solid rgba(99, 102, 241, 0.3);
  padding: 1rem;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.92), rgba(30, 64, 175, 0.65));
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.35);
  color: #e5e7eb;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.link-btn {
  border: none;
  background: none;
  color: #2563eb;
  cursor: pointer;
  font-size: 0.9rem;
  padding: 0;
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
  border: 1px solid #d1d5db;
  border-radius: 4px;
  min-height: 36px;
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

.character-meta {
  flex: 1;
}

.character-desc {
  margin: 0.25rem 0;
  color: rgba(255, 255, 255, 0.85);
  line-height: 1.4;
}

.character-upload {
  margin-top: 0.5rem;
}

.character-upload summary {
  cursor: pointer;
  margin-bottom: 0.5rem;
}

.upload-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.btn-secondary {
  background: #1d4ed8;
  color: #fff;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
}

.input-error.success {
  color: #059669;
}
</style>
