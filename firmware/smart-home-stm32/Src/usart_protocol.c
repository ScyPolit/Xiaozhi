#include "usart_protocol.h"
#include "gpio_led.h"

#include <stdint.h>
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

#define USART_SR_RXNE   (1UL << 5)
#define USART_SR_TXE    (1UL << 7)
#define USART_CR1_UE    (1UL << 13)
#define USART_CR1_RE    (1UL << 2)
#define USART_CR1_TE    (1UL << 3)
#define USART_CR1_RXNEIE (1UL << 5)

#define UART_LINE_BUFFER_SIZE 128U
#define SYSTEM_PCLK2_HZ       8000000UL
#define USART1_IRQn_BIT       5U

static volatile uint8_t g_rx_line[UART_LINE_BUFFER_SIZE];
static volatile uint16_t g_rx_index = 0U;
static volatile uint8_t g_line_ready = 0U;

static void usart1_init(void);
static void usart1_send_char(char ch);
static void usart1_send_string(const char *text);
static void protocol_send_ok(void);
static void protocol_send_err(void);
static void protocol_send_status(void);
static void protocol_handle_line(char *line);
static void protocol_normalize_line(char *line);
static int protocol_parse_set(const char *line, uint8_t *led_id, uint8_t *state);
static int protocol_parse_all(const char *line, uint8_t *state);

void USART_Protocol_Init(void)
{
    g_rx_index = 0U;
    g_line_ready = 0U;
    memset((void *)g_rx_line, 0, sizeof(g_rx_line));
    usart1_init();
}

void USART_Protocol_Process(void)
{
    char line[UART_LINE_BUFFER_SIZE];
    uint16_t i;

    if (g_line_ready == 0U)
    {
        return;
    }

    for (i = 0U; i < UART_LINE_BUFFER_SIZE; i++)
    {
        line[i] = (char)g_rx_line[i];
        g_rx_line[i] = 0U;
    }

    g_rx_index = 0U;
    g_line_ready = 0U;

    line[UART_LINE_BUFFER_SIZE - 1U] = '\0';
    protocol_normalize_line(line);
    protocol_handle_line(line);
}

void USART_Protocol_RxByte(unsigned char byte)
{
    if (byte == '\r')
    {
        return;
    }

    if (byte == '\n')
    {
        if (g_rx_index > 0U)
        {
            g_rx_line[g_rx_index] = '\0';
            g_line_ready = 1U;
        }
        return;
    }

    if (g_line_ready != 0U)
    {
        return;
    }

    if (g_rx_index < (UART_LINE_BUFFER_SIZE - 1U))
    {
        g_rx_line[g_rx_index++] = byte;
    }
    else
    {
        g_rx_index = 0U;
        memset((void *)g_rx_line, 0, sizeof(g_rx_line));
    }
}

void USART1_IRQHandler(void)
{
    if ((USART1_SR & USART_SR_RXNE) != 0U)
    {
        USART_Protocol_RxByte((unsigned char)(USART1_DR & 0xFFU));
    }
}

static void usart1_init(void)
{
    RCC_APB2ENR |= (1UL << 2);   /* IOPAEN */
    RCC_APB2ENR |= (1UL << 14);  /* USART1EN */

    /* PA9 TX: AF Push-Pull 50MHz => 0xB, PA10 RX: floating input => 0x4 */
    GPIOA_CRH &= ~((0xFUL << 4) | (0xFUL << 8));
    GPIOA_CRH |=  ((0xBUL << 4) | (0x4UL << 8));

    USART1_CR1 = 0U;
    USART1_CR2 = 0U;
    USART1_CR3 = 0U;
    USART1_BRR = (SYSTEM_PCLK2_HZ + (115200UL / 2UL)) / 115200UL;
    USART1_CR1 = USART_CR1_UE | USART_CR1_RE | USART_CR1_TE | USART_CR1_RXNEIE;

    NVIC_ISER1 = (1UL << USART1_IRQn_BIT);
}

static void usart1_send_char(char ch)
{
    while ((USART1_SR & USART_SR_TXE) == 0U)
    {
    }

    USART1_DR = (uint32_t)ch;
}

static void usart1_send_string(const char *text)
{
    if (text == 0)
    {
        return;
    }

    while (*text != '\0')
    {
        usart1_send_char(*text++);
    }
}

static void protocol_send_ok(void)
{
    usart1_send_string("OK\r\n");
}

static void protocol_send_err(void)
{
    usart1_send_string("ERR\r\n");
}

static void protocol_send_status(void)
{
    char buffer[96];

    snprintf(buffer,
             sizeof(buffer),
             "STATUS 1:%s 2:%s 3:%s 4:%s 5:%s\r\n",
             (LED_Get(1U) == LED_STATE_ON) ? "ON" : "OFF",
             (LED_Get(2U) == LED_STATE_ON) ? "ON" : "OFF",
             (LED_Get(3U) == LED_STATE_ON) ? "ON" : "OFF",
             (LED_Get(4U) == LED_STATE_ON) ? "ON" : "OFF",
             (LED_Get(5U) == LED_STATE_ON) ? "ON" : "OFF");

    usart1_send_string(buffer);
}

static void protocol_handle_line(char *line)
{
    uint8_t led_id = 0U;
    uint8_t state = 0U;

    if ((line == 0) || (line[0] == '\0'))
    {
        protocol_send_err();
        return;
    }

    if (strcmp(line, "STATUS") == 0)
    {
        protocol_send_status();
        return;
    }

    if (protocol_parse_all(line, &state) == 1)
    {
        LED_SetAll(state);
        protocol_send_ok();
        return;
    }

    if (protocol_parse_set(line, &led_id, &state) == 1)
    {
        LED_Set(led_id, state);
        protocol_send_ok();
        return;
    }

    protocol_send_err();
}

static void protocol_normalize_line(char *line)
{
    uint16_t i;

    if (line == 0)
    {
        return;
    }

    for (i = 0U; line[i] != '\0'; i++)
    {
        if (line[i] >= 'a' && line[i] <= 'z')
        {
            line[i] = (char)(line[i] - ('a' - 'A'));
        }
    }
}

static int protocol_parse_set(const char *line, uint8_t *led_id, uint8_t *state)
{
    unsigned int id = 0U;
    char state_text[8] = {0};

    if ((line == 0) || (led_id == 0) || (state == 0))
    {
        return 0;
    }

    if (sscanf(line, "SET %u %7s", &id, state_text) != 2)
    {
        return 0;
    }

    if ((id < 1U) || (id > 5U))
    {
        return 0;
    }

    if (strcmp(state_text, "ON") == 0)
    {
        *state = LED_STATE_ON;
    }
    else if (strcmp(state_text, "OFF") == 0)
    {
        *state = LED_STATE_OFF;
    }
    else
    {
        return 0;
    }

    *led_id = (uint8_t)id;
    return 1;
}

static int protocol_parse_all(const char *line, uint8_t *state)
{
    char state_text[8] = {0};

    if ((line == 0) || (state == 0))
    {
        return 0;
    }

    if (sscanf(line, "ALL %7s", state_text) != 1)
    {
        return 0;
    }

    if (strcmp(state_text, "ON") == 0)
    {
        *state = LED_STATE_ON;
        return 1;
    }

    if (strcmp(state_text, "OFF") == 0)
    {
        *state = LED_STATE_OFF;
        return 1;
    }

    return 0;
}
