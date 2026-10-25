#include "gpio_led.h"
#include <stdint.h>

#define RCC_BASE        0x40021000UL
#define AFIO_BASE       0x40010000UL
#define GPIOA_BASE      0x40010800UL
#define GPIOB_BASE      0x40010C00UL

#define RCC_APB2ENR     (*(volatile uint32_t *)(RCC_BASE + 0x18U))
#define AFIO_MAPR       (*(volatile uint32_t *)(AFIO_BASE + 0x04U))

#define RCC_APB2ENR_AFIOEN  (1UL << 0)
#define AFIO_MAPR_SWJ_MASK  (7UL << 24)
#define AFIO_MAPR_SWJ_NOJTAG_SWDP (2UL << 24)

typedef struct
{
    volatile uint32_t CRL;
    volatile uint32_t CRH;
    volatile uint32_t IDR;
    volatile uint32_t ODR;
    volatile uint32_t BSRR;
    volatile uint32_t BRR;
    volatile uint32_t LCKR;
} GPIO_TypeDef;

typedef enum
{
    GPIO_PIN_RESET = 0,
    GPIO_PIN_SET
} GPIO_PinState;

#define GPIOA           ((GPIO_TypeDef *)GPIOA_BASE)
#define GPIOB           ((GPIO_TypeDef *)GPIOB_BASE)
#define GPIO_PIN_0      ((uint16_t)0x0001U)
#define GPIO_PIN_4      ((uint16_t)0x0010U)
#define GPIO_PIN_5      ((uint16_t)0x0020U)
#define GPIO_PIN_6      ((uint16_t)0x0040U)
#define GPIO_PIN_7      ((uint16_t)0x0080U)
#define GPIO_PIN_15     ((uint16_t)0x8000U)
#define AC_BUZZ_ON_MS       1000UL
#define AC_BUZZ_OFF_MS      200UL
#define AC_BUZZ_GAP_MS      400UL

extern uint32_t APP_GetMillis(void);

typedef struct
{
    GPIO_TypeDef *port;
    uint16_t pin;
    const char *name;
    const char *pin_name;
    uint8_t state;
} led_channel_t;

typedef enum
{
    BUZZER_PATTERN_IDLE = 0,
    BUZZER_PATTERN_ON_1S,
    BUZZER_PATTERN_OFF_BEEP_1,
    BUZZER_PATTERN_OFF_GAP,
    BUZZER_PATTERN_OFF_BEEP_2
} buzzer_pattern_t;

static led_channel_t g_leds[LED_COUNT] =
{
    {GPIOA, GPIO_PIN_4, "\\u5ba2\\u5385\\u706f", "PA4", LED_STATE_OFF},
    {GPIOA, GPIO_PIN_5, "\\u5367\\u5ba4\\u706f", "PA5", LED_STATE_OFF},
    {GPIOA, GPIO_PIN_6, "\\u53a8\\u623f\\u706f", "PA6", LED_STATE_OFF},
    {GPIOA, GPIO_PIN_7, "\\u536b\\u751f\\u95f4\\u706f", "PA7", LED_STATE_OFF},
    {GPIOB, GPIO_PIN_0, "\\u68b3\\u5986\\u53f0\\u706f", "PB0", LED_STATE_OFF},
    {GPIOA, GPIO_PIN_15, "\\u7a7a\\u8c03", "PA15", LED_STATE_OFF}
};

static buzzer_pattern_t g_buzzer_pattern = BUZZER_PATTERN_IDLE;
static uint32_t g_buzzer_next_tick = 0U;

static uint8_t led_is_valid(uint8_t led_id)
{
    return (led_id >= LED_1_ID && led_id <= LED_6_ID) ? 1U : 0U;
}

static void HAL_GPIO_WritePin(GPIO_TypeDef *GPIOx, uint16_t GPIO_Pin, GPIO_PinState PinState)
{
    if (PinState == GPIO_PIN_SET)
    {
        GPIOx->BSRR = GPIO_Pin;
    }
    else
    {
        GPIOx->BRR = GPIO_Pin;
    }
}

static void led_write_pin(led_channel_t *led, uint8_t state)
{
    GPIO_PinState pin_state;

    if (led == 0)
    {
        return;
    }

#if LED_ACTIVE_HIGH
    pin_state = (state == LED_STATE_ON) ? GPIO_PIN_SET : GPIO_PIN_RESET;
#else
    pin_state = (state == LED_STATE_ON) ? GPIO_PIN_RESET : GPIO_PIN_SET;
#endif
    HAL_GPIO_WritePin(led->port, led->pin, pin_state);
}

static uint8_t time_reached(uint32_t deadline)
{
    return ((uint32_t)(APP_GetMillis() - deadline) < 0x80000000UL) ? 1U : 0U;
}

static void ac_buzzer_write(uint8_t state)
{
    led_write_pin(&g_leds[LED_6_ID - 1U], state);
}

static void ac_buzzer_start_pattern(uint8_t logical_state)
{
    if (logical_state == LED_STATE_ON)
    {
        g_buzzer_pattern = BUZZER_PATTERN_ON_1S;
        ac_buzzer_write(LED_STATE_ON);
        g_buzzer_next_tick = APP_GetMillis() + AC_BUZZ_ON_MS;
    }
    else
    {
        g_buzzer_pattern = BUZZER_PATTERN_OFF_BEEP_1;
        ac_buzzer_write(LED_STATE_ON);
        g_buzzer_next_tick = APP_GetMillis() + AC_BUZZ_OFF_MS;
    }
}

void LED_Init(void)
{
    uint8_t index;

    RCC_APB2ENR |= RCC_APB2ENR_AFIOEN;
    RCC_APB2ENR |= (1UL << 2);  /* IOPAEN */
    RCC_APB2ENR |= (1UL << 3);  /* IOPBEN */

    /* PA15 is JTDI by default. Disable JTAG and keep SWD enabled. */
    AFIO_MAPR = (AFIO_MAPR & ~AFIO_MAPR_SWJ_MASK) | AFIO_MAPR_SWJ_NOJTAG_SWDP;

    /* PA4..PA7 and PB0: general push-pull output, 2 MHz. */
    GPIOA->CRL &= ~((0xFUL << 16) | (0xFUL << 20) | (0xFUL << 24) | (0xFUL << 28));
    GPIOA->CRL |=  ((0x2UL << 16) | (0x2UL << 20) | (0x2UL << 24) | (0x2UL << 28));
    GPIOB->CRL &= ~(0xFUL << 0);
    GPIOB->CRL |=  (0x2UL << 0);

    /* PA15 buzzer/AC simulator: general push-pull output, 2 MHz. */
    GPIOA->CRH &= ~(0xFUL << 28);
    GPIOA->CRH |=  (0x2UL << 28);

    for (index = 0U; index < LED_COUNT; index++)
    {
        g_leds[index].state = LED_STATE_OFF;
        led_write_pin(&g_leds[index], LED_STATE_OFF);
    }

    g_buzzer_pattern = BUZZER_PATTERN_IDLE;
    g_buzzer_next_tick = 0U;
}

const char *LED_GetName(uint8_t led_id)
{
    if (!led_is_valid(led_id))
    {
        return "";
    }

    return g_leds[led_id - 1U].name;
}

const char *LED_GetPinName(uint8_t led_id)
{
    if (!led_is_valid(led_id))
    {
        return "";
    }

    return g_leds[led_id - 1U].pin_name;
}

void LED_Set(uint8_t led_id, uint8_t state)
{
    uint8_t index;

    if (!led_is_valid(led_id))
    {
        return;
    }

    index = (uint8_t)(led_id - 1U);
    g_leds[index].state = (state != 0U) ? LED_STATE_ON : LED_STATE_OFF;

    if (led_id == LED_6_ID)
    {
        ac_buzzer_start_pattern(g_leds[index].state);
    }
    else
    {
        led_write_pin(&g_leds[index], g_leds[index].state);
    }
}

void LED_SetAll(uint8_t state)
{
    uint8_t index;

    for (index = 0U; index < LED_COUNT; index++)
    {
        LED_Set((uint8_t)(index + 1U), state);
    }
}

uint8_t LED_Get(uint8_t led_id)
{
    if (!led_is_valid(led_id))
    {
        return LED_STATE_OFF;
    }

    return g_leds[led_id - 1U].state;
}

void LED_Toggle(uint8_t led_id)
{
    if (!led_is_valid(led_id))
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

void LED_Process(void)
{
    if (g_buzzer_pattern == BUZZER_PATTERN_IDLE)
    {
        return;
    }

    if (!time_reached(g_buzzer_next_tick))
    {
        return;
    }

    switch (g_buzzer_pattern)
    {
        case BUZZER_PATTERN_ON_1S:
            ac_buzzer_write(LED_STATE_OFF);
            g_buzzer_pattern = BUZZER_PATTERN_IDLE;
            break;

        case BUZZER_PATTERN_OFF_BEEP_1:
            ac_buzzer_write(LED_STATE_OFF);
            g_buzzer_pattern = BUZZER_PATTERN_OFF_GAP;
            g_buzzer_next_tick = APP_GetMillis() + AC_BUZZ_GAP_MS;
            break;

        case BUZZER_PATTERN_OFF_GAP:
            ac_buzzer_write(LED_STATE_ON);
            g_buzzer_pattern = BUZZER_PATTERN_OFF_BEEP_2;
            g_buzzer_next_tick = APP_GetMillis() + AC_BUZZ_OFF_MS;
            break;

        case BUZZER_PATTERN_OFF_BEEP_2:
        default:
            ac_buzzer_write(LED_STATE_OFF);
            g_buzzer_pattern = BUZZER_PATTERN_IDLE;
            break;
    }
}
