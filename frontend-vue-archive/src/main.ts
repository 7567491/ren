import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import { setupI18n } from './plugins/i18n';
import './assets/main.css';
import 'filepond/dist/filepond.min.css';
import 'filepond-plugin-image-preview/dist/filepond-plugin-image-preview.css';
import 'video.js/dist/video-js.css';

const app = createApp(App);
const pinia = createPinia();
app.use(pinia);
app.use(setupI18n());
app.mount('#app');
