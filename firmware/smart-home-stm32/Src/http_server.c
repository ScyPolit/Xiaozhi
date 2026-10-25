#include "http_server.h"
#include "app_config.h"
#include "esp8266_at.h"
#include "gpio_led.h"

#include <stdio.h>
#include <string.h>

#define HTTP_RESPONSE_SIZE 1024U
#define HTTP_JSON_SIZE     768U

static void http_send_text(uint8_t connection_id, int status_code, const char *status_text, const char *body);
static void http_send_options(uint8_t connection_id);
static void http_send_error(uint8_t connection_id, int status_code, const char *error);
static int http_parse_led_id(const char *query);
static int http_parse_state(const char *query, uint8_t *state);
static const char *http_status_text(int status_code);

void HTTP_Server_HandleRequest(uint8_t connection_id, const char *request, uint16_t length)
{
    char method[8] = {0};
    char target[128] = {0};
    char path[80] = {0};
    char *query;
    uint8_t state = LED_STATE_OFF;
    int led_id;
    char json[HTTP_JSON_SIZE];
    uint8_t i;

    (void)length;

    if ((request == 0) || (sscanf(request, "%7s %127s", method, target) != 2))
    {
        http_send_error(connection_id, 400, "Bad request");
        return;
    }

    if (strcmp(method, "OPTIONS") == 0)
    {
        http_send_options(connection_id);
        return;
    }

    strncpy(path, target, sizeof(path) - 1U);
    query = strchr(path, '?');
    if (query != 0)
    {
        *query++ = '\0';
    }

    if ((strcmp(method, "GET") == 0) && (strcmp(path, "/api/health") == 0))
    {
        snprintf(json,
                 sizeof(json),
                 "{\"ok\":true,\"device\":\"STM32F103C8T6\",\"wifi\":%s,\"hostname\":\"%s\"}",
                 ESP8266_IsReady() ? "true" : "false",
                 DEVICE_HOSTNAME);
        HTTP_SendJson(connection_id, 200, json);
        return;
    }

    if ((strcmp(method, "GET") == 0) && (strcmp(path, "/api/leds") == 0))
    {
        size_t used = 0U;

        used += (size_t)snprintf(json + used, sizeof(json) - used, "{\"leds\":[");
        for (i = 1U; i <= LED_COUNT; i++)
        {
            used += (size_t)snprintf(json + used,
                                     sizeof(json) - used,
                                     "%s{\"id\":%u,\"name\":\"%s\",\"pin\":\"%s\",\"state\":%s}",
                                     (i == 1U) ? "" : ",",
                                     (unsigned int)i,
                                     LED_GetName(i),
                                     LED_GetPinName(i),
                                     (LED_Get(i) == LED_STATE_ON) ? "true" : "false");
        }
        (void)snprintf(json + used, sizeof(json) - used, "]}");
        HTTP_SendJson(connection_id, 200, json);
        return;
    }

    if ((strcmp(method, "GET") == 0) && (strcmp(path, "/api/led") == 0))
    {
        led_id = http_parse_led_id(query);
        if ((led_id < 1) || (led_id > (int)LED_COUNT))
        {
            http_send_error(connection_id, 400, "Invalid led id");
            return;
        }

        if (!http_parse_state(query, &state))
        {
            http_send_error(connection_id, 400, "Invalid state");
            return;
        }

        LED_Set((uint8_t)led_id, state);
        snprintf(json,
                 sizeof(json),
                 "{\"ok\":true,\"id\":%d,\"state\":%s}",
                 led_id,
                 (state == LED_STATE_ON) ? "true" : "false");
        HTTP_SendJson(connection_id, 200, json);
        return;
    }

    if ((strcmp(method, "GET") == 0) && (strcmp(path, "/api/ac") == 0))
    {
        if (!http_parse_state(query, &state))
        {
            http_send_error(connection_id, 400, "Invalid state");
            return;
        }

        LED_Set(LED_6_ID, state);
        snprintf(json,
                 sizeof(json),
                 "{\"ok\":true,\"id\":%u,\"name\":\"%s\",\"pin\":\"%s\",\"state\":%s}",
                 (unsigned int)LED_6_ID,
                 LED_GetName(LED_6_ID),
                 LED_GetPinName(LED_6_ID),
                 (state == LED_STATE_ON) ? "true" : "false");
        HTTP_SendJson(connection_id, 200, json);
        return;
    }

    if ((strcmp(method, "GET") == 0) && (strcmp(path, "/api/all") == 0))
    {
        if (!http_parse_state(query, &state))
        {
            http_send_error(connection_id, 400, "Invalid state");
            return;
        }

        LED_SetAll(state);
        snprintf(json,
                 sizeof(json),
                 "{\"ok\":true,\"state\":%s}",
                 (state == LED_STATE_ON) ? "true" : "false");
        HTTP_SendJson(connection_id, 200, json);
        return;
    }

    http_send_error(connection_id, 404, "Not found");
}

void HTTP_SendJson(uint8_t connection_id, int status_code, const char *json)
{
    http_send_text(connection_id, status_code, http_status_text(status_code), (json != 0) ? json : "{}");
}

static void http_send_text(uint8_t connection_id, int status_code, const char *status_text, const char *body)
{
    static char response[HTTP_RESPONSE_SIZE];
    unsigned int content_length = 0U;

    if (body != 0)
    {
        content_length = (unsigned int)strlen(body);
    }

    snprintf(response,
             sizeof(response),
             "HTTP/1.1 %d %s\r\n"
             "Access-Control-Allow-Origin: *\r\n"
             "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
             "Access-Control-Allow-Headers: Content-Type\r\n"
             "Access-Control-Allow-Private-Network: true\r\n"
             "Content-Type: application/json; charset=utf-8\r\n"
             "Connection: close\r\n"
             "Content-Length: %u\r\n"
             "\r\n"
             "%s",
             status_code,
             status_text,
             content_length,
             (body != 0) ? body : "");

    (void)ESP8266_SendHttpResponse(connection_id, response);
}

static void http_send_options(uint8_t connection_id)
{
    static char response[HTTP_RESPONSE_SIZE];

    snprintf(response,
             sizeof(response),
             "HTTP/1.1 200 OK\r\n"
             "Access-Control-Allow-Origin: *\r\n"
             "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
             "Access-Control-Allow-Headers: Content-Type\r\n"
             "Access-Control-Allow-Private-Network: true\r\n"
             "Content-Type: application/json; charset=utf-8\r\n"
             "Connection: close\r\n"
             "Content-Length: 2\r\n"
             "\r\n"
             "{}");

    (void)ESP8266_SendHttpResponse(connection_id, response);
}

static void http_send_error(uint8_t connection_id, int status_code, const char *error)
{
    char json[128];

    snprintf(json,
             sizeof(json),
             "{\"ok\":false,\"error\":\"%s\"}",
             (error != 0) ? error : "Error");
    HTTP_SendJson(connection_id, status_code, json);
}

static int http_parse_led_id(const char *query)
{
    const char *id_text;
    int id = 0;

    if (query == 0)
    {
        return 0;
    }

    id_text = strstr(query, "id=");
    if (id_text == 0)
    {
        return 0;
    }

    (void)sscanf(id_text, "id=%d", &id);
    return id;
}

static int http_parse_state(const char *query, uint8_t *state)
{
    const char *state_text;

    if ((query == 0) || (state == 0))
    {
        return 0;
    }

    state_text = strstr(query, "state=");
    if (state_text == 0)
    {
        return 0;
    }

    state_text += 6;
    if ((strncmp(state_text, "on", 2) == 0) ||
        (strncmp(state_text, "true", 4) == 0) ||
        (strncmp(state_text, "1", 1) == 0))
    {
        *state = LED_STATE_ON;
        return 1;
    }

    if ((strncmp(state_text, "off", 3) == 0) ||
        (strncmp(state_text, "false", 5) == 0) ||
        (strncmp(state_text, "0", 1) == 0))
    {
        *state = LED_STATE_OFF;
        return 1;
    }

    return 0;
}

static const char *http_status_text(int status_code)
{
    switch (status_code)
    {
        case 200:
            return "OK";
        case 400:
            return "Bad Request";
        case 404:
            return "Not Found";
        case 500:
            return "Internal Server Error";
        default:
            return "OK";
    }
}
