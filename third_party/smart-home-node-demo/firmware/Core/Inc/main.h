#ifndef __MAIN_H__
#define __MAIN_H__

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdio.h>
#include <string.h>

/*
 * 说明：
 * 1. 本头文件采用 HAL 风格组织。
 * 2. 实际工程中请确保 STM32CubeMX 生成的 main.h 中包含 stm32xxxx_hal.h。
 * 3. 如果你使用的是 STM32F103C8T6，可将下面的头文件替换为 stm32f1xx_hal.h。
 * 4. 如果你使用的是 STM32F401RE，可将下面的头文件替换为 stm32f4xx_hal.h。
 */
#include "stm32f1xx_hal.h"

void Error_Handler(void);

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H__ */
