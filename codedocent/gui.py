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


def _create_folder_row(frame: ttk.Frame) -> tk.StringVar:
    """Create the folder-picker row and return the StringVar."""
    ttk.Label(frame, text="Folder to analyze:").grid(
        row=0, column=0, sticky="w", pady=(0, 4),
    )
    folder_var = tk.StringVar()
    ttk.Entry(frame, textvariable=folder_var, width=40).grid(
        row=1, column=0, sticky="ew", padx=(0, 6),
    )

    def _browse() -> None:
        path = filedialog.askdirectory()
        if path:
            folder_var.set(path)

    ttk.Button(frame, text="Browse...", command=_browse).grid(
        row=1, column=1, sticky="w",
    )
    return folder_var


def _create_model_row(frame: ttk.Frame) -> tk.StringVar:
    """Create the model-dropdown row and return the StringVar."""
    ttk.Label(frame, text="Model:").grid(
        row=2, column=0, sticky="w", pady=(12, 4),
    )
    ollama_ok = _check_ollama()
    models = _fetch_ollama_models() if ollama_ok else []
    model_values = models if models else ["No AI"]
    model_var = tk.StringVar(value=model_values[0])
    ttk.Combobox(
        frame, textvariable=model_var, values=model_values,
        state="readonly", width=37,
    ).grid(row=3, column=0, columnspan=2, sticky="ew")
    return model_var


def _create_mode_row(frame: ttk.Frame) -> tk.StringVar:
    """Create the mode-selector row and return the StringVar."""
    ttk.Label(frame, text="Mode:").grid(
        row=4, column=0, sticky="w", pady=(12, 4),
    )
    mode_var = tk.StringVar(value="interactive")
    modes_frame = ttk.Frame(frame)
    modes_frame.grid(row=5, column=0, columnspan=2, sticky="w")
    for text, value in [("Interactive", "interactive"),
                        ("Full export", "full"),
                        ("Text tree", "text")]:
        ttk.Radiobutton(
            modes_frame, text=text, variable=mode_var, value=value,
        ).pack(anchor="w")
    return mode_var


def _create_go_button(
    frame: ttk.Frame,
    root: tk.Tk,
    folder_var: tk.StringVar,
    model_var: tk.StringVar,
    mode_var: tk.StringVar,
) -> None:
    """Create the Go button with its launch logic."""
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


def _build_gui() -> None:
    """Build and run the tkinter GUI window."""
    root = tk.Tk()
    root.title("codedocent")
    root.resizable(False, False)

    frame = ttk.Frame(root, padding=16)
    frame.grid(row=0, column=0, sticky="nsew")

    folder_var = _create_folder_row(frame)
    model_var = _create_model_row(frame)
    mode_var = _create_mode_row(frame)
    _create_go_button(frame, root, folder_var, model_var, mode_var)

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
