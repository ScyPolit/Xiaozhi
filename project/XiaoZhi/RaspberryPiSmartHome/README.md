# 树莓派智能家居 GPIO 服务

树莓派连接电脑热点 `scypolit` 后，本服务提供与现有 STM32 控制器一致的 HTTP API。网关只需把 `SMART_HOME_URL` 指向树莓派地址即可。

## 接线

LED 正极串联 220-330 欧电阻后分别连接 BCM17、18、27、22、23，负极接 GND。BCM24 预留给继电器或第六个 LED。继电器必须使用带驱动和隔离的模块，不可直接由 GPIO 驱动负载。

## 安装

```bash
sudo mkdir -p /opt/zhihe-smart-home
sudo cp app.py requirements.txt /opt/zhihe-smart-home/
cd /opt/zhihe-smart-home
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
sudo cp zhihe-smart-home.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now zhihe-smart-home
```

建议在树莓派 NetworkManager 中创建热点自动连接：

```bash
sudo nmcli device wifi connect scypolit password '<热点密码>' ifname wlan0
sudo nmcli connection modify scypolit connection.autoconnect yes
```

本地模拟：`python app.py --simulate --port 18880`。
