#ifndef ESP8266_AT_H
#define ESP8266_AT_H

#include <stdint.h>

uint8_t ESP8266_Init(void);
uint8_t ESP8266_SendCommand(const char *cmd, const char *expect, uint32_t timeout_ms);
uint8_t ESP8266_ConnectWiFi(const char *ssid, const char *password);
uint8_t ESP8266_StartServer(uint16_t port);
uint8_t ESP8266_SetHostname(const char *hostname);
uint8_t ESP8266_SendHttpResponse(uint8_t connection_id, const char *response);
void ESP8266_UART_RxCallback(uint8_t byte);
void ESP8266_Process(void);
uint8_t ESP8266_IsReady(void);

#endif /* ESP8266_AT_H */
