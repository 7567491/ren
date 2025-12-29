/**
 * 前端配置文件
 *
 * 此文件包含前端应用的固定配置，不应由最终用户修改。
 * 如需更改后端API地址，请修改此文件并重新部署。
 */

// 计算后端API基础地址
function resolveApiBase() {
    const FALLBACK = 'http://127.0.0.1:18000';

    if (typeof window === 'undefined') {
        return FALLBACK;
    }

    try {
        const params = new URLSearchParams(window.location.search);
        if (params.has('api_base')) {
            return params.get('api_base');
        }

        const origin = window.location.origin;
        if (origin && origin !== 'null' && origin !== 'file://') {
            return origin;
        }
    } catch (err) {
        console.warn('⚠️  解析 URL 参数失败，使用默认 API 地址', err);
    }

    return FALLBACK;
}

// 前端配置
const APP_CONFIG = {
    API_BASE: resolveApiBase(),

    // API配置
    API_TIMEOUT: 30000,  // 请求超时时间（毫秒）
    POLL_INTERVAL: 2000, // 状态轮询间隔（毫秒）

    // 调试模式（生产环境应设为false）
    DEBUG: true
};

// 冻结配置对象，防止运行时修改
Object.freeze(APP_CONFIG);

// 调试信息
if (APP_CONFIG.DEBUG) {
    console.log('🔧 应用配置:', {
        API_BASE: APP_CONFIG.API_BASE,
        环境: /Mobile|Android|iPhone/i.test(navigator.userAgent) ? '移动端' : '桌面端',
        浏览器: navigator.userAgent
    });
}
