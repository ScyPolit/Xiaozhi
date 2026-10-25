# 历史与第三方参考代码

本目录中的代码不参与智核默认启动流程：

- `sparkbot-legacy-baidu`：旧百度 API 协议对应的 SparkBot 源码，保留用于历史对照。
- `smart-home-node-demo`：早期 Node.js 串口控制样例，保留协议与实现参考。

当前入口分别是 `apps/gateway`、`apps/smart-home-rpi`、`firmware/sparkbot` 和 `firmware/smart-home-stm32`。新功能不应继续添加到本目录的历史实现中。
