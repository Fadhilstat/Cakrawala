from __future__ import annotations

import base64
import ctypes
import json
import os
import secrets
import sys
import threading
from ctypes import wintypes
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, Button, Frame, Label, Text, Tk, messagebox, simpledialog

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cakrawala.personal.mt5_collector import (  # noqa: E402
    DEFAULT_SYNC_URL,
    MT5CollectorError,
    collect_payload,
    mask_account_name,
    post_payload,
)

APP_TITLE = "Cakrawala MT5 Collector"
APP_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Cakrawala"
CONFIG_PATH = APP_DIR / "mt5_collector.json"
DPAPI_DESCRIPTION = "Cakrawala MT5 Collector token"


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def _blob_from_bytes(data: bytes) -> tuple[DATA_BLOB, ctypes.Array[ctypes.c_char]]:
    buffer = ctypes.create_string_buffer(data)
    blob = DATA_BLOB(
        len(data),
        ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)),
    )
    return blob, buffer


def _protect_secret(value: str) -> str:
    if os.name != "nt":
        raise RuntimeError("Windows secret protection is required.")
    source, source_buffer = _blob_from_bytes(value.encode("utf-8"))
    del source_buffer
    output = DATA_BLOB()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    success = crypt32.CryptProtectData(
        ctypes.byref(source),
        DPAPI_DESCRIPTION,
        None,
        None,
        None,
        0x01,
        ctypes.byref(output),
    )
    if not success:
        raise ctypes.WinError()
    try:
        protected = ctypes.string_at(output.pbData, output.cbData)
        return base64.b64encode(protected).decode("ascii")
    finally:
        kernel32.LocalFree(output.pbData)


def _unprotect_secret(encoded: str) -> str:
    if os.name != "nt":
        raise RuntimeError("Windows secret protection is required.")
    protected = base64.b64decode(encoded.encode("ascii"), validate=True)
    source, source_buffer = _blob_from_bytes(protected)
    del source_buffer
    output = DATA_BLOB()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    success = crypt32.CryptUnprotectData(
        ctypes.byref(source),
        None,
        None,
        None,
        None,
        0x01,
        ctypes.byref(output),
    )
    if not success:
        raise ctypes.WinError()
    try:
        plain = ctypes.string_at(output.pbData, output.cbData)
        return plain.decode("utf-8")
    finally:
        kernel32.LocalFree(output.pbData)


def _save_token(token: str) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "sync_url": DEFAULT_SYNC_URL,
        "protected_token": _protect_secret(token),
    }
    CONFIG_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_token() -> str | None:
    if not CONFIG_PATH.exists():
        return None
    try:
        payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if payload.get("version") != 1:
            return None
        if payload.get("sync_url") != DEFAULT_SYNC_URL:
            return None
        encoded = str(payload.get("protected_token", ""))
        return _unprotect_secret(encoded) if encoded else None
    except (OSError, ValueError, RuntimeError, ctypes.Error):
        return None


def _new_token() -> str:
    return secrets.token_urlsafe(48)


def _summary(payload: dict[str, object]) -> str:
    account = payload.get("account")
    account_name = "account"
    if isinstance(account, dict):
        account_name = mask_account_name(str(account.get("account_name", "account")))
    positions = payload.get("positions")
    deals = payload.get("deals")
    position_count = len(positions) if isinstance(positions, list) else 0
    deal_count = len(deals) if isinstance(deals, list) else 0
    return (
        f"MT5 read-only test passed for {account_name}.\n"
        f"Open positions: {position_count}\n"
        f"Closed positions in selected history window: {deal_count}"
    )


class CollectorApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("620x430")
        self.root.minsize(560, 380)

        Label(
            root,
            text=APP_TITLE,
            font=("Segoe UI", 18, "bold"),
        ).pack(padx=20, pady=(22, 4), anchor="w")
        Label(
            root,
            text=(
                "Reads your already logged-in MetaTrader 5 terminal. "
                "It does not place, modify, or close orders."
            ),
            font=("Segoe UI", 10),
            wraplength=570,
            justify="left",
        ).pack(padx=20, pady=(0, 14), anchor="w")

        button_row = Frame(root)
        button_row.pack(fill="x", padx=20, pady=4)
        self.test_button = Button(
            button_row,
            text="1. Test MT5 Read-Only",
            command=self.test_mt5,
            width=22,
        )
        self.test_button.pack(side=LEFT, padx=(0, 8))
        self.setup_button = Button(
            button_row,
            text="2. Configure Private Sync",
            command=self.configure_sync,
            width=22,
        )
        self.setup_button.pack(side=LEFT, padx=8)
        self.sync_button = Button(
            button_row,
            text="3. Sync Now",
            command=self.sync_now,
            width=18,
        )
        self.sync_button.pack(side=RIGHT, padx=(8, 0))

        self.status = Label(
            root,
            text=self._initial_status(),
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        self.status.pack(fill="x", padx=20, pady=(14, 6))

        self.log = Text(root, height=13, wrap="word", font=("Consolas", 10))
        self.log.pack(fill=BOTH, expand=True, padx=20, pady=(0, 20))
        self._write(
            "Keep MetaTrader 5 open and logged in. Start with the read-only test.\n"
        )

    def _initial_status(self) -> str:
        return "Private sync token: configured" if _load_token() else "Private sync token: not configured"

    def _write(self, text: str) -> None:
        self.log.insert(END, text)
        self.log.see(END)

    def _set_busy(self, busy: bool, label: str | None = None) -> None:
        state = "disabled" if busy else "normal"
        for button in (self.test_button, self.setup_button, self.sync_button):
            button.config(state=state)
        if label:
            self.status.config(text=label)

    def _run_background(self, task: callable, label: str) -> None:
        self._set_busy(True, label)

        def runner() -> None:
            try:
                task()
            except Exception as exc:
                self.root.after(0, self._handle_error, exc)
            finally:
                self.root.after(0, self._set_busy, False, self._initial_status())

        threading.Thread(target=runner, daemon=True).start()

    def _handle_error(self, exc: Exception) -> None:
        message = str(exc) if isinstance(exc, MT5CollectorError) else type(exc).__name__
        self._write(f"ERROR: {message}\n")
        messagebox.showerror(APP_TITLE, message)

    def test_mt5(self) -> None:
        def task() -> None:
            payload = collect_payload(history_days=120)
            summary = _summary(payload)
            self.root.after(0, self._write, summary + "\n")
            self.root.after(0, messagebox.showinfo, APP_TITLE, summary)

        self._run_background(task, "Testing local MT5 connection...")

    def configure_sync(self) -> None:
        current = _load_token()
        if current:
            replace = messagebox.askyesno(
                APP_TITLE,
                "A protected sync token already exists on this Windows account. Replace it?",
            )
            if not replace:
                return

        token = simpledialog.askstring(
            APP_TITLE,
            (
                "Paste the same PERSONAL_FOREX_INGEST_TOKEN stored in Vercel.\n\n"
                "Leave this blank and press OK if you want the collector to generate a new token."
            ),
            show="*",
            parent=self.root,
        )
        if token is None:
            return
        token = token.strip()
        generated = False
        if not token:
            token = _new_token()
            generated = True
        if len(token) < 32:
            messagebox.showerror(APP_TITLE, "Use a private sync token with at least 32 characters.")
            return

        try:
            _save_token(token)
        except Exception as exc:
            self._handle_error(exc)
            return

        self.status.config(text=self._initial_status())
        if generated:
            self.root.clipboard_clear()
            self.root.clipboard_append(token)
            self.root.update()
            messagebox.showinfo(
                APP_TITLE,
                (
                    "A new token was generated and copied to your clipboard.\n\n"
                    "Add it to Vercel as PERSONAL_FOREX_INGEST_TOKEN, Production only, "
                    "then redeploy. The token is protected locally with Windows DPAPI."
                ),
            )
        else:
            messagebox.showinfo(
                APP_TITLE,
                "Token saved with Windows DPAPI for this Windows account.",
            )

    def sync_now(self) -> None:
        token = _load_token()
        if not token:
            messagebox.showwarning(
                APP_TITLE,
                "Configure the private sync token before uploading data.",
            )
            return

        def task() -> None:
            payload = collect_payload(history_days=120)
            result = post_payload(token, payload)
            line = (
                "Sync complete. "
                f"positions inserted={result.get('inserted_positions', 0)}, "
                f"deals inserted={result.get('inserted_deals', 0)}, "
                f"duplicate_batch={result.get('duplicate_batch', False)}"
            )
            self.root.after(0, self._write, line + "\n")
            self.root.after(0, messagebox.showinfo, APP_TITLE, line)

        self._run_background(task, "Collecting and syncing private MT5 data...")


def main() -> None:
    if os.name != "nt":
        raise SystemExit("Cakrawala MT5 Collector is intended for Windows.")
    root = Tk()
    CollectorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
