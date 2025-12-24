"""
gui_helpers.py

Shared UI construction helpers.
"""

from typing import Any, Callable, Dict, Optional

import customtkinter as ctk  # type: ignore


def create_grid_header(
    parent: Any, 
    text: str, 
    row: int, 
    col: int, 
    bg_color: str = "transparent",
    width: int = 40,
    font: Optional[tuple] = ("Arial", 10, "bold")
) -> ctk.CTkLabel:
    """Creates a standard grid header label."""
    label = ctk.CTkLabel(parent, text=text, width=width, fg_color=bg_color, font=font)
    label.grid(row=row, column=col, padx=1, sticky="nsew")
    return label

def create_config_row(
    parent: Any,
    label: str,
    default_val: Any,
    storage: Dict[str, ctk.CTkEntry],
    key: str
) -> None:
    """Creates a 'Label: Entry' row and stores reference."""
    frame = ctk.CTkFrame(parent)
    frame.pack(fill="x", pady=2)
    ctk.CTkLabel(frame, text=label, width=180, anchor="w").pack(side="left", padx=5)
    entry = ctk.CTkEntry(frame)
    entry.insert(0, str(default_val))
    entry.pack(side="right", expand=True, fill="x", padx=5)
    storage[key] = entry

def create_button(
    parent: Any,
    text: str,
    command: Callable,
    side: str = "right",
    width: int = 100,
    fg_color: Optional[str] = None,
    hover_color: Optional[str] = None
) -> ctk.CTkButton:
    """Creates a standard action button."""
    btn = ctk.CTkButton(
        parent, text=text, width=width, command=command,
        fg_color=fg_color, hover_color=hover_color
    )
    btn.pack(side=side, padx=5)
    return btn
