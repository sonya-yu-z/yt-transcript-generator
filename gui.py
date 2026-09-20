#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox


REPO_ROOT = Path(__file__).resolve().parent
YTX_SCRIPT = REPO_ROOT / "ytx.py"

# ---------- palette ----------
BG = "#FFF9FB"
CARD = "#FFFFFF"
TEXT = "#6B4E5A"           # warm plum
MUTED = "#9B7B89"          # dusty mauve
BUTTON_TEXT = "#765461"
PINK = "#F7DCE6"
PINK_HOVER = "#F2CEDC"
PINK_ACTIVE = "#EABFD0"
PINK_DISABLED = "#F7EEF1"
BORDER = "#EEDFE5"
ENTRY_BG = "#FFFCFD"
STATUS_BG = "#FFFDFE"

# ---------- fonts ----------
TITLE_FONT = ("Avenir Next", 22, "bold")
SUBTITLE_FONT = ("Avenir Next", 11)
SECTION_FONT = ("Avenir Next", 10, "bold")
ENTRY_FONT = ("Avenir Next", 12)
BUTTON_FONT = ("Avenir Next", 11, "bold")
SMALL_BUTTON_FONT = ("Avenir Next", 10, "bold")
STATUS_FONT = ("Menlo", 10)


class RoundedButton(tk.Canvas):
    def __init__(
        self,
        parent,
        text,
        command,
        width=250,
        height=48,
        radius=16,
        font=BUTTON_FONT,
    ):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=parent.cget("bg"),
            highlightthickness=0,
            bd=0,
            relief="flat",
            cursor="pointinghand",
        )

        self._text = text
        self._command = command
        self._radius = radius
        self._font = font
        self._state = "normal"
        self._fill = PINK

        self._draw()

        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)

    def _round_rect(self, x1, y1, x2, y2, r, **kwargs):
        self.create_arc(
            x1, y1, x1 + 2 * r, y1 + 2 * r,
            start=90, extent=90, style="pieslice", **kwargs
        )
        self.create_arc(
            x2 - 2 * r, y1, x2, y1 + 2 * r,
            start=0, extent=90, style="pieslice", **kwargs
        )
        self.create_arc(
            x1, y2 - 2 * r, x1 + 2 * r, y2,
            start=180, extent=90, style="pieslice", **kwargs
        )
        self.create_arc(
            x2 - 2 * r, y2 - 2 * r, x2, y2,
            start=270, extent=90, style="pieslice", **kwargs
        )

        self.create_rectangle(
            x1 + r, y1, x2 - r, y2,
            **kwargs
        )
        self.create_rectangle(
            x1, y1 + r, x2, y2 - r,
            **kwargs
        )

    def _draw(self):
        self.delete("all")

        fill = PINK_DISABLED if self._state == "disabled" else self._fill
        text_fill = "#BDAAB1" if self._state == "disabled" else BUTTON_TEXT

        self._round_rect(
            1,
            1,
            int(self["width"]) - 2,
            int(self["height"]) - 2,
            self._radius,
            fill=fill,
            outline=fill,
        )

        self.create_text(
            int(self["width"]) // 2,
            int(self["height"]) // 2,
            text=self._text,
            fill=text_fill,
            font=self._font,
        )

    def _enter(self, _event):
        if self._state == "normal":
            self._fill = PINK_HOVER
            self._draw()

    def _leave(self, _event):
        if self._state == "normal":
            self._fill = PINK
            self._draw()

    def _press(self, _event):
        if self._state == "normal":
            self._fill = PINK_ACTIVE
            self._draw()

    def _release(self, event):
        if self._state != "normal":
            return

        self._fill = PINK_HOVER
        self._draw()

        if (
            0 <= event.x <= int(self["width"])
            and 0 <= event.y <= int(self["height"])
        ):
            self._command()

    def set_state(self, state: str):
        self._state = state
        self._fill = PINK

        self.configure(
            cursor="arrow" if state == "disabled" else "pointinghand"
        )

        self._draw()


class TranscriptApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("YT Transcript Generator")
        self.root.geometry("720x600")
        self.root.minsize(680, 560)
        self.root.configure(bg=BG)

        self.last_transcript: Path | None = None
        self.running = False
        self.url_var = tk.StringVar()

        self.build_ui()

    def card(self, parent, padx=20, pady=18):
        return tk.Frame(
            parent,
            bg=CARD,
            padx=padx,
            pady=pady,
            highlightthickness=1,
            highlightbackground=BORDER,
        )

    def build_ui(self):
        outer = tk.Frame(
            self.root,
            bg=BG,
            padx=28,
            pady=24,
        )
        outer.pack(
            fill="both",
            expand=True,
        )

        # ---------- header ----------
        tk.Label(
            outer,
            text="YT Transcript Generator",
            font=TITLE_FONT,
            fg=TEXT,
            bg=BG,
        ).pack()

        tk.Label(
            outer,
            text="YouTube in. Clean transcript out.",
            font=SUBTITLE_FONT,
            fg=MUTED,
            bg=BG,
        ).pack(
            pady=(5, 20)
        )

        # ---------- URL ----------
        url_card = self.card(outer)
        url_card.pack(
            fill="x",
            pady=(0, 14),
        )

        tk.Label(
            url_card,
            text="YOUTUBE URL",
            font=SECTION_FONT,
            fg=TEXT,
            bg=CARD,
        ).pack(
            anchor="w"
        )

        row = tk.Frame(
            url_card,
            bg=CARD,
        )
        row.pack(
            fill="x",
            pady=(10, 0),
        )

        entry_shell = tk.Frame(
            row,
            bg=ENTRY_BG,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor="#DFAFC1",
        )
        entry_shell.pack(
            side="left",
            fill="x",
            expand=True,
        )

        self.url_entry = tk.Entry(
            entry_shell,
            textvariable=self.url_var,
            font=ENTRY_FONT,
            fg=TEXT,
            bg=ENTRY_BG,
            insertbackground=TEXT,
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        self.url_entry.pack(
            fill="x",
            expand=True,
            padx=12,
            pady=9,
        )

        paste = RoundedButton(
            row,
            "Paste",
            self.paste_url,
            width=92,
            height=42,
            radius=14,
            font=SMALL_BUTTON_FONT,
        )
        paste.pack(
            side="left",
            padx=(10, 0),
        )

        # ---------- Generate ----------
        generate_card = self.card(outer)
        generate_card.pack(
            fill="x",
            pady=(0, 14),
        )

        tk.Label(
            generate_card,
            text="GENERATE",
            font=SECTION_FONT,
            fg=TEXT,
            bg=CARD,
        ).pack(
            anchor="w",
            pady=(0, 12),
        )

        grid = tk.Frame(
            generate_card,
            bg=CARD,
        )
        grid.pack(
            fill="x"
        )

        grid.grid_columnconfigure(
            0,
            weight=1,
        )
        grid.grid_columnconfigure(
            1,
            weight=1,
        )

        self.generate_button = RoundedButton(
            grid,
            "Generate Transcript",
            lambda: self.run_variant([]),
            width=300,
            height=46,
        )

        self.timestamps_button = RoundedButton(
            grid,
            "With Timestamps",
            lambda: self.run_variant(["--timestamps"]),
            width=300,
            height=46,
        )

        self.captions_button = RoundedButton(
            grid,
            "Captions Only",
            lambda: self.run_variant(["--no-whisper"]),
            width=300,
            height=46,
        )

        self.force_button = RoundedButton(
            grid,
            "Force Regenerate",
            lambda: self.run_variant(["--force"]),
            width=300,
            height=46,
        )

        self.generate_button.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 6),
            pady=(0, 6),
        )

        self.timestamps_button.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(6, 0),
            pady=(0, 6),
        )

        self.captions_button.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(0, 6),
            pady=(6, 0),
        )

        self.force_button.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(6, 0),
            pady=(6, 0),
        )

        # ---------- Status ----------
        status_card = self.card(outer)
        status_card.pack(
            fill="both",
            expand=True,
        )

        status_header = tk.Frame(
            status_card,
            bg=CARD,
        )
        status_header.pack(
            fill="x"
        )

        tk.Label(
            status_header,
            text="STATUS",
            font=SECTION_FONT,
            fg=TEXT,
            bg=CARD,
        ).pack(
            side="left"
        )

        actions = tk.Frame(
            status_header,
            bg=CARD,
        )
        actions.pack(
            side="right"
        )

        self.downloads_button = RoundedButton(
            actions,
            "Open Downloads",
            self.open_downloads,
            width=142,
            height=38,
            radius=13,
            font=SMALL_BUTTON_FONT,
        )
        self.downloads_button.pack(
            side="left",
            padx=(0, 8),
        )

        self.open_button = RoundedButton(
            actions,
            "Open Transcript",
            self.open_transcript,
            width=142,
            height=38,
            radius=13,
            font=SMALL_BUTTON_FONT,
        )
        self.open_button.set_state("disabled")
        self.open_button.pack(
            side="left"
        )

        self.output = tk.Text(
            status_card,
            height=10,
            wrap="word",
            bg=STATUS_BG,
            fg=TEXT,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground="#F1E6EA",
            font=STATUS_FONT,
            padx=12,
            pady=12,
        )
        self.output.pack(
            fill="both",
            expand=True,
            pady=(12, 0),
        )

        self.output.insert(
            "end",
            "Ready.\n",
        )
        self.output.configure(
            state="disabled"
        )

        self.url_entry.focus_set()

        self.root.bind(
            "<Return>",
            lambda _event: self.run_variant([]),
        )

    def paste_url(self):
        try:
            self.url_var.set(
                self.root.clipboard_get().strip()
            )
        except tk.TclError:
            pass

    def set_running(self, running: bool):
        self.running = running

        state = (
            "disabled"
            if running
            else "normal"
        )

        for button in (
            self.generate_button,
            self.timestamps_button,
            self.captions_button,
            self.force_button,
        ):
            button.set_state(state)

    def write_status(
        self,
        text: str,
        clear: bool = False,
    ):
        self.output.configure(
            state="normal"
        )

        if clear:
            self.output.delete(
                "1.0",
                "end",
            )

        self.output.insert(
            "end",
            text,
        )

        self.output.see(
            "end"
        )

        self.output.configure(
            state="disabled"
        )

    def run_variant(
        self,
        extra_args: list[str],
    ):
        if self.running:
            return

        url = self.url_var.get().strip()

        if not url:
            messagebox.showwarning(
                "Missing URL",
                "Paste a YouTube URL first.",
            )
            return

        self.set_running(True)
        self.last_transcript = None

        self.open_button.set_state(
            "disabled"
        )

        self.write_status(
            "Running...\n\n",
            clear=True,
        )

        threading.Thread(
            target=self.worker,
            args=(url, extra_args),
            daemon=True,
        ).start()

    def worker(
        self,
        url: str,
        extra_args: list[str],
    ):
        command = [
            sys.executable,
            str(YTX_SCRIPT),
            url,
            *extra_args,
        ]

        try:
            result = subprocess.run(
                command,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            stdout = result.stdout or ""
            stderr = result.stderr or ""
            transcript_path = None

            for line in stdout.splitlines():
                if line.startswith("TRANSCRIPT="):
                    transcript_path = Path(
                        line.split(
                            "=",
                            1,
                        )[1].strip()
                    ).expanduser()

            combined = stdout

            if stderr:
                combined += (
                    "\n"
                    "--------------------\n"
                    "Details\n"
                    "--------------------\n"
                    f"{stderr}"
                )

            if not combined.strip():
                combined = (
                    "Process finished with no output.\n"
                )

            self.root.after(
                0,
                self.finish_run,
                result.returncode,
                combined,
                transcript_path,
            )

        except Exception as exc:
            self.root.after(
                0,
                self.finish_run,
                -1,
                (
                    f"GUI_ERROR="
                    f"{type(exc).__name__}: "
                    f"{exc}\n"
                ),
                None,
            )

    def finish_run(
        self,
        return_code: int,
        output: str,
        transcript_path: Path | None,
    ):
        self.write_status(
            output,
            clear=True,
        )

        self.set_running(False)

        if (
            transcript_path
            and transcript_path.exists()
        ):
            self.last_transcript = (
                transcript_path
            )

            self.open_button.set_state(
                "normal"
            )

        if return_code == 0:
            self.write_status(
                "\nDone.\n"
            )
        else:
            self.write_status(
                f"\nExited with code {return_code}.\n"
            )

    def open_transcript(self):
        if (
            self.last_transcript
            and self.last_transcript.exists()
        ):
            subprocess.run(
                [
                    "open",
                    str(self.last_transcript),
                ],
                check=False,
            )

    def open_downloads(self):
        subprocess.run(
            [
                "open",
                str(Path.home() / "Downloads"),
            ],
            check=False,
        )


def main():
    if not YTX_SCRIPT.exists():
        raise FileNotFoundError(
            f"Could not find {YTX_SCRIPT}"
        )

    root = tk.Tk()
    TranscriptApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
