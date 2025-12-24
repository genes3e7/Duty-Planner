"""
ui_components.py

Custom UI Widgets.
"""
from typing import Any, Callable

import customtkinter as ctk  # type: ignore

import constants as C


class ShiftGridCell(ctk.CTkButton):
    """Interactive Cell Button for the Grid."""
    
    def __init__(
        self, 
        master: Any, 
        person: str, 
        day: int, 
        command: Callable[[Any], None]
    ) -> None:
        super().__init__(
            master, text="", width=42, height=30, corner_radius=4,
            border_width=1, border_color="#D0D0D0",
            fg_color=C.SHIFT_COLORS[C.ShiftType.EMPTY][0],
            text_color=C.SHIFT_COLORS[C.ShiftType.EMPTY][1],
            command=self._on_click
        )
        self.person = person
        self.day = day
        self.current_val = C.ShiftType.EMPTY.value
        self._is_disabled = False
        self._external_callback = command

    def _on_click(self) -> None:
        if not self._is_disabled:
            self._external_callback(self)

    def set_val(self, val: str) -> None:
        if self._is_disabled and val != "":
            return
        self.current_val = val
        colors = C.SHIFT_COLORS.get(val, C.SHIFT_COLORS[C.ShiftType.EMPTY])
        self.configure(
            text=val, 
            fg_color=colors[0], 
            text_color=colors[1], 
            state="normal"
        )
        self.configure(hover_color="#E0E0E0" if val == "" else colors[0])

    def set_disabled(self, disabled: bool) -> None:
        self._is_disabled = disabled
        if disabled:
            self.set_val(C.ShiftType.EMPTY.value)
            self.configure(state="disabled", fg_color="#E0E0E0", text="")
        else:
            self.configure(
                state="normal", 
                fg_color=C.SHIFT_COLORS[C.ShiftType.EMPTY][0]
            )
