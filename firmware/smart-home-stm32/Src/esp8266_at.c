#include "esp8266_at.h"
#include "app_config.h"
#include "http_server.h"

#include <stdio.h>
#include <string.h>

#define USART1_BASE     0x40013800UL
#define RCC_BASE        0x40021000UL
#define GPIOA_BASE      0x40010800UL
#define NVIC_ISER1      (*(volatile uint32_t *)0xE000E104UL)

#define RCC_APB2ENR     (*(volatile uint32_t *)(RCC_BASE + 0x18U))
#define GPIOA_CRH       (*(volatile uint32_t *)(GPIOA_BASE + 0x04U))
#define USART1_SR       (*(volatile uint32_t *)(USART1_BASE + 0x00U))
#define USART1_DR       (*(volatile uint32_t *)(USART1_BASE + 0x04U))
#define USART1_BRR      (*(volatile uint32_t *)(USART1_BASE + 0x08U))
#define USART1_CR1      (*(volatile uint32_t *)(USART1_BASE + 0x0CU))
#define USART1_CR2      (*(volatile uint32_t *)(USART1_BASE + 0x10U))
#define USART1_CR3      (*(volatile uint32_t *)(USART1_BASE + 0x14U))

#define USART_SR_RXNE       (1UL << 5)
#define USART_SR_TXE        (1UL << 7)
#define USART_SR_TC         (1UL << 6)
#define USART_CR1_UE        (1UL << 13)
#define USART_CR1_RE        (1UL << 2)
#define USART_CR1_TE        (1UL << 3)
#define USART_CR1_RXNEIE    (1UL << 5)

#define SYSTEM_PCLK2_HZ     8000000UL
#define USART1_IRQn_BIT     5U
#define UART_RX_BUFFER_SIZE 1024U
#define AT_RESPONSE_SIZE    512U
#define IPD_HEADER_SIZE     48U
#define HTTP_PAYLOAD_SIZE   768U

extern uint32_t APP_GetMillis(void);

static volatile uint8_t g_rx_buffer[UART_RX_BUFFER_SIZE];
static volatile uint16_t g_rx_head = 0U;
static volatile uint16_t g_rx_tail = 0U;
static char g_at_response[AT_RESPONSE_SIZE];
static uint8_t g_ready = 0U;
volatile uint32_t g_esp8266_init_stage = 0U;

static void usart1_init(void);
static void usart1_send_byte(uint8_t byte);
static void usart1_send_string(const char *text);
static void usart1_send_data(const char *data, uint16_t length);
static uint8_t uart_pop(uint8_t *byte);
static void uart_drain(uint32_t quiet_ms);
static void at_response_reset(void);
static void at_response_append(uint8_t byte);
static uint8_t esp_wait_for(const char *expect, uint32_t timeout_ms);

void ESP8266_UART_RxCallback(uint8_t byte)
{
    uint16_t next_head = (uint16_t)((g_rx_head + 1U) % UART_RX_BUFFER_SIZE);

    if (next_head != g_rx_tail)
    {
        g_rx_buffer[g_rx_head] = byte;
        g_rx_head = next_head;
    }
}

void USART1_IRQHandler(void)
{
    if ((USART1_SR & USART_SR_RXNE) != 0U)
    {
        ESP8266_UART_RxCallback((uint8_t)(USART1_DR & 0xFFU));
    }
}

uint8_t ESP8266_Init(void)
{
    usart1_init();
    g_ready = 0U;
    g_esp8266_init_stage = 1U;

    if (!ESP8266_SendCommand("AT", "OK", ESP8266_UART_TIMEOUT_MS))
    {
        return 0U;
    }
    g_esp8266_init_stage = 2U;

    (void)ESP8266_SendCommand("ATE0", "OK", ESP8266_UART_TIMEOUT_MS);

    if (!ESP8266_SendCommand("AT+CWMODE=1", "OK", ESP8266_UART_TIMEOUT_MS))
    {
        return 0U;
    }
    g_esp8266_init_stage = 3U;

    (void)ESP8266_SetHostname(DEVICE_HOSTNAME);

    if (!ESP8266_ConnectWiFi(WIFI_SSID, WIFI_PASSWORD))
    {
        return 0U;
    }
    g_esp8266_init_stage = 4U;

    (void)ESP8266_SendCommand("AT+CIFSR", "OK", ESP8266_UART_TIMEOUT_MS);

    if (!ESP8266_SendCommand("AT+CIPMUX=1", "OK", ESP8266_UART_TIMEOUT_MS))
    {
        return 0U;
    }
    g_esp8266_init_stage = 5U;

    if (!ESP8266_StartServer(HTTP_PORT))
    {
        return 0U;
    }
    g_esp8266_init_stage = 6U;

    (void)ESP8266_SendCommand("AT+MDNS=1,\"" DEVICE_HOSTNAME "\",\"http\",80", "OK", ESP8266_UART_TIMEOUT_MS);
    g_ready = 1U;
    g_esp8266_init_stage = 7U;
    return 1U;
}

uint8_t ESP8266_SendCommand(const char *cmd, const char *expect, uint32_t timeout_ms)
{
    if (cmd == 0)
    {
        return 0U;
    }

    uart_drain(30U);
    at_response_reset();
    usart1_send_string(cmd);
    usart1_send_string("\r\n");

    if (expect == 0)
    {
        return 1U;
    }

    return esp_wait_for(expect, timeout_ms);
}

uint8_t ESP8266_ConnectWiFi(const char *ssid, const char *password)
{
    char command[160];

    if ((ssid == 0) || (password == 0))
    {
        return 0U;
    }

    snprintf(command, sizeof(command), "AT+CWJAP=\"%s\",\"%s\"", ssid, password);
    return ESP8266_SendCommand(command, "OK", 20000U);
}

uint8_t ESP8266_StartServer(uint16_t port)
{
    char command[32];

    snprintf(command, sizeof(command), "AT+CIPSERVER=1,%u", (unsigned int)port);
    return ESP8266_SendCommand(command, "OK", ESP8266_UART_TIMEOUT_MS);
}

uint8_t ESP8266_SetHostname(const char *hostname)
{
    char command[96];

    if (hostname == 0)
    {
        return 0U;
    }

    snprintf(command, sizeof(command), "AT+CWHOSTNAME=\"%s\"", hostname);
    return ESP8266_SendCommand(command, "OK", ESP8266_UART_TIMEOUT_MS);
}

uint8_t ESP8266_SendHttpResponse(uint8_t connection_id, const char *response)
{
    char command[32];
    uint16_t length;

    if (response == 0)
    {
        return 0U;
    }

    length = (uint16_t)strlen(response);
    snprintf(command, sizeof(command), "AT+CIPSEND=%u,%u",
             (unsigned int)connection_id,
             (unsigned int)length);

    if (!ESP8266_SendCommand(command, ">", ESP8266_UART_TIMEOUT_MS))
    {
        snprintf(command, sizeof(command), "AT+CIPCLOSE=%u", (unsigned int)connection_id);
        (void)ESP8266_SendCommand(command, "OK", 1000U);
        return 0U;
    }

    at_response_reset();
    usart1_send_data(response, length);
    (void)esp_wait_for("SEND OK", ESP8266_UART_TIMEOUT_MS);

    snprintf(command, sizeof(command), "AT+CIPCLOSE=%u", (unsigned int)connection_id);
    (void)ESP8266_SendCommand(command, "OK", 1000U);
    return 1U;
}

void ESP8266_Process(void)
{
    static char header[IPD_HEADER_SIZE];
    static char payload[HTTP_PAYLOAD_SIZE];
    static uint16_t header_index = 0U;
    static uint16_t payload_index = 0U;
    static uint16_t payload_length = 0U;
    static uint8_t connection_id = 0U;
    static uint8_t collecting_payload = 0U;
    uint8_t byte;
    char *ipd;
    int parsed_id;
    int parsed_len;

    while (uart_pop(&byte))
    {
        if (collecting_payload != 0U)
        {
            if (payload_index < (HTTP_PAYLOAD_SIZE - 1U))
            {
                payload[payload_index] = (char)byte;
            }
            payload_index++;

            if (payload_index >= payload_length)
            {
                uint16_t copy_len = payload_length;

                if (copy_len >= HTTP_PAYLOAD_SIZE)
                {
                    copy_len = HTTP_PAYLOAD_SIZE - 1U;
                }

                payload[copy_len] = '\0';
                HTTP_Server_HandleRequest(connection_id, payload, copy_len);

                collecting_payload = 0U;
                payload_index = 0U;
                payload_length = 0U;
                header_index = 0U;
                memset(header, 0, sizeof(header));
            }
            continue;
        }

        if (header_index < (IPD_HEADER_SIZE - 1U))
        {
            header[header_index++] = (char)byte;
            header[header_index] = '\0';
        }
        else
        {
            memmove(header, header + 1, IPD_HEADER_SIZE - 2U);
            header[IPD_HEADER_SIZE - 2U] = (char)byte;
            header[IPD_HEADER_SIZE - 1U] = '\0';
        }

        if (byte == ':')
        {
            ipd = strstr(header, "+IPD,");
            if ((ipd != 0) && (sscanf(ipd, "+IPD,%d,%d:", &parsed_id, &parsed_len) == 2))
            {
                if ((parsed_id >= 0) && (parsed_id <= 4) && (parsed_len > 0))
                {
                    connection_id = (uint8_t)parsed_id;
                    payload_length = (uint16_t)parsed_len;
                    payload_index = 0U;
                    collecting_payload = 1U;
                }
            }
            header_index = 0U;
            memset(header, 0, sizeof(header));
        }

        if ((byte == '\n') && (strstr(header, "+IPD,") == 0))
        {
            header_index = 0U;
            memset(header, 0, sizeof(header));
        }
    }
}

uint8_t ESP8266_IsReady(void)
{
    return g_ready;
}

static void usart1_init(void)
{
    RCC_APB2ENR |= (1UL << 2);   /* IOPAEN */
    RCC_APB2ENR |= (1UL << 14);  /* USART1EN */

    /* PA9 TX: AF push-pull 50 MHz, PA10 RX: floating input. */
    GPIOA_CRH &= ~((0xFUL << 4) | (0xFUL << 8));
    GPIOA_CRH |=  ((0xBUL << 4) | (0x4UL << 8));

    USART1_CR1 = 0U;
    USART1_CR2 = 0U;
    USART1_CR3 = 0U;
    USART1_BRR = (SYSTEM_PCLK2_HZ + (115200UL / 2UL)) / 115200UL;
    USART1_CR1 = USART_CR1_UE | USART_CR1_RE | USART_CR1_TE | USART_CR1_RXNEIE;

    NVIC_ISER1 = (1UL << USART1_IRQn_BIT);
}

static void usart1_send_byte(uint8_t byte)
{
    while ((USART1_SR & USART_SR_TXE) == 0U)
    {
    }

    USART1_DR = byte;
}

static void usart1_send_string(const char *text)
{
    if (text == 0)
    {
        return;
    }

    while (*text != '\0')
    {
        usart1_send_byte((uint8_t)*text++);
    }
}

static void usart1_send_data(const char *data, uint16_t length)
{
    uint16_t i;

    for (i = 0U; i < length; i++)
    {
        usart1_send_byte((uint8_t)data[i]);
    }

    while ((USART1_SR & USART_SR_TC) == 0U)
    {
    }
}

static uint8_t uart_pop(uint8_t *byte)
{
    if ((byte == 0) || (g_rx_head == g_rx_tail))
    {
        return 0U;
    }

    *byte = g_rx_buffer[g_rx_tail];
    g_rx_tail = (uint16_t)((g_rx_tail + 1U) % UART_RX_BUFFER_SIZE);
    return 1U;
}

static void uart_drain(uint32_t quiet_ms)
{
    uint8_t byte;
    uint32_t last_rx = APP_GetMillis();

    while ((APP_GetMillis() - last_rx) < quiet_ms)
    {
        if (uart_pop(&byte))
        {
            last_rx = APP_GetMillis();
        }
    }
}

static void at_response_reset(void)
{
    memset(g_at_response, 0, sizeof(g_at_response));
}

static void at_response_append(uint8_t byte)
{
    size_t length = strlen(g_at_response);

    if (length < (AT_RESPONSE_SIZE - 1U))
    {
        g_at_response[length] = (char)byte;
        g_at_response[length + 1U] = '\0';
    }
    else
    {
        memmove(g_at_response, g_at_response + 1, AT_RESPONSE_SIZE - 2U);
        g_at_response[AT_RESPONSE_SIZE - 2U] = (char)byte;
        g_at_response[AT_RESPONSE_SIZE - 1U] = '\0';
    }
}

static uint8_t esp_wait_for(const char *expect, uint32_t timeout_ms)
{
    uint32_t start = APP_GetMillis();
    uint8_t byte;

    while ((APP_GetMillis() - start) < timeout_ms)
    {
        while (uart_pop(&byte))
        {
            at_response_append(byte);

            if (strstr(g_at_response, "ERROR") != 0)
            {
                return 0U;
            }

            if ((expect != 0) && (strstr(g_at_response, expect) != 0))
            {
                return 1U;
            }
        }
    }

    return 0U;
}
