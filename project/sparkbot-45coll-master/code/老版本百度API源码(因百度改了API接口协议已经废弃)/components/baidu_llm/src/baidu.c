/*
 * SPDX-FileCopyrightText: 2015-2022 Espressif Systems (Shanghai) CO LTD
 *
 * SPDX-License-Identifier: Unlicense OR CC0-1.0
 */

#include <string.h>
#include <sys/param.h>
#include <stdlib.h>
#include <ctype.h>

#include "esp_log.h"
#include "esp_event.h"
#include "esp_tls.h"

#include "cJSON.h"
#include "esp_http_client.h"

#include "baidu.h"
#include <regex.h>
#include <ctype.h>
#include <limits.h>
#include "nvs_flash.h"

#include "tracked_chassis_control.h"
#define MAX_HTTP_RESPONSE_SIZE 2048 // 根据实际需求调整大小
extern void memory_monitor();
static char *response_data;
static int response_data_len = 0;

extern char baidu_api_key[64];
extern char baidu_secret_key[64];
extern uint16_t baidu_tts_speed;
extern uint16_t baidu_tts_pit;
extern uint16_t baidu_tts_vol;
extern uint16_t baidu_tts_per;
extern char llm_url[200];
extern char llm_api_key[64];
extern char llm_modle[64];
extern char asr_api_key[64];
extern char qweather_api_key[64];

// 需要填入相对于的API KEY才能使用全部功能
#define HEFENG_WEATHER_API ""   //和风天气API   获取地址https://dev.qweather.com/docs/api/
#define BAIDU_CLIENT_ID ""      //百度语音识别、合成ID   获取地址https://cloud.baidu.com/product/speech
#define BAIDU_CLIENT_SECRET ""  //百度语音识别、合成SECRET
#define BAIDU_TOKEN_URL "https://aip.baidubce.com/oauth/2.0/token?client_id=%s&client_secret=%s&grant_type=client_credentials"

#define SYSTEM_PROMPT "你将扮演一个活泼可爱的机器人，通过控制左右轮子的运动来让小主人开心。以下是详细的操作规则和输出格式：轮子控制命令格式：使用中括号 [] 包裹命令。命令格式为 [l(变量)r(变量)]，其中 l 表示左轮子，r 表示右轮子。变量范围为 -100 到 100 之间的整数。命令执行规则：如果运动需要多条命令，请连续输出多个 [l(变量)r(变量)] 命令。机器人会按照顺序执行这些命令。用户省略变量值时，变量等于50来执行。特殊命令：如果听到特殊命令“充电”，直接输出控制命令 [c]。示例：向前：[l50r50]；向左转：[l-50r50]；输出要求：输出完控制命令后，说一句 10-30字有趣可爱的话，能让人开心。尽可能用运动来模拟完成指令，例如画个正方形。非运动对话：如果不是关于运动的对话，请作为智能助手，回答简洁在 100字 以内。请严格按照以上规则和格式执行命令，只需要输出控制命令+文字，并确保输出内容活泼可爱，让小主人开心！"

#define LLM_URL "https://api.siliconflow.cn/v1/chat/completions"
#define LLM_API_KEY ""   //硅基流动AI的API_KEY    获取地址https://cloud.siliconflow.cn/i/jSwYy9N3
#define LLM_MODEL "deepseek-ai/DeepSeek-V2.5"


#define BAIDUBCE_STT_URL            "https://vop.baidu.com/pro_api?dev_pid=80001&cuid=123456PHP&token=%s"

#define TTS_SPEED 6 // 语速
#define TTS_PIT 3    // 音调
#define TTS_VOL 8   // 音量
#define TTS_PER 4103 // 配音音色
#define BAIDU_TTS_FORMAT "tex=%s&tok=%s&cuid=12345postman&ctp=1&lan=zh&spd=%d&pit=%d&vol=%d&per=%d&aue=6&="

#define LLM_MESSAGE_FORMAT "{\"model\": \"%s\",\"messages\":[{\"role\":\"user\",\"content\":\"%s\"},{\"role\":\"system\",\"content\":\"%s\"}],\"top_p\":%.2f,\"temperature\":%.2f,\"max_tokens\": 1024}"
#define LLM_TOP_P 0.9
#define LLM_TEMPERATURE 0.8
static const char *TAG = "baidu_speech";
void default_api_key()
{
    if (strlen(baidu_api_key) == 0)
    {
        strcpy(baidu_api_key, BAIDU_CLIENT_ID);
        strcpy(baidu_secret_key, BAIDU_CLIENT_SECRET);
        baidu_tts_speed = TTS_SPEED;
        baidu_tts_pit = TTS_PIT;
        baidu_tts_vol = TTS_VOL;
        baidu_tts_per = TTS_PER;
    }
    if (strlen(llm_api_key) == 0)
    {
        strcpy(llm_url, LLM_URL);
        strcpy(llm_api_key, LLM_API_KEY);
        strcpy(llm_modle, LLM_MODEL);
    }
    if(strlen(qweather_api_key) == 0){
         strcpy(qweather_api_key, HEFENG_WEATHER_API);
    }
}
esp_http_client_handle_t baidu_erniebot_http_handle = NULL;
char *baidu_audio_token;
// 定义25天的秒数（25天 * 24小时 * 60分钟 * 60秒）
#define STORAGE_INTERVAL_SECONDS (25 * 24 * 60 * 60)
// NVS命名空间和键名
static const char *NVS_NAMESPACE = "storage";
static const char *NVS_KEY_TIMESTAMP = "last_timestamp";
static const char *NVS_KEY_STRING = "stored_string";
// 从NVS读取时间戳和字符串
esp_err_t nvs_read_data(time_t *last_timestamp, char *stored_string, size_t max_len)
{
    nvs_handle_t nvs_handle;
    esp_err_t err;

    // 打开NVS命名空间
    err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs_handle);
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "Failed to open NVS namespace: %s", esp_err_to_name(err));
        return err;
    }

    // 读取时间戳
    err = nvs_get_i64(nvs_handle, NVS_KEY_TIMESTAMP, (int64_t *)last_timestamp);
    if (err != ESP_OK && err != ESP_ERR_NVS_NOT_FOUND)
    {
        ESP_LOGE(TAG, "Failed to read timestamp: %s", esp_err_to_name(err));
        nvs_close(nvs_handle);
        return err;
    }

    // 读取字符串
    size_t required_size = 0;
    err = nvs_get_str(nvs_handle, NVS_KEY_STRING, NULL, &required_size);
    if (err != ESP_OK && err != ESP_ERR_NVS_NOT_FOUND)
    {
        ESP_LOGE(TAG, "Failed to read string size: %s", esp_err_to_name(err));
        nvs_close(nvs_handle);
        return err;
    }

    if (required_size > 0)
    {
        err = nvs_get_str(nvs_handle, NVS_KEY_STRING, stored_string, &required_size);
        if (err != ESP_OK)
        {
            ESP_LOGE(TAG, "Failed to read string: %s", esp_err_to_name(err));
            nvs_close(nvs_handle);
            return err;
        }
        ESP_LOGI(TAG, "Stored string: %s,size:%d,strlen:%d", "123", required_size, strlen(stored_string));
        stored_string[required_size - 1] = '\0';
        stored_string[required_size] = '\0';
    }
    else
    {
        // memset(stored_string, 0, max_len);
        stored_string[0] = '\0'; // 如果没有数据，清空字符串
    }

    nvs_close(nvs_handle);
    return ESP_OK;
}

// 将时间戳和字符串写入NVS
esp_err_t nvs_write_data(time_t timestamp, const char *string_to_store)
{
    nvs_handle_t nvs_handle;
    esp_err_t err;

    // 打开NVS命名空间
    err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs_handle);
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "Failed to open NVS namespace: %s", esp_err_to_name(err));
        return err;
    }

    // 写入时间戳
    err = nvs_set_i64(nvs_handle, NVS_KEY_TIMESTAMP, (int64_t)timestamp);
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "Failed to write timestamp: %s", esp_err_to_name(err));
        nvs_close(nvs_handle);
        return err;
    }

    // 写入字符串
    err = nvs_set_str(nvs_handle, NVS_KEY_STRING, string_to_store);
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "Failed to write string: %s", esp_err_to_name(err));
        nvs_close(nvs_handle);
        return err;
    }

    // 提交更改
    err = nvs_commit(nvs_handle);
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "Failed to commit NVS changes: %s", esp_err_to_name(err));
    }

    nvs_close(nvs_handle);
    return err;
}

// 获取当前时间戳
time_t get_current_timestamp(void)
{
    time_t now;
    time(&now);
    return now;
}
void process_response_data(const char *response)
{
    cJSON *root = cJSON_Parse(response);
    if (root == NULL)
    {
        ESP_LOGE(TAG, "Failed to parse JSON response");
    }
    else
    {
        // 提取access_token
        cJSON *access_token = cJSON_GetObjectItem(root, "access_token");
        if (access_token != NULL && cJSON_IsString(access_token))
        {
            char *token = access_token->valuestring;
            // ESP_LOGI(TAG, "access_token: %s", token);
            int len = strlen(token);
            memcpy(baidu_audio_token, token, len);
            baidu_audio_token[len] = '\0';
            // ESP_LOGI(TAG, "baidu_audio_token: %s", baidu_audio_token);
            // 写入NVS
            time_t current_timestamp = get_current_timestamp();

            esp_err_t err = nvs_write_data(current_timestamp, baidu_audio_token);
            if (err != ESP_OK)
            {
                ESP_LOGE(TAG, "Failed to write data to NVS");
                return;
            }

            ESP_LOGI(TAG, "New string stored: %s", baidu_audio_token);
        }
        else
        {
            ESP_LOGE(TAG, "Failed to extract access_token from JSON");
        }
    }

    cJSON_Delete(root);
    response = NULL;
}
esp_err_t _http_event_handler(esp_http_client_event_t *evt)
{
    switch (evt->event_id)
    {
    case HTTP_EVENT_ON_DATA:
        ESP_LOGI(TAG, "HTTP_EVENT_ON_DATA, len=%d", evt->data_len);
        if (!esp_http_client_is_chunked_response(evt->client))
        {
            // 打印响应数据
            if (response_data_len + evt->data_len < MAX_HTTP_RESPONSE_SIZE)
            {
                memcpy(response_data + response_data_len, evt->data, evt->data_len);
                response_data_len += evt->data_len;
            }
            else
            {
                ESP_LOGE(TAG, "Response buffer overflow!");
            }
        }
        else
        {
            memcpy(response_data + response_data_len, evt->data, evt->data_len);
            response_data_len += evt->data_len;
        }
        break;
    case HTTP_EVENT_ON_FINISH:
        ESP_LOGI(TAG, "HTTP_EVENT_ON_FINISH");
        // 确保响应数据以 null 结尾
        response_data[response_data_len] = '\0';
        // ESP_LOGI(TAG, "Response data: %s", response_data);
        process_response_data(response_data);
        break;
    case HTTP_EVENT_DISCONNECTED:
        ESP_LOGI(TAG, "HTTP_EVENT_DISCONNECTED");
        free(response_data);
        break;
    default:
        break;
    }
    return ESP_OK;
}
void baidu_token_get()
{
    response_data = malloc(MAX_HTTP_RESPONSE_SIZE);
    // 定义HTTP客户端配置
    char *token_url;
    token_url = malloc(MAX_HTTP_RESPONSE_SIZE);
    sprintf(token_url, BAIDU_TOKEN_URL, baidu_api_key, baidu_secret_key);
    esp_http_client_config_t config = {
        .url = token_url,
        .method = HTTP_METHOD_POST,
        .event_handler = _http_event_handler,

    };

    // 初始化HTTP客户端
    esp_http_client_handle_t client = esp_http_client_init(&config);

    // 设置请求头
    esp_http_client_set_header(client, "Content-Type", "application/json");
    esp_http_client_set_header(client, "Accept", "application/json");

    // // 设置POST请求体
    char *post_data;
    asprintf(&post_data, "{\"client_id\": \"%s\", \"client_secret\": \"%s\"}", baidu_api_key, baidu_secret_key);

    // 执行请求
    esp_http_client_set_post_field(client, post_data, strlen(post_data));

    // 执行请求
    ESP_LOGI(TAG, "Sending POST request...");
    esp_err_t err = esp_http_client_perform(client);
    if (err == ESP_OK)
    {
        ESP_LOGI(TAG, "HTTP POST Status = %d, content_length = %lld",
                 esp_http_client_get_status_code(client),
                 esp_http_client_get_content_length(client));
    }
    else
    {
        ESP_LOGE(TAG, "HTTP POST request failed: %s", esp_err_to_name(err));
    }
    // 清理HTTP客户端
    free(token_url);
    free(post_data);
    esp_http_client_cleanup(client);
}
/*
 * Parses the data response from the Baidu API at the following endpoint:
 * http://vop.baidu.com/server_api
 *
 * This function handles the response format and extracts relevant information
 * for further processing in the application.
 */
static char *baidu_stt_response_parse(const char *data, size_t len)
{
    cJSON *root = cJSON_Parse(data);
    if (root == NULL) {
        ESP_LOGI(TAG, "Error parsing JSON: %s\n", cJSON_GetErrorPtr());
        return NULL; 
    }

    cJSON *result_node = cJSON_GetObjectItem(root, "result");
    if (result_node == NULL || result_node->type != cJSON_Array) {
        ESP_LOGI(TAG, "Error: 'result' key not found in JSON.\n");
        ESP_LOGI(TAG, "Data received: %s", data);
        cJSON_Delete(root);
        return NULL; 
    }

    cJSON *first_result = cJSON_GetArrayItem(result_node, 0);
    if (first_result == NULL || first_result->type != cJSON_String) {
        ESP_LOGI(TAG, "Error: First item in 'result' is not a string.\n");
        ESP_LOGI(TAG, "Data received: %s", data);
        cJSON_Delete(root);
        return NULL;
    }

    char *result_value = NULL;
    asprintf(&result_value, "%s", first_result->valuestring);
    cJSON_Delete(root);

    ESP_LOGI(TAG, "result_value: %s", result_value);

    return result_value;
}
// static char *baidu_stt_response_parse(const char *data, size_t len)
// {
//     cJSON *root = cJSON_Parse(data);
//     if (root == NULL)
//     {
//         ESP_LOGI(TAG, "Error parsing JSON: %s\n", cJSON_GetErrorPtr());
//         return NULL;
//     }

//     cJSON *result_node = cJSON_GetObjectItem(root, "text");
//     if (result_node == NULL)
//     {
//         ESP_LOGE(TAG, "Error: 'text' key not found in JSON.\n");
//         ESP_LOGI(TAG, "Data received: %s", data);
//         cJSON_Delete(root);
//         return NULL;
//     }

//     // cJSON *first_result = cJSON_GetArrayItem(result_node, 0);
//     // if (first_result == NULL || first_result->type != cJSON_String)
//     // {
//     //     ESP_LOGI(TAG, "Error: First item in 'result' is not a string.\n");
//     //     ESP_LOGI(TAG, "Data received: %s", data);
//     //     cJSON_Delete(root);
//     //     return NULL;
//     // }

//     char *result_value = NULL;
//     asprintf(&result_value, "%s", result_node->valuestring);
//     cJSON_Delete(root);

//     ESP_LOGI(TAG, "result_value: %s", result_value);

//     return result_value;
// }

void extractBrackets(const char *input, char *brackets, char *outside)
{
    int bracketIndex = 0;
    int outsideIndex = 0;
    int inBracket = 0;
    char *p;
    p = (char *)malloc(strlen(input) + 1);
    brackets[bracketIndex] = '\0';
    outside[outsideIndex] = '\0';
    for (int i = 0; input[i] != '\0'; i++)
    {
        if (input[i] != ' ')
        {
            p[bracketIndex++] = input[i];
        }
    }
    p[bracketIndex] = '\0';
    ESP_LOGI(TAG, "p: %s", p);
    bracketIndex = 0;
    for (int i = 0; p[i] != '\0'; i++)
    {
        if (p[i] == '[')
        {
            inBracket = 1;
            continue;
        }
        else if (p[i] == ']')
        {
            inBracket = 0;
            continue;
        }

        if (inBracket)
        {
            int l, r;
            if (sscanf((const char *)p + i, "l%dr%d", &l, &r) == 2)
            {
                // ESP_LOGI(TAG, "Found brackets: l%d r%d", l, r);
                while (p[i] != ']')
                {
                    brackets[bracketIndex++] = p[i];
                    i++;
                }
                inBracket = 0;
                continue;
            }
            else
            {
                while (p[i] != ']')
                {
                    i++;
                }
                inBracket = 0;
                continue;
            }
        }
        else
        {
            outside[outsideIndex++] = p[i];
        }
    }
    free(p);
    brackets[bracketIndex] = '\0';
    outside[outsideIndex] = '\0';
}
/*
 * Parses the data response from the Baidu API at the following endpoint:
 * https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-lite-8k
 *
 * This function handles the response format and extracts relevant information
 * for further processing in the application.
 */
static char *baidu_content_response_parse(const char *data, size_t len)
{
    cJSON *root = cJSON_Parse(data);
    if (root == NULL)
    {
        printf("Error parsing JSON: %s\n", cJSON_GetErrorPtr());
        goto err;
    }

    // 获取 choices 数组
    cJSON *choices = cJSON_GetObjectItem(root, "choices");
    if (choices != NULL && cJSON_IsArray(choices))
    {
        // 获取数组的第一个元素
        cJSON *first_choice = cJSON_GetArrayItem(choices, 0);
        if (first_choice != NULL)
        {
            // 获取 message 对象
            cJSON *message = cJSON_GetObjectItem(first_choice, "message");
            if (message != NULL)
            {
                // 获取 content 字段
                cJSON *result_node = cJSON_GetObjectItem(message, "content");
                if (result_node == NULL || !cJSON_IsString(result_node))
                {
                    printf("Error: 'content' key not found or not a string.\n");
                    goto err;
                }
                char *result_value = strdup(result_node->valuestring);
                // // 这里提取出要转语音的文字
                char *brackets;
                char *outside;
                brackets = (char *)malloc(1024);
                outside = (char *)malloc(1024);
                // 巡线命令
                if (result_value[0] == '[' && result_value[1] == 'c' && result_value[2] == ']')
                {
                    ESP_LOGI(TAG, "line follow");
                    char *motor_data = "c";
                    tracked_chassis_motion_control(motor_data);
                    int i = 0;
                    while (result_value[i + 3] != '\0')
                    {
                        outside[i] = result_value[i + 3];
                        i++;
                    }
                    outside[i] = '\0';
                    cJSON_Delete(root);
                    free(result_value);
                    return outside;
                }
                extractBrackets(result_value, brackets, outside);
                if (strlen(brackets) != 0)
                {
                    // 提取到速度l和r值，通过串口发送小车
                    // ESP_LOGI(TAG, "llm move: %s", brackets);
                    char motor_data[100];
                    sprintf(motor_data, "l%s", brackets);
                    tracked_chassis_motion_control(motor_data);
                }
                if (strlen(outside) == 0)
                {

                    // 错误没有读取到文字
                    ESP_LOGE(TAG, "not find text");
                    sprintf(outside, "我没有理解你说的话");
                    cJSON_Delete(root);
                    free(result_value);
                    return outside;
                }
                cJSON_Delete(root);

                free(result_value);
                return outside;
            }
            else
            {
                printf("Error: 'message' key not found or not a string.\n");
                goto err;
            }
        }
        else
        {
            printf("Failed to get first choice.\n");
            goto err;
        }
    }
    else
    {
        printf("Error: 'choices' key not found or not an array.\n");
        goto err;
    }

    // cJSON *result_node = cJSON_GetObjectItem(root, "result");
    // if (result_node == NULL || !cJSON_IsString(result_node))
    // {
    //     printf("Error: 'result' key not found or not a string.\n");
    //     goto err;
    // }

    cJSON_Delete(root);

err:
    cJSON_Delete(root);
    return NULL;
}

static char *baidu_content_stream_response_parse(const char *data, size_t len)
{
    cJSON *root = cJSON_Parse(data);
    if (root == NULL)
    {
        ESP_LOGE(TAG, "Error parsing JSON: %s", cJSON_GetErrorPtr());
        goto err;
    }

    cJSON *is_end = cJSON_GetObjectItem(root, "is_end");
    if (is_end == NULL || !cJSON_IsBool(is_end))
    {
        ESP_LOGE(TAG, "Error: response is not stream");
        goto err;
    }

    if (cJSON_IsTrue(is_end))
    {
        ESP_LOGI(TAG, "response is end");
        goto err;
    }

    cJSON *result_node = cJSON_GetObjectItem(root, "result");
    if (result_node == NULL || !cJSON_IsString(result_node))
    {
        ESP_LOGE(TAG, "Error: 'result' key not found or not a string.");
        goto err;
    }

    char *result_value = strdup(result_node->valuestring);

    cJSON_Delete(root);
    return result_value;

err:
    cJSON_Delete(root);
    return NULL;
}

esp_err_t baidu_erniebot_send_request(const char *content)
{
    if (content == NULL)
    {
        ESP_LOGI(TAG, "NULL content input");
        return ESP_OK;
    }

    esp_http_client_config_t config = {
        // .user_data              = local_response_buffer,
        .url = llm_url,
        .method = HTTP_METHOD_POST,
    };

    /* Set the headers */
    baidu_erniebot_http_handle = esp_http_client_init(&config);
    esp_http_client_set_header(baidu_erniebot_http_handle, "Content-Type", "application/json");
    char *bearer = NULL;
    asprintf(&bearer, "Bearer %s", llm_api_key);
    esp_http_client_set_header(baidu_erniebot_http_handle, "Authorization", bearer);

    /* Create JSON payload with format and content */
    char *json_payload = NULL;
    // asprintf(&json_payload, BAIDUBCE_MESSAGE_FORMAT, content);
    asprintf(&json_payload, LLM_MESSAGE_FORMAT, llm_modle, content, SYSTEM_PROMPT, LLM_TOP_P, LLM_TEMPERATURE);

    ESP_LOGI(TAG, "json_payload_len: %d", strlen(json_payload));

    // // 设置 POST 数据
    // esp_http_client_set_post_field(baidu_erniebot_http_handle, json_payload, strlen(json_payload));
    // esp_err_t err = esp_http_client_perform(baidu_erniebot_http_handle);

    esp_http_client_open(baidu_erniebot_http_handle, strlen(json_payload));
    esp_http_client_write(baidu_erniebot_http_handle, json_payload, strlen(json_payload));
    free(json_payload);

    json_payload = NULL;
    free(bearer);
    return ESP_OK;
}

esp_err_t baidu_erniebot_recv_response(char **response_data)
{
    int content_length = esp_http_client_fetch_headers(baidu_erniebot_http_handle);
    char *output_buffer = heap_caps_calloc(1, content_length + 1, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    // int read_length = esp_http_client_read_response(baidu_erniebot_http_handle, output_buffer, content_length);
    int read_length = esp_http_client_read_response(baidu_erniebot_http_handle, output_buffer, content_length);

    if (read_length > 0)
    {
        ESP_LOGI(TAG, "read_length: %d output_buffer: %s", read_length, output_buffer);
        *response_data = baidu_content_response_parse(output_buffer, read_length);
        // *response_data = baidu_content_response_parse(output_buffer, content_length);
    }
    else
    {
        ESP_LOGE(TAG, "Failed to read any data from response");
        esp_http_client_close(baidu_erniebot_http_handle);
        esp_http_client_cleanup(baidu_erniebot_http_handle);
        baidu_erniebot_http_handle = NULL;
        return ESP_OK;
    }

    esp_http_client_close(baidu_erniebot_http_handle);
    esp_http_client_cleanup(baidu_erniebot_http_handle);
    baidu_erniebot_http_handle = NULL;

    free(output_buffer);
    output_buffer = NULL;

    return ESP_OK;
}

// WAV头结构体（打包确保无填充）
typedef struct
{
    char riff[4];
    uint32_t file_size;
    char wave[4];
    char fmt[4];
    uint32_t fmt_size;
    uint16_t audio_format;
    uint16_t num_channels;
    uint32_t sample_rate;
    uint32_t byte_rate;
    uint16_t block_align;
    uint16_t bits_per_sample;
    char data[4];
    uint32_t data_size;
} wav_header_t;

void generate_wav_header(uint8_t *header, uint32_t pcm_data_size, uint16_t num_channels, uint32_t sample_rate, uint16_t bits_per_sample)
{
    wav_header_t wav_header = {
        .riff = {'R', 'I', 'F', 'F'},
        .file_size = 36 + pcm_data_size,
        .wave = {'W', 'A', 'V', 'E'},
        .fmt = {'f', 'm', 't', ' '},
        .fmt_size = 16,
        .audio_format = 1,
        .num_channels = num_channels,
        .sample_rate = sample_rate,
        .byte_rate = sample_rate * num_channels * bits_per_sample / 8,
        .block_align = num_channels * bits_per_sample / 8,
        .bits_per_sample = bits_per_sample,
        .data = {'d', 'a', 't', 'a'},
        .data_size = (pcm_data_size)};
    ESP_LOGI(TAG, "wav_header.file_size: %d", wav_header.file_size);
    memcpy(header, &wav_header, sizeof(wav_header_t));
}

/*
 * The following code sends an audio input to Baidu's speech-to-text (STT) service,
 * receives a text response, and processes it.
 */
static esp_http_client_handle_t g_baidu_asr_http_handle = NULL;
esp_err_t baidu_asr_send_audio(const int16_t *audio, size_t len, size_t total_len)
{
    char *url_str = NULL;
    asprintf(&url_str, BAIDUBCE_STT_URL, baidu_audio_token);

    if (!g_baidu_asr_http_handle) {
        esp_http_client_config_t config = {
            .url = url_str,
            .method = HTTP_METHOD_POST,
            .skip_cert_common_name_check = true,
            .buffer_size = 1460,
            .timeout_ms = 30000,
        };

        /* Set the headers */
        g_baidu_asr_http_handle = esp_http_client_init(&config);
        esp_http_client_set_header(g_baidu_asr_http_handle, "Content-Type", "audio/pcm;rate=16000");

        esp_http_client_open(g_baidu_asr_http_handle, total_len);
    }

    for (int written_len = 0; written_len < len; ) {
        written_len += esp_http_client_write(g_baidu_asr_http_handle, (char *)(audio + written_len), len - written_len);
    }

    return ESP_OK;
}
// #define BAIDUBCE_STT_URL "https://api.siliconflow.cn/v1/audio/transcriptions"
// esp_err_t baidu_asr_send_audio(const int16_t *audio, size_t len, size_t total_len)
// {
//     // char *url_str = NULL;

//     // url_str = heap_caps_malloc(1024, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
//     // // memset(url_str, 0, 1024);
//     // // ESP_LOGI(TAG, "size: %ld, %ld, %ld", strlen(url_str), strlen(BAIDUBCE_STT_URL), strlen(baidu_audio_token));
//     // sprintf(url_str, BAIDUBCE_STT_URL, baidu_audio_token);
//     // asprintf(&url_str, BAIDUBCE_STT_URL, baidu_audio_token);

//     uint16_t num_channels = 1;     // 单声道
//     uint32_t sample_rate = 16000;  // 16kHz采样率
//     uint16_t bits_per_sample = 16; // 16位深度

//     // 生成WAV头
//     uint8_t *wav_buffer = malloc(sizeof(wav_header_t) + len);
//     memset(wav_buffer, 0, sizeof(wav_header_t) + len);
//     generate_wav_header(wav_buffer, len, num_channels, sample_rate, bits_per_sample);
//     memcpy(wav_buffer + sizeof(wav_header_t), audio, len);

//     size_t wav_data_len = 0;
//     wav_data_len = sizeof(wav_header_t) + len;
//     const char *boundary = "b43b4cbce06c8b5c691d6598f01dc495";
//     char model_part[256];
//     snprintf(model_part, sizeof(model_part),
//              "--%s\r\n"
//              "Content-Disposition: form-data; name=\"model\"\r\n\r\n"
//              "FunAudioLLM/SenseVoiceSmall\r\n",
//              boundary);

//     char file_part_header[256];
//     snprintf(file_part_header, sizeof(file_part_header),
//              "--%s\r\n"
//              "Content-Disposition: form-data; name=\"file\"; filename=\"audio.wav\"\r\n"
//              "Content-Type: audio/wav\r\n\r\n",
//              boundary);

//     char end_part[256];
//     snprintf(end_part, sizeof(end_part), "\r\n--%s--\r\n", boundary);

//     // 计算Content-Length
//     size_t content_length = strlen(model_part) + strlen(file_part_header) + wav_data_len + strlen(end_part);
//     char content_length_str[20];
//     snprintf(content_length_str, sizeof(content_length_str), "%d", content_length);
//     ESP_LOGI(TAG, "content_length: %d", content_length);
//     if (!g_baidu_asr_http_handle)
//     {
//         esp_http_client_config_t config = {
//             .url = BAIDUBCE_STT_URL,
//             .method = HTTP_METHOD_POST,
//             .buffer_size = 1460,
//             .timeout_ms = 30000,
//         };

//         /* Set the headers */
//         g_baidu_asr_http_handle = esp_http_client_init(&config);
//         esp_http_client_set_header(g_baidu_asr_http_handle, "Accept-Encoding", "gzip, deflate");

//         esp_http_client_set_header(g_baidu_asr_http_handle, "accept", "application/json");
//         char *bearer = NULL;
//         asprintf(&bearer, "Bearer %s", asr_api_key);
//         esp_http_client_set_header(g_baidu_asr_http_handle, "Authorization", bearer);
//         char ctype[256];
//         memset(ctype, 0, sizeof(ctype));
//         snprintf(ctype, sizeof(ctype), "multipart/form-data; boundary=%s", boundary);
//         esp_http_client_set_header(g_baidu_asr_http_handle, "Content-Type", ctype);

//         // 发送请求
//         esp_http_client_open(g_baidu_asr_http_handle, content_length);
//         esp_http_client_write(g_baidu_asr_http_handle, model_part, strlen(model_part));
//         esp_http_client_write(g_baidu_asr_http_handle, file_part_header, strlen(file_part_header));
//         for (int written_len = 0; written_len < wav_data_len;)
//         {
//             written_len += esp_http_client_write(g_baidu_asr_http_handle, (char *)(wav_buffer + written_len), wav_data_len - written_len);
//             ESP_LOGI(TAG, "written_len: %d", written_len);
//         }
//         esp_http_client_write(g_baidu_asr_http_handle, end_part, strlen(end_part));
//         free(bearer);
//     }
//     free(wav_buffer);

//     return ESP_OK;
// }

esp_err_t baidu_asr_recv_text(char **text)
{
    int content_length = esp_http_client_fetch_headers(g_baidu_asr_http_handle);

    char *output_buffer = heap_caps_calloc(1, content_length + 1, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);

    int read_length = esp_http_client_read_response(g_baidu_asr_http_handle, output_buffer, content_length);
    if (read_length > 0)
    {
        *text = baidu_stt_response_parse(output_buffer, content_length);
    }
    else
    {
        ESP_LOGE(TAG, "Failed to read any data from response");
    }

    free(output_buffer);
    output_buffer = NULL;
    esp_http_client_close(g_baidu_asr_http_handle);
    esp_http_client_cleanup(g_baidu_asr_http_handle);
    g_baidu_asr_http_handle = NULL;

    return ESP_OK;
}

/*
 * The following code sends a text input to Baidu's text-to-speech (TTS) service,
 * receives an audio response, and processes it.
 *
 */
static esp_http_client_handle_t g_baidu_tts_http_handle = NULL;

// esp_err_t baidu_tts_send_text(const char *text)
// {
//     // 硅基流动的api测试,结果有点奇怪，语音速度很慢，暂时不用
//     esp_http_client_config_t config = {
//         .url = "https://api.siliconflow.cn/v1/audio/speech",
//         // .url = "http://192.168.31.89:9002",
//         .method = HTTP_METHOD_POST,
//         .timeout_ms = 30000,
//         .buffer_size = 1460,
//         .skip_cert_common_name_check = true,
//     };

//     g_baidu_tts_http_handle = esp_http_client_init(&config);
//     esp_http_client_set_header(g_baidu_tts_http_handle, "Accept-Encoding", "gzip, deflate");
//     esp_http_client_set_header(g_baidu_tts_http_handle, "Connection", "keep-alive");
//     esp_http_client_set_header(g_baidu_tts_http_handle, "Content-Type", "application/json");
//     esp_http_client_set_header(g_baidu_tts_http_handle, "Authorization", "Bearer " GUIJI_API_KEY);
// #define TTS_MODEL "FunAudioLLM/CosyVoice2-0.5B"
// #define TTS_VOICE "FunAudioLLM/CosyVoice2-0.5B:diana"
// #define TTS_SPEED 1.2
// #define TTS_GAIN 1.0
// // #define TTS_FORMAT "{\"input\": \"%s\", \"model\": \"%s\", \"voice\": \"%s\", \"response_format\": \"wav\", \"sample_rate\": \"16000\", \"speed\": %.2f, \"gain\": %.2f}"
// #define TTS_FORMAT "{\"input\": \"%s\", \"model\": \"%s\", \"voice\": \"%s\", \"response_format\": \"wav\", \"sample_rate\": \"16000\"}"

//     char *rep_text = malloc(strlen(text) + 1);
//     int j = 0;
//     for (int i = 0; i < strlen(text); i++)
//     {
//         if (text[i] != '\n' && text[i] != '\r')
//         {
//             rep_text[j] = text[i];
//             j++;
//         }
//     }
//     rep_text[j] = '\0';
//     char *payload = NULL;
//     // Create JSON payload with model, max tokens, and content
//     asprintf(&payload, TTS_FORMAT, rep_text, TTS_MODEL, TTS_VOICE);
//     // ESP_LOGI(TAG, "payload: %s", payload);
//     esp_http_client_open(g_baidu_tts_http_handle, strlen(payload));
//     esp_http_client_write(g_baidu_tts_http_handle, payload, strlen(payload));
//     free(payload);
//     payload = NULL;
//     return ESP_OK;
// }

esp_err_t baidu_tts_send_text(const char *text)
{
    esp_http_client_config_t config = {
        .url = "https://tsn.baidu.com/text2audio",
        .method = HTTP_METHOD_POST,
        .timeout_ms = 30000,
        .buffer_size = 1460,
        .skip_cert_common_name_check = true,
    };

    // Set the headers
    g_baidu_tts_http_handle = esp_http_client_init(&config);
    esp_http_client_set_header(g_baidu_tts_http_handle, "Content-Type", "application/json");

    char *payload = NULL;
    // Create JSON payload with model, max tokens, and content
    asprintf(&payload, BAIDU_TTS_FORMAT, text, baidu_audio_token, baidu_tts_speed, baidu_tts_pit, baidu_tts_vol, baidu_tts_per);
    // ESP_LOGI(TAG, "payload: %s", payload);
    esp_http_client_open(g_baidu_tts_http_handle, strlen(payload));
    esp_http_client_write(g_baidu_tts_http_handle, payload, strlen(payload));
    free(payload);
    payload = NULL;
    return ESP_OK;
}

bool baidu_tts_recv_audio(uint8_t **data, size_t *len, size_t *total_len, bool recv)
{
    static int s_baidu_tts_audio_total_len = -1;
    if (recv)
    {
        if (s_baidu_tts_audio_total_len == -1)
        {
            s_baidu_tts_audio_total_len = esp_http_client_fetch_headers(g_baidu_tts_http_handle);
            ESP_LOGI(TAG, "s_baidu_tts_audio_total_len: %d", s_baidu_tts_audio_total_len);
            *total_len = s_baidu_tts_audio_total_len;
        }

        /* 500 ms audio */
        int audio_length = 16000 * 2 * 500 / 1000;
        // int audio_length = s_baidu_tts_audio_total_len;
        uint8_t *output_buffer = heap_caps_calloc(1, audio_length, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);

        /* Read 500 ms for audio playing */
        int read_length = esp_http_client_read(g_baidu_tts_http_handle, (char *)output_buffer, audio_length);
        // ESP_LOGI(TAG, "s_baidu_tts_audio_total_len: %d, read_length: %d", s_baidu_tts_audio_total_len, read_length);

        if (read_length > 0)
        {
            *len = read_length;
            *data = output_buffer;
            return true;
        }
        else
        {
            free(output_buffer);
            output_buffer = NULL;
            goto end;
        }
    }
    else
    {
        goto end;
    }

    return false;

end:
    ESP_LOGW(TAG, "End of audio response");
    *data = NULL;
    esp_http_client_close(g_baidu_tts_http_handle);
    esp_http_client_cleanup(g_baidu_tts_http_handle);
    g_baidu_tts_http_handle = NULL;
    s_baidu_tts_audio_total_len = -1;
    return false;
}
void get_baidu_audio_token(void)
{
    // 读取NVS中的数据
    time_t last_timestamp = 0;
    // char stored_string[128] = {0};
    baidu_audio_token = (char *)malloc(128);
    memset(baidu_audio_token, 0, 128);
    esp_err_t err = nvs_read_data(&last_timestamp, baidu_audio_token, sizeof(baidu_audio_token));
    // 获取当前时间
    time_t current_timestamp = get_current_timestamp();
    // 判断是否超过25天
    if (current_timestamp - last_timestamp >= STORAGE_INTERVAL_SECONDS || last_timestamp == 0)
    {
        ESP_LOGI(TAG, "25 days have passed or first run. Storing new string...");

        // 新字符串
        baidu_token_get();
        // const char *new_string = "Hello, this is a new string!";
    }
    else
    {
        ESP_LOGI(TAG, "25 days have not passed yet. Last stored string: %s", "123");
    }
}