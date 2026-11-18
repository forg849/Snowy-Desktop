import ctypes
import random
import sys
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from ctypes import wintypes
from typing import Callable


TRANSPARENT_COLOR = "#010203"
GROUND_CELL_WIDTH = 6
FRAME_DELAY_MS = 33


@dataclass
class Snowflake:
    x: float
    y: float
    radius: float
    speed: float
    drift: float
    color: str
    canvas_item: int | None = None


class SnowyDesktop:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Снежный рабочий стол")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.overlay: tk.Toplevel | None = None
        self.canvas: tk.Canvas | None = None
        self.flakes: list[Snowflake] = []
        self.snow_heights: list[float] = []
        self.ground_item: int | None = None
        self.paused = tk.BooleanVar(value=False)
        self.accumulation_enabled = tk.BooleanVar(value=True)

        self.density = tk.IntVar(value=140)
        self.speed = tk.DoubleVar(value=2.2)
        self.flake_size = tk.DoubleVar(value=2.5)
        self.wind = tk.DoubleVar(value=0.0)
        self.snow_depth = tk.IntVar(value=70)

        self._build_controls()

    def _build_controls(self) -> None:
        style = ttk.Style(self.root)
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Hint.TLabel", foreground="#667085")
        style.configure("Value.TLabel", foreground="#315b7d", font=("Segoe UI", 9, "bold"))
        style.configure("Section.TLabelframe.Label", font=("Segoe UI", 10, "bold"))

        panel = ttk.Frame(self.root, padding=20)
        panel.grid(sticky="nsew")
        ttk.Label(
            panel, text="Снег на рабочем столе", style="Title.TLabel"
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))
        ttk.Label(
            panel,
            text="Настрой снег по своему вкусу. Окно можно свернуть — снег останется.",
            style="Hint.TLabel",
            wraplength=390,
        ).grid(row=1, column=0, sticky="w", pady=(0, 16))

        settings = ttk.LabelFrame(
            panel, text="Параметры", padding=12, style="Section.TLabelframe"
        )
        settings.grid(row=2, column=0, sticky="ew")
        settings.columnconfigure(0, weight=1)
        self._add_slider(
            settings, 0, "Количество снежинок", self.density, 20, 350,
            lambda value: str(int(value)),
        )
        self._add_slider(
            settings, 2, "Скорость", self.speed, 0.5, 6,
            lambda value: f"{value:.1f}",
        )
        self._add_slider(
            settings, 4, "Размер снежинок", self.flake_size, 1, 6,
            lambda value: f"{value:.1f}",
        )
        self._add_slider(
            settings, 6, "Ветер", self.wind, -4, 4,
            lambda value: f"{value:+.1f}",
        )
        self._add_slider(
            settings, 8, "Высота снега у нижнего края", self.snow_depth, 0, 140,
            lambda value: f"{int(value)} px",
        )

        ttk.Checkbutton(
            panel, text="Накапливать снег", variable=self.accumulation_enabled
        ).grid(row=3, column=0, sticky="w", pady=(10, 2))
        ttk.Checkbutton(
            panel, text="Пауза", variable=self.paused
        ).grid(row=4, column=0, sticky="w", pady=(0, 12))

        buttons = ttk.Frame(panel)
        buttons.grid(row=5, column=0, sticky="ew")
        ttk.Button(
            buttons, text="Свернуть настройки", command=self.root.iconify
        ).pack(side="left")
        ttk.Button(
            buttons, text="Выключить снег", command=self.close
        ).pack(side="right")
        ttk.Label(
            panel,
            text="Чтобы открыть настройки снова, нажмите на окно в панели задач.",
            style="Hint.TLabel",
            wraplength=390,
        ).grid(row=6, column=0, sticky="w", pady=(12, 0))

        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - self.root.winfo_reqwidth()) // 2
        y = (self.root.winfo_screenheight() - self.root.winfo_reqheight()) // 2
        self.root.geometry(f"+{x}+{y}")

    @staticmethod
    def _add_slider(
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.Variable,
        minimum: float,
        maximum: float,
        format_value: Callable[[float], str],
    ) -> None:
        value_text = tk.StringVar(value=format_value(float(variable.get())))
        ttk.Label(parent, text=label).grid(
            row=row, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Label(parent, textvariable=value_text, style="Value.TLabel").grid(
            row=row, column=1, sticky="e", pady=(4, 0)
        )
        ttk.Scale(
            parent,
            from_=minimum,
            to=maximum,
            variable=variable,
            orient="horizontal",
        ).grid(row=row + 1, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        variable.trace_add(
            "write",
            lambda *_: value_text.set(format_value(float(variable.get()))),
        )

    def start_overlay(self) -> None:
        if self.overlay is not None:
            return

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetSystemMetrics.argtypes = [ctypes.c_int]
        user32.GetSystemMetrics.restype = ctypes.c_int
        user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
        user32.SetWindowLongPtrW.argtypes = [
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_ssize_t,
        ]
        user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
        user32.SetLayeredWindowAttributes.argtypes = [
            wintypes.HWND,
            wintypes.DWORD,
            wintypes.BYTE,
            wintypes.DWORD,
        ]
        user32.SetLayeredWindowAttributes.restype = wintypes.BOOL
        user32.SetWindowPos.argtypes = [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ]
        user32.SetWindowPos.restype = wintypes.BOOL
        left = user32.GetSystemMetrics(76)
        top = user32.GetSystemMetrics(77)
        width = user32.GetSystemMetrics(78)
        height = user32.GetSystemMetrics(79)

        overlay = tk.Toplevel(self.root)
        overlay.withdraw()
        overlay.overrideredirect(True)
        overlay.geometry(f"{width}x{height}{left:+d}{top:+d}")
        overlay.configure(bg=TRANSPARENT_COLOR)
        overlay.wm_attributes("-transparentcolor", TRANSPARENT_COLOR)
        overlay.wm_attributes("-topmost", True)

        canvas = tk.Canvas(
            overlay,
            bg=TRANSPARENT_COLOR,
            highlightthickness=0,
            borderwidth=0,
            width=width,
            height=height,
        )
        canvas.pack(fill="both", expand=True)
        overlay.update_idletasks()

        hwnd = wintypes.HWND(int(overlay.wm_frame(), 0))
        ctypes.set_last_error(0)
        extended_style = user32.GetWindowLongPtrW(hwnd, -20)
        if extended_style == 0 and ctypes.get_last_error():
            raise ctypes.WinError(ctypes.get_last_error())
        extended_style |= 0x00000020 | 0x00080000 | 0x00000080 | 0x08000000
        ctypes.set_last_error(0)
        user32.SetWindowLongPtrW(hwnd, -20, extended_style)
        if ctypes.get_last_error():
            raise ctypes.WinError(ctypes.get_last_error())
        if not user32.SetLayeredWindowAttributes(
            hwnd, 0x00030201, 0, 0x00000001
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        if not user32.SetWindowPos(
            hwnd,
            wintypes.HWND(-1),
            0,
            0,
            0,
            0,
            0x0001 | 0x0002 | 0x0010 | 0x0020,
        ):
            raise ctypes.WinError(ctypes.get_last_error())

        self.overlay = overlay
        self.canvas = canvas
        cell_count = (width + GROUND_CELL_WIDTH - 1) // GROUND_CELL_WIDTH
        self.snow_heights = [0.0] * cell_count
        self.flakes = [self._new_flake(width, height) for _ in range(self.density.get())]
        self.ground_item = None
        overlay.deiconify()
        self._animate(width, height)

    def _new_flake(self, width: int, height: int) -> Snowflake:
        return Snowflake(
            x=random.uniform(0, width),
            y=random.uniform(-height, 0),
            radius=random.uniform(0.7, 1.5),
            speed=random.uniform(0.7, 1.3),
            drift=random.uniform(-0.5, 0.5),
            color=random.choice(("#ffffff", "#e7f4ff", "#cfe8ff")),
        )

    def _animate(self, width: int, height: int) -> None:
        if self.overlay is None or self.canvas is None:
            return
        if not self.overlay.winfo_exists():
            self.overlay = None
            self.canvas = None
            return

        if not self.paused.get():
            self._draw_frame(width, height)
        self.overlay.after(FRAME_DELAY_MS, self._animate, width, height)

    def _draw_frame(self, width: int, height: int) -> None:
        canvas = self.canvas
        if canvas is None:
            return

        target_count = self.density.get()
        for flake in self.flakes[target_count:]:
            if flake.canvas_item is not None:
                canvas.delete(flake.canvas_item)
        self.flakes = self.flakes[:target_count]
        while len(self.flakes) < target_count:
            flake = self._new_flake(width, height)
            flake.canvas_item = canvas.create_oval(
                0, 0, 0, 0, fill=flake.color, outline=""
            )
            self.flakes.append(flake)

        wind = self.wind.get()
        fall_speed = self.speed.get()
        for flake in self.flakes:
            if flake.canvas_item is None:
                flake.canvas_item = canvas.create_oval(
                    0, 0, 0, 0, fill=flake.color, outline=""
                )
            flake.x += wind + flake.drift
            flake.y += fall_speed * flake.speed
            if flake.x < 0:
                flake.x += width
            elif flake.x >= width:
                flake.x -= width

            cell = min(int(flake.x // GROUND_CELL_WIDTH), len(self.snow_heights) - 1)
            ground_y = height - self.snow_heights[cell]
            if self.accumulation_enabled.get() and self.snow_depth.get() > 0:
                if flake.y + flake.radius >= ground_y:
                    self.snow_heights[cell] = min(
                        self.snow_depth.get(),
                        self.snow_heights[cell] + max(0.25, flake.radius * 0.35),
                    )
                    flake.x = random.uniform(0, width)
                    flake.y = random.uniform(-30, -5)
            if flake.y > height + 5:
                flake.x = random.uniform(0, width)
                flake.y = random.uniform(-30, -5)

            radius = flake.radius * self.flake_size.get() / 2.5
            canvas.coords(
                flake.canvas_item,
                flake.x - radius,
                flake.y - radius,
                flake.x + radius,
                flake.y + radius,
            )

        max_depth = self.snow_depth.get() if self.accumulation_enabled.get() else 0
        if max_depth > 0:
            for index, value in enumerate(self.snow_heights):
                if value > max_depth:
                    self.snow_heights[index] = float(max_depth)
            points = [0, height]
            for index, value in enumerate(self.snow_heights):
                points.extend((index * GROUND_CELL_WIDTH, height - value))
            points.extend((width, height))
            if self.ground_item is None:
                self.ground_item = canvas.create_polygon(
                    *points, fill="#eaf6ff", outline=""
                )
            else:
                canvas.coords(self.ground_item, *points)
                canvas.itemconfigure(self.ground_item, state="normal")
        else:
            self.snow_heights = [0.0] * len(self.snow_heights)
            if self.ground_item is not None:
                canvas.itemconfigure(self.ground_item, state="hidden")

    def close(self) -> None:
        if self.overlay is not None:
            self.overlay.destroy()
            self.overlay = None
            self.canvas = None
        self.root.destroy()


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("Это приложение предназначено для Windows.")
    root = tk.Tk()
    app = SnowyDesktop(root)
    root.after(100, app.start_overlay)
    root.mainloop()


if __name__ == "__main__":
    main()