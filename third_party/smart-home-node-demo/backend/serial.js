const { SerialPort, ReadlineParser } = require('serialport');
const config = require('./config');

const LED_DEFINITIONS = [
  { id: 1, name: '客厅灯', pin: 'PA4', state: false },
  { id: 2, name: '卧室灯', pin: 'PA5', state: false },
  { id: 3, name: '厨房灯', pin: 'PA6', state: false },
  { id: 4, name: '卫生间灯', pin: 'PA7', state: false },
  { id: 5, name: '梳妆台灯', pin: 'PB0', state: false }
];

class SerialLedController {
  constructor() {
    this.port = null;
    this.parser = null;
    this.isOpen = false;
    this.lastError = null;
    this.pendingRequest = null;
    this.leds = LED_DEFINITIONS.map((item) => ({ ...item }));
  }

  init() {
    try {
      this.port = new SerialPort({
        path: config.serialPort,
        baudRate: config.baudRate,
        autoOpen: false
      });

      this.parser = this.port.pipe(new ReadlineParser({ delimiter: '\n' }));
      this.parser.on('data', (line) => this.handleLine(line));

      this.port.on('open', () => {
        this.isOpen = true;
        this.lastError = null;
        console.log(`[serial] opened ${config.serialPort} @ ${config.baudRate}`);
      });

      this.port.on('close', () => {
        this.isOpen = false;
        this.rejectPending(this.createHttpError(503, '串口已关闭'));
        console.warn('[serial] port closed');
      });

      this.port.on('error', (error) => {
        this.isOpen = false;
        this.lastError = error.message;
        this.rejectPending(this.createHttpError(500, `serialport 异常：${error.message}`));
        console.error('[serial] error:', error.message);
      });

      this.port.open((error) => {
        if (error) {
          this.lastError = error.message;
          this.isOpen = false;
          console.warn(`[serial] open failed: ${error.message}`);
        }
      });
    } catch (error) {
      this.lastError = error.message;
      this.isOpen = false;
      console.warn(`[serial] init failed: ${error.message}`);
    }
  }

  getHealth() {
    return {
      backendOnline: true,
      stm32Online: this.isOpen,
      serialConnected: this.isOpen,
      serialPort: config.serialPort,
      baudRate: config.baudRate,
      serialTimeoutMs: config.serialTimeoutMs,
      lastError: this.lastError
    };
  }

  getLeds() {
    return this.leds.map((item) => ({ ...item }));
  }

  async setLed(id, state) {
    const led = this.findLed(id);
    if (!led) {
      throw this.createHttpError(400, '非法 LED ID');
    }

    this.validateState(state);
    await this.sendCommand(`SET ${Number(id)} ${state ? 'ON' : 'OFF'}`);
    led.state = Boolean(state);
    return this.getLeds();
  }

  async setAll(state) {
    this.validateState(state);
    await this.sendCommand(`ALL ${state ? 'ON' : 'OFF'}`);
    this.leds = this.leds.map((item) => ({ ...item, state: Boolean(state) }));
    return this.getLeds();
  }

  async refreshStatus() {
    const response = await this.sendCommand('STATUS');
    const parsed = this.parseStatus(response);
    this.leds = this.leds.map((item) => ({
      ...item,
      state: parsed[item.id] ?? item.state
    }));
    return this.getLeds();
  }

  validateState(state) {
    if (typeof state !== 'boolean') {
      throw this.createHttpError(400, 'state 参数必须为布尔值 true 或 false');
    }
  }

  findLed(id) {
    return this.leds.find((item) => item.id === Number(id));
  }

  createHttpError(status, message) {
    const error = new Error(message);
    error.status = status;
    return error;
  }

  ensurePortReady() {
    if (!this.port) {
      throw this.createHttpError(503, '串口对象未初始化');
    }

    if (!this.isOpen) {
      throw this.createHttpError(
        503,
        `串口不可用，请检查设备连接与配置。当前串口：${config.serialPort}`
      );
    }

    if (this.pendingRequest) {
      throw this.createHttpError(429, '串口忙，请稍后重试');
    }
  }

  sendCommand(command) {
    this.ensurePortReady();

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pendingRequest = null;
        reject(this.createHttpError(504, 'STM32 无响应，请检查固件、串口和波特率配置'));
      }, config.serialTimeoutMs);

      this.pendingRequest = {
        resolve: (line) => {
          clearTimeout(timeout);
          this.pendingRequest = null;
          resolve(line);
        },
        reject: (error) => {
          clearTimeout(timeout);
          this.pendingRequest = null;
          reject(error.status ? error : this.createHttpError(500, error.message));
        }
      };

      this.port.write(`${command}\n`, (error) => {
        if (error) {
          clearTimeout(timeout);
          this.pendingRequest = null;
          reject(this.createHttpError(500, `串口发送失败：${error.message}`));
          return;
        }

        this.port.drain((drainError) => {
          if (drainError) {
            clearTimeout(timeout);
            this.pendingRequest = null;
            reject(this.createHttpError(500, `串口刷新失败：${drainError.message}`));
          }
        });
      });
    }).then((line) => {
      const normalized = String(line || '').trim();
      if (normalized === 'ERR') {
        throw this.createHttpError(502, 'STM32 返回 ERR，命令执行失败');
      }
      return normalized;
    });
  }

  handleLine(line) {
    const normalized = String(line || '').trim();
    if (!normalized) {
      return;
    }

    if (this.pendingRequest) {
      this.pendingRequest.resolve(normalized);
    }
  }

  rejectPending(error) {
    if (this.pendingRequest) {
      this.pendingRequest.reject(
        error.status ? error : this.createHttpError(500, error.message || '串口请求失败')
      );
    }
  }

  parseStatus(line) {
    if (!line.startsWith('STATUS ')) {
      throw this.createHttpError(502, `STM32 返回了无法识别的状态：${line}`);
    }

    const result = {};
    const parts = line.replace('STATUS ', '').split(' ');

    for (const part of parts) {
      const [idText, stateText] = part.split(':');
      const id = Number(idText);
      if (!Number.isInteger(id) || id < 1 || id > 5) {
        continue;
      }
      result[id] = stateText === 'ON';
    }

    return result;
  }
}

module.exports = new SerialLedController();
