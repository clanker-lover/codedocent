"""Tkinter GUI launcher for codedocent."""

from __future__ import annotations

import os
import subprocess  # nosec B404
import sys
import threading

from codedocent.cloud_ai import CLOUD_PROVIDERS
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


def _create_backend_row(frame: ttk.Frame) -> tk.StringVar:
    """Create backend radio buttons (Cloud AI / Local AI)."""
    ttk.Label(frame, text="AI Backend:").grid(
        row=2, column=0, sticky="w", pady=(12, 4),
    )
    backend_var = tk.StringVar(value="local")
    backend_frame = ttk.Frame(frame)
    backend_frame.grid(row=3, column=0, columnspan=2, sticky="w")
    ttk.Radiobutton(
        backend_frame, text="Cloud AI", variable=backend_var, value="cloud",
    ).pack(side="left", padx=(0, 12))
    ttk.Radiobutton(
        backend_frame, text="Local AI (Ollama)", variable=backend_var,
        value="local",
    ).pack(side="left")
    return backend_var


def _create_cloud_provider_row(frame: ttk.Frame) -> ttk.Combobox:
    """Create cloud provider dropdown. Returns the Combobox widget."""
    ttk.Label(frame, text="Cloud Provider:").grid(
        row=4, column=0, sticky="w", pady=(8, 4),
    )
    providers = [CLOUD_PROVIDERS[p]["name"] for p in
                 ("openai", "openrouter", "groq", "custom")]
    combo = ttk.Combobox(
        frame, values=providers, state="readonly", width=37,
    )
    combo.set(providers[0])
    combo.grid(row=5, column=0, columnspan=2, sticky="ew")
    return combo


def _create_cloud_model_row(frame: ttk.Frame) -> ttk.Combobox:
    """Create cloud model dropdown. Returns the Combobox widget."""
    ttk.Label(frame, text="Cloud Model:").grid(
        row=6, column=0, sticky="w", pady=(8, 4),
    )
    combo = ttk.Combobox(frame, state="readonly", width=37)
    combo.grid(row=7, column=0, columnspan=2, sticky="ew")
    return combo


def _create_api_key_label(frame: ttk.Frame) -> ttk.Label:
    """Create the API key status label."""
    label = ttk.Label(frame, text="", foreground="gray")
    label.grid(row=8, column=0, columnspan=2, sticky="w", pady=(4, 0))
    return label


def _create_model_row(
    frame: ttk.Frame, root: tk.Tk,
) -> tk.StringVar:
    """Create the local model-dropdown row and return the StringVar."""
    ttk.Label(frame, text="Model:").grid(
        row=9, column=0, sticky="w", pady=(12, 4),
    )
    model_var = tk.StringVar(value="Checking...")
    combo = ttk.Combobox(
        frame, textvariable=model_var, values=["Checking..."],
        state="readonly", width=37,
    )
    combo.grid(row=10, column=0, columnspan=2, sticky="ew")

    def _bg_fetch() -> None:
        try:
            ollama_ok = _check_ollama()
            models = _fetch_ollama_models() if ollama_ok else []
        except Exception:  # pylint: disable=broad-exception-caught
            models = []
        model_values = models if models else ["No AI"]

        def _update_ui() -> None:
            combo["values"] = model_values
            model_var.set(model_values[0])

        root.after(0, _update_ui)

    threading.Thread(target=_bg_fetch, daemon=True).start()
    return model_var


def _create_mode_row(frame: ttk.Frame) -> tk.StringVar:
    """Create the mode-selector row and return the StringVar."""
    ttk.Label(frame, text="Mode:").grid(
        row=11, column=0, sticky="w", pady=(12, 4),
    )
    mode_var = tk.StringVar(value="interactive")
    modes_frame = ttk.Frame(frame)
    modes_frame.grid(row=12, column=0, columnspan=2, sticky="w")
    for text, value in [("Interactive", "interactive"),
                        ("Full export", "full"),
                        ("Text tree", "text")]:
        ttk.Radiobutton(
            modes_frame, text=text, variable=mode_var, value=value,
        ).pack(anchor="w")
    return mode_var


_PROVIDER_KEYS = ["openai", "openrouter", "groq", "custom"]


def _create_go_button(  # pylint: disable=too-many-arguments,too-many-positional-arguments  # noqa: E501
    frame: ttk.Frame,
    root: tk.Tk,
    folder_var: tk.StringVar,
    model_var: tk.StringVar,
    mode_var: tk.StringVar,
    backend_var: tk.StringVar,
    cloud_provider_combo: ttk.Combobox,
    cloud_model_combo: ttk.Combobox,
) -> None:
    """Create the Go button with its launch logic."""
    def _go() -> None:
        folder = folder_var.get().strip()
        if not folder:
            return

        cmd = [sys.executable, "-m", "codedocent", folder]

        if backend_var.get() == "cloud":
            provider_name = cloud_provider_combo.get()
            # Reverse-lookup provider key
            provider_key = "openai"
            for key in _PROVIDER_KEYS:
                if CLOUD_PROVIDERS[key]["name"] == provider_name:
                    provider_key = key
                    break
            cloud_model = cloud_model_combo.get()
            cmd.extend(["--cloud", provider_key])
            if cloud_model:
                cmd.extend(["--model", cloud_model])
        else:
            selected_model = model_var.get()
            if selected_model == "Checking...":
                return
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
        row=13, column=0, columnspan=2, pady=(16, 0),
    )


def _build_gui() -> None:
    """Build and run the tkinter GUI window."""
    root = tk.Tk()
    root.title("codedocent")
    root.resizable(False, False)

    frame = ttk.Frame(root, padding=16)
    frame.grid(row=0, column=0, sticky="nsew")

    folder_var = _create_folder_row(frame)
    backend_var = _create_backend_row(frame)
    cloud_provider_combo = _create_cloud_provider_row(frame)
    cloud_model_combo = _create_cloud_model_row(frame)
    api_key_label = _create_api_key_label(frame)
    model_var = _create_model_row(frame, root)
    mode_var = _create_mode_row(frame)

    # Cloud widgets to show/hide
    cloud_widgets = [
        frame.grid_slaves(row=4)[0],  # provider label
        cloud_provider_combo,
        frame.grid_slaves(row=6)[0],  # model label
        cloud_model_combo,
        api_key_label,
    ]
    # Local widgets to show/hide
    local_widgets = [
        frame.grid_slaves(row=9)[0],   # model label
        frame.grid_slaves(row=10)[0],   # model combo
    ]

    def _update_visibility(*_args: object) -> None:
        if backend_var.get() == "cloud":
            for w in cloud_widgets:
                w.grid()
            for w in local_widgets:
                w.grid_remove()
        else:
            for w in cloud_widgets:
                w.grid_remove()
            for w in local_widgets:
                w.grid()

    def _update_cloud_models(*_args: object) -> None:
        provider_name = cloud_provider_combo.get()
        for key in _PROVIDER_KEYS:
            if CLOUD_PROVIDERS[key]["name"] == provider_name:
                models = CLOUD_PROVIDERS[key]["models"]
                cloud_model_combo["values"] = models
                if models:
                    cloud_model_combo.set(models[0])
                else:
                    cloud_model_combo.set("")
                # Update API key status
                env_var = CLOUD_PROVIDERS[key]["env_var"]
                if os.environ.get(env_var):
                    api_key_label.config(
                        text=f"API key found in ${env_var}",
                        foreground="green",
                    )
                else:
                    api_key_label.config(
                        text=f"Set ${env_var} in your terminal",
                        foreground="red",
                    )
                break

    backend_var.trace_add("write", _update_visibility)
    cloud_provider_combo.bind("<<ComboboxSelected>>", _update_cloud_models)

    # Initial state
    _update_cloud_models()
    _update_visibility()

    _create_go_button(
        frame, root, folder_var, model_var, mode_var,
        backend_var, cloud_provider_combo, cloud_model_combo,
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
