import tkinter as tk
from tkinter import ttk
import asyncio
import threading
import websockets
import json

WS_URI = "ws://localhost:6789"
TOKEN = "ctrl123"


class GameShowController(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WWTBAM Controller")
        self.logo_visible = True
        self.lifeline_rows = []
        self.max_lifelines = 6

        self.ws = None
        self.lifeline_types = {
            "Ask the Audience": 1,
            "Fifty fifty": 2,
            "Phone a Friend": 3,
            "Double Dip": 4,
            "Switch Question": 5,
            "Ask the Host": 6,
            "Ask the Expert": 7,
            "Pass Question": 8,
            "Ask Audience Member": 11,
        }

        self.create_widgets()
        threading.Thread(target=self.run_websocket, daemon=True).start()

    def create_widgets(self):
        content_frame = tk.Frame(self)
        content_frame.pack(side="left", fill="both", expand=True)

        self.create_answer_section(content_frame)
        self.create_correct_section(content_frame)
        self.create_logo_toggle(content_frame)
        self.create_layout_section(content_frame)
        self.create_display_section(content_frame)
        self.create_lifeline_section(content_frame)
        self.create_money_tree_section()

    def create_answer_section(self, parent):
        frame = tk.LabelFrame(parent, text="Log Answer")
        frame.pack(padx=5, pady=5, fill="x")
        for ans in ["A", "B", "C", "D"]:
            btn = tk.Button(
                frame,
                text=ans,
                width=5,
                command=lambda a=ans: self.send_msg(["login", a]),
            )
            btn.pack(side="left", padx=5, pady=5)

    def create_correct_section(self, parent):
        frame = tk.LabelFrame(parent, text="Correct Answer")
        frame.pack(padx=5, pady=5, fill="x")
        self.correct_var = tk.StringVar(value="A")
        for ans in ["A", "B", "C", "D"]:
            tk.Radiobutton(
                frame,
                text=ans,
                variable=self.correct_var,
                value=ans,
                indicatoron=0,
                width=5,
                command=self.send_correct,
            ).pack(side="left", padx=5, pady=5)

    def create_logo_toggle(self, parent):
        tk.Button(parent, text="Toggle Logo", command=self.toggle_logo).pack(pady=10)

    def create_layout_section(self, parent):
        frame = tk.LabelFrame(parent, text="Select Layout")
        frame.pack(padx=5, pady=5, fill="x")
        self.layout_var = tk.StringVar(value="international-2002")
        layouts = [
            ("International 2002", "international-2002"),
            ("International Rave Revival", "international-rave-revival"),
            ("WWM", "wwm"),
        ]
        for label, value in layouts:
            btn = tk.Radiobutton(
                frame,
                text=label,
                value=value,
                variable=self.layout_var,
                indicatoron=0,
                width=25,
                command=lambda v=value: self.send_msg(["setGraphicsVersion", v]),
            )
            btn.pack(side="left", padx=5, pady=5)

    def create_display_section(self, parent):
        frame = tk.LabelFrame(parent, text="Display")
        frame.pack(padx=5, pady=5, fill="x")
        self.display_mode = tk.StringVar(value="question")

        def set_display(mode):
            self.display_mode.set(mode)
            self.send_msg(["setDisplayScreen", mode])

        for label, mode in [("Question", "question"), ("Money Tree", "money-tree")]:
            tk.Radiobutton(
                frame,
                text=label,
                variable=self.display_mode,
                value=mode,
                indicatoron=0,
                width=15,
                command=lambda m=mode: set_display(m),
            ).pack(side="left", padx=5, pady=5)

    def create_lifeline_section(self, parent):
        self.lifeline_frame = tk.LabelFrame(parent, text="Lifelines")
        self.lifeline_frame.pack(padx=5, pady=10, fill="x")
        self.lifeline_rows = []
        self.add_lifeline_row("Ask the Audience")
        self.add_lifeline_row("Phone a Friend")
        self.add_lifeline_row("Fifty fifty")
        self.add_lifeline_button = tk.Button(
            self.lifeline_frame, text="+ Add Lifeline", command=self.try_add_lifeline
        )
        self.add_lifeline_button.pack(pady=5)

    def try_add_lifeline(self):
        self.add_lifeline_button.pack_forget()
        if len(self.lifeline_rows) < self.max_lifelines:
            self.add_lifeline_row("Ask the Audience")
        self.redraw_lifelines()
        self.add_lifeline_button.pack(pady=5)

    def add_lifeline_row(self, default_type):  # extended with move up/down
        index = len(self.lifeline_rows) + 1
        frame = tk.Frame(self.lifeline_frame)
        frame.pack(fill="x", padx=5, pady=3)

        type_var = tk.StringVar(value=default_type)
        available_var = tk.BooleanVar(value=True)
        used_var = tk.BooleanVar(value=False)

        def send_status():
            if not available_var.get():
                status = "unavailable"
            else:
                status = "used" if used_var.get() else "available"
            self.send_msg(["setLifelineStatus", index, status])

        def update_label():
            use_btn.configure(text=f"Use {type_var.get()}")

        def send_config():
            config = {
                i + 1: self.lifeline_types[row["type_var"].get()]
                for i, row in enumerate(self.lifeline_rows)
            }
            self.send_msg(["setLifelineConfiguration", config])

        def on_type_change(event=None):
            update_label()
            send_config()

        def remove():
            if len(self.lifeline_rows) > 1:
                frame.destroy()
                self.lifeline_rows.remove(row)
                self.refresh_lifeline_config()

        dropdown = ttk.Combobox(
            frame,
            values=list(self.lifeline_types.keys()),
            textvariable=type_var,
            state="readonly",
            width=18,
        )
        dropdown.bind("<<ComboboxSelected>>", on_type_change)
        dropdown.pack(side="left")

        tk.Checkbutton(
            frame, text="Available", variable=available_var, command=send_status
        ).pack(side="left")
        tk.Checkbutton(frame, text="Used", variable=used_var, command=send_status).pack(
            side="left"
        )
        use_btn = tk.Button(
            frame,
            text=f"Use {default_type}",
            width=18,
            command=lambda: self.use_lifeline(index),
        )
        use_btn.pack(side="right")

        if index > 1:
            tk.Button(frame, text="❌", width=3, command=remove).pack(side="right")

        row = {
            "frame": frame,
            "type_var": type_var,
            "available_var": available_var,
            "used_var": used_var,
            "use_btn": use_btn,
        }

        self.lifeline_rows.append(row)
        self.refresh_lifeline_config()

    def redraw_lifelines(self):
        pass  # Method no longer needed

    def refresh_lifeline_config(self):
        config = {
            i + 1: self.lifeline_types[row["type_var"].get()]
            for i, row in enumerate(self.lifeline_rows)
        }
        self.send_msg(["setLifelineConfiguration", config])

    def use_lifeline(self, index):
        if 0 < index <= len(self.lifeline_rows):
            row = self.lifeline_rows[index - 1]
            if row["available_var"].get():
                row["used_var"].set(True)
                self.send_msg(["setLifelineStatus", index, "used"])

    def create_money_tree_section(self):
        side = tk.Frame(self)
        side.pack(side="right", fill="y", padx=10, pady=10)
        self.current_level = tk.IntVar(value=0)

        tk.Label(side, text="Money Level").pack()
        for i in reversed(range(0, 16)):
            b = tk.Radiobutton(
                side,
                text=str(i),
                variable=self.current_level,
                value=i,
                indicatoron=0,
                width=5,
                command=lambda lvl=i: self.set_level(lvl),
            )
            b.pack(pady=2)

        nav = tk.Frame(side)
        nav.pack(pady=10)
        tk.Button(nav, text="⬆️", width=5, command=self.level_up).pack(
            side="top", pady=2
        )
        tk.Button(nav, text="⬇️", width=5, command=self.level_down).pack(
            side="top", pady=2
        )

    def set_level(self, level):
        self.current_level.set(level)
        self.send_msg(["setCurrentLevel", self.current_level.get()])

    def level_up(self):
        if self.current_level.get() < 15:
            self.set_level(self.current_level.get() + 1)

    def level_down(self):
        if self.current_level.get() > 0:
            self.set_level(self.current_level.get() - 1)

    def toggle_logo(self):
        self.logo_visible = not self.logo_visible
        self.send_msg(["setVisibility", "img-logo-overlay", self.logo_visible])

    def send_correct(self):
        self.send_msg(["showCorrectAnswer", self.correct_var.get()])

    def send_msg(self, msg):
        if self.ws and self.ws.state == 1:
            asyncio.run_coroutine_threadsafe(
                self.ws.send(json.dumps({"type": "message", "message": msg})), self.loop
            )
        else:
            print("WebSocket not connected")

    def run_websocket(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.ws_handler())

    async def ws_handler(self):
        try:
            self.ws = await websockets.connect(WS_URI)
            await self.ws.send(json.dumps({"role": "controller", "token": TOKEN}))
            print("Connected to WebSocket")
            async for msg in self.ws:
                print("Received:", msg)
        except Exception as e:
            print("WebSocket error:", e)


if __name__ == "__main__":
    app = GameShowController()
    app.mainloop()
