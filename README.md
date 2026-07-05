# 📱 WhatsApp Username Sniper

Automatically checks whether WhatsApp usernames are available by typing them
into the username field on your phone and reading the result via ADB.
No root, no patches, no Frida — just a USB cable.

<img width="979" height="512" alt="image" src="https://github.com/user-attachments/assets/97044d15-5f14-407d-a930-8c8cf65a4b82" />

---

<img src="https://img.shields.io/badge/Android-3DDC84?style=for-the-badge&logo=android&logoColor=white" />

## How it works

WhatsApp introduced usernames in 2026. Short, clean names get claimed fast.  
This tool connects to your phone over ADB, navigates to the username edit screen, types candidates one by one, and reads the UI response — logging every available name to `hits.txt` instantly.

---
## SHOWCASE

[![Whatsapp Username Sniper Showcase](https://img.youtube.com/vi/Kr5I5f5yCvI/0.jpg)](https://www.youtube.com/watch?v=Kr5I5f5yCvI)

---

## Requirements

| What | Details |
|------|---------|
| Python | 3.9 or newer — **no extra packages needed** |
| ADB | [Platform Tools installer](https://github.com/cli-stuff/platform-tools-installer-windows) — must be on PATH |
| Android phone | USB debugging enabled, plugged in via USB |
| WhatsApp | Installed and logged in |

Root is not required.

---

## Installation

**1. Install Python**  
[python.org](https://python.org) → check *"Add Python to PATH"* during setup.

**2. Get ADB**  
Download Android Platform Tools, extract, add to PATH. Verify:
```
adb version
```

**3. Enable USB debugging on your phone**  
Settings → About phone → tap Build number 7× → Developer options → USB debugging → Allow.

**4. Connect and authorize**
```
adb devices
```
Must show `device` (not `unauthorized`).

---

## Usage

**1.** Open WhatsApp on your phone:  
`Settings → Profile → Username → ✎ (edit icon)`

**2.** Run the script:
```
python sniper.py
```

**3.** Pick a mode:

```
  1  →  Combo      ∞ random combinations
  2  →  Wordlist   your own list (wordlist.txt)
  3  →  Settings   webhooks & config
  4  →  EN Dict    random common English words
  5  →  DE Dict    random common German words
```

**4.** Set a delay (0.5 s recommended — going lower risks throttling).

**5.** Follow the calibration step — the script auto-detects the text field.  
If detection fails it will ask for the X/Y coordinates once.

---

## Modes

### 1 — Combo
Generates an infinite stream of truly random strings.  
Choose length (3–8) and charset:

| # | Charset | Example |
|---|---------|---------|
| 1 | Letters  `a-z` | `kfmq` |
| 2 | Digits   `0-9` | `3917` |
| 3 | Mixed    `a-z + 0-9` | `b4xz` |

### 2 — Wordlist
Reads `wordlist.txt` (or any file you point it at) line by line.  
You can resume from a specific line if you stopped mid-run.  
Bundled: **1,000 German words**, 5–8 characters.

### 3 — Settings
Configure Discord webhooks — one per mode.  
Changes are saved to `settings.json` and persist across runs.

### 4 — EN Dict  *(auto-downloaded)*
Uses Google's **top ~9,900 most common English words** (no swear words).  
Downloaded on first use, cached as `dict_en.txt`.  
Words are shuffled before every full pass — no repeats until the whole list is exhausted.

### 5 — DE Dict  *(auto-downloaded)*
Uses the **top 50,000 most common German words** by real-world frequency.  
Downloaded on first use, cached as `dict_de.txt`.  
Same shuffle-then-iterate logic as EN Dict.

---

## Discord Webhooks

Open **mode 3 → Settings** to configure up to 9 webhook slots:

| Slot | Fires when |
|------|-----------|
| 3-char … 8-char | Combo mode with that length |
| Wordlist | Mode 2 |
| EN Dict | Mode 4 |
| DE Dict | Mode 5 |

Each slot posts to a different Discord channel.  
After saving a URL you can send a test message immediately.

---

## Auto-Pause

Every **15 minutes** the sniper automatically pauses for **5 minutes**.  
A live MM:SS countdown is shown. This reduces the chance of WhatsApp throttling the field.  
Ctrl+C during a pause exits cleanly.

---

## Output

While running, names are color-coded:

| Color | Meaning |
|-------|---------|
| Green  | Available — saved to `hits.txt` + webhook fired |
| Red    | Taken |
| Yellow | Timeout / no response |

A pinned stats bar shows hits, checked count, speed (checks/s), and elapsed time.

---

## Files

| File | Description |
|------|-------------|
| `sniper.py` | Main script — only file you need to run |
| `wordlist.txt` | Word list for mode 2 (1,000 German words bundled) |
| `dict_en.txt` | Cached English dictionary (auto-created on first EN Dict run) |
| `dict_de.txt` | Cached German dictionary (auto-created on first DE Dict run) |
| `hits.txt` | Available names found — appended, never overwritten |
| `settings.json` | Saved webhook URLs — created automatically |
| `webhook_errors.log` | Webhook delivery errors (created if a POST fails) |

---

## Notes

- Keep the phone screen on and unlocked while scanning.
- Combo mode is truly random — every check is an independent random pick.
- Dict modes cover the full list before repeating (shuffle → iterate → reshuffle).
- `hits.txt` accumulates across runs — previous results are never lost.
- If WhatsApp updates and breaks detection, try increasing the delay to 1 s+.

---

## Disclaimer

Using this tool may violate WhatsApp's Terms of Service.  
Your account could be restricted or banned.  
Use at your own risk — the author takes no responsibility for any consequences.

---

*by Hemiize · github.com/Hemiize/Whatsapp-Username-Sniper*
