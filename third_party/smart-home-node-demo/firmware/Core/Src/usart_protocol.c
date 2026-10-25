#include "main.h"
#include "gpio_led.h"

#define UART_RX_BUFFER_SIZE   128U
#define UART_LINE_BUFFER_SIZE 128U

static UART_HandleTypeDef *g_uart = NULL;
static uint8_t g_rx_byte = 0U;
static uint8_t g_rx_line[UART_LINE_BUFFER_SIZE];
static volatile uint16_t g_rx_index = 0U;
static volatile uint8_t g_line_ready = 0U;

static void Protocol_StartReceiveIT(void);
static void Protocol_SendString(const char *text);
static void Protocol_SendOk(void);
static void Protocol_SendErr(void);
static void Protocol_SendStatus(void);
static void Protocol_HandleLine(char *line);
static void Protocol_NormalizeLine(char *line);
static int Protocol_ParseSetCommand(const char *line, uint8_t *led_id, uint8_t *state);
static int Protocol_ParseAllCommand(const char *line, uint8_t *state);

void USART_Protocol_Init(UART_HandleTypeDef *huart)
{
    g_uart = huart;
    g_rx_byte = 0U;
    g_rx_index = 0U;
    g_line_ready = 0U;
    memset(g_rx_line, 0, sizeof(g_rx_line));
    Protocol_StartReceiveIT();
}

void USART_Protocol_Process(void)
{
    char line[UART_LINE_BUFFER_SIZE];

    if (g_line_ready == 0U)
    {
        return;
    }

    __disable_irq();
    strncpy(line, (const char *)g_rx_line, UART_LINE_BUFFER_SIZE - 1U);
    line[UART_LINE_BUFFER_SIZE - 1U] = '\0';
    memset(g_rx_line, 0, sizeof(g_rx_line));
    g_rx_index = 0U;
    g_line_ready = 0U;
    __enable_irq();

    Protocol_NormalizeLine(line);
    Protocol_HandleLine(line);
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if ((g_uart == NULL) || (huart->Instance != g_uart->Instance))
    {
        return;
    }

    if ((g_rx_byte == '\n') || (g_rx_byte == '\r'))
    {
        if (g_rx_index > 0U)
        {
            g_rx_line[g_rx_index] = '\0';
            g_line_ready = 1U;
            g_rx_index = 0U;
        }
    }
    else
    {
        if ((g_line_ready == 0U) && (g_rx_index < (UART_LINE_BUFFER_SIZE - 1U)))
        {
            g_rx_line[g_rx_index++] = g_rx_byte;
        }
        else
        {
            g_rx_index = 0U;
            memset(g_rx_line, 0, sizeof(g_rx_line));
        }
    }

    Protocol_StartReceiveIT();
}

void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart)
{
    if ((g_uart != NULL) && (huart->Instance == g_uart->Instance))
    {
        Protocol_StartReceiveIT();
    }
}

static void Protocol_StartReceiveIT(void)
{
    if (g_uart != NULL)
    {
        HAL_UART_Receive_IT(g_uart, &g_rx_byte, 1U);
    }
}

static void Protocol_SendString(const char *text)
{
    if ((g_uart == NULL) || (text == NULL))
    {
        return;
    }

    HAL_UART_Transmit(g_uart, (uint8_t *)text, (uint16_t)strlen(text), 100U);
}

static void Protocol_SendOk(void)
{
    Protocol_SendString("OK\r\n");
}

static void Protocol_SendErr(void)
{
    Protocol_SendString("ERR\r\n");
}

static void Protocol_SendStatus(void)
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

    Protocol_SendString(buffer);
}

static void Protocol_HandleLine(char *line)
{
    uint8_t led_id = 0U;
    uint8_t state = 0U;

    if ((line == NULL) || (line[0] == '\0'))
    {
        Protocol_SendErr();
        return;
    }

    if (strcmp(line, "STATUS") == 0)
    {
        Protocol_SendStatus();
        return;
    }

    if (Protocol_ParseAllCommand(line, &state) == 1)
    {
        LED_SetAll(state);
        Protocol_SendOk();
        return;
    }

    if (Protocol_ParseSetCommand(line, &led_id, &state) == 1)
    {
        LED_Set(led_id, state);
        Protocol_SendOk();
        return;
    }

    Protocol_SendErr();
}

static void Protocol_NormalizeLine(char *line)
{
    uint16_t i;

    if (line == NULL)
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

static int Protocol_ParseSetCommand(const char *line, uint8_t *led_id, uint8_t *state)
{
    unsigned int id = 0U;
    char state_text[8] = {0};

    if ((line == NULL) || (led_id == NULL) || (state == NULL))
    {
        return 0;
    }

    if (sscanf(line, "SET %u %7s", &id, state_text) != 2)
    {
        return 0;
    }

    if (id < 1U || id > 5U)
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

static int Protocol_ParseAllCommand(const char *line, uint8_t *state)
{
    char state_text[8] = {0};

    if ((line == NULL) || (state == NULL))
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
