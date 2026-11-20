#!/usr/bin/env python3
"""Capture audio from RP2040 and run local STT (Vosk)."""
import argparse
import io
import json
import os
import select
import sys
import termios
import time
import wave

import numpy as np
import paho.mqtt.client as mqtt
from vosk import KaldiRecognizer, Model

SAMPLE_RATE = 16000
CHANNELS = 1
MODEL_PATH = os.getenv("MODEL_PATH", "/home/sh/ledmatrix/models/vosk-en-us")
MQTT_HOST = os.getenv("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
NODE_ID = os.getenv("NODE_ID", "led_matrix")
DEVICE = None


def find_device():
    global DEVICE
    if os.path.exists("/dev/rp2040-audio"):
        DEVICE = "/dev/rp2040-audio"
        return DEVICE
    import glob
    for p in sorted(glob.glob("/dev/ttyACM*")):
        # Try to identify by reading
        DEVICE = p
        return p
    return None


def open_serial(dev):
    fd = os.open(dev, os.O_RDWR | os.O_NOCTTY)
    attrs = termios.tcgetattr(fd)
    attrs[1] = termios.OPOST | termios.ONLCR
    attrs[3] = termios.CREAD | termios.CLOCAL
    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 1
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    return fd


def record_audio(fd, duration):
    """Read raw PCM from RP2040 for given duration."""
    data = bytearray()
    target = SAMPLE_RATE * 2 * duration  # 16-bit = 2 bytes per sample
    start = time.time()
    while time.time() - start < duration:
        r, _, _ = select.select([fd], [], [], 0.1)
        if r:
            n = os.read(fd, 4096)
            if n:
                data.extend(n)
                if len(data) >= target:
                    break
    return bytes(data[:target])


def transcribe(pcm_data):
    rec = KaldiRecognizer(Model(MODEL_PATH), SAMPLE_RATE)
    rec.SetWords(False)
    chunks = []
    for i in range(0, len(pcm_data), 4000):
        if rec.AcceptWaveform(pcm_data[i:i + 4000]):
            r = json.loads(rec.Result())
            if r.get("text"):
                chunks.append(r["text"])
    final = json.loads(rec.FinalResult())
    if final.get("text"):
        chunks.append(final["text"])
    return " ".join(chunks).strip()


def main():
    ap = argparse.ArgumentParser(description="RP2040 audio capture + STT")
    ap.add_argument("-d", "--duration", type=int, default=5, help="Recording duration in seconds")
    ap.add_argument("-D", "--device", help="Serial device (auto-detected)")
    ap.add_argument("--publish", action="store_true", help="Publish text to MQTT matrix topic")
    ap.add_argument("--save-wav", help="Save captured audio to WAV file")
    args = ap.parse_args()

    dev = args.device or find_device()
    if not dev:
        print("No RP2040 audio device found", file=sys.stderr)
        sys.exit(1)
    print(f"Device: {dev}, recording {args.duration}s...")
    fd = open_serial(dev)
    pcm = record_audio(fd, args.duration)
    os.close(fd)
    print(f"Captured {len(pcm)} bytes ({len(pcm)/2/SAMPLE_RATE:.1f}s)")

    if args.save_wav:
        import wave
        w = wave.open(args.save_wav, "wb")
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)
        w.close()
        print(f"Saved: {args.save_wav}")

    text = transcribe(pcm)
    print(f"STT: {text}")

    if args.publish and text:
        mq = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        mq.connect(MQTT_HOST, MQTT_PORT, 60)
        mq.publish("%s/message/set" % NODE_ID, text)
        mq.disconnect()
        print(f"Published to {NODE_ID}/message/set")


if __name__ == "__main__":
    main()
EOF
chmod +x /home/sh/rp2040-audio/tools/capture-stt.py
mkdir -p /home/sh/rp2040-audio/tools
mv /home/sh/rp2040-audio/tools/capture-stt.py /home/sh/rp2040-audio/tools/capture-stt.py 2>/dev/null
mkdir -p /home/sh/rp2040-audio/tools
cat > /home/sh/rp2040-audio/tools/capture-stt.py <<'PYEOF'
#!/usr/bin/env python3
"""Capture audio from RP2040 and run local STT (Vosk)."""
import argparse
import io
import json
import os
import select
import sys
import termios
import time
import wave

import numpy as np
import paho.mqtt.client as mqtt
from vosk import KaldiRecognizer, Model

SAMPLE_RATE = 16000
MODEL_PATH = os.getenv("MODEL_PATH", "/home/sh/ledmatrix/models/vosk-en-us")
MQTT_HOST = os.getenv("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
NODE_ID = os.getenv("NODE_ID", "led_matrix")


def find_device():
    for p in ("/dev/rp2040-audio",):
        if os.path.exists(p):
            return p
    import glob
    ds = sorted(glob.glob("/dev/ttyACM*"))
    return ds[0] if ds else None


def open_serial(dev):
    fd = os.open(dev, os.O_RDWR | os.O_NOCTTY)
    attrs = termios.tcgetattr(fd)
    attrs[1] = termios.OPOST | termios.ONLCR
    attrs[3] = termios.CREAD | termios.CLOCAL
    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 1
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    return fd


def record_audio(fd, duration):
    data = bytearray()
    target = SAMPLE_RATE * 2 * duration
    start = time.time()
    while time.time() - start < duration:
        r, _, _ = select.select([fd], [], [], 0.1)
        if r:
            n = os.read(fd, 4096)
            if n:
                data.extend(n)
                if len(data) >= target:
                    break
    return bytes(data[:target])


def transcribe(pcm_data):
    rec = KaldiRecognizer(Model(MODEL_PATH), SAMPLE_RATE)
    rec.SetWords(False)
    chunks = []
    for i in range(0, len(pcm_data), 4000):
        if rec.AcceptWaveform(pcm_data[i:i + 4000]):
            r = json.loads(rec.Result())
            if r.get("text"):
                chunks.append(r["text"])
    final = json.loads(rec.FinalResult())
    if final.get("text"):
        chunks.append(final["text"])
    return " ".join(chunks).strip()


def main():
    ap = argparse.ArgumentParser(description="RP2040 audio capture + STT")
    ap.add_argument("-d", "--duration", type=int, default=5, help="Recording duration in seconds")
    ap.add_argument("-D", "--device", help="Serial device (auto-detected)")
    ap.add_argument("--publish", action="store_true", help="Publish text to MQTT matrix topic")
    ap.add_argument("--save-wav", help="Save captured audio to WAV file")
    args = ap.parse_args()

    dev = args.device or find_device()
    if not dev:
        print("No RP2040 audio device found", file=sys.stderr)
        sys.exit(1)
    print(f"Device: {dev}, recording {args.duration}s...")
    fd = open_serial(dev)
    pcm = record_audio(fd, args.duration)
    os.close(fd)
    print(f"Captured {len(pcm)} bytes ({len(pcm)/2/SAMPLE_RATE:.1f}s)")

    if args.save_wav:
        w = wave.open(args.save_wav, "wb")
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)
        w.close()
        print(f"Saved: {args.save_wav}")

    text = transcribe(pcm)
    print(f"STT: {text}")

    if args.publish and text:
        mq = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        mq.connect(MQTT_HOST, MQTT_PORT, 60)
        mq.publish("%s/message/set" % NODE_ID, text)
        mq.disconnect()
        print(f"Published to {NODE_ID}/message/set")


if __name__ == "__main__":
    main()
PYEOF
python3 -m py_compile /home/sh/rp2040-audio/tools/capture-stt.py && echo "ok"