# 演示步骤

本文给出一个从硬件连接到 Web 控制演示的完整流程，适合课堂展示、毕业设计答辩或项目 Demo。

## 1. 连接 LED 硬件

按照 [`wiring.md`](wiring.md) 完成接线：

- `PA4` → 客厅灯
- `PA5` → 卧室灯
- `PA6` → 厨房灯
- `PA7` → 卫生间灯
- `PB0` → 梳妆台灯

每个 LED 串联一个 `220Ω` 或 `330Ω` 电阻。

## 2. 烧录 STM32 固件

1. 使用 STM32CubeMX 生成基础 HAL 工程。
2. 将 [`firmware/`](../firmware/) 中的核心文件复制到工程中。
3. 编译工程。
4. 使用 ST-Link 或其他下载工具烧录到开发板。
5. 上电运行。

如果需要配置细节，请参考：

- [`firmware/stm32cube_notes.md`](../firmware/stm32cube_notes.md)

## 3. 查看串口号

### Windows

打开设备管理器，查看“端口（COM 和 LPT）”，例如：

- `COM3`
- `COM5`

### macOS

在终端执行：

```bash
ls /dev/tty.*
```

### Linux

在终端执行：

```bash
ls /dev/ttyUSB*
ls /dev/ttyACM*
```

## 4. 使用串口助手验证固件

在启动后端前，建议先用串口助手测试 STM32 是否正常响应。

串口参数：

- 波特率：`115200`
- 数据位：`8`
- 停止位：`1`
- 校验位：`None`

发送：

```text
STATUS
```

预期返回：

```text
STATUS 1:OFF 2:OFF 3:OFF 4:OFF 5:OFF
```

再发送：

```text
ALL ON
```

预期返回：

```text
OK
```

如果 LED 全亮，说明固件和硬件正常。

## 5. 启动后端

进入 [`backend/`](../backend/) 目录并安装依赖：

```bash
npm install
```

### Windows CMD 示例

```cmd
set SERIAL_PORT=COM5 && npm start
```

### macOS / Linux 示例

```bash
SERIAL_PORT=/dev/ttyUSB0 npm start
```

启动成功后，后端默认监听：

- `http://localhost:3000`

可访问健康检查接口：

- `http://localhost:3000/api/health`

## 6. 打开前端页面

方式一：直接打开 [`frontend/index.html`](../frontend/index.html)

方式二：使用静态服务器，例如：

```bash
cd frontend
python -m http.server 8080
```

然后访问：

- `http://localhost:8080`

## 7. 点击按钮控制 LED

页面打开后：

1. 查看顶部状态卡片：
   - 后端在线
   - STM32 在线
   - 串口正常
2. 页面会显示 5 张灯光控制卡片。
3. 点击任意房间的“打开”按钮。
4. 观察对应 LED 是否点亮。
5. 再点击“关闭”，观察 LED 是否熄灭。

## 8. 演示全开、全关、状态刷新

### 一键全开

点击“`一键全开`”，观察 5 个 LED 是否全部点亮。

### 一键全关

点击“`一键全关`”，观察 5 个 LED 是否全部熄灭。

### 刷新状态

点击“`刷新状态`”，前端会调用后端，再由后端向 STM32 发送 [`STATUS`](protocol.md) 命令，获取实时状态并更新页面。

## 9. 推荐演示讲解词

可以按以下逻辑讲解：

1. 浏览器页面只是控制界面。
2. 实际控制命令先发给本地 Node.js 后端。
3. 后端通过串口把文本命令发给 STM32。
4. STM32 解析命令后控制 GPIO 输出。
5. GPIO 高低电平驱动 LED 亮灭。
6. 状态查询时，STM32 再把当前灯状态返回给后端和前端。

## 10. 演示失败时的快速排查

### 页面显示后端离线

检查 [`backend/server.js`](../backend/server.js) 是否已启动。

### 页面显示串口异常

检查：

- 串口号是否正确
- 串口是否被占用
- STM32 是否已连接

### 页面按钮点击无效

检查：

- 固件是否已烧录
- LED 接线是否正确
- 串口协议是否能通过串口助手正常测试

### LED 逻辑反了

把 [`LED_ACTIVE_HIGH`](../firmware/Core/Inc/gpio_led.h) 从 `1` 改为 `0` 后重新编译烧录。
