#ifndef GPIO_LED_H
#define GPIO_LED_H

#include <stdint.h>

#define LED_ACTIVE_HIGH 1
#define LED_COUNT       6U

#define LED_STATE_OFF   0U
#define LED_STATE_ON    1U

#define LED_1_ID        1U
#define LED_2_ID        2U
#define LED_3_ID        3U
#define LED_4_ID        4U
#define LED_5_ID        5U
#define LED_6_ID        6U

const char *LED_GetName(uint8_t led_id);
const char *LED_GetPinName(uint8_t led_id);
void LED_Init(void);
void LED_Set(uint8_t led_id, uint8_t state);
void LED_SetAll(uint8_t state);
uint8_t LED_Get(uint8_t led_id);
void LED_Toggle(uint8_t led_id);
void LED_Process(void);

#endif /* GPIO_LED_H */
