# 前端说明

前端使用原生 [`HTML`](index.html)、[`CSS`](src/style.css)、[`JavaScript`](src/main.js) 实现，适合教学演示、快速部署和二次开发。

## 文件说明

- [`index.html`](index.html)：页面结构与模板。
- [`src/style.css`](src/style.css)：智能家居风格界面样式。
- [`src/api.js`](src/api.js)：封装后端 API 请求。
- [`src/main.js`](src/main.js)：页面渲染、状态管理、按钮交互逻辑。

## 页面功能

- 页面标题：智能家居 LED 控制系统
- 显示后端状态、STM32 状态、串口状态
- 显示 5 张灯光控制卡片
- 支持单灯开关
- 支持一键全开 / 一键全关
- 支持刷新 STM32 实时状态
- 请求失败时显示错误提示
- 操作期间按钮进入 loading / disabled 状态

## 使用方式

### 方式 1：直接打开

直接在浏览器中打开 [`index.html`](index.html)。

### 方式 2：静态服务器

例如使用 Python：

```bash
python -m http.server 8080
```

然后访问：

- `http://localhost:8080`

## 后端地址

前端默认请求：

- `http://localhost:3000`

该地址定义在 [`src/api.js`](src/api.js) 中：

```js
const API_BASE_URL = 'http://localhost:3000';
```

如果你的后端端口不同，请修改该常量。

## 交互流程

1. 页面加载后调用 [`getHealth()`](src/api.js) 检查后端和串口状态。
2. 然后调用 [`getLeds()`](src/api.js) 获取当前 LED 缓存状态。
3. 点击单灯按钮时调用 [`setLedState()`](src/api.js)。
4. 点击全开 / 全关时调用 [`setAllLedState()`](src/api.js)。
5. 点击刷新状态时调用 [`refreshLedsStatus()`](src/api.js)。

## 调试建议

- 如果页面显示“后端离线”，先确认 [`backend/server.js`](../backend/server.js) 是否已启动。
- 如果页面显示“串口异常”，检查串口号和 STM32 固件。
- 如果按钮点击后报错，打开浏览器开发者工具查看 Network 和 Console。

## 可扩展方向

- 增加房间图标和动画
- 增加亮度调节滑块
- 增加场景模式按钮
- 增加自动轮询状态
- 增加 WebSocket 实时推送
