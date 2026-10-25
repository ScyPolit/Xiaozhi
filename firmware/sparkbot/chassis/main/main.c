
// void app_main(void)
// {
//     gpio_init();
//     // power gpio init
//     gpio_set_direction(POWER_GPIO, GPIO_MODE_OUTPUT);
//     gpio_set_level(POWER_GPIO, 0);
//     ESP_LOGI(TAG, "POWER_GPIO OFF!");

//     // // power gpio init
//     gpio_set_direction(RX_GPIO, GPIO_MODE_OUTPUT);
//     gpio_set_level(RX_GPIO, 0);
//     // ESP_LOGI(TAG, "RX_GPIO OFF!");

// }
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/uart.h"
#include "driver/gpio.h"
#include "sdkconfig.h"
#include "esp_sleep.h"
#include "esp_log.h"
#include "light_control.h"
#include "motion_control.h"
#include "power_management.h"
#include "iot_button.h"
#include "ir_senser.h"
#include <ctype.h>

#define KEY_GPIO GPIO_NUM_8
#define POWER_GPIO GPIO_NUM_2
#define RX_GPIO GPIO_NUM_20
static const char *TAG = "main";

#define UART_ECHO_TXD (GPIO_NUM_21)
#define UART_ECHO_RXD (GPIO_NUM_20)
#define UART_ECHO_RTS (-1)
#define UART_ECHO_CTS (-1)

#define ECHO_UART_PORT_NUM (0)
#define ECHO_UART_BAUD_RATE (115200)
#define ECHO_TASK_STACK_SIZE (4096)
#define BUF_SIZE (1024)
#define MAX_PAIRS 15 // llm最多几个命令

uint8_t line_state = false;
void power_off(void)
{
    gpio_config_t io_conf =
        {
            /*中断使能*/
            .intr_type = GPIO_INTR_DISABLE,
            /*输出模式调节*/
            .mode = GPIO_MODE_OUTPUT,
            /*配置引脚的掩码*/
            .pin_bit_mask = 1 << GPIO_NUM_20,
            /*下拉使能*/
            .pull_down_en = 1,
            /*上拉使能*/
            .pull_up_en = 0,
        };
    gpio_config(&io_conf);
    ESP_LOGI(TAG, "POWER OFF!");
    gpio_set_level(POWER_GPIO, 0);

    gpio_set_direction(RX_GPIO, GPIO_MODE_OUTPUT);
    gpio_set_level(RX_GPIO, 0);
}
// 从字符串中提取数字
int extractNumber(const char *str)
{
    int num = 0;
    // ESP_LOGI(TAG, "Extracting number from: %s", str);
    sscanf(str, "%d", &num);
    if (num < 30 && num > 0)
    {
        num += 40;
    }
    if (num < 0 && num > -30)
    {
        num -= 40;
    }
    // ESP_LOGI(TAG, "Extracted number: %d", num);
    return num;
}

// 提取 x 和 y 的值并存入数组
int extractXY(const char *input, int x[], int y[])
{
    int count = 0;
    const char *ptr = input;
    while (*ptr)
    {
        if (*ptr == 'l')
        {
            ptr++;
            int currentX = extractNumber(ptr);
            if (currentX < -100 || currentX > 100)
            {
                continue; // x 超出范围，跳过这组
            }
            while (*ptr)
            {
                if (*ptr == 'r')
                {
                    ptr++;
                    int currentY = extractNumber(ptr);
                    if (currentY < -100 || currentY > 100)
                    {
                        break; // y 超出范围，跳过这组
                    }
                    x[count] = currentX;
                    y[count] = currentY;
                    count++;
                    break;
                }
                else
                {
                    ptr++;
                }
            }
        }
        else
        {
            ptr++;
        }
    }
    return count;
}
static void echo_task(void *arg)
{
    /* Configure parameters of an UART driver,
     * communication pins and install the driver */
    uart_config_t uart_config = {
        .baud_rate = ECHO_UART_BAUD_RATE,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    int intr_alloc_flags = 0;

#if CONFIG_UART_ISR_IN_IRAM
    intr_alloc_flags = ESP_INTR_FLAG_IRAM;
#endif

    ESP_ERROR_CHECK(uart_driver_install(ECHO_UART_PORT_NUM, BUF_SIZE * 2, 0, 0, NULL, intr_alloc_flags));
    ESP_ERROR_CHECK(uart_param_config(ECHO_UART_PORT_NUM, &uart_config));
    ESP_ERROR_CHECK(uart_set_pin(ECHO_UART_PORT_NUM, UART_ECHO_TXD, UART_ECHO_RXD, UART_ECHO_RTS, UART_ECHO_CTS));

    // Configure a temporary buffer for the incoming data
    uint8_t *data = (uint8_t *)malloc(BUF_SIZE);

    static int uart_read_count = 0;
    static uint32_t sleep_time = 0;
    static bool uart_read_web_flag = false;

    // sprintf((char *)data, "%s", "ll60r60l-30r-60l60r-30l-60r-60l30r80l80r30l-60r60l30r-80");
    // int len = strlen((const char *)data);

    static float x_value = 0.0f;
    static float y_value = 0.0f;
    static int x_llm[MAX_PAIRS];
    static int y_llm[MAX_PAIRS];
    static int llm_pair_count = 0;
    static int llm_index = 0;
    while (1)
    {
        // Read data from the UART
        int len = uart_read_bytes(ECHO_UART_PORT_NUM, data, (BUF_SIZE - 1), 20 / portTICK_PERIOD_MS);
        // vTaskDelay(20 / portTICK_PERIOD_MS);
        // Write data back to the UART
        // uart_write_bytes(ECHO_UART_PORT_NUM, (const char *)data, len);
        if (len)
        {
            sleep_time = 0;

            data[len] = '\0';
            len = 0;
            // ESP_LOGI(TAG, "Recv command: %s", (char *)data);
            char command = 0;
            int value = 0;
            ESP_LOGI(TAG, "Recv DATA: %s", (char *)data);
            sscanf((const char *)data, "%c", &command);
            ESP_LOGI(TAG, "Recv command: %c", command);
            if (command == 'l')
            {
                llm_pair_count = extractXY((const char *)data + 1, x_llm, y_llm);
                if (llm_pair_count)
                {
                    llm_index = 0;
                    uart_read_count = 0;
                    ESP_LOGI(TAG, "llm_pair_count: %d\n", llm_pair_count);
                }
                /* code */
            }
            if (command == 'x')
            {
                if (sscanf((const char *)data, "x%f y%f", &x_value, &y_value) == 2)
                {
                    uart_read_count = 0;
                    uart_read_web_flag = true;
                    ESP_LOGI(TAG, "Parsed x: %.2f, y: %.2f\n", x_value, y_value);
                    spark_bot_motion_control(x_value, y_value);
                }
            }
            if (command == 'w')
            {
                if (sscanf((const char *)data + 1, "%d", &value) == 1)
                {
                    rgb_ws2812_mode_set((light_mode_t)value);
                    set_power_current_light_mode((light_mode_t)value);
                }
            }
            if (command == 'c') // 巡线或者充电
            {
                line_state = 1;
                // set_motor_speed_coefficients(value);
            }
            if (command == 'd')
            {
                spark_bot_dance();
            }
        }
        if (uart_read_web_flag == true)
        {
            uart_read_count++; // 累计没有读取到数据的次数，直到25*20ms后（0.5s），自动停止
            if (uart_read_count > 80)
            {
                uart_read_count = 0;
                uart_read_web_flag = false;
                spark_bot_motion_control(0, 0);
            }
        }
        else if (llm_index < llm_pair_count) // 轮流执行llm对话命令，每个动作持续0.8s
        {
            uart_read_count++; // 累计没有读取到数据的次数，直到40*20ms后（0.8s），自动停止
            if (uart_read_count > 80)
            {
                ESP_LOGI(TAG, "llm index: %d", llm_index);
                uart_read_count = 0;
                ESP_LOGI(TAG, "X = %d, Y = %d", x_llm[llm_index], y_llm[llm_index]);
                // x_value = x_llm[llm_index];
                // y_value = y_llm[llm_index];
                // ESP_LOGI(TAG, "Parsed x: %.2f, y: %.2f\n", x_value, y_value);
                spark_bot_set_motor_speed(x_llm[llm_index], y_llm[llm_index]);
                llm_index++;
            }
            if (llm_index == llm_pair_count) // llm对话命令执行结束
            {
                uart_read_web_flag = true;
            }
        }
        if (line_state == 0)
        {
            sleep_time++;
            if (sleep_time > 500) // 10s关机
            {

                if (gpio_get_level(9) == 1 && gpio_get_level(UART_ECHO_RXD) == 0) // 不在充电并且头部没有放上来
                {
                    power_off();
                }

                // gpio_wakeup_enable(KEY_GPIO, GPIO_INTR_LOW_LEVEL);
                // gpio_wakeup_enable(UART_ECHO_RXD, GPIO_INTR_HIGH_LEVEL);

                // esp_sleep_enable_gpio_wakeup();
                // esp_light_sleep_start(); // 开启睡眠
                sleep_time = 0;
            }
        }
    }
}
static void button_single_click_cb(void *arg, void *data)
{
    // 按键单击
    if (line_state)
    {
        spark_bot_motion_control(0, 0);
        line_state = 0;
    }
    else
    {
        spark_bot_motion_control(0, 0.8);
        line_state = 2;
    }

    ESP_LOGI(TAG, "single click:");
}

static void button_double_click_cb(void *arg, void *data)
{
    // 按键双击
    if (line_state)
    {
        spark_bot_motion_control(0, 0);
        line_state = 0;
    }
    else
        line_state = 1;
    ESP_LOGI(TAG, "double click:");
}
static void button_long_press_start_cb(void *arg, void *data)
{
    // 按键长按开始
    rgb_ws2812_mode_set((light_mode_t)LIGHT_MODE_SHOW);
    set_power_current_light_mode((light_mode_t)LIGHT_MODE_SHOW);
    ESP_LOGI(TAG, "long press start:");
}
static void button_long_press_up_cb(void *arg, void *data)
{
    ESP_LOGI(TAG, "long press up:");
    // vTaskDelay(100 / portTICK_PERIOD_MS);
    // power_off();
    // const uint64_t WAKEUP_PIN_BITMASK = 0b0010;
    // // 按键长按结束
    // gpio_deep_sleep_hold_dis(); // 在深度睡眠时禁用所有数字gpio pad保持功能。
    // esp_deep_sleep_enable_gpio_wakeup(WAKEUP_PIN_BITMASK, ESP_GPIO_WAKEUP_GPIO_LOW);
    // esp_deep_sleep_start(); // 开始深度休眠
}
void key_event_init()
{
    button_config_t btn_config = {
        .type = BUTTON_TYPE_GPIO,
        .long_press_time = 1200,
        .short_press_time = 400,
        .gpio_button_config = {
            .gpio_num = KEY_GPIO,
            .active_level = 0,
        }};

    button_handle_t btn = iot_button_create(&btn_config);
    // iot_button_register_cb(btn, BUTTON_PRESS_DOWN, button_press_cb, NULL);
    // iot_button_register_cb(btn, BUTTON_PRESS_UP, button_press_up_cb, NULL);
    iot_button_register_cb(btn, BUTTON_SINGLE_CLICK, button_single_click_cb, NULL);
    iot_button_register_cb(btn, BUTTON_DOUBLE_CLICK, button_double_click_cb, NULL);
    iot_button_register_cb(btn, BUTTON_LONG_PRESS_START, button_long_press_start_cb, NULL);
    iot_button_register_cb(btn, BUTTON_LONG_PRESS_UP, button_long_press_up_cb, NULL);
}
extern int ir_0_adc_value;
extern int ir_1_adc_value;
void line_walking_task(void *arg)
{
    while (1)
    {
        if (line_state == 1)
        {
            while (line_state == 1)
            {
                if (ir_0_adc_value < 3000 && ir_1_adc_value < 3000)
                {
                    // spark_bot_motion_control(0, 0.4); // go straight
                    spark_bot_set_motor_speed(100, 100);
                }
                if (ir_0_adc_value > 3000)
                {
                    spark_bot_set_motor_speed(-80, 80);
                }
                if (ir_1_adc_value > 3000)
                {
                    spark_bot_set_motor_speed(80, -80);
                }
                if (ir_0_adc_value > 3000 && ir_1_adc_value > 3000)
                {
                    spark_bot_set_motor_speed(90, 90);
                }
                // 判断是否充电，如果gpio为低则充电
                if (gpio_get_level(9) == 0)
                    line_state = 0;
                vTaskDelay(2 / portTICK_PERIOD_MS);
            }
            spark_bot_motion_control(0, 0); // stop
        }
        vTaskDelay(10 / portTICK_PERIOD_MS);
    }
}
void app_main(void)
{
    uint8_t key_value = 0;
    // 电源io打开使能
    gpio_set_direction(POWER_GPIO, GPIO_MODE_OUTPUT);
    gpio_set_level(POWER_GPIO, 1);

    ESP_LOGI(TAG, "POWER_GPIO ON!");
    ESP_LOGI(TAG, "Let's go!");

    motor_ledc_init();
    rgb_ws2812_init();
    battery_voltage_monitor_start();
    ir_senser_start();

    xTaskCreate(echo_task, "uart_echo_task", ECHO_TASK_STACK_SIZE, NULL, 10, NULL);
    xTaskCreate(line_walking_task, "line_walking_task", 2048, NULL, 11, NULL);

    key_event_init();
}
