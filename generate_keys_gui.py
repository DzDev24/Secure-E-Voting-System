"""
generate_keys_gui.py – Graphical voter key generation (CustomTkinter).

Each voter runs this to generate their own RSA key pair.
Their private key is saved locally, and their public key is registered.

Run:  python generate_keys_gui.py
"""

import json
import os
import threading
import customtkinter as ctk

from crypto_utils import generate_keypair


ctk.set_appearance_mode("light")


BG        = "#F3F4F6"
CARD      = "#FFFFFF"
BORDER    = "#E5E7EB"
ACCENT    = "#4F46E5"
ACCENT_HV = "#4338CA"
SUCCESS   = "#059669"
ERROR     = "#DC2626"
TEXT      = "#111827"
TEXT_SUB  = "#6B7280"
HEADER_BG = "#1E293B"
HEADER_FG = "#FFFFFF"


DATA_DIR    = os.path.join(os.path.dirname(__file__), "data")
KEYS_DIR    = os.path.join(DATA_DIR, "keys")
VOTERS_FILE = os.path.join(DATA_DIR, "voters.json")

FONT = "Segoe UI"


class KeyGenApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("Generate Voter Keys")
        self.geometry("440x480")
        self.minsize(380, 440)
        self.configure(fg_color=BG)

        self._container = ctk.CTkFrame(self, fg_color="transparent")
        self._container.pack(fill="both", expand=True)

        self._show_input_page()

   

    def _header(self, parent):
        bar = ctk.CTkFrame(parent, fg_color=HEADER_BG, height=60, corner_radius=0)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        ctk.CTkLabel(bar, text="Generate Your Keys",
                     font=ctk.CTkFont(family=FONT, size=16, weight="bold"),
                     text_color=HEADER_FG).pack(side="left", padx=20)

    def _card(self, parent, title=None):
        frame = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=12,
                             border_width=1, border_color=BORDER)
        if title:
            ctk.CTkLabel(frame, text=title,
                         font=ctk.CTkFont(family=FONT, size=11, weight="bold"),
                         text_color=TEXT_SUB).pack(anchor="w", padx=20, pady=(16, 8))
            ctk.CTkFrame(frame, fg_color=BORDER, height=1).pack(fill="x", padx=16)
        return frame

    def _clear(self):
        for w in self._container.winfo_children():
            w.destroy()

   

    def _show_input_page(self):
        self._clear()
        self._header(self._container)

        content = ctk.CTkFrame(self._container, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=28, pady=24)

        card = self._card(content, "VOTER KEY GENERATION")
        card.pack(fill="x", pady=(10, 0))

        ctk.CTkLabel(card, text="Enter your registered name to generate\nyour personal RSA key pair.",
                     font=ctk.CTkFont(family=FONT, size=12),
                     text_color=TEXT_SUB, justify="center"
                     ).pack(padx=24, pady=(12, 14))

        self._name_var = ctk.StringVar()
        entry = ctk.CTkEntry(card, textvariable=self._name_var,
                             placeholder_text="Your registered name",
                             height=42, corner_radius=8,
                             font=ctk.CTkFont(family=FONT, size=13),
                             border_color=BORDER, fg_color="#F9FAFB")
        entry.pack(fill="x", padx=24, pady=(0, 14))
        entry.focus_set()
        entry.bind("<Return>", lambda e: self._on_generate())

        self._gen_btn = ctk.CTkButton(
            card, text="Generate Keys", height=44, corner_radius=8,
            fg_color=ACCENT, hover_color=ACCENT_HV,
            font=ctk.CTkFont(family=FONT, size=14, weight="bold"),
            command=self._on_generate)
        self._gen_btn.pack(fill="x", padx=24)

        self._msg_var = ctk.StringVar()
        ctk.CTkLabel(card, textvariable=self._msg_var,
                     font=ctk.CTkFont(family=FONT, size=11),
                     text_color=ERROR, wraplength=360
                     ).pack(fill="x", padx=24, pady=(8, 20))

    

    def _on_generate(self):
        name = self._name_var.get().strip()
        self._msg_var.set("")

        if not name:
            self._msg_var.set("Please enter your name.")
            return

        # Check voter registry
        if not os.path.exists(VOTERS_FILE):
            self._msg_var.set("Voter registry not found. Ask the admin to run Election Setup first.")
            return

        try:
            with open(VOTERS_FILE) as fh:
                voters = json.load(fh)
        except (json.JSONDecodeError, IOError):
            self._msg_var.set("Could not read voter registry.")
            return

        if name not in voters:
            self._msg_var.set(f"Name '{name}' is not registered. Contact the admin.")
            return

        if voters[name].get("public_key"):
            self._msg_var.set(f"Keys for '{name}' have already been generated.")
            return

        self._gen_btn.configure(state="disabled", text="Generating…")
        self._msg_var.set("Generating RSA key pair — please wait…")
        self.update_idletasks()

        threading.Thread(target=self._do_generate, args=(name, voters),
                         daemon=True).start()

    def _do_generate(self, name, voters):
        try:
            pub, priv = generate_keypair(1024)

            # Save private key
            os.makedirs(KEYS_DIR, exist_ok=True)
            priv_path = os.path.join(KEYS_DIR, f"{name}_private.json")
            with open(priv_path, "w") as fh:
                json.dump({"private_key": priv}, fh, indent=2)

            # Register public key
            voters[name] = {"public_key": pub}
            with open(VOTERS_FILE, "w") as fh:
                json.dump(voters, fh, indent=2)

            self.after(0, lambda: self._show_success(name))
        except Exception as exc:
            self.after(0, lambda: self._show_error(str(exc)))

    def _show_error(self, msg):
        self._gen_btn.configure(state="normal", text="Generate Keys")
        self._msg_var.set(f"Error: {msg}")

 

    def _show_success(self, name):
        self._clear()
        self._header(self._container)

        content = ctk.CTkFrame(self._container, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=28, pady=24)

        card = self._card(content)
        card.pack(fill="x", pady=(10, 10))

        ctk.CTkLabel(card, text="✓",
                     font=ctk.CTkFont(size=36, weight="bold"),
                     text_color=SUCCESS).pack(pady=(20, 4))
        ctk.CTkLabel(card, text="KEYS GENERATED",
                     font=ctk.CTkFont(family=FONT, size=16, weight="bold"),
                     text_color=SUCCESS).pack(pady=(0, 10))

        ctk.CTkFrame(card, fg_color=BORDER, height=1).pack(fill="x", padx=24)

        priv_path = os.path.join(KEYS_DIR, f"{name}_private.json")
        summary = (f"Keys created for: {name}\n\n"
                   f"Private key: {priv_path}\n"
                   f"Public key: registered in voters.json\n\n"
                   f"You can now vote using the Voter Interface.")
        ctk.CTkLabel(card, text=summary,
                     font=ctk.CTkFont(family=FONT, size=11),
                     text_color=TEXT, wraplength=360, justify="center"
                     ).pack(padx=24, pady=(14, 24))

        btn_row = ctk.CTkFrame(content, fg_color="transparent")
        btn_row.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(btn_row, text="Generate for Another Voter", height=42,
                      corner_radius=8, fg_color=ACCENT, hover_color=ACCENT_HV,
                      font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
                      command=self._show_input_page
                      ).pack(side="left", expand=True, fill="x", padx=(0, 4))

        ctk.CTkButton(btn_row, text="Close", height=42, corner_radius=8,
                      fg_color=BORDER, hover_color="#D1D5DB", text_color=TEXT,
                      font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
                      command=self.destroy
                      ).pack(side="left", expand=True, fill="x", padx=(4, 0))


if __name__ == "__main__":
    app = KeyGenApp()
    app.mainloop()
