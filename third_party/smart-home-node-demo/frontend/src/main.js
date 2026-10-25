import { getHealth, getLeds, refreshLedsStatus, setAllLedState, setLedState } from './api.js';

const state = {
  leds: [],
  busy: false
};

const ledGrid = document.getElementById('ledGrid');
const template = document.getElementById('ledCardTemplate');
const backendStatus = document.getElementById('backendStatus');
const stm32Status = document.getElementById('stm32Status');
const serialStatus = document.getElementById('serialStatus');
const messageBox = document.getElementById('messageBox');
const refreshStatusBtn = document.getElementById('refreshStatusBtn');
const allOnBtn = document.getElementById('allOnBtn');
const allOffBtn = document.getElementById('allOffBtn');

function setMessage(message, isError = false) {
  messageBox.textContent = message;
  messageBox.classList.toggle('error-text', isError);
}

function setBusy(isBusy) {
  state.busy = isBusy;
  refreshStatusBtn.disabled = isBusy;
  allOnBtn.disabled = isBusy;
  allOffBtn.disabled = isBusy;

  document.querySelectorAll('.toggle-btn').forEach((button) => {
    button.disabled = isBusy;
    button.textContent = isBusy ? '处理中...' : button.dataset.nextLabel;
  });
}

function setStatusElement(element, online, onlineText, offlineText) {
  element.textContent = online ? onlineText : offlineText;
  element.classList.toggle('online', online);
  element.classList.toggle('offline', !online);
}

function renderLeds() {
  ledGrid.innerHTML = '';

  state.leds.forEach((led) => {
    const fragment = template.content.cloneNode(true);
    const card = fragment.querySelector('.led-card');
    const roomName = fragment.querySelector('.room-name');
    const pinName = fragment.querySelector('.pin-name');
    const stateText = fragment.querySelector('.state-text');
    const toggleBtn = fragment.querySelector('.toggle-btn');

    roomName.textContent = led.name;
    pinName.textContent = `引脚：${led.pin} · LED ${led.id}`;
    stateText.textContent = led.state ? '开启' : '关闭';
    toggleBtn.textContent = led.state ? '关闭' : '打开';
    toggleBtn.dataset.nextLabel = led.state ? '关闭' : '打开';

    card.classList.toggle('on', led.state);
    card.classList.toggle('off', !led.state);

    toggleBtn.addEventListener('click', async () => {
      await handleSingleToggle(led.id, !led.state);
    });

    ledGrid.appendChild(fragment);
  });
}

async function loadHealth() {
  try {
    const response = await getHealth();
    const health = response.data;
    setStatusElement(backendStatus, health.backendOnline, '后端在线', '后端离线');
    setStatusElement(stm32Status, health.stm32Online, 'STM32 在线', 'STM32 离线');
    setStatusElement(serialStatus, health.serialConnected, '串口正常', '串口异常');

    if (health.lastError) {
      setMessage(`串口提示：${health.lastError}`, true);
    }
  } catch (error) {
    setStatusElement(backendStatus, false, '后端在线', '后端离线');
    setStatusElement(stm32Status, false, 'STM32 在线', 'STM32 离线');
    setStatusElement(serialStatus, false, '串口正常', '串口异常');
    setMessage(`健康检查失败：${error.message}`, true);
  }
}

async function loadLeds() {
  try {
    const response = await getLeds();
    state.leds = response.leds;
    renderLeds();
    setMessage('已加载 LED 状态缓存。');
  } catch (error) {
    setMessage(`加载 LED 列表失败：${error.message}`, true);
  }
}

async function handleSingleToggle(id, nextState) {
  try {
    setBusy(true);
    const response = await setLedState(id, nextState);
    state.leds = response.leds;
    renderLeds();
    setMessage(response.message || `LED ${id} 状态已更新`);
    await loadHealth();
  } catch (error) {
    setMessage(`单灯控制失败：${error.message}`, true);
  } finally {
    setBusy(false);
  }
}

async function handleAllToggle(nextState) {
  try {
    setBusy(true);
    const response = await setAllLedState(nextState);
    state.leds = response.leds;
    renderLeds();
    setMessage(response.message || '全部灯状态已更新');
    await loadHealth();
  } catch (error) {
    setMessage(`批量控制失败：${error.message}`, true);
  } finally {
    setBusy(false);
  }
}

async function handleRefreshStatus() {
  try {
    setBusy(true);
    const response = await refreshLedsStatus();
    state.leds = response.leds;
    renderLeds();
    setMessage(response.message || '已刷新 STM32 实时状态');
    await loadHealth();
  } catch (error) {
    setMessage(`刷新状态失败：${error.message}`, true);
  } finally {
    setBusy(false);
  }
}

refreshStatusBtn.addEventListener('click', handleRefreshStatus);
allOnBtn.addEventListener('click', () => handleAllToggle(true));
allOffBtn.addEventListener('click', () => handleAllToggle(false));

async function bootstrap() {
  await loadHealth();
  await loadLeds();
}

bootstrap();
