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
import string
import subprocess
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime


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


def _print_header(total=0):
    """
    Print the full header (logo + initial empty stats bar).
    Returns (stats_row, scroll_start) — both 1-based terminal row numbers.
    """
    row = 1   # cursor starts at row 1 after _clr()

    def ln(text=""):
        nonlocal row
        print(text)
        row += 1

    ln()
    for art_line in _ART:
        ln(f"{CYN}{BLD}{art_line}{RST}")
    ln()
    ln(f"{GRN}{BLD}{'U S E R N A M E   S N I P E R':^50}{RST}")
    ln(f"{YEL}{'by ' + _AUTHOR + '  ·  v1.0':^50}{RST}")
    ln()
    ln(f"{DIM}{_hr()}{RST}")

    stats_row = row
    ln(_fmt_stats(0, 0, 0.0, 0.0, total))  # placeholder stats

    ln(f"{DIM}{_hr()}{RST}")

    scroll_start = row   # cursor is here; results go from this row onward

    return stats_row, scroll_start


def _fmt_stats(hits, checked, speed, elapsed, total=0):
    h = int(elapsed // 3600)
    m = int((elapsed % 3600) // 60)
    s = int(elapsed % 60)
    if total:
        chk_str = f"{CYN}│{RST}  {checked}/{total}  "
    else:
        chk_str = f"{CYN}│{RST}  CHECKED: {checked:<7}  "
    return (
        f"  {DIM}┤{RST} "
        f"{GRN}{BLD}AVAILABLE: {hits:<5}{RST}  "
        + chk_str +
        f"{CYN}│{RST}  "
        f"SPEED: {speed:>4.1f}/s  "
        f"{CYN}│{RST}  "
        f"TIME: {h:02d}:{m:02d}:{s:02d}  "
        f"{DIM}├{RST}"
    )


def _update_stats(stats_row, hits, checked, speed, elapsed, total=0):
    """Overwrite the stats bar without moving the results cursor."""
    text = _fmt_stats(hits, checked, speed, elapsed, total)
    _w(f"\033[s"              # save cursor
       f"\033[{stats_row};1H" # go to stats row
       f"\033[2K"             # clear line
       f"{text}"              # new stats
       f"\033[u")             # restore cursor


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
                self._adb("shell", "input", "tap",
                          str(self._field_x), str(self._field_y))
                time.sleep(0.2)
            self._adb("shell", "input", "keyevent",
                      "KEYCODE_MOVE_END", *["KEYCODE_DEL"] * 30)
            time.sleep(0.1)
            self._adb("shell", "input", "text", username)
            time.sleep(0.15)
            return True
        except Exception:
            return False

    # ── UIAutomator ───────────────────────────────────────────────────────────

    def _find_field(self):
        try:
            self._adb("shell", "uiautomator", "dump",
                      "--compressed", "/sdcard/uidump.xml")
            time.sleep(0.5)
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
        self._adb("shell", "uiautomator", "dump", "--compressed",
                  "/sdcard/" + name)
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
                "username not available",
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
            time.sleep(1.8 if first else 0.7)
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

    def gen_3char(self):
        for c in itertools.product(string.ascii_lowercase + string.digits, repeat=3):
            yield "".join(c)

    def gen_4char(self):
        for c in itertools.product(string.ascii_lowercase + string.digits, repeat=4):
            yield "".join(c)

    def gen_wordlist(self, path):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                u = line.strip()
                if u and 3 <= len(u) <= 25:
                    yield u

    # ── Output ────────────────────────────────────────────────────────────────

    def _save_hit(self, username):
        ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        path = Path(__file__).parent / "hits.txt"
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{ts}]  {username}\n")

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self, mode, wordlist=None):
        gen_map = {
            1: (self.gen_3char,                    f"3-char  ({36**3:,} combos)"),
            2: (self.gen_4char,                    f"4-char  ({36**4:,} combos)"),
            3: (lambda: self.gen_wordlist(wordlist), "wordlist"),
        }
        gen_fn, label = gen_map[mode]

        # Count total for progress display
        if mode == 1:
            total = 36 ** 3
        elif mode == 2:
            total = 36 ** 4
        else:
            total = sum(
                1 for line in open(wordlist, encoding="utf-8", errors="ignore")
                if line.strip() and 3 <= len(line.strip()) <= 25
            )

        self.t0 = time.time()

        # ── Full-screen persistent layout ─────────────────────────────────────
        _clr()
        stats_row, scroll_start = _print_header(total)

        # Activate scroll region: only lines from scroll_start to bottom scroll
        _w(f"\033[{scroll_start};{_term_h()}r")
        # Position cursor at the top of the scroll region
        _w(f"\033[{scroll_start};1H")

        try:
            for username in gen_fn():
                res = self.check(username)
                ts  = _ts()

                if res is None:
                    print(f"  {DIM}[{ts}]  ?  {username}{RST}")
                elif res["available"]:
                    self.hits.append(username)
                    self._save_hit(username)
                    print(
                        f"  {GRN}{BLD}[{ts}]  ★  "
                        f"{username.upper():<20}  ◄── AVAILABLE!{RST}"
                    )
                else:
                    print(f"  {DIM}[{ts}]  ✗  {username}{RST}")

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

        # ── Summary ──────────────────────────────────────────────────────────
        elapsed = time.time() - self.t0
        speed   = self.checked / elapsed if elapsed > 0 else 0.0
        print()
        print(f"  {DIM}{_hr()}{RST}")
        print(f"  {WHT}{BLD}RESULTS{RST}")
        print(f"  {DIM}{_hr('─', 40)}{RST}")
        print(f"  Checked    :  {self.checked}")
        print(f"  Available  :  {GRN}{BLD}{len(self.hits)}{RST}")
        print(f"  Speed      :  {speed:.1f} checks/s")
        print(f"  Duration   :  {int(elapsed // 60)}m {int(elapsed % 60)}s")
        if self.hits:
            print(f"  {DIM}{_hr('─', 40)}{RST}")
            for h in self.hits:
                print(f"  {GRN}  ★  {h}{RST}")
            print(f"\n  {DIM}→ Saved to hits.txt{RST}")
        print(f"  {DIM}{_hr()}{RST}")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # Interactive setup (no scroll region yet — just print normally)
    _clr()
    for line in _ART:
        print(f"{CYN}{BLD}{line}{RST}")
    print()
    print(f"{GRN}{BLD}{'U S E R N A M E   S N I P E R':^50}{RST}")
    print(f"{YEL}{'by ' + _AUTHOR + '  ·  v1.0':^50}{RST}")
    print()
    print(f"{DIM}{_hr()}{RST}")
    print()

    # Count default wordlist
    _wl_default = Path(__file__).parent / "wordlist.txt"
    if _wl_default.exists():
        _wl_count = sum(
            1 for line in open(_wl_default, encoding="utf-8", errors="ignore")
            if line.strip() and 3 <= len(line.strip()) <= 25
        )
        _wl_info = f"  ·  {_wl_count:,} words"
    else:
        _wl_info = ""

    # Mode
    print(f"  {WHT}Mode{RST}")
    print(f"  {DIM}  1  →  3-character  (aaa … 999  ·  {36**3:,} combos){RST}")
    print(f"  {DIM}  2  →  4-character  (aaaa … 9999  ·  {36**4:,} combos){RST}")
    print(f"  {DIM}  3  →  Wordlist  (wordlist.txt{_wl_info}){RST}")
    print()

    try:
        mode = int(input(f"  {CYN}›{RST}  Mode [1/2/3] : ").strip())
        if mode not in (1, 2, 3):
            raise ValueError
    except (ValueError, EOFError):
        print(f"  {RED}Invalid.{RST}")
        sys.exit(1)

    wordlist = None
    if mode == 3:
        wordlist = input(f"  {CYN}›{RST}  Wordlist path : ").strip()
        if not Path(wordlist).exists():
            print(f"  {RED}File not found.{RST}")
            sys.exit(1)

    # Delay
    print()
    try:
        raw   = input(
            f"  {CYN}›{RST}  Delay per check (seconds)  "
            f"{DIM}[default: 0.5]{RST} : "
        ).strip()
        delay = float(raw) if raw else 0.5
        delay = max(0.0, delay)
    except (ValueError, EOFError):
        delay = 0.5

    print(f"  {GRN}→{RST}  {delay} s / check")
    print()

    # Navigate
    print(f"  {YEL}[!]{RST}  Open WhatsApp  →  Settings → Profile → Username → ✎")
    input(f"\n  {CYN}›{RST}  Press ENTER when the username edit screen is open ...")

    sniper = Sniper(delay=delay)
    sniper.calibrate()
    sniper.run(mode, wordlist)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        _w("\033[r")   # always reset scroll region on exit
        print("\n\n  Aborted.")
        sys.exit(0)


# Standard library only — zero external dependencies
import sys, time, itertools, string, subprocess, re
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# INTEGRITY / BRANDING
# The author identity is stored encoded so it cannot be found by plain-text
# search.  Modifying it causes a silent exit on startup.
# ─────────────────────────────────────────────────────────────────────────────

_C = (83, 71, 86, 116, 97, 87, 108, 54, 90, 81, 61, 61)   # do not change


def _load():
    import base64
    d = base64.b64decode(bytes(_C)).decode()
    # Two independent checks: length guard + weighted-character fingerprint
    if len(d) != 7:
        import os; os._exit(0)
    if sum(ord(x) * (n + 1) for n, x in enumerate(d)) != 2985:
        import os; os._exit(0)
    return d


_AUTHOR = _load()   # populated once at startup; script exits silently if tampered


# ─────────────────────────────────────────────────────────────────────────────
# TERMINAL COLOURS
# ─────────────────────────────────────────────────────────────────────────────

GRN = "\033[92m"   # bright green   — hits / success
RED = "\033[91m"   # bright red     — errors
YEL = "\033[93m"   # yellow         — warnings / prompts
CYN = "\033[96m"   # cyan           — stats / headers
WHT = "\033[97m"   # bright white   — section headings
MAG = "\033[95m"   # magenta        — accent
DIM = "\033[2m"    # dim            — taken usernames / timestamps
BLD = "\033[1m"    # bold
RST = "\033[0m"    # reset all


# ─────────────────────────────────────────────────────────────────────────────
# LOGO
# ─────────────────────────────────────────────────────────────────────────────

_LOGO_ROWS = [
    ("╔" + "═" * 62 + "╗",                                          "dim"),
    ("║" + " " * 62 + "║",                                          "dim"),
    ("║    ██╗    ██╗ █████╗       ███████╗███╗   ██╗██╗             ║", "art"),
    ("║    ██║    ██║██╔══██╗      ██╔════╝████╗  ██║██║             ║", "art"),
    ("║    ██║ █╗ ██║███████║      ███████╗██╔██╗ ██║██║             ║", "art"),
    ("║    ██║███╗██║██╔══██║      ╚════██║██║╚██╗██║╚═╝             ║", "art"),
    ("║    ╚███╔███╔╝██║  ██║      ███████║██║ ╚████║██╗             ║", "art"),
    ("║     ╚══╝╚══╝ ╚═╝  ╚═╝      ╚══════╝╚═╝  ╚═══╝╚═╝             ║", "art"),
    ("║" + " " * 62 + "║",                                          "dim"),
    ("║              U S E R N A M E   S N I P E R                  ║", "title"),
    (f"║                      by {_AUTHOR}  ·  v1.0"
     + " " * (62 - 26 - len(_AUTHOR)) + "║",                        "author"),
    ("╚" + "═" * 62 + "╝",                                          "dim"),
]

_STYLE = {
    "dim":    lambda s: f"  {DIM}{s}{RST}",
    "art":    lambda s: f"  {CYN}{s}{RST}",
    "title":  lambda s: f"  {GRN}{BLD}{s}{RST}",
    "author": lambda s: f"  {YEL}{s}{RST}",
}


def _print_logo():
    print()
    for text, style in _LOGO_ROWS:
        print(_STYLE[style](text))
    print()


def _hr(ch="─", n=64):
    return "  " + ch * n


def _ts():
    return datetime.now().strftime("%H:%M:%S")


# ─────────────────────────────────────────────────────────────────────────────
# SNIPER
# ─────────────────────────────────────────────────────────────────────────────

class Sniper:

    # Button label text across all supported WhatsApp locales
    _SAVE_TEXTS = {
        "save",         # English
        "speichern",    # German
        "guardar",      # Spanish
        "enregistrer",  # French
        "salvar",       # Portuguese
        "\u0441\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c",  # Russian (сохранить)
        "\u062d\u0641\u0638",                                        # Arabic  (حفظ)
        "\u4fdd\u5b58",                                              # Chinese/Japanese (保存)
        "\uc800\uc7a5",                                              # Korean  (저장)
    }

    def __init__(self, delay=0.5):
        self.delay     = delay
        self.hits      = []
        self.checked   = 0
        self.t0        = None
        self._field_x  = None
        self._field_y  = None
        self._baseline = None

    # ── ADB ───────────────────────────────────────────────────────────────────

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
                print(f"  {GRN}[+]{RST} Device   : {devs[0].split(chr(9))[0]}")
                return True
        print(f"  {RED}[!]{RST} No ADB device found.")
        print(f"  {DIM}    Connect via USB and enable USB debugging.{RST}")
        return False

    def _adb_input(self, username):
        """Type `username` into the focused field via ADB."""
        try:
            if self._field_x is not None:
                self._adb("shell", "input", "tap",
                          str(self._field_x), str(self._field_y))
                time.sleep(0.2)
            # Clear field: move to end then delete 30 chars in a single call
            # (avoids the race condition of separate select + delete calls)
            self._adb("shell", "input", "keyevent",
                      "KEYCODE_MOVE_END", *["KEYCODE_DEL"] * 30)
            time.sleep(0.1)
            self._adb("shell", "input", "text", username)
            time.sleep(0.15)
            return True
        except Exception:
            return False

    # ── UIAutomator ───────────────────────────────────────────────────────────

    def _find_field(self):
        """Locate the username EditText coordinates via UIAutomator dump."""
        try:
            self._adb("shell", "uiautomator", "dump",
                      "--compressed", "/sdcard/uidump.xml")
            time.sleep(0.5)
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
        self._adb("shell", "uiautomator", "dump", "--compressed",
                  "/sdcard/" + name)
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
        print(f"  {GRN}[+]{RST} Baseline : {len(self._baseline)} nodes captured")

    # ── Detection ─────────────────────────────────────────────────────────────

    def _find_save_btn(self, nodes):
        """
        Return True (available), False (taken), or None (not visible yet).

        Strategy 0 : explicit status text in the accessibility tree
        Strategy 1 : resource-id match  (works if WhatsApp kept View IDs)
        Strategy 2 : save-button label  → find its smallest clickable container
                     and read that container's  .enabled  attribute
        Strategy 3 : baseline diff      → any new clickable node below the field
        """
        fy    = self._field_y or 300
        label = None

        for key, n in nodes.items():
            text = n["text"].lower()
            rid  = n["rid"]

            # 0a  explicit "not available" message
            if text and any(p in text for p in (
                "nicht verf\u00fcgbar", "not available",
                "already taken", "bereits vergeben",
                "username not available",
            )):
                return False

            # 0b  explicit "available" message
            if text in (
                "verf\u00fcgbar", "username available",
                "benutzername verf\u00fcgbar",
                "dieser benutzername ist verf\u00fcgbar",
            ):
                return True

            # 1  resource-id
            if ("upr_edit_save_button" in rid or
                    ("save_button" in rid
                     and "container" not in rid
                     and "stub"      not in rid)):
                return n["enabled"]

            # remember the label node for strategy 2
            if text in self._SAVE_TEXTS:
                try:
                    m = re.findall(r'\[(\d+),(\d+)\]', n["bounds"])
                    if m and int(m[0][1]) >= fy - 100:
                        label = n
                except Exception:
                    pass

        # 2  smallest CLICKABLE container of the save-button label
        #
        #    The label TextView always has enabled=True — it's just text.
        #    The real button state lives on its clickable parent View.
        #    When username is taken  → parent.enabled = False
        #    When username is free   → parent.enabled = True
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

        # 3  baseline diff
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

        return None   # button not in dump yet — still loading

    def _poll(self, username, total_wait=5.5):
        """Poll UIAutomator until result is known or timeout."""
        deadline = time.time() + total_wait
        first    = True
        while time.time() < deadline:
            # First iteration: allow WhatsApp debounce + server round-trip
            time.sleep(1.8 if first else 0.7)
            first = False
            state = self._find_save_btn(self._parse_nodes(self._dump_ui()))
            if state is True:
                return {"available": True,  "username": username}
            if state is False:
                return {"available": False, "username": username}
        return None

    # ── Setup ─────────────────────────────────────────────────────────────────

    def calibrate(self):
        print(_hr("═"))
        print(f"  {WHT}{BLD}SETUP{RST}")
        print(_hr("═"))

        if not self._check_adb():
            sys.exit(1)

        print(f"  {DIM}[*]{RST} Detecting username field ...")
        if self._find_field():
            print(f"  {GRN}[+]{RST} Field at ({self._field_x}, {self._field_y})")
        else:
            print(f"  {YEL}[!]{RST} Auto-detect failed — enter coordinates manually:")
            try:
                x = input(f"      {CYN}X{RST} (default 540): ").strip()
                y = input(f"      {CYN}Y{RST} (default 600): ").strip()
                self._field_x = int(x) if x else 540
                self._field_y = int(y) if y else 600
            except (ValueError, EOFError):
                self._field_x, self._field_y = 540, 600
            print(f"  {GRN}[+]{RST} Using ({self._field_x}, {self._field_y})")

        print(f"  {DIM}[*]{RST} Capturing UI baseline ...")
        self._capture_baseline()
        print(_hr("─"))
        print()

    # ── Core ──────────────────────────────────────────────────────────────────

    def check(self, username):
        """Check one username. Returns {'available': bool, 'username': str} or None."""
        self.checked += 1
        if not self._adb_input(username):
            return None
        res = self._poll(username)
        if res is None:
            self._find_field()   # field may have lost focus; silently recalibrate
        return res

    # ── Generators ────────────────────────────────────────────────────────────

    def gen_3char(self):
        for c in itertools.product(string.ascii_lowercase + string.digits, repeat=3):
            yield "".join(c)

    def gen_4char(self):
        for c in itertools.product(string.ascii_lowercase + string.digits, repeat=4):
            yield "".join(c)

    def gen_wordlist(self, path):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                u = line.strip()
                if u and 3 <= len(u) <= 25:
                    yield u

    # ── Output / stats ────────────────────────────────────────────────────────

    def _save_hit(self, username):
        ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        path = Path(__file__).parent / "hits.txt"
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{ts}]  {username}\n")

    def _stats_line(self):
        elapsed = time.time() - (self.t0 or time.time())
        speed   = self.checked / elapsed if elapsed > 0 else 0.0
        h = int(elapsed // 3600)
        m = int((elapsed % 3600) // 60)
        s = int(elapsed % 60)
        return (
            f"  {CYN}┤ {GRN}HIT: {len(self.hits):<4}{RST}{CYN}"
            f" │ CHECKED: {self.checked:<7}"
            f" │ {speed:>4.1f} chk/s"
            f" │ {h:02d}:{m:02d}:{s:02d} ├{RST}"
        )

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self, mode, wordlist=None):
        gen_map = {
            1: (self.gen_3char,
                f"3-char  ({36**3:,} combinations)"),
            2: (self.gen_4char,
                f"4-char  ({36**4:,} combinations)"),
            3: (lambda: self.gen_wordlist(wordlist),
                "wordlist"),
        }
        gen_fn, label = gen_map[mode]
        self.t0 = time.time()

        print(_hr("═"))
        print(f"  {WHT}{BLD}SCANNING{RST}")
        print(_hr("─"))
        print(f"  Mode    {CYN}:{RST}  {label}")
        print(f"  Delay   {CYN}:{RST}  {self.delay} s / check")
        print(f"  Output  {CYN}:{RST}  hits.txt")
        print(_hr("═"))
        print()

        try:
            for username in gen_fn():
                res = self.check(username)
                ts  = _ts()

                if res is None:
                    print(f"  {DIM}[{ts}]  ?  {username}{RST}")
                elif res["available"]:
                    self.hits.append(username)
                    self._save_hit(username)
                    print(
                        f"\n"
                        f"  {GRN}{BLD}  ★  [{ts}]  "
                        f"{username.upper():<20}  ◄  AVAILABLE!{RST}\n"
                    )
                else:
                    print(f"  {DIM}[{ts}]  ✗  {username}{RST}")

                # Stats separator every 25 checks
                if self.checked % 25 == 0:
                    print()
                    print(self._stats_line())
                    print()

                if self.delay > 0:
                    time.sleep(self.delay)

        except KeyboardInterrupt:
            print(f"\n\n  {YEL}Stopped.{RST}")

        # ── Final summary ────────────────────────────────────────────────────
        elapsed = time.time() - self.t0
        speed   = self.checked / elapsed if elapsed > 0 else 0.0
        print()
        print(_hr("═"))
        print(f"  {WHT}{BLD}RESULTS{RST}")
        print(_hr("─"))
        print(f"  Checked    {CYN}:{RST}  {self.checked}")
        print(f"  Available  {CYN}:{RST}  {GRN}{BLD}{len(self.hits)}{RST}")
        print(f"  Speed      {CYN}:{RST}  {speed:.1f} checks/s")
        print(f"  Duration   {CYN}:{RST}  {int(elapsed // 60)}m {int(elapsed % 60)}s")
        if self.hits:
            print(_hr("─"))
            for h in self.hits:
                print(f"  {GRN}  ★  {h}{RST}")
            print(f"\n  {DIM}→ Saved to hits.txt{RST}")
        print(_hr("═"))


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    _print_logo()
    print(_hr("─"))
    print()

    # ── Mode ────────────────────────────────────────────────────────────────
    print(f"  {WHT}Mode{RST}")
    print(f"  {DIM}  1  →  3-character  (aaa … 999  ·  {36**3:,} combos){RST}")
    print(f"  {DIM}  2  →  4-character  (aaaa … 9999  ·  {36**4:,} combos){RST}")
    print(f"  {DIM}  3  →  Wordlist  (wordlist.txt){RST}")
    print()

    try:
        mode = int(input(f"  {CYN}›{RST}  Mode [1/2/3] : ").strip())
        if mode not in (1, 2, 3):
            raise ValueError
    except (ValueError, EOFError):
        print(f"  {RED}Invalid selection — exiting.{RST}")
        sys.exit(1)

    wordlist = None
    if mode == 3:
        wordlist = input(f"  {CYN}›{RST}  Wordlist path : ").strip()
        if not Path(wordlist).exists():
            print(f"  {RED}File not found.{RST}")
            sys.exit(1)

    # ── Delay ───────────────────────────────────────────────────────────────
    print()
    try:
        raw   = input(
            f"  {CYN}›{RST}  Delay between checks in seconds  {DIM}[default: 0.5]{RST} : "
        ).strip()
        delay = float(raw) if raw else 0.5
        delay = max(0.0, delay)
    except (ValueError, EOFError):
        delay = 0.5

    print(f"  {GRN}→{RST}  {delay} s / check")
    print()

    # ── Navigate ────────────────────────────────────────────────────────────
    print(f"  {YEL}[!]{RST}  Open WhatsApp and go to:")
    print(f"  {DIM}       Settings → Profile → Username → ✎  (edit icon){RST}")
    input(f"\n  {CYN}›{RST}  Press ENTER when the username edit screen is open ...")

    # ── Run ─────────────────────────────────────────────────────────────────
    sniper = Sniper(delay=delay)
    sniper.calibrate()
    sniper.run(mode, wordlist)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Aborted.")
        sys.exit(0)
