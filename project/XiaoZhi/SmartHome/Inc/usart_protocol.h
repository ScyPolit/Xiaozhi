#ifndef USART_PROTOCOL_H
#define USART_PROTOCOL_H

void USART_Protocol_Init(void);
void USART_Protocol_Process(void);
void USART_Protocol_RxByte(unsigned char byte);

#endif /* USART_PROTOCOL_H */
