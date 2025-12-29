/**
 * 前端配置文件
 *
 * 此文件包含前端应用的固定配置，不应由最终用户修改。
 * 如需更改后端API地址，请修改此文件并重新部署。
 */

// 后端API基础地址（固定配置）
const APP_CONFIG = {
    // Linode服务器固定IP + 后端API端口
    API_BASE: 'http://139.162.52.158:18000',

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
