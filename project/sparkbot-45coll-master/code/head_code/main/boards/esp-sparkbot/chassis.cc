/*
    ESP-SparkBot tracked chassis control.
    https://gitee.com/esp-friends/esp_sparkbot/tree/master/example/tank/c2_tracked_chassis
*/

#include "sdkconfig.h"
#include "iot/thing.h"
#include "board.h"

#include <driver/gpio.h>
#include <driver/uart.h>
#include <esp_log.h>
#include <cstring>
#include <string>

#include "boards/esp-sparkbot/config.h"

#define TAG "Chassis"

namespace iot {

class Chassis : public Thing {
private:
    light_mode_t light_mode_ = LIGHT_MODE_ALWAYS_ON;
    std::string motion_state_ = "stopped";

    void SendUartMessage(const char* command_str) {
        uint8_t len = strlen(command_str);
        uart_write_bytes(ECHO_UART_PORT_NUM, command_str, len);
        ESP_LOGI(TAG, "Sent command: %s", command_str);
    }

    void Move(const char* command_str, const char* state) {
        SendUartMessage(command_str);
        motion_state_ = state;
    }

    void InitializeEchoUart() {
        uart_config_t uart_config = {
            .baud_rate = ECHO_UART_BAUD_RATE,
            .data_bits = UART_DATA_8_BITS,
            .parity = UART_PARITY_DISABLE,
            .stop_bits = UART_STOP_BITS_1,
            .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
            .source_clk = UART_SCLK_DEFAULT,
        };
        int intr_alloc_flags = 0;

        ESP_ERROR_CHECK(uart_driver_install(ECHO_UART_PORT_NUM, BUF_SIZE * 2, 0, 0, NULL, intr_alloc_flags));
        ESP_ERROR_CHECK(uart_param_config(ECHO_UART_PORT_NUM, &uart_config));
        ESP_ERROR_CHECK(uart_set_pin(ECHO_UART_PORT_NUM, UART_ECHO_TXD, UART_ECHO_RXD, UART_ECHO_RTS, UART_ECHO_CTS));

        SendUartMessage("w2");
    }

public:
    Chassis() : Thing("Chassis", "SparkBot tracked chassis, movement and light effects"),
                light_mode_(LIGHT_MODE_WHITE_BREATH_SLOW) {
        InitializeEchoUart();

        properties_.AddNumberProperty("light_mode", "light effect index", [this]() -> int {
            return (light_mode_ - 2 <= 0) ? 1 : light_mode_ - 2;
        });

        properties_.AddStringProperty("motion_state", "current movement state", [this]() -> std::string {
            return motion_state_;
        });

        methods_.AddMethod("GoForward", "move forward", ParameterList(), [this](const ParameterList& parameters) {
            Move("x0.0 y1.0", "forward");
        });

        methods_.AddMethod("GoBack", "move backward", ParameterList(), [this](const ParameterList& parameters) {
            Move("x0.0 y-1.0", "backward");
        });

        methods_.AddMethod("TurnLeft", "turn left", ParameterList(), [this](const ParameterList& parameters) {
            Move("x-1.0 y0.0", "left");
        });

        methods_.AddMethod("TurnRight", "turn right", ParameterList(), [this](const ParameterList& parameters) {
            Move("x1.0 y0.0", "right");
        });

        methods_.AddMethod("Stop", "stop moving", ParameterList(), [this](const ParameterList& parameters) {
            Move("x0.0 y0.0", "stopped");
        });

        methods_.AddMethod("Dance", "dance", ParameterList(), [this](const ParameterList& parameters) {
            SendUartMessage("d1");
            light_mode_ = LIGHT_MODE_MAX;
            motion_state_ = "dancing";
        });

        methods_.AddMethod("SwitchLightMode", "set light mode", ParameterList({
            Parameter("lightmode", "integer from 1 to 6", kValueTypeNumber, true)
        }), [this](const ParameterList& parameters) {
            char command_str[5] = {'w', 0, 0};
            char mode = static_cast<char>(parameters["lightmode"].number()) + 2;

            ESP_LOGI(TAG, "Input Light Mode: %c", (mode + '0'));

            if (mode >= 3 && mode <= 8) {
                command_str[1] = mode + '0';
                SendUartMessage(command_str);
            }
        });
    }
};

} // namespace iot

DECLARE_THING(Chassis);
