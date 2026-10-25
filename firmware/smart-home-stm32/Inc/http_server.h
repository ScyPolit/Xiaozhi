#ifndef HTTP_SERVER_H
#define HTTP_SERVER_H

#include <stdint.h>

void HTTP_Server_HandleRequest(uint8_t connection_id, const char *request, uint16_t length);
void HTTP_SendJson(uint8_t connection_id, int status_code, const char *json);

#endif /* HTTP_SERVER_H */
