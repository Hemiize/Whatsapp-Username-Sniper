#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WhatsApp Username Sniper  v1.0
Automated username availability checker — ADB + UIAutomator
No root required.
"""

import sys
import os
import time
import itertools
import random
import string
import subprocess
import re
import shutil
import json
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# Dictionary sources (downloaded on first use)
# ─────────────────────────────────────────────────────────────────────────────
_EN_DICT_URL = "https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-no-swears.txt"
_DE_DICT_URL = "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2016/de/de_50k.txt"


# ─────────────────────────────────────────────────────────────────────────────
# Windows: enable ANSI / Virtual Terminal Processing
# Without this, escape codes print as literal text (←[96m etc.)
# ─────────────────────────────────────────────────────────────────────────────
if sys.platform == "win32":
    try:
        import ctypes
        _k32 = ctypes.windll.kernel32
        _h   = _k32.GetStdHandle(-11)          # STD_OUTPUT_HANDLE
        _m   = ctypes.c_ulong()
        _k32.GetConsoleMode(_h, ctypes.byref(_m))
        _k32.SetConsoleMode(_h, _m.value | 0x4) # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Integrity / branding
# Author stored encoded — modifying _C causes silent exit at startup.
# ─────────────────────────────────────────────────────────────────────────────
_C = (83, 71, 86, 116, 97, 87, 108, 54, 90, 81, 61, 61)

def _load():
    import base64
    d = base64.b64decode(bytes(_C)).decode()
    if len(d) != 7 or sum(ord(x) * (n + 1) for n, x in enumerate(d)) != 2985:
        os._exit(0)
    return d

_AUTHOR = _load()


# ─────────────────────────────────────────────────────────────────────────────
# Colours
# ─────────────────────────────────────────────────────────────────────────────
GRN = "\033[92m"
RED = "\033[91m"
YEL = "\033[93m"
CYN = "\033[96m"
WHT = "\033[97m"
MAG = "\033[95m"
DIM = "\033[2m"
BLD = "\033[1m"
RST = "\033[0m"


# ─────────────────────────────────────────────────────────────────────────────
# Terminal helpers
# ─────────────────────────────────────────────────────────────────────────────
def _w(s):
    """Write a raw string (control sequences, no newline)."""
    sys.stdout.write(s)
    sys.stdout.flush()

def _clr():
    _w("\033[2J\033[H")

def _term_h():
    try:
        return shutil.get_terminal_size().lines
    except Exception:
        return 40

def _hr(ch="─", n=66):
    return ch * n

def _ts():
    return datetime.now().strftime("%H:%M:%S")

# Bar geometry — computed once in _print_header, then used by _fmt_stats / _update_stats
_ANSI_RE = re.compile(r'\033\[[^m]*m')
_BAR_W   = 0   # equalized visible width for both info + stats bars
_BAR_PAD = ""  # left-centering whitespace prefix

def _vlen(s):
    """Visible length of s — strips ANSI escape codes."""
    return len(_ANSI_RE.sub('', s))


# ─────────────────────────────────────────────────────────────────────────────
# Logo + header builder
#
# Printed once before scanning.  Returns the number of lines printed so we
# know where to place the stats bar and where to start the scroll region.
# ─────────────────────────────────────────────────────────────────────────────
_ART = [
    r"  ██╗    ██╗  █████╗      ███████╗███╗  ██╗██╗",
    r"  ██║    ██║ ██╔══██╗     ██╔════╝████╗ ██║██║",
    r"  ██║ █╗ ██║ ███████║     ███████╗██╔██╗██║██║",
    r"  ██║███╗██║ ██╔══██║     ╚════██║██║╚████║╚═╝",
    r"  ╚███╔███╔╝ ██║  ██║     ███████║██║ ╚███║██╗",
    r"   ╚══╝╚══╝  ╚═╝  ╚═╝     ╚══════╝╚═╝  ╚══╝╚═╝",
]


def _print_header(total=0, mode_info=""):
    """
    Print the full header (logo + mode info + stats bar).
    Returns (stats_row, scroll_start) — both 1-based terminal row numbers.
    """
    global _BAR_W, _BAR_PAD
    row = 1

    def ln(text=""):
        nonlocal row
        print(text)
        row += 1

    # ── Compute equalized bar width + centering BEFORE printing anything ─────
    term_w = shutil.get_terminal_size().columns
    # Sample natural stats width (temporarily zero globals to avoid recursion)
    _bw_save, _bp_save = _BAR_W, _BAR_PAD
    _BAR_W, _BAR_PAD   = 0, ""
    stats_nat          = _fmt_stats(0, 0, 0.0, 0.0, total)
    _BAR_W, _BAR_PAD   = _bw_save, _bp_save

    mode_vlen  = _vlen(mode_info) if mode_info else 0
    stats_vlen = _vlen(stats_nat)
    _BAR_W     = max(mode_vlen, stats_vlen)
    _BAR_PAD   = " " * max(0, (term_w - _BAR_W) // 2)

    # Equalize mode_info to _BAR_W by padding before the closing  |
    closer = f"  {DIM}|{RST}"
    if mode_info and mode_vlen < _BAR_W and mode_info.endswith(closer):
        mode_info = mode_info[:-len(closer)] + " " * (_BAR_W - mode_vlen) + closer

    sep_line = _BAR_PAD + f"{DIM}{'─' * _BAR_W}{RST}"

    # ── Print ─────────────────────────────────────────────────────────────────
    ln()
    for art_line in _ART:
        art_offset = " " * max(0, (_BAR_W - _vlen(art_line)) // 2)
        ln(_BAR_PAD + art_offset + f"{CYN}{BLD}{art_line}{RST}")
    ln()
    ln(_BAR_PAD + f"{GRN}{BLD}{'U S E R N A M E   S N I P E R':^{_BAR_W}}{RST}")
    ln(_BAR_PAD + f"{YEL}{'by ' + _AUTHOR + '  ·  v1.0':^{_BAR_W}}{RST}")
    ln(_BAR_PAD + f"{DIM}{'github.com/Hemiize/Whatsapp-Username-Sniper':^{_BAR_W}}{RST}")
    ln()
    ln(sep_line)
    if mode_info:
        ln(_BAR_PAD + mode_info)
    ln(sep_line)

    stats_row = row
    ln(_fmt_stats(0, 0, 0.0, 0.0, total))  # placeholder — uses _BAR_W + _BAR_PAD

    ln(sep_line)

    scroll_start = row
    return stats_row, scroll_start


def _fmt_stats(hits, checked, speed, elapsed, total=0):
    h = int(elapsed // 3600)
    m = int((elapsed % 3600) // 60)
    s = int(elapsed % 60)
    # Pad plain strings BEFORE adding ANSI — keeps separator positions stable
    hits_s = f"{hits:<6}"
    if total:
        tw    = len(str(total))
        chk_s = f"{checked:>{tw}}/{total}"
    else:
        chk_s = str(checked)
    chk_s  = f"{chk_s:<16}"
    spd_s  = f"{speed:>8.1f}/s"
    tim_s  = f"{h:02d}:{m:02d}:{s:02d}"
    sep    = f"  {DIM}|{RST}  "
    inner  = (
        f"  {DIM}|{RST}  {DIM}HITS{RST}  {GRN}{BLD}{hits_s}{RST}"
        + sep + f"{CYN}{BLD}{chk_s}{RST}"
        + sep + f"{YEL}{BLD}{spd_s}{RST}"
        + sep + f"{WHT}{BLD}{tim_s}{RST}"
    )
    closer = f"  {DIM}|{RST}"
    raw    = inner + closer
    # Pad to equalized target width so both bars are always the same visible width
    gap = _BAR_W - _vlen(raw)
    if gap > 0:
        raw = inner + " " * gap + closer
    return _BAR_PAD + raw


def _update_stats(stats_row, hits, checked, speed, elapsed, total=0):
    """Overwrite the stats bar without moving the results cursor."""
    text = _fmt_stats(hits, checked, speed, elapsed, total)
    _w(f"\033[s"              # save cursor
       f"\033[{stats_row};1H" # go to stats row
       f"\033[2K"             # clear line
       f"{text}"              # new stats
       f"\033[u")             # restore cursor


# ─────────────────────────────────────────────────────────────────────────────
# Settings  (persisted to settings.json next to the script)
# ─────────────────────────────────────────────────────────────────────────────

_SETTINGS_FILE = Path(__file__).parent / "settings.json"

def _load_settings() -> dict:
    if _SETTINGS_FILE.exists():
        try:
            return json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def _save_settings(data: dict):
    _SETTINGS_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _download_dict(url: str, dest: Path, label: str) -> int:
    """Download word list, keep only a-z words (3-25 chars), shuffle, save."""
    print(f"  {DIM}[*]{RST} Downloading {label} dictionary ...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "WA-Sniper/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  {RED}[!]{RST} Download failed: {e}")
        return 0
    words = []
    for line in raw.splitlines():
        # support both "word" and "word frequency" formats
        parts = line.strip().split()
        if not parts:
            continue
        w = parts[0].lower()
        if w and 3 <= len(w) <= 25 and w.isalpha() and w.isascii():
            words.append(w)
    random.shuffle(words)
    dest.write_text("\n".join(words), encoding="utf-8")
    print(f"  {GRN}[✓]{RST} {len(words):,} words saved → {dest.name}")
    return len(words)


# ─────────────────────────────────────────────────────────────────────────────
# Persistent ADB shell
#
# One 'adb shell' process lives for the entire session.  Shell-side commands
# (input tap/text/keyevent, uiautomator dump) are piped through stdin so no
# new Windows process is spawned per command (~80-150 ms overhead saved each).
# adb pull / adb devices still use subprocess.run — they can't run inside the
# shell.
# ─────────────────────────────────────────────────────────────────────────────

class _PersistentShell:
    _SENTINEL = "__SNIPER_DONE__"

    def __init__(self):
        self._proc = None

    def _start(self):
        try:
            self._proc = subprocess.Popen(
                ["adb", "shell"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0,
            )
        except Exception:
            self._proc = None

    def _alive(self):
        return self._proc is not None and self._proc.poll() is None

    def _ensure(self):
        if not self._alive():
            self._start()

    def run(self, cmd: str, timeout: float = 10.0) -> str:
        """Send cmd, wait for sentinel echo, return captured stdout."""
        self._ensure()
        if not self._alive():
            return ""
        try:
            payload = f"{cmd} ; echo {self._SENTINEL}\n".encode()
            self._proc.stdin.write(payload)
            self._proc.stdin.flush()
            out      = []
            deadline = time.time() + timeout
            while time.time() < deadline:
                line = self._proc.stdout.readline()
                if not line:
                    break
                decoded = line.decode(errors="replace").rstrip("\r\n")
                if decoded == self._SENTINEL:
                    break
                out.append(decoded)
            return "\n".join(out)
        except Exception:
            self._proc = None
            return ""

    def send(self, cmd: str):
        """Fire-and-forget: write cmd to stdin without reading output."""
        self._ensure()
        if not self._alive():
            return
        try:
            self._proc.stdin.write(f"{cmd}\n".encode())
            self._proc.stdin.flush()
        except Exception:
            self._proc = None

    def close(self):
        if self._proc:
            try:
                self._proc.stdin.write(b"exit\n")
                self._proc.stdin.flush()
                self._proc.wait(timeout=2)
            except Exception:
                pass
            try:
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None


# ─────────────────────────────────────────────────────────────────────────────
# Sniper
# ─────────────────────────────────────────────────────────────────────────────

class Sniper:

    _SAVE_TEXTS = {
        "save",        "speichern",   "guardar",
        "enregistrer", "salvar",
        "\u0441\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c",
        "\u062d\u0641\u0638",
        "\u4fdd\u5b58",
        "\uc800\uc7a5",
    }

    def __init__(self, delay=0.5):
        self.delay     = delay
        self.hits      = []
        self.checked   = 0
        self.t0        = None
        self._field_x  = None
        self._field_y  = None
        self._baseline = None
        self._shell    = _PersistentShell()
        self.webhook   = None   # Discord webhook URL (set from settings)

    # ── ADB ──────────────────────────────────────────────────────────────────

    def _adb(self, *args, timeout=12):
        try:
            return subprocess.run(
                ["adb"] + list(args),
                capture_output=True, text=True, timeout=timeout,
            )
        except Exception:
            return None

    def _check_adb(self):
        r = self._adb("devices")
        if r:
            devs = [l for l in r.stdout.splitlines() if "\tdevice" in l]
            if devs:
                print(f"  {GRN}[+]{RST} Device  : {devs[0].split(chr(9))[0]}")
                return True
        print(f"  {RED}[!]{RST} No ADB device found.")
        print(f"       Connect via USB and enable USB debugging.")
        return False

    def _adb_input(self, username):
        try:
            if self._field_x is not None:
                self._shell.send(
                    f"input tap {self._field_x} {self._field_y}")
                time.sleep(0.2)
            self._shell.send(
                "input keyevent KEYCODE_MOVE_END "
                + " ".join(["KEYCODE_DEL"] * 30)
            )
            time.sleep(0.1)
            # Single-quote so the shell doesn't expand special chars
            safe = username.replace("'", "'\\''")
            self._shell.send(f"input text '{safe}'")
            time.sleep(0.15)
            return True
        except Exception:
            return False

    # ── UIAutomator ───────────────────────────────────────────────────────────

    def _find_field(self):
        try:
            self._shell.run("uiautomator dump --compressed /sdcard/uidump.xml")
            # No explicit sleep — _shell.run() blocks until the dump completes
            tmp = Path(__file__).parent / "uidump.xml"
            self._adb("pull", "/sdcard/uidump.xml", str(tmp))
            root = ET.parse(str(tmp)).getroot()
            for node in root.iter("node"):
                cls  = node.get("class",        "")
                rid  = node.get("resource-id",  "").lower()
                cdsc = node.get("content-desc", "").lower()
                if "EditText" in cls and not any(
                        w in rid + cdsc for w in ("search", "such")):
                    m = re.findall(r'\[(\d+),(\d+)\]', node.get("bounds", ""))
                    if len(m) == 2:
                        self._field_x = (int(m[0][0]) + int(m[1][0])) // 2
                        self._field_y = (int(m[0][1]) + int(m[1][1])) // 2
                        return True
        except Exception:
            pass
        return False

    def _dump_ui(self, name="ud.xml"):
        local = Path(__file__).parent / name
        self._shell.run(f"uiautomator dump --compressed /sdcard/{name}")
        self._adb("pull", "/sdcard/" + name, str(local))
        return local

    def _parse_nodes(self, path):
        nodes = {}
        try:
            for node in ET.parse(str(path)).getroot().iter("node"):
                b   = node.get("bounds", "")
                cls = node.get("class",  "")
                if not b:
                    continue
                nodes[b + "|" + cls] = {
                    "rid":       node.get("resource-id", ""),
                    "text":      node.get("text",        "").strip(),
                    "class":     cls,
                    "bounds":    b,
                    "enabled":   node.get("enabled",   "false").lower() == "true",
                    "clickable": node.get("clickable",  "false").lower() == "true",
                }
        except Exception:
            pass
        return nodes

    def _capture_baseline(self):
        self._baseline = self._parse_nodes(self._dump_ui("baseline.xml"))
        print(f"  {GRN}[+]{RST} Baseline : {len(self._baseline)} nodes")

    def _find_save_btn(self, nodes):
        fy    = self._field_y or 300
        label = None

        for key, n in nodes.items():
            text = n["text"].lower()
            rid  = n["rid"]

            if text and any(p in text for p in (
                "nicht verf\u00fcgbar", "not available",
                "already taken",        "bereits vergeben",
                "username not available","only available", "whatsapp business"
            )):
                return False

            if text in (
                "verf\u00fcgbar", "username available",
                "benutzername verf\u00fcgbar",
                "dieser benutzername ist verf\u00fcgbar",
            ):
                return True

            if ("upr_edit_save_button" in rid or
                    ("save_button" in rid
                     and "container" not in rid
                     and "stub"      not in rid)):
                return n["enabled"]

            if text in self._SAVE_TEXTS:
                try:
                    m = re.findall(r'\[(\d+),(\d+)\]', n["bounds"])
                    if m and int(m[0][1]) >= fy - 100:
                        label = n
                except Exception:
                    pass

        if label is not None:
            try:
                m  = re.findall(r'\[(\d+),(\d+)\]', label["bounds"])
                cx = (int(m[0][0]) + int(m[1][0])) // 2
                cy = (int(m[0][1]) + int(m[1][1])) // 2
            except Exception:
                cx, cy = 0, 0
            best      = None
            best_area = float("inf")
            for key, n in nodes.items():
                if n is label or not n["clickable"]:
                    continue
                try:
                    m  = re.findall(r'\[(\d+),(\d+)\]', n["bounds"])
                    x1, y1 = int(m[0][0]), int(m[0][1])
                    x2, y2 = int(m[1][0]), int(m[1][1])
                except Exception:
                    continue
                if x1 <= cx <= x2 and y1 <= cy <= y2:
                    area = (x2 - x1) * (y2 - y1)
                    if area < best_area:
                        best_area, best = area, n
            if best is not None:
                return best["enabled"]

        if self._baseline:
            for key, n in nodes.items():
                if key in self._baseline or not n["clickable"]:
                    continue
                try:
                    m = re.findall(r'\[(\d+),(\d+)\]', n["bounds"])
                    if m and int(m[0][1]) >= fy - 100:
                        return n["enabled"]
                except Exception:
                    pass

        return None

    def _poll(self, username, total_wait=5.5):
        deadline = time.time() + total_wait
        first    = True
        while time.time() < deadline:
            time.sleep(1.8 if first else 0.5)  # 0.5 s — faster with persistent shell
            first = False
            state = self._find_save_btn(self._parse_nodes(self._dump_ui()))
            if state is True:
                return {"available": True,  "username": username}
            if state is False:
                return {"available": False, "username": username}
        return None

    # ── Setup ─────────────────────────────────────────────────────────────────

    def calibrate(self):
        print()
        print(f"  {WHT}{BLD}SETUP{RST}")
        print(f"  {DIM}{_hr('─', 40)}{RST}")

        if not self._check_adb():
            sys.exit(1)

        print(f"  {DIM}[*]{RST} Detecting username field ...")
        if self._find_field():
            print(f"  {GRN}[+]{RST} Field at ({self._field_x}, {self._field_y})")
        else:
            print(f"  {YEL}[!]{RST} Auto-detect failed. Enter coordinates:")
            try:
                x = input(f"      {CYN}X{RST} [default 540]: ").strip()
                y = input(f"      {CYN}Y{RST} [default 600]: ").strip()
                self._field_x = int(x) if x else 540
                self._field_y = int(y) if y else 600
            except (ValueError, EOFError):
                self._field_x, self._field_y = 540, 600
            print(f"  {GRN}[+]{RST} Using ({self._field_x}, {self._field_y})")

        print(f"  {DIM}[*]{RST} Capturing UI baseline ...")
        self._capture_baseline()
        print()

    # ── Core ──────────────────────────────────────────────────────────────────

    def check(self, username):
        self.checked += 1
        if not self._adb_input(username):
            return None
        res = self._poll(username)
        if res is None:
            self._find_field()
        return res

    # ── Generators ────────────────────────────────────────────────────────────

    def gen_combo(self, length, charset):
        """Infinite stream of random strings — truly random picks each time."""
        while True:
            yield "".join(random.choices(charset, k=length))

    def gen_dict_random(self, path):
        """Random word stream — shuffles full dict, yields every word once, then reshuffles.
        No word is repeated until the entire dictionary has been exhausted."""
        words = [
            ln.strip() for ln in open(path, encoding="utf-8", errors="ignore")
            if ln.strip() and 3 <= len(ln.strip()) <= 25
        ]
        if not words:
            return
        while True:
            random.shuffle(words)
            yield from words

    def gen_wordlist(self, path, start_line=1):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                if i < start_line:
                    continue
                u = line.strip()
                if u and 3 <= len(u) <= 25:
                    yield u

    # ── Output ────────────────────────────────────────────────────────────────

    def _save_hit(self, username):
        ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        path = Path(__file__).parent / "hits.txt"
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{ts}]  {username}\n")
    def _notify_webhook(self, username):
        """POST a Discord webhook message when a username is available."""
        if not self.webhook:
            return
        _webhook_post(self.webhook, username)

    # ── Run ─────────────────────────────────────────────────────────────────────────

    def run(self, length=None, charset=None, wordlist=None, start_line=1, dict_random=None):
        if dict_random:
            _wc           = sum(1 for ln in open(dict_random, encoding="utf-8", errors="ignore") if ln.strip())
            gen_fn        = lambda: self.gen_dict_random(dict_random)
            total         = 0
            charset_label = f"{_wc:,} words"
            mode_str      = "dict-rand"
        elif wordlist:
            gen_fn        = lambda: self.gen_wordlist(wordlist, start_line)
            total         = sum(
                1 for ln in open(wordlist, encoding="utf-8", errors="ignore")
                if ln.strip() and 3 <= len(ln.strip()) <= 25
            )
            mode_str      = "wordlist"
            charset_label = f"{total:,} words"
        else:
            gen_fn        = lambda: self.gen_combo(length, charset)
            total         = 0   # infinite — truly random, no fixed total
            has_alpha     = any(c.isalpha() for c in charset)
            has_digit     = any(c.isdigit() for c in charset)
            charset_label = (
                "a-z + 0-9" if (has_alpha and has_digit)
                else "a-z"   if has_alpha
                else "0-9"
            )
            mode_str      = f"{length}-char"

        self.t0 = time.time()

        mode_info = (
            f"  {DIM}|{RST}  {DIM}MODE{RST}  {WHT}{BLD}{mode_str:<10}{RST}"
            f"  {DIM}|{RST}  {DIM}CHARSET{RST}  {WHT}{BLD}{charset_label:<14}{RST}"
            f"  {DIM}|{RST}  {DIM}DELAY{RST}  {WHT}{BLD}{self.delay:.1f}s{RST}"
            f"  {DIM}|{RST}"
        )
        _clr()
        stats_row, scroll_start = _print_header(total, mode_info)

        # Activate scroll region: only lines from scroll_start to bottom scroll
        _w(f"\033[{scroll_start};{_term_h()}r")
        # Position cursor at the top of the scroll region
        _w(f"\033[{scroll_start};1H")

        _WORK_SEC  = 15 * 60   # 15 min active
        _BREAK_SEC =  5 * 60   # 5 min break
        _last_break = time.time()

        try:
            for username in gen_fn():
                # ── Break check ───────────────────────────────────────────
                if time.time() - _last_break >= _WORK_SEC:
                    _w("\033[r")                      # full scroll
                    print()
                    print(f"  {YEL}{BLD}[PAUSE]{RST}  15 min reached — resting 5 min to avoid throttling ...")
                    try:
                        for remaining in range(_BREAK_SEC, 0, -1):
                            m, s = divmod(remaining, 60)
                            _w(f"\r  {DIM}  Resuming in  {RST}{WHT}{BLD}{m:02d}:{s:02d}{RST}   ")
                            time.sleep(1)
                    except KeyboardInterrupt:
                        raise
                    _w(f"\r{' ' * 40}\r")
                    print(f"  {GRN}[✓]{RST}  Break over — resuming ...")
                    print()
                    # Restore scroll region
                    _w(f"\033[{scroll_start};{_term_h()}r")
                    _w(f"\033[{scroll_start};1H")
                    _last_break = time.time()

                res = self.check(username)
                ts  = _ts()

                if res is None:
                    print(f"  {DIM}[{ts}]  ?  {YEL}{username}{RST}")
                elif res["available"]:
                    self.hits.append(username)
                    self._save_hit(username)
                    self._notify_webhook(username)
                    print(
                        f"  {DIM}[{ts}]  >>  {RST}"
                        f"{GRN}{BLD}{username.upper():<20}{RST}"
                        f"  {GRN}{BLD}<-- AVAILABLE!{RST}"
                    )
                else:
                    print(f"  {DIM}[{ts}]  x  {RST}{RED}{username}{RST}")

                # Refresh the pinned stats bar
                elapsed = time.time() - self.t0
                speed   = self.checked / elapsed if elapsed > 0 else 0.0
                _update_stats(stats_row, len(self.hits),
                              self.checked, speed, elapsed, total)

                if self.delay > 0:
                    time.sleep(self.delay)

        except KeyboardInterrupt:
            pass

        finally:
            # Restore scroll region to full screen
            _w("\033[r")
            # Move cursor well below the results area
            _w(f"\033[{scroll_start + 5};1H")
            # Tear down the persistent shell
            self._shell.close()

        # ── Summary ────────────────────────────────────────────────────────────────
        elapsed = time.time() - self.t0
        speed   = self.checked / elapsed if elapsed > 0 else 0.0
        print()
        print(f"  {DIM}{_hr()}{RST}")
        print(f"  {WHT}{BLD}RESULTS{RST}")
        print(f"  {DIM}{_hr('\u2500', 40)}{RST}")
        print(f"  Checked    :  {self.checked}")
        print(f"  Available  :  {GRN}{BLD}{len(self.hits)}{RST}")
        print(f"  Speed      :  {speed:.1f} checks/s")
        print(f"  Duration   :  {int(elapsed // 60)}m {int(elapsed % 60)}s")
        if self.hits:
            print(f"  {DIM}{_hr('\u2500', 40)}{RST}")
            for h in self.hits:
                print(f"  {GRN}  >>  {h}{RST}")
            print(f"\n  {DIM}\u2192 Saved to hits.txt{RST}")
        print(f"  {DIM}{_hr()}{RST}")


def _webhook_post(url: str, username: str, test: bool = False):
    """Send a Discord webhook POST. Returns (ok: bool, error: str)."""
    try:
        msg = (
            f"\u2705 **Test** — webhook works!"
            if test else
            f"\u2705 **`{username}`** is available!"
        )
        payload = json.dumps({
            "content": msg,
            "embeds": [{
                "title": "\u2705 Username Available!" if not test else "\U0001f4e1 Webhook Test",
                "description": f"**`{username}`**",
                "color": 5763719 if not test else 3447003,
                "footer": {"text": "WA Sniper \u00b7 Hemiize"},
            }]
        }).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "WA-Sniper/1.0",
            },
            method="POST",
        )
        urllib.request.urlopen(req, timeout=8)
        return True, ""
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode(errors="replace")
        except Exception:
            pass
        err = f"HTTP {e.code} {e.reason} — {body[:200]}"
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
    try:
        _log = Path(__file__).parent / "webhook_errors.log"
        with open(_log, "a", encoding="utf-8") as _f:
            _f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]  {username}  {err}\n")
    except Exception:
        pass
    return False, err


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    _clr()
    for line in _ART:
        print(f"{CYN}{BLD}{line}{RST}")
    print()
    print(f"{GRN}{BLD}{'U S E R N A M E   S N I P E R':^50}{RST}")
    print(f"{YEL}{'by ' + _AUTHOR + '  ·  v1.0':^50}{RST}")
    print(f"{DIM}{'github.com/Hemiize/Whatsapp-Username-Sniper':^50}{RST}")
    print()
    print(f"{DIM}{_hr()}{RST}")

    def section(title):
        print()
        print(f"  {WHT}{BLD}{title}{RST}")
        print(f"  {DIM}{_hr('·', 40)}{RST}")
        print()

    def prompt(text, default=None, valid=None):
        sfx = f"  {DIM}[{default}]{RST}" if default is not None else ""
        while True:
            try:
                raw = input(f"  {CYN}›{RST}  {text}{sfx} : ").strip()
            except EOFError:
                raw = ""
            if not raw and default is not None:
                return str(default)
            if valid is None or raw in valid:
                return raw
            print(f"  {RED}Invalid — choose: {', '.join(str(v) for v in valid)}{RST}")

    # ── Wordlist info ──────────────────────────────────────────────────────
    _wl_default = Path(__file__).parent / "wordlist.txt"
    if _wl_default.exists():
        _wl_count = sum(
            1 for ln in open(_wl_default, encoding="utf-8", errors="ignore")
            if ln.strip() and 3 <= len(ln.strip()) <= 25
        )
        _wl_info = f"{_wl_count:,} words"
    else:
        _wl_count = 0
        _wl_info  = "wordlist.txt"

    # ── Load persisted settings ────────────────────────────────────────────
    settings = _load_settings()

    # ── Mode loop (returns here after Settings) ────────────────────────────
    wordlist    = None
    length      = None
    charset     = None
    start_line  = 1
    dict_active = None   # Path to downloaded dict (EN or DE)

    while True:
        section("MODE")
        _wh_keys  = [f"webhook_{n}" for n in range(3, 9)] + ["webhook_wordlist", "webhook_dict_en", "webhook_dict_de"]
        _wh_count = sum(1 for k in _wh_keys if settings.get(k))
        wh_state  = f"{GRN}{_wh_count}/9{RST}" if _wh_count else f"{YEL}none{RST}"
        _en_path  = Path(__file__).parent / "dict_en.txt"
        _de_path  = Path(__file__).parent / "dict_de.txt"
        _en_info  = f"{sum(1 for l in open(_en_path,encoding='utf-8',errors='ignore') if l.strip()):,} words" if _en_path.exists() else f"{YEL}not downloaded{RST}"
        _de_info  = f"{sum(1 for l in open(_de_path,encoding='utf-8',errors='ignore') if l.strip()):,} words" if _de_path.exists() else f"{YEL}not downloaded{RST}"
        print(f"  {DIM}  1  →  Combo      random combinations{RST}")
        print(f"  {DIM}  2  →  Wordlist   {_wl_info}{RST}")
        print(f"  {DIM}  4  →  EN Dict    English words  ({_en_info}){RST}")
        print(f"  {DIM}  5  →  DE Dict    German words   ({_de_info}){RST}")
        print(f"  {DIM}  3  →  Settings   webhooks {wh_state} configured{RST}")
        print()
        mode = prompt("Mode [1/2/3/4/5]", valid=["1", "2", "3", "4", "5"])

        # ── Settings ──────────────────────────────────────────────────────
        if mode == "3":
            _slots = [
                (f"webhook_{n}", f"{n}-char") for n in range(3, 9)
            ] + [
                ("webhook_wordlist", "Wordlist"),
                ("webhook_dict_en",  "EN Dict "),
                ("webhook_dict_de",  "DE Dict "),
            ]

            while True:
                section("SETTINGS")
                print(f"  {DIM}  Discord Webhooks  —  each slot posts to a separate channel{RST}")
                print()
                for i, (key, label) in enumerate(_slots, 1):
                    val  = settings.get(key, "")
                    disp = (
                        f"{WHT}{val[:46]}…{RST}" if len(val) > 50
                        else f"{WHT}{val}{RST}"  if val
                        else f"{YEL}not set{RST}"
                    )
                    print(f"  {DIM}  {i}  →  {label:<10}{RST}  {disp}")
                print()
                print(f"  {DIM}  0  →  Back{RST}")
                print()
                try:
                    raw_choice = input(f"  {CYN}›{RST}  Slot [0-7] : ").strip()
                except EOFError:
                    raw_choice = "0"

                if not raw_choice or raw_choice == "0":
                    break

                try:
                    idx = int(raw_choice) - 1
                    if not 0 <= idx < len(_slots):
                        raise ValueError
                except ValueError:
                    print(f"  {RED}Invalid choice.{RST}")
                    continue

                key, label = _slots[idx]
                cur = settings.get(key, "")
                print()
                print(f"  {DIM}  Configuring :{RST}  {WHT}{BLD}{label}{RST}")
                if cur:
                    print(f"  {DIM}  Current     :{RST}  {WHT}{cur}{RST}")
                else:
                    print(f"  {DIM}  Current     :{RST}  {YEL}not configured{RST}")
                print(f"  {DIM}  blank = keep  ·  'clear' = remove{RST}")
                print()
                try:
                    raw_wh = input(f"  {CYN}›{RST}  Webhook URL : ").strip()
                except EOFError:
                    raw_wh = ""
                if raw_wh.lower() == "clear":
                    settings.pop(key, None)
                    _save_settings(settings)
                    print(f"  {GRN}[✓]{RST}  Webhook removed.")
                elif raw_wh:
                    settings[key] = raw_wh
                    _save_settings(settings)
                    print(f"  {GRN}[✓]{RST}  Webhook saved.")
                    print()
                    try:
                        raw_test = input(
                            f"  {CYN}›{RST}  Test webhook now?  {DIM}[y/N]{RST} : "
                        ).strip().lower()
                    except EOFError:
                        raw_test = ""
                    if raw_test == "y":
                        print(f"  {DIM}  Sending test message ...{RST}")
                        ok, err = _webhook_post(raw_wh, "testuser", test=True)
                        if ok:
                            print(f"  {GRN}[✓]{RST}  Discord received the message!")
                        else:
                            print(f"  {RED}[!]{RST}  Failed: {err}")
                else:
                    print(f"  {DIM}  No changes.{RST}")
                print()

            continue   # back to mode selection

        # ── Wordlist ──────────────────────────────────────────────────────
        if mode == "2":
            section("WORDLIST")
            print(f"  {DIM}  Default : wordlist.txt  ({_wl_info}){RST}")
            print()
            try:
                raw = input(
                    f"  {CYN}›{RST}  Path  {DIM}[Enter = wordlist.txt]{RST} : "
                ).strip()
            except EOFError:
                raw = ""
            wordlist = raw if raw else str(_wl_default)
            if not Path(wordlist).exists():
                print(f"  {RED}File not found: {wordlist}{RST}")
                sys.exit(1)

            print()
            try:
                raw_sl = input(
                    f"  {CYN}›{RST}  Start from line  {DIM}[1]{RST} : "
                ).strip()
                start_line = int(raw_sl) if raw_sl else 1
                start_line = max(1, start_line)
            except (ValueError, EOFError):
                start_line = 1
            if start_line > 1:
                print(f"  {GRN}›{RST}  Skipping to line {start_line}")

        elif mode in ("4", "5"):
            # ── EN / DE Dictionary ────────────────────────────────────────
            lang     = "EN" if mode == "4" else "DE"
            dict_url = _EN_DICT_URL if mode == "4" else _DE_DICT_URL
            dest     = Path(__file__).parent / ("dict_en.txt" if mode == "4" else "dict_de.txt")
            section(f"{lang} DICTIONARY")
            if dest.exists():
                wc = sum(1 for ln in open(dest, encoding="utf-8", errors="ignore") if ln.strip())
                print(f"  {GRN}[✓]{RST}  Cached: {dest.name}  ({wc:,} words)")
                print(f"  {DIM}  1  →  Use cached  |  2  →  Re-download{RST}")
                print()
                try:
                    rc = input(f"  {CYN}›{RST}  [1/2] : ").strip()
                except EOFError:
                    rc = "1"
                if rc == "2":
                    if _download_dict(dict_url, dest, lang) == 0:
                        continue
            else:
                if _download_dict(dict_url, dest, lang) == 0:
                    continue
            dict_active = str(dest)

        else:
            # ── Length ────────────────────────────────────────────────────
            section("LENGTH")
            for n in range(3, 9):
                print(f"  {DIM}  {n}  →  {n}-char   (∞ random){RST}")
            print()
            length = int(prompt("Length [3-8]", default="4",
                                valid=[str(i) for i in range(3, 9)]))

            # ── Charset ───────────────────────────────────────────────────
            section("CHARSET")
            print(f"  {DIM}  1  →  Letters   a-z         (random lowercase){RST}")
            print(f"  {DIM}  2  →  Digits    0-9         (random digits){RST}")
            print(f"  {DIM}  3  →  Mixed     a-z + 0-9   (random mix){RST}")
            print()
            cs = prompt("Charset [1/2/3]", default="3", valid=["1", "2", "3"])
            charset = (
                string.ascii_lowercase                    if cs == "1" else
                string.digits                             if cs == "2" else
                string.ascii_lowercase + string.digits
            )

        break   # mode selected, proceed

    # ── Delay ─────────────────────────────────────────────────────────────
    section("DELAY")
    print(f"  {DIM}  Recommended: 0.3 – 1.0 s  (too fast → WhatsApp may throttle){RST}")
    print()
    try:
        raw   = input(f"  {CYN}›{RST}  Seconds per check  {DIM}[0.5]{RST} : ").strip()
        delay = float(raw) if raw else 0.5
        delay = max(0.0, delay)
    except (ValueError, EOFError):
        delay = 0.5
    print(f"  {GRN}›{RST}  {delay:.1f} s / check")

    # ── Ready ─────────────────────────────────────────────────────────────
    section("READY")
    print(f"  {YEL}[!]{RST}  Open WhatsApp")
    print(f"       Settings  →  Profile  →  Username  →  pencil icon (edit)")
    input(f"\n  {CYN}›{RST}  Press ENTER when the username screen is open ... ")

    sniper         = Sniper(delay=delay)
    # Pick the webhook for the active mode/length
    if dict_active:
        key = "webhook_dict_en" if mode == "4" else "webhook_dict_de"
        sniper.webhook = settings.get(key) or None
    elif wordlist:
        sniper.webhook = settings.get("webhook_wordlist") or None
    else:
        sniper.webhook = settings.get(f"webhook_{length}") or None
    sniper.calibrate()
    sniper.run(length=length, charset=charset, wordlist=wordlist,
               start_line=start_line, dict_random=dict_active)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        _w("\033[r")   # always reset scroll region on exit
        print("\n\n  Aborted.")
        sys.exit(0)


