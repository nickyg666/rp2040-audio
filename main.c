#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "pico/stdlib.h"
#include "pico/time.h"
#include "hardware/pio.h"
#include "hardware/clocks.h"
#include "hardware/pwm.h"
#include "tusb.h"
#include "i2s_in.pio.h"

#define SAMPLE_RATE     16000
#define AUDIO_PIN_DATA  10  /* I2S DIN from PCM1808 */
#define AUDIO_PIN_BCK   11  /* I2S BCK (bit clock) */
#define AUDIO_PIN_LRCK  12  /* I2S LRCK (word select) */
#define AUDIO_PIN_SCK   13  /* System clock for PCM1808 (PWM) */
#define CHUNK_SIZE      512  /* bytes per USB write */

static PIO  audio_pio;
static uint audio_sm;

/* Generate system clock (SCK) for PCM1808 via PWM */
static void sck_init(void) {
    gpio_set_function(AUDIO_PIN_SCK, GPIO_FUNC_PWM);
    uint slice = pwm_gpio_to_slice_num(AUDIO_PIN_SCK);
    /* SCK = 256 * fs = 4.096 MHz */
    uint32_t sys_clk = clock_get_hz(clk_sys);
    uint32_t top = sys_clk / (SAMPLE_RATE * 256) - 1;
    if (top > 65535) top = 65535;
    pwm_set_wrap(slice, top);
    pwm_set_chan_level(slice, pwm_gpio_to_channel(AUDIO_PIN_SCK), top / 2);
    pwm_set_enabled(slice, true);
}

/* I2S capture init */
static void i2s_init(void) {
    audio_pio = pio0;
    audio_sm = 1;  /* use SM 1 to leave SM 0 free */
    uint offset = pio_add_program(audio_pio, &i2s_in_program);
    i2s_in_program_init(audio_pio, audio_sm, offset, SAMPLE_RATE,
                        AUDIO_PIN_DATA, AUDIO_PIN_BCK);
}

int main(void) {
    stdio_init_all();
    sleep_ms(500);

    sck_init();
    sleep_ms(100);  /* let PCM1808 stabilize */
    i2s_init();

    printf("RP2040 Audio Capture ready (16kHz 16-bit mono)\n");
    printf("Streaming raw PCM over USB CDC\n");
    fflush(stdout);

    /* Stream audio: read 32-bit I2S words, convert to 16-bit PCM */
    while (true) {
        /* Wait for data in RX FIFO */
        if (!pio_sm_is_rx_fifo_empty(audio_pio, audio_sm)) {
            uint32_t word = pio_sm_get(audio_pio, audio_sm);
            /* Take top 16 bits (24-bit ADC, shift right 8 then take 16) */
            int16_t sample = (int16_t)(word >> 16);
            /* Write as little-endian 16-bit */
            uint8_t buf[2];
            buf[0] = (uint8_t)(sample & 0xFF);
            buf[1] = (uint8_t)((sample >> 8) & 0xFF);
            /* Batch writes */
            static uint8_t outbuf[CHUNK_SIZE];
            static int outpos = 0;
            outbuf[outpos++] = buf[0];
            outbuf[outpos++] = buf[1];
            if (outpos >= CHUNK_SIZE) {
                if (stdio_usb_connected()) {
                    for (int i = 0; i < outpos; ) {
                        int n = outpos - i;
                        int avail = (int)tud_cdc_write_available();
                        if (n > avail) n = avail;
                        if (n > 0) {
                            tud_cdc_write(outbuf + i, (uint32_t)n);
                            tud_task();
                            tud_cdc_write_flush();
                            i += n;
                        } else {
                            tud_task();
                        }
                    }
                }
                outpos = 0;
            }
        } else {
            tight_loop_contents();
        }
    }
    return 0;
}
