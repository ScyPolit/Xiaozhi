#include "gpio_led.h"

typedef struct
{
    GPIO_TypeDef *port;
    uint16_t pin;
    uint8_t state;
} LED_Channel_t;

static LED_Channel_t g_leds[LED_COUNT] =
{
    {GPIOA, GPIO_PIN_4, LED_STATE_OFF},
    {GPIOA, GPIO_PIN_5, LED_STATE_OFF},
    {GPIOA, GPIO_PIN_6, LED_STATE_OFF},
    {GPIOA, GPIO_PIN_7, LED_STATE_OFF},
    {GPIOB, GPIO_PIN_0, LED_STATE_OFF}
};

static GPIO_PinState LED_ToPinState(uint8_t state)
{
#if LED_ACTIVE_HIGH
    return (state == LED_STATE_ON) ? GPIO_PIN_SET : GPIO_PIN_RESET;
#else
    return (state == LED_STATE_ON) ? GPIO_PIN_RESET : GPIO_PIN_SET;
#endif
}

static uint8_t LED_IsValidId(uint8_t led_id)
{
    return (led_id >= LED_1_ID && led_id <= LED_5_ID) ? 1U : 0U;
}

void LED_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    uint8_t index;

    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();

    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;

    GPIO_InitStruct.Pin = GPIO_PIN_4 | GPIO_PIN_5 | GPIO_PIN_6 | GPIO_PIN_7;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    GPIO_InitStruct.Pin = GPIO_PIN_0;
    HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

    for (index = 0U; index < LED_COUNT; index++)
    {
        g_leds[index].state = LED_STATE_OFF;
        HAL_GPIO_WritePin(g_leds[index].port, g_leds[index].pin, LED_ToPinState(LED_STATE_OFF));
    }
}

void LED_Set(uint8_t led_id, uint8_t state)
{
    uint8_t index;

    if (!LED_IsValidId(led_id))
    {
        return;
    }

    index = led_id - 1U;
    g_leds[index].state = (state != 0U) ? LED_STATE_ON : LED_STATE_OFF;
    HAL_GPIO_WritePin(g_leds[index].port, g_leds[index].pin, LED_ToPinState(g_leds[index].state));
}

void LED_SetAll(uint8_t state)
{
    uint8_t index;

    for (index = 0U; index < LED_COUNT; index++)
    {
        LED_Set(index + 1U, state);
    }
}

uint8_t LED_Get(uint8_t led_id)
{
    if (!LED_IsValidId(led_id))
    {
        return LED_STATE_OFF;
    }

    return g_leds[led_id - 1U].state;
}

void LED_Toggle(uint8_t led_id)
{
    if (!LED_IsValidId(led_id))
    {
        return;
    }

    if (LED_Get(led_id) == LED_STATE_ON)
    {
        LED_Set(led_id, LED_STATE_OFF);
    }
    else
    {
        LED_Set(led_id, LED_STATE_ON);
    }
}
