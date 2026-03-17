# Stash Device Bridge

> Motion controller plugin for **Stash** that syncs multifunscript files with video playback and controls TCode-compatible devices through stash.

---

## Quick Introduction

With the rise of people building and selling multi-axis devices there has often been the problem of what player to use. I certainly had this issue when I first built my OSR2. I ended up landing on using XTPlayer but when I would go back and use my handy again I would always go back to stash. Stash to me just allowed for so much more and I already had everything organized nicely on there. This ended up with me looking for plugin for stash that allowed for multi-axis but sadly I was unable to find one. If there is one out there already please let me know but here is my take on it. With my little to no knowledge of coding this was built almost entirely through AI so it probably is riddled with bugs and before you ask no I do not know how to fix them. I hope people much smarter than me can see this and improve on it to make it function better and have more features but until those people do (and I really hope they do) enjoy!

Tested only using my OSR2 as it is the only device I own that works through USB. Use this at your own risk and please be careful!

---

## Features

- sync with Stash video playback
- Multifunscript support (multi-axis) (currently no suck, vib, or lube)
- Per-axis calibration (min/max range setup)
- Live calibration sliders with movement testing
- Serial device support (anything that plugs in with a USB)
- Motion smoothing (velocity limiting)

---

## Installation

### 1. Install dependencies

- type in your taskbar search CMD. Open command prompt and paste the following -> pip install websockets pyserial

### 2. Install plugin

- Copy the plugin folder into your Stash plugins directory (typically in C:\Users\"name of your desktop"\.stash\plugins)

- Sometimes if you don't have a plugins folder you need to create one. Simply create a folder in .stash and name it plugins

- Your folder should now look something like:



.stash/
└── plugins/
└── device-bridge/
├── plugin.yml
├── deviceBridge.js
├── start_controller.py
└── controller/


---

## Usage

### 1. Prepare your scripts

- Create or locate your stash library folder
- Place your .funscript files in the same folder as your video file
- Make sure filenames match your video and include channel names

### 2. Open the app

- Locate the start_stash_with_controller.bat This is the application you need to use now as it opens both stash and your WebSocket. Click on this to open it up.
  - Feel free to rename this application and move it. But you might need to change (%USERPROFILE%\Desktop\stash-win.exe) within it to model your stash.exe location

### 3. Connect your device

- In the settings/plugins/plugin UI: Click scan Devices.
- Select the COM port your device is connected to and click connect Device
- If it's your first time with this device hit Setup New Device. Enter the name you want it called then follow the instructions on assigning the axes.
  - Don't worry if you mess up the axes just go back (you might have to restart) and click setup new device and name it the same it will overwrite it.

### 4. Play a scene

- Simply go and play a scene like normal. It should sync the motion and funscripts in real time with the video.

---

## Other notes

### Profiles

- Upon setting up a device or clicking save calibration a profile is created in the profiles folder within controller

### Basic how it works

- The plugin uses a local WebSocket connection (`localhost:5757`) to communicate between Stash and the Python controller.
- The browser sends the current video time and scene information to the WebSocket
- The Python backend processes this and finds the corresponding funscripts and using the time calculates motion
- Commands are sent back through the WebSocket through to your device