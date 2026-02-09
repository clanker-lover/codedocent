"""Tkinter GUI launcher for codedocent."""

from __future__ import annotations

import subprocess  # nosec B404
import sys

from codedocent.ollama_utils import check_ollama, fetch_ollama_models

try:
    import tkinter as tk
    from tkinter import ttk, filedialog
except ImportError:
    tk = None  # type: ignore[assignment]

_HAS_TK = tk is not None

# Re-export for testability
_check_ollama = check_ollama
_fetch_ollama_models = fetch_ollama_models


def _build_gui() -> None:
    """Build and run the tkinter GUI window."""
    root = tk.Tk()
    root.title("codedocent")
    root.resizable(False, False)

    frame = ttk.Frame(root, padding=16)
    frame.grid(row=0, column=0, sticky="nsew")

    # --- Folder picker ---
    ttk.Label(frame, text="Folder to analyze:").grid(
        row=0, column=0, sticky="w", pady=(0, 4),
    )

    folder_var = tk.StringVar()
    folder_entry = ttk.Entry(frame, textvariable=folder_var, width=40)
    folder_entry.grid(row=1, column=0, sticky="ew", padx=(0, 6))

    def _browse() -> None:
        path = filedialog.askdirectory()
        if path:
            folder_var.set(path)

    ttk.Button(frame, text="Browse...", command=_browse).grid(
        row=1, column=1, sticky="w",
    )

    # --- Model dropdown ---
    ttk.Label(frame, text="Model:").grid(
        row=2, column=0, sticky="w", pady=(12, 4),
    )

    ollama_ok = _check_ollama()
    models = _fetch_ollama_models() if ollama_ok else []

    model_values = models if models else ["No AI"]
    model_var = tk.StringVar(value=model_values[0])
    model_combo = ttk.Combobox(
        frame, textvariable=model_var, values=model_values,
        state="readonly", width=37,
    )
    model_combo.grid(row=3, column=0, columnspan=2, sticky="ew")

    # --- Mode selector ---
    ttk.Label(frame, text="Mode:").grid(
        row=4, column=0, sticky="w", pady=(12, 4),
    )

    mode_var = tk.StringVar(value="interactive")
    modes_frame = ttk.Frame(frame)
    modes_frame.grid(row=5, column=0, columnspan=2, sticky="w")

    ttk.Radiobutton(
        modes_frame, text="Interactive", variable=mode_var,
        value="interactive",
    ).pack(anchor="w")
    ttk.Radiobutton(
        modes_frame, text="Full export", variable=mode_var,
        value="full",
    ).pack(anchor="w")
    ttk.Radiobutton(
        modes_frame, text="Text tree", variable=mode_var,
        value="text",
    ).pack(anchor="w")

    # --- Go button ---
    def _go() -> None:
        folder = folder_var.get().strip()
        if not folder:
            return

        cmd = [sys.executable, "-m", "codedocent", folder]

        selected_model = model_var.get()
        if selected_model == "No AI":
            cmd.append("--no-ai")
        else:
            cmd.extend(["--model", selected_model])

        mode = mode_var.get()
        if mode == "full":
            cmd.append("--full")
        elif mode == "text":
            cmd.append("--text")

        subprocess.Popen(cmd)  # pylint: disable=consider-using-with  # nosec B603  # noqa: E501
        root.destroy()

    ttk.Button(frame, text="Go", command=_go).grid(
        row=6, column=0, columnspan=2, pady=(16, 0),
    )

    root.mainloop()


def main() -> None:
    """Entry point for codedocent-gui."""
    if not _HAS_TK:
        print("tkinter is not installed.")
        print("Install it with: sudo apt install python3-tk")
        raise SystemExit(1)
    _build_gui()


if __name__ == "__main__":
    main()
