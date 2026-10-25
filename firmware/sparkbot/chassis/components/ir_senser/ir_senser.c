#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "driver/gpio.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "ir_senser.h"
extern adc_oneshot_unit_handle_t adc1_handle;
#define IR_0_ADC_CHAN           ADC_CHANNEL_0
#define IR_0_ADC_ATTEN          ADC_ATTEN_DB_12
#define IR_1_ADC_CHAN           ADC_CHANNEL_1
#define IR_1_ADC_ATTEN          ADC_ATTEN_DB_12
#define ADC_SMOOTH_WINDOW_SIZE  10

int ir_0_adc_value = 0;
int ir_1_adc_value = 0;

static int ir_0_adc_raw;
static int ir_1_adc_raw;
static const char *TAG = "ir_senser";
// 平滑滤波
static int ir_0_adc_smoothing(int new_sample)
{
    static int samples[ADC_SMOOTH_WINDOW_SIZE] = {0};
    static uint8_t index = 0;
    static int sum = 0;

    sum -= samples[index];
    samples[index] = new_sample;
    sum += new_sample;
    index = (index + 1) % ADC_SMOOTH_WINDOW_SIZE;

    return sum / ADC_SMOOTH_WINDOW_SIZE;
}
static int ir_1_adc_smoothing(int new_sample)
{
    static int samples[ADC_SMOOTH_WINDOW_SIZE] = {0};
    static uint8_t index = 0;
    static int sum = 0;

    sum -= samples[index];
    samples[index] = new_sample;
    sum += new_sample;
    index = (index + 1) % ADC_SMOOTH_WINDOW_SIZE;

    return sum / ADC_SMOOTH_WINDOW_SIZE;
};
/*---------------------------------------------------------------
        ADC Calibration
---------------------------------------------------------------*/
static bool example_adc_calibration_init(adc_unit_t unit, adc_channel_t channel, adc_atten_t atten, adc_cali_handle_t *out_handle)
{
    adc_cali_handle_t handle = NULL;
    esp_err_t ret = ESP_FAIL;
    bool calibrated = false;

#if ADC_CALI_SCHEME_CURVE_FITTING_SUPPORTED
    if (!calibrated) {
        ESP_LOGI(TAG, "calibration scheme version is %s", "Curve Fitting");
        adc_cali_curve_fitting_config_t cali_config = {
            .unit_id = unit,
            .chan = channel,
            .atten = atten,
            .bitwidth = ADC_BITWIDTH_DEFAULT,
        };
        ret = adc_cali_create_scheme_curve_fitting(&cali_config, &handle);
        if (ret == ESP_OK) {
            calibrated = true;
        }
    }
#endif

#if ADC_CALI_SCHEME_LINE_FITTING_SUPPORTED
    if (!calibrated) {
        ESP_LOGI(TAG, "calibration scheme version is %s", "Line Fitting");
        adc_cali_line_fitting_config_t cali_config = {
            .unit_id = unit,
            .atten = atten,
            .bitwidth = ADC_BITWIDTH_DEFAULT,
        };
        ret = adc_cali_create_scheme_line_fitting(&cali_config, &handle);
        if (ret == ESP_OK) {
            calibrated = true;
        }
    }
#endif

    *out_handle = handle;
    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "Calibration Success");
    } else if (ret == ESP_ERR_NOT_SUPPORTED || !calibrated) {
        ESP_LOGW(TAG, "eFuse not burnt, skip software calibration");
    } else {
        ESP_LOGE(TAG, "Invalid arg or no memory");
    }

    return calibrated;
}
static void ir_senser_task(void *arg)
{
    //-------------ADC1 Config---------------//
    adc_oneshot_chan_cfg_t config = {
        .bitwidth = ADC_BITWIDTH_DEFAULT,
        .atten = IR_0_ADC_ATTEN,
    };
    ESP_ERROR_CHECK(adc_oneshot_config_channel(adc1_handle, IR_0_ADC_CHAN, &config));
    ESP_ERROR_CHECK(adc_oneshot_config_channel(adc1_handle, IR_1_ADC_CHAN, &config));
    
    //-------------ADC1 Calibration Init---------------//
    adc_cali_handle_t adc1_cali_chan0_handle = NULL;
    bool do_calibration1_chan0 = example_adc_calibration_init(ADC_UNIT_1, IR_0_ADC_CHAN, IR_0_ADC_ATTEN, &adc1_cali_chan0_handle);

    adc_cali_handle_t adc1_cali_chan1_handle = NULL;
    bool do_calibration1_chan1 = example_adc_calibration_init(ADC_UNIT_1, IR_1_ADC_CHAN, IR_1_ADC_ATTEN, &adc1_cali_chan1_handle);

    ESP_LOGI(TAG, "while1");
    while (1) {
        // 获取bat adc值
        ESP_ERROR_CHECK(adc_oneshot_read(adc1_handle, IR_0_ADC_CHAN, &ir_0_adc_raw));
        ir_0_adc_value = ir_0_adc_smoothing(ir_0_adc_raw);
        // ESP_LOGI(TAG, "ir_0_adc_value: %d", ir_0_adc_value);

        ESP_ERROR_CHECK(adc_oneshot_read(adc1_handle, IR_1_ADC_CHAN, &ir_1_adc_raw));
        ir_1_adc_value = ir_1_adc_smoothing(ir_1_adc_raw);
        // ESP_LOGI(TAG, "ir_1_adc_value: %d", ir_1_adc_value);
        vTaskDelay(2 / portTICK_PERIOD_MS);
    }
}
void ir_senser_start(void)
{
    xTaskCreate(ir_senser_task, "ir_senser_task", 2048, NULL, 4, NULL);
}
