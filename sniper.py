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

    def gen_combo(self, length, charset):
        """All combos of `length` chars from `charset`, starting at a random index.
        Uses the nth-element trick — O(1) memory, covers every combo exactly once."""
        base  = len(charset)
        total = base ** length
        start = random.randint(0, total - 1)

        def nth(n):
            chars = []
            for _ in range(length):
                chars.append(charset[n % base])
                n //= base
            return "".join(reversed(chars))

        for i in range(total):
            yield nth((start + i) % total)

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

    def run(self, length=None, charset=None, wordlist=None):
        if wordlist:
            gen_fn        = lambda: self.gen_wordlist(wordlist)
            total         = sum(
                1 for line in open(wordlist, encoding="utf-8", errors="ignore")
                if line.strip() and 3 <= len(line.strip()) <= 25
            )
            mode_str      = "wordlist"
            charset_label = f"{total:,} words"
        else:
            gen_fn        = lambda: self.gen_combo(length, charset)
            total         = len(charset) ** length
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

        try:
            for username in gen_fn():
                res = self.check(username)
                ts  = _ts()

                if res is None:
                    print(f"  {DIM}[{ts}]  ?  {YEL}{username}{RST}")
                elif res["available"]:
                    self.hits.append(username)
                    self._save_hit(username)
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
                print(f"  {GRN}  >>  {h}{RST}")
            print(f"\n  {DIM}→ Saved to hits.txt{RST}")
        print(f"  {DIM}{_hr()}{RST}")


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

    # ── Mode ──────────────────────────────────────────────────────────────
    section("MODE")
    print(f"  {DIM}  1  →  Combo      bruteforce all combinations{RST}")
    print(f"  {DIM}  2  →  Wordlist   {_wl_info}{RST}")
    print()
    mode = prompt("Mode [1/2]", valid=["1", "2"])

    wordlist = None
    length   = None
    charset  = None

    if mode == "2":
        # ── Wordlist ──────────────────────────────────────────────────────
        section("WORDLIST")
        print(f"  {DIM}  Default : wordlist.txt  ({_wl_info}){RST}")
        print()
        try:
            raw = input(f"  {CYN}›{RST}  Path  {DIM}[Enter = wordlist.txt]{RST} : ").strip()
        except EOFError:
            raw = ""
        wordlist = raw if raw else str(_wl_default)
        if not Path(wordlist).exists():
            print(f"  {RED}File not found: {wordlist}{RST}")
            sys.exit(1)

    else:
        # ── Length ────────────────────────────────────────────────────────
        section("LENGTH")
        for n in range(3, 9):
            print(f"  {DIM}  {n}  →  {n}-char   ({36**n:>12,} combos  [mixed]){RST}")
        print()
        length = int(prompt("Length [3-8]", default="4",
                            valid=[str(i) for i in range(3, 9)]))

        # ── Charset ───────────────────────────────────────────────────────
        section("CHARSET")
        print(f"  {DIM}  1  →  Letters   a-z         ({26**length:>12,} combos){RST}")
        print(f"  {DIM}  2  →  Digits    0-9         ({10**length:>12,} combos){RST}")
        print(f"  {DIM}  3  →  Mixed     a-z + 0-9   ({36**length:>12,} combos){RST}")
        print()
        cs = prompt("Charset [1/2/3]", default="3", valid=["1", "2", "3"])
        charset = (
            string.ascii_lowercase                    if cs == "1" else
            string.digits                             if cs == "2" else
            string.ascii_lowercase + string.digits
        )

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

    sniper = Sniper(delay=delay)
    sniper.calibrate()
    sniper.run(length=length, charset=charset, wordlist=wordlist)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        _w("\033[r")   # always reset scroll region on exit
        print("\n\n  Aborted.")
        sys.exit(0)


