# RP2040 Audio Capture + Local STT

Streams 16-bit 16kHz mono PCM from a PCM1808 I2S ADC to the host over USB CDC.
Host runs Vosk STT and publishes text to MQTT (or saves WAV).

## Wiring (PCM1808 -> RP2040-zero)
- PCM1808 DOUT -> GPIO 10 (data)
- PCM1808 BCK  -> GPIO 11 (bit clock)
- PCM1808 LRCK -> GPIO 12 (word select)
- PCM1808 SCK  -> GPIO 13 (system clock, 4.096 MHz via PWM)
- VDD -> 3.3V, GND -> GND
- Analog mic/line-in -> PCM1808 VIN

## Build
```bash
cd /home/sh/rp2040-audio
PICO_SDK_PATH=/home/sh/pico/pico-sdk cmake -B build
cmake --build build
```

## Flash
Copy build/rp2040_audio.uf2 to RPI-RP2 drive.

## Host usage
```bash
# Record 5s and transcribe
python3 tools/capture-stt.py -d 5

# Record and publish to LED matrix
python3 tools/capture-stt.py -d 5 --publish

# Save audio
python3 tools/capture-stt.py -d 5 --save-wav /tmp/audio.wav
```

## Integration with LED Matrix
The STT text is published to MQTT topic `led_matrix/message/set`,
which the matrix HA bridge forwards to the display.
