"""
launcher.py – Main entry point for the Secure E-Voting System.

Provides buttons to launch each component of the system.
Double-click Start.bat or run:  python launcher.py
"""

import os
import subprocess
import sys
import customtkinter as ctk

# ─── Theme ───────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("light")

# ─── Palette ─────────────────────────────────────────────────────────────────
BG        = "#F3F4F6"
CARD      = "#FFFFFF"
BORDER    = "#E5E7EB"
ACCENT    = "#4F46E5"
ACCENT_HV = "#4338CA"
SUCCESS   = "#059669"
SUCCESS_HV = "#047857"
TEXT      = "#111827"
TEXT_SUB  = "#6B7280"
HEADER_BG = "#1E293B"
HEADER_FG = "#FFFFFF"
PURPLE    = "#7C3AED"
PURPLE_HV = "#6D28D9"
CYAN      = "#0891B2"
CYAN_HV   = "#0E7490"

FONT = "Segoe UI"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class LauncherApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("Secure E-Voting System")
        self.geometry("420x480")
        self.minsize(380, 440)
        self.resizable(False, False)
        self.configure(fg_color=BG)

        # ── Header ──────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=HEADER_BG, height=74, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(expand=True)
        ctk.CTkLabel(header_inner, text="Secure E-Voting System",
                     font=ctk.CTkFont(family=FONT, size=18, weight="bold"),
                     text_color=HEADER_FG).pack()
        ctk.CTkLabel(header_inner, text="Select a component to launch",
                     font=ctk.CTkFont(family=FONT, size=11),
                     text_color="#94A3B8").pack()

        # ── Content ─────────────────────────────────────────────────────
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=32, pady=24)

        # Button cards
        self._make_button(content,
            title="Election Setup",
            desc="Register candidates and voters, generate server keys",
            color=ACCENT, hover=ACCENT_HV,
            command=lambda: self._launch("admin_setup_gui.py"),
            icon="⚙")

        self._make_button(content,
            title="Generate My Keys",
            desc="Generate your personal RSA key pair (each voter)",
            color=CYAN, hover=CYAN_HV,
            command=lambda: self._launch("generate_keys_gui.py"),
            icon="🔑")

        self._make_button(content,
            title="Admin Panel",
            desc="Start server, monitor results, manage the election",
            color=PURPLE, hover=PURPLE_HV,
            command=lambda: self._launch("admin_gui.py"),
            icon="📊")

        self._make_button(content,
            title="Voter Interface",
            desc="Log in and cast your vote",
            color=SUCCESS, hover=SUCCESS_HV,
            command=lambda: self._launch("voter_client_gui.py"),
            icon="🗳")

    def _make_button(self, parent, title, desc, color, hover, command, icon=""):
        btn_frame = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=10,
                                  border_width=1, border_color=BORDER,
                                  cursor="hand2")
        btn_frame.pack(fill="x", pady=(0, 10))

        inner = ctk.CTkFrame(btn_frame, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=12)

        # Icon + text on the left
        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        title_row = ctk.CTkFrame(left, fg_color="transparent")
        title_row.pack(anchor="w")
        ctk.CTkLabel(title_row, text=icon,
                     font=ctk.CTkFont(size=16)).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(title_row, text=title,
                     font=ctk.CTkFont(family=FONT, size=14, weight="bold"),
                     text_color=TEXT).pack(side="left")

        ctk.CTkLabel(left, text=desc,
                     font=ctk.CTkFont(family=FONT, size=11),
                     text_color=TEXT_SUB, anchor="w").pack(anchor="w", pady=(2, 0))

        # Launch button on the right
        btn = ctk.CTkButton(inner, text="Open", width=70, height=34,
                            corner_radius=8, fg_color=color, hover_color=hover,
                            font=ctk.CTkFont(family=FONT, size=12, weight="bold"),
                            command=command)
        btn.pack(side="right", padx=(10, 0))

    def _launch(self, script):
        """Launch a Python script as a separate process."""
        script_path = os.path.join(SCRIPT_DIR, script)
        subprocess.Popen(
            [sys.executable, script_path],
            cwd=SCRIPT_DIR,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )


if __name__ == "__main__":
    app = LauncherApp()
    app.mainloop()
