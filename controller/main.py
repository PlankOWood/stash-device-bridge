import serial
import serial.tools.list_ports
import time
import json
import os
import threading
import asyncio
import websockets

UPDATE_RATE = 1/100
DEADBAND = 2

VIDEO_TIME_MS = 0

loader = None
engine = None
device = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_DIR = os.path.join(BASE_DIR, "profiles")

os.makedirs(PROFILE_DIR, exist_ok=True)

print("Profile directory:", PROFILE_DIR)

# -------------------------------------------------
# DEFAULT AXIS RANGES
# -------------------------------------------------

DEFAULT_RANGES = {
    "stroke": {"min":200,"max":800},
    "sway": {"min":200,"max":800},
    "surge": {"min":200,"max":800},
    "twist": {"min":300,"max":700},
    "roll": {"min":300,"max":700},
    "pitch": {"min":300,"max":700}
}

# -------------------------------------------------
# FRAME BUFFER
# -------------------------------------------------

frame_buffer = {}
test_override = {}

# -------------------------------------------------
# CHANNEL DETECTION
# -------------------------------------------------

def detect_channel(filename):

    name = filename.lower()

    if "stroke" in name:
        return "stroke"
    if "sway" in name:
        return "sway"
    if "surge" in name:
        return "surge"
    if "twist" in name:
        return "twist"
    if "roll" in name:
        return "roll"
    if "pitch" in name:
        return "pitch"

    return "stroke"

# -------------------------------------------------
# WEBSOCKET SERVER
# -------------------------------------------------

async def time_server(websocket):

    global VIDEO_TIME_MS
    global device
    global test_override

    async for message in websocket:

        data = json.loads(message)

        if "time" in data:
            VIDEO_TIME_MS = data["time"]
            continue

        if "scene" in data:
            load_scene_scripts(data["scene"])
            continue

        command = data.get("command")

        # -----------------------------
        # GET CURRENT STATUS (NEW)
        # -----------------------------

        if command == "get_status":

            if device:

                await websocket.send(json.dumps({
                    "type": "device_connected",
                    "name": device["profile"]["name"],
                    "ranges": device["ranges"]
                }))

        # -----------------------------
        # SCAN DEVICES
        # -----------------------------

        elif command == "scan_devices":

            ports = list(serial.tools.list_ports.comports())
            profiles = load_profiles()

            devices = []

            for port in ports:

                profile_name = None

                for profile in profiles:
                    if profile["connection"]["port"] == port.device:
                        profile_name = profile["name"]

                devices.append({
                    "port": port.device,
                    "name": profile_name
                })

            await websocket.send(json.dumps({
                "type": "device_list",
                "devices": devices
            }))

        # -----------------------------
        # CONNECT DEVICE
        # -----------------------------

        elif command == "connect_device":

            port = data.get("port")

            profiles = load_profiles()

            for profile in profiles:

                if profile["connection"]["port"] == port:

                    device_connect(profile)

                    await websocket.send(json.dumps({
                        "type": "device_profile",
                        "ranges": device["ranges"]
                    }))

                    break

        # -----------------------------
        # TEST RANGE
        # -----------------------------

        elif command == "test_range":

            channel = data.get("channel")
            value = data.get("value")

            test_override[channel] = int(value)

        elif command == "clear_override":

            channel = data.get("channel")

            if channel in test_override:
                del test_override[channel]

        # -----------------------------
        # SET RANGE
        # -----------------------------

        elif command == "set_range":

            channel = data.get("channel")
            min_v = data.get("min")
            max_v = data.get("max")

            if device:

                device["ranges"][channel] = {
                    "min": min_v,
                    "max": max_v
                }

        # -----------------------------
        # SAVE PROFILE
        # -----------------------------

        elif command == "save_profile":

            if device:

                path = os.path.join(PROFILE_DIR, f"{device['profile']['name']}.json")

                device["profile"]["ranges"] = device["ranges"]

                with open(path, "w") as f:
                    json.dump(device["profile"], f, indent=4)

                print("Profile saved:", path)

        # -----------------------------
        # MOVE TO MIDDLE
        # -----------------------------

        elif command == "move_to_middle":

            if device:

                mapping = device["mapping"]
                ranges = device["ranges"]

                test_override.clear()

                for channel in mapping:

                    r = ranges.get(channel, DEFAULT_RANGES[channel])

                    mid = int((r["min"] + r["max"]) / 2)

                    frame_buffer[channel] = (mid / 999) * 100

# -------------------------------------------------
# SERVER
# -------------------------------------------------

def start_ws_server():

    async def server():

        async with websockets.serve(time_server, "localhost", 5757):

            print("WebSocket server running on port 5757")

            await asyncio.Future()

    asyncio.run(server())

# -------------------------------------------------
# DEVICE
# -------------------------------------------------

def device_connect(profile):

    global device

    port = profile["connection"]["port"]

    ser = serial.Serial(
        port,
        115200,
        timeout=0,
        write_timeout=0
    )

    time.sleep(2)

    ranges = profile.get("ranges")

    if not ranges:
        ranges = DEFAULT_RANGES.copy()

    device = {
        "ser": ser,
        "mapping": profile["mapping"],
        "ranges": ranges,
        "profile": profile
    }

    print("Connected:", profile["name"])

# -------------------------------------------------
# DEVICE WRITER (WITH SMOOTHING)
# -------------------------------------------------

def device_writer():

    global device
    global frame_buffer
    global test_override

    last_sent = {}
    current_values = {}

    MAX_STEP = 15

    while True:

        if not device:
            time.sleep(.1)
            continue

        ser = device["ser"]
        mapping = device["mapping"]
        ranges = device["ranges"]

        commands = []

        for channel, axis in mapping.items():

            if channel in test_override:

                target = int(test_override[channel])

            else:

                pos = frame_buffer.get(channel, 50)

                r = ranges.get(channel, DEFAULT_RANGES[channel])

                target = int(r["min"] + (pos / 100) * (r["max"] - r["min"]))

            target = max(0, min(999, target))

            current = current_values.get(axis, target)

            delta = target - current

            if abs(delta) > MAX_STEP:
                current += MAX_STEP if delta > 0 else -MAX_STEP
            else:
                current = target

            current = int(current)
            current_values[axis] = current

            if last_sent.get(axis) != current:

                commands.append(f"{axis}{current:03d}")
                last_sent[axis] = current

        if commands:

            for cmd in commands:
                try:
                    ser.write((cmd + "\n").encode())
                except:
                    pass

        time.sleep(UPDATE_RATE)

# -------------------------------------------------
# SCRIPT LOADER
# -------------------------------------------------

def load_scene_scripts(scene_path):

    global loader, engine, frame_buffer

    folder = os.path.dirname(scene_path)
    name = os.path.splitext(os.path.basename(scene_path))[0]

    loader.channels = {}
    frame_buffer.clear()

    print("Loading scripts:", name)

    for file in os.listdir(folder):

        if not file.endswith(".funscript"):
            continue

        if not file.startswith(name):
            continue

        path = os.path.join(folder, file)

        channel = detect_channel(file)

        with open(path) as f:
            data = json.load(f)

        loader.channels[channel] = data["actions"]

        print("Loaded channel:", channel)

    engine.build_timelines()

# -------------------------------------------------
# PROFILE LOADING
# -------------------------------------------------

def load_profiles():

    profiles = []

    for file in os.listdir(PROFILE_DIR):

        if file.endswith(".json"):

            path = os.path.join(PROFILE_DIR, file)

            with open(path) as f:
                profiles.append(json.load(f))

    return profiles

# -------------------------------------------------
# FUNSCRIPT LOADER
# -------------------------------------------------

class FunscriptLoader:

    def __init__(self):
        self.channels = {}

# -------------------------------------------------
# TIMELINE
# -------------------------------------------------

class ChannelTimeline:

    def __init__(self, actions):
        self.actions = actions

    def get(self, t):

        a = self.actions

        if not a:
            return 50

        if t <= a[0]["at"]:
            return a[0]["pos"]

        for i in range(len(a) - 1):

            p = a[i]
            n = a[i + 1]

            if p["at"] <= t <= n["at"]:

                r = (t - p["at"]) / (n["at"] - p["at"])

                return p["pos"] + r * (n["pos"] - p["pos"])

        return a[-1]["pos"]

# -------------------------------------------------
# PLAYBACK ENGINE
# -------------------------------------------------

class PlaybackEngine:

    def __init__(self, loader):

        self.loader = loader
        self.timelines = {}
        self.last_values = {}

    def build_timelines(self):

        global device

        self.timelines = {}

        for c, a in self.loader.channels.items():
            self.timelines[c] = ChannelTimeline(a)

        if device:
            for ch in device["mapping"]:
                if ch not in self.timelines:
                    self.timelines[ch] = ChannelTimeline([{"at":0,"pos":50}])

    def run(self):

        global VIDEO_TIME_MS
        global frame_buffer

        while True:

            now = VIDEO_TIME_MS

            for ch in self.timelines:

                v = self.timelines[ch].get(now)

                last = self.last_values.get(ch)

                if last is not None and abs(v - last) < DEADBAND:
                    v = last

                self.last_values[ch] = v

                frame_buffer[ch] = v

            time.sleep(UPDATE_RATE)

# -------------------------------------------------
# MAIN
# -------------------------------------------------

def main():

    threading.Thread(target=start_ws_server, daemon=True).start()
    threading.Thread(target=device_writer, daemon=True).start()

    global loader
    loader = FunscriptLoader()

    global engine
    engine = PlaybackEngine(loader)

    print("Waiting for Stash time sync...")

    engine.run()

if __name__ == "__main__":
    main()