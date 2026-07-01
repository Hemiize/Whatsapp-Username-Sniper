# WhatsApp Username Sniper 💻

❌ DISCLAIMER: PLEASE USE AT UR OWN RISK (CONSEQUENCES FROM META UNKNOWN) ❌

Automatically checks whether WhatsApp usernames are available by typing them
into the username field on your phone and reading the result via ADB.
No root, no patches, no Frida — just a USB cable.
Only tested on Windows

<img width="979" height="512" alt="image" src="https://github.com/user-attachments/assets/98c24d81-4515-4474-80fa-0f8734dc7794" />


---

## What it does

WhatsApp added usernames in 2026. Good ones (short, clean words or 3–4 char
combos) get claimed fast. This tool connects to your phone over ADB, opens the
username edit screen, and runs through a list of candidates one by one —
logging every available name to `hits.txt`.

Three scanning modes:
- **3-char** — every combination of a–z and 0–9 (46,656 total)
- **4-char** — same but four characters (1,679,616 total)
- **Wordlist** — your own list from `wordlist.txt`, one name per line

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
Make sure you enable a "Do not disturb" mode so it doesnt click on the notifications on accident!

**2. Run the script**
```
python sniper.py
```

**3. Pick a mode**
```
Mode
  1  →  3-character  (aaa … 999  ·  46,656 combos)
  2  →  4-character  (aaaa … 9999  ·  1,679,616 combos)
  3  →  Wordlist  (wordlist.txt  ·  N words)
```

**4. Set a delay**
0.5 s is a safe default. Go lower at your own risk — WhatsApp will throttle
or temporarily lock the username field if you hammer it.

**5. Follow the calibration step**
The script auto-detects the username field on screen. If it fails, it asks
for the X/Y coordinates — you can find them with any screenshot tool.

Available usernames are printed in green and saved to `hits.txt` immediately.
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
- If WhatsApp updates and breaks detection, try bumping the delay to 1 s+.
- `hits.txt` accumulates across runs so you won't lose previous results.
