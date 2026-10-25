#include "application.h"

#include <cstring>
#include <esp_log.h>

#define TAG "XiaozhiBridge"

extern "C" void xiaozhi_app_chat_action(const char *action)
{
    auto &app = Application::GetInstance();
    const char *safe_action = (action == nullptr || action[0] == '\0') ? "toggle" : action;

    if (strcmp(safe_action, "start") == 0)
    {
        auto state = app.GetDeviceState();
        if (state == kDeviceStateIdle || state == kDeviceStateActivating)
        {
            ESP_LOGI(TAG, "HTTP chat action: start");
            app.ToggleChatState();
        }
        return;
    }

    if (strcmp(safe_action, "listen") == 0)
    {
        ESP_LOGI(TAG, "HTTP chat action: listen");
        app.StartListening();
        return;
    }

    if (strcmp(safe_action, "stop") == 0)
    {
        ESP_LOGI(TAG, "HTTP chat action: stop");
        app.StopListening();
        return;
    }

    if (strcmp(safe_action, "abort") == 0)
    {
        ESP_LOGI(TAG, "HTTP chat action: abort");
        app.Schedule([&app]() {
            app.AbortSpeaking(kAbortReasonNone);
        });
        return;
    }

    ESP_LOGI(TAG, "HTTP chat action: toggle");
    app.ToggleChatState();
}
