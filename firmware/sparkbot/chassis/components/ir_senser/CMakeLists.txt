idf_component_register(SRCS "ir_senser.c"
                    INCLUDE_DIRS "include"
                    REQUIRES power_management
                    PRIV_REQUIRES esp_adc driver)
