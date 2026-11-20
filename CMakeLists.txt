cmake_minimum_required(VERSION 3.13)
include(pico_sdk_import.cmake)

project(rp2040_audio C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

add_executable(rp2040_audio main.c)

pico_generate_pio_header(rp2040_audio ${CMAKE_CURRENT_SOURCE_DIR}/i2s_in.pio)

target_link_libraries(rp2040_audio pico_stdlib hardware_pio hardware_pwm)

pico_enable_stdio_usb(rp2040_audio 1)
pico_enable_stdio_uart(rp2040_audio 0)

pico_add_extra_outputs(rp2040_audio)
