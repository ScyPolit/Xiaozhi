module.exports = {
  port: Number(process.env.PORT || 3000),
  serialPort: process.env.SERIAL_PORT || "COM3",
  baudRate: Number(process.env.BAUD_RATE || 115200),
  serialTimeoutMs: Number(process.env.SERIAL_TIMEOUT_MS || 1500)
};
