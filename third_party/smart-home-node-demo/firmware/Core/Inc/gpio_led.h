#ifndef __GPIO_LED_H__
#define __GPIO_LED_H__

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"

#define LED_ACTIVE_HIGH 1
#define LED_COUNT       5

#define LED_1_ID        1U
#define LED_2_ID        2U
#define LED_3_ID        3U
#define LED_4_ID        4U
#define LED_5_ID        5U

typedef enum
{
    LED_STATE_OFF = 0U,
    LED_STATE_ON  = 1U
} LED_State_t;

void LED_Init(void);
void LED_Set(uint8_t led_id, uint8_t state);
void LED_SetAll(uint8_t state);
uint8_t LED_Get(uint8_t led_id);
void LED_Toggle(uint8_t led_id);

#ifdef __cplusplus
}
#endif

#endif /* __GPIO_LED_H__ */
