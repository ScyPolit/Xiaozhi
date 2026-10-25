const express = require('express');
const cors = require('cors');
const config = require('./config');
const serialController = require('./serial');

const app = express();

app.use(cors());
app.use(express.json());

serialController.init();

app.get('/api/health', (req, res) => {
  res.json({
    success: true,
    message: '后端服务运行正常',
    data: serialController.getHealth()
  });
});

app.get('/api/leds', (req, res) => {
  res.json({
    success: true,
    leds: serialController.getLeds()
  });
});

app.get('/api/leds/status', async (req, res, next) => {
  try {
    const leds = await serialController.refreshStatus();
    res.json({
      success: true,
      message: '已从 STM32 刷新状态',
      leds
    });
  } catch (error) {
    next(error);
  }
});

app.post('/api/leds/all', async (req, res, next) => {
  try {
    const { state } = req.body;
    const leds = await serialController.setAll(state);
    res.json({
      success: true,
      message: state ? '全部灯已打开' : '全部灯已关闭',
      leds
    });
  } catch (error) {
    next(error);
  }
});

app.post('/api/leds/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    const { state } = req.body;
    const leds = await serialController.setLed(id, state);
    res.json({
      success: true,
      message: `LED ${id} 已${state ? '打开' : '关闭'}`,
      leds
    });
  } catch (error) {
    next(error);
  }
});

app.use((req, res) => {
  res.status(404).json({
    success: false,
    message: '接口不存在'
  });
});

app.use((error, req, res, next) => {
  const status = error.status || 500;
  res.status(status).json({
    success: false,
    message: error.message || '服务器内部错误'
  });
});

app.listen(config.port, () => {
  console.log(`backend server listening on http://localhost:${config.port}`);
});
