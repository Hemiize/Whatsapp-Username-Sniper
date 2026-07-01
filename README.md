# WhatsApp Username Sniper

Automatically checks whether WhatsApp usernames are available by typing them
into the username field on your phone and reading the result via ADB.
No root, no patches, no Frida — just a USB cable.

<img width="979" height="512" alt="image" src="https://github.com/user-attachments/assets/97044d15-5f14-407d-a930-8c8cf65a4b82" />

---

<img src="{https://img.shields.io/badge/Android-3DDC84?style=for-the-badge&logo=android&logoColor=white}" />

## What it does

WhatsApp added usernames in 2026. Good ones (short, clean words or 3–4 char
combos) get claimed fast. This tool connects to your phone over ADB, opens the
username edit screen, and runs through a list of candidates one by one —
logging every available name to `hits.txt`.

Two scanning modes:

- **Combo** — bruteforce all combinations for a chosen length (3–8 chars) and
  charset (letters, digits, or mixed). Starts at a random position every run
  so you never waste time grinding through `aaa`, `aab`, `aac` first.
- **Wordlist** — check your own list from `wordlist.txt`, one name per line.

---

## Requirements

- Python 3.9 or newer (no extra packages)
- [ADB (Android Debug Bridge)](https://developer.android.com/tools/releases/platform-tools) — must be on your PATH
- An Android phone with USB debugging turned on
- WhatsApp installed and logged in on that phone

Root is not needed.

---

## Installation

**1. Install Python**
Download from [python.org](https://python.org) if you don't have it.
Make sure to check "Add Python to PATH" during setup.

**2. Get ADB**
Download Android Platform Tools and either put the folder on your PATH
or drop `adb.exe` next to `sniper.py`.

Verify it works:
```
adb version
```

**3. Enable USB debugging on your phone**
Go to Settings → About phone → tap Build number 7 times → Developer options → USB debugging.

**4. Connect and authorize**
Plug in via USB. When the "Allow USB debugging?" prompt appears on the phone, tap Allow.
Then check that ADB sees the device:
```
adb devices
```
It should show `device` (not `unauthorized`).

---

## Usage

**1. Open the username screen on your phone**
WhatsApp → Settings → Profile → Username → tap the edit icon (✎)

**2. Run the script**
```
python sniper.py
```

**3. Pick a mode**
```
  1  →  Combo      bruteforce all combinations
  2  →  Wordlist   500 words
```

**4. Configure combo mode (if selected)**

Choose a length:
```
  3  →  3-char   (     46,656 combos  [mixed])
  4  →  4-char   (  1,679,616 combos  [mixed])
  5  →  5-char   ( 60,466,176 combos  [mixed])
  ...
```

Then choose a charset:
```
  1  →  Letters   a-z         (   17,576 combos)
  2  →  Digits    0-9         (    1,000 combos)
  3  →  Mixed     a-z + 0-9   (   46,656 combos)
```

**5. Set a delay**
0.5 s is a safe default. Go lower at your own risk — WhatsApp will throttle
or temporarily lock the username field if you hammer it.

**6. Follow the calibration step**
The script auto-detects the username field on screen. If it fails, it asks
for the X/Y coordinates — you can find them with any screenshot tool.

During scanning, names are color-coded in real time:
- **Green** — available (also saved to `hits.txt` immediately)
- **Red** — taken
- **Yellow** — timeout / no response

Press Ctrl+C at any time to stop.

---

## Files

| File | Description |
|------|-------------|
| `sniper.py` | The script — only file you need to run |
| `wordlist.txt` | Names to check in wordlist mode (edit freely) |
| `hits.txt` | Available names found — appended, never overwritten |

---

## Notes

- Keep your phone screen on and unlocked while scanning.
- Combo mode picks a random start index every run — all combos are still
  covered exactly once, just not in alphabetical order.
- If WhatsApp updates and breaks detection, try bumping the delay to 1 s+.
- `hits.txt` accumulates across runs so you won't lose previous results.
