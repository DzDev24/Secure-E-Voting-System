"""
admin_setup_gui.py – Graphical election setup interface (CustomTkinter).

Allows the admin to:
  1. Add/remove candidate names.
  2. Add/remove voter names.
  3. Generate server RSA keys and save the election configuration.

Run:  python admin_setup_gui.py
"""

import json
import os
import threading
import customtkinter as ctk

from crypto_utils import generate_keypair

# ─── Theme ───────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("light")

# ─── Palette (matches other interfaces) ──────────────────────────────────────
BG        = "#F3F4F6"
CARD      = "#FFFFFF"
BORDER    = "#E5E7EB"
ACCENT    = "#4F46E5"
ACCENT_HV = "#4338CA"
SUCCESS   = "#059669"
ERROR     = "#DC2626"
WARNING   = "#D97706"
TEXT      = "#111827"
TEXT_SUB  = "#6B7280"
HEADER_BG = "#1E293B"
HEADER_FG = "#FFFFFF"

# ─── Paths ───────────────────────────────────────────────────────────────────
DATA_DIR         = os.path.join(os.path.dirname(__file__), "data")
SERVER_PUB_FILE  = os.path.join(DATA_DIR, "server_public_key.json")
SERVER_PRIV_FILE = os.path.join(DATA_DIR, "server_private_key.json")
VOTERS_FILE      = os.path.join(DATA_DIR, "voters.json")
CANDIDATES_FILE  = os.path.join(DATA_DIR, "candidates.json")

FONT = "Segoe UI"


class SetupApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("Election Setup")
        self.geometry("560x640")
        self.minsize(480, 560)
        self.configure(fg_color=BG)

        self._candidates = []
        self._voters = []

        self._container = ctk.CTkFrame(self, fg_color="transparent")
        self._container.pack(fill="both", expand=True)

        self._show_setup_page()

    # ── helpers ──────────────────────────────────────────────────────────

    def _header(self, parent):
        bar = ctk.CTkFrame(parent, fg_color=HEADER_BG, height=60, corner_radius=0)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        ctk.CTkLabel(bar, text="Election Setup",
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

    # ══════════════════════════════════════════════════════════════════════
    #  Setup Page
    # ══════════════════════════════════════════════════════════════════════

    def _show_setup_page(self):
        self._clear()
        self._header(self._container)

        content = ctk.CTkFrame(self._container, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=28, pady=16)

        # ── Pinned bottom: status + Create button (pack FIRST) ──────────
        bottom = ctk.CTkFrame(content, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", pady=(10, 0))

        self._status_msg = ctk.StringVar()
        self._status_label = ctk.CTkLabel(bottom, textvariable=self._status_msg,
                     font=ctk.CTkFont(family=FONT, size=11),
                     text_color=TEXT_SUB, wraplength=480, justify="center")
        self._status_label.pack(pady=(0, 6))

        self._create_btn = ctk.CTkButton(
            bottom, text="Create Election", height=44, corner_radius=8,
            fg_color=SUCCESS, hover_color="#047857",
            font=ctk.CTkFont(family=FONT, size=14, weight="bold"),
            command=self._on_create)
        self._create_btn.pack(fill="x")

        # Two-card area takes remaining space
        cards_area = ctk.CTkFrame(content, fg_color="transparent")
        cards_area.pack(fill="both", expand=True)
        cards_area.grid_rowconfigure(0, weight=1)
        cards_area.grid_rowconfigure(1, weight=1)
        cards_area.grid_columnconfigure(0, weight=1)

        # ── Candidates card (top half) ──────────────────────────────────
        cand_card = self._card(cards_area, "CANDIDATES")
        cand_card.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

        cand_input = ctk.CTkFrame(cand_card, fg_color="transparent")
        cand_input.pack(fill="x", padx=16, pady=(10, 6))

        self._cand_entry = ctk.CTkEntry(cand_input, placeholder_text="Candidate name",
                                         height=36, corner_radius=8,
                                         font=ctk.CTkFont(family=FONT, size=12),
                                         border_color=BORDER, fg_color="#F9FAFB")
        self._cand_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._cand_entry.bind("<Return>", lambda e: self._add_candidate())

        ctk.CTkButton(cand_input, text="Add", width=60, height=36, corner_radius=8,
                      fg_color=ACCENT, hover_color=ACCENT_HV,
                      font=ctk.CTkFont(family=FONT, size=12, weight="bold"),
                      command=self._add_candidate).pack(side="right")

        self._cand_list_frame = ctk.CTkScrollableFrame(
            cand_card, fg_color="transparent",
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color="#D1D5DB")
        self._cand_list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 4))

        self._cand_msg = ctk.StringVar()
        ctk.CTkLabel(cand_card, textvariable=self._cand_msg,
                     font=ctk.CTkFont(family=FONT, size=10),
                     text_color=ERROR).pack(padx=16, pady=(0, 6))

        # ── Voters card (bottom half) ───────────────────────────────────
        voter_card = self._card(cards_area, "VOTERS")
        voter_card.grid(row=1, column=0, sticky="nsew", pady=(5, 0))

        voter_input = ctk.CTkFrame(voter_card, fg_color="transparent")
        voter_input.pack(fill="x", padx=16, pady=(10, 6))

        self._voter_entry = ctk.CTkEntry(voter_input, placeholder_text="Voter name",
                                          height=36, corner_radius=8,
                                          font=ctk.CTkFont(family=FONT, size=12),
                                          border_color=BORDER, fg_color="#F9FAFB")
        self._voter_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._voter_entry.bind("<Return>", lambda e: self._add_voter())

        ctk.CTkButton(voter_input, text="Add", width=60, height=36, corner_radius=8,
                      fg_color=ACCENT, hover_color=ACCENT_HV,
                      font=ctk.CTkFont(family=FONT, size=12, weight="bold"),
                      command=self._add_voter).pack(side="right")

        self._voter_list_frame = ctk.CTkScrollableFrame(
            voter_card, fg_color="transparent",
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color="#D1D5DB")
        self._voter_list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 4))

        self._voter_msg = ctk.StringVar()
        ctk.CTkLabel(voter_card, textvariable=self._voter_msg,
                     font=ctk.CTkFont(family=FONT, size=10),
                     text_color=ERROR).pack(padx=16, pady=(0, 6))


        self._cand_entry.focus_set()

        # Re-populate lists if returning from success page
        self._refresh_cand_list()
        self._refresh_voter_list()

    # ── List management ─────────────────────────────────────────────────

    def _add_candidate(self):
        name = self._cand_entry.get().strip()
        self._cand_msg.set("")
        if not name:
            self._cand_msg.set("Enter a candidate name.")
            return
        if name in self._candidates:
            self._cand_msg.set(f"'{name}' is already in the list.")
            return
        self._candidates.append(name)
        self._cand_entry.delete(0, "end")
        self._refresh_cand_list()

    def _remove_candidate(self, name):
        self._candidates.remove(name)
        self._refresh_cand_list()

    def _refresh_cand_list(self):
        for w in self._cand_list_frame.winfo_children():
            w.destroy()
        for name in self._candidates:
            row = ctk.CTkFrame(self._cand_list_frame, fg_color="#F0F0FF",
                               corner_radius=6)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=name,
                         font=ctk.CTkFont(family=FONT, size=12),
                         text_color=TEXT).pack(side="left", padx=12, pady=6)
            ctk.CTkButton(row, text="✕", width=28, height=28, corner_radius=6,
                          fg_color="transparent", hover_color="#FECACA",
                          text_color=ERROR,
                          font=ctk.CTkFont(size=12, weight="bold"),
                          command=lambda n=name: self._remove_candidate(n)
                          ).pack(side="right", padx=4, pady=4)

    def _add_voter(self):
        name = self._voter_entry.get().strip()
        self._voter_msg.set("")
        if not name:
            self._voter_msg.set("Enter a voter name.")
            return
        if name in self._voters:
            self._voter_msg.set(f"'{name}' is already in the list.")
            return
        self._voters.append(name)
        self._voter_entry.delete(0, "end")
        self._refresh_voter_list()

    def _remove_voter(self, name):
        self._voters.remove(name)
        self._refresh_voter_list()

    def _refresh_voter_list(self):
        for w in self._voter_list_frame.winfo_children():
            w.destroy()
        for name in self._voters:
            row = ctk.CTkFrame(self._voter_list_frame, fg_color="#F0FDF4",
                               corner_radius=6)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=name,
                         font=ctk.CTkFont(family=FONT, size=12),
                         text_color=TEXT).pack(side="left", padx=12, pady=6)
            ctk.CTkButton(row, text="✕", width=28, height=28, corner_radius=6,
                          fg_color="transparent", hover_color="#FECACA",
                          text_color=ERROR,
                          font=ctk.CTkFont(size=12, weight="bold"),
                          command=lambda n=name: self._remove_voter(n)
                          ).pack(side="right", padx=4, pady=4)

    # ── Create election ─────────────────────────────────────────────────

    def _on_create(self):
        if len(self._candidates) < 2:
            self._status_msg.set("Add at least 2 candidates.")
            self._status_label.configure(text_color=ERROR)
            return
        if len(self._voters) < 1:
            self._status_msg.set("Add at least 1 voter.")
            self._status_label.configure(text_color=ERROR)
            return

        self._create_btn.configure(state="disabled", text="Generating keys…")
        self._status_msg.set("Generating server RSA keys — this may take a moment…")
        self._status_label.configure(text_color=TEXT_SUB)
        self.update_idletasks()

        threading.Thread(target=self._do_create, daemon=True).start()

    def _do_create(self):
        try:
            os.makedirs(DATA_DIR, exist_ok=True)

            # Server keys
            server_pub, server_priv = generate_keypair(1024)
            with open(SERVER_PUB_FILE, "w") as fh:
                json.dump({"public_key": server_pub}, fh, indent=2)
            with open(SERVER_PRIV_FILE, "w") as fh:
                json.dump({"private_key": server_priv}, fh, indent=2)

            # Candidates
            with open(CANDIDATES_FILE, "w") as fh:
                json.dump(self._candidates, fh, indent=2)

            # Voters — names only, no keys
            voters = {name: {} for name in self._voters}
            with open(VOTERS_FILE, "w") as fh:
                json.dump(voters, fh, indent=2)

            self.after(0, self._show_success)
        except Exception as exc:
            self.after(0, lambda: self._show_error(str(exc)))

    def _show_error(self, msg):
        self._create_btn.configure(state="normal", text="Create Election")
        self._status_msg.set(f"Error: {msg}")
        self._status_label.configure(text_color=ERROR)

    # ══════════════════════════════════════════════════════════════════════
    #  Success Page
    # ══════════════════════════════════════════════════════════════════════

    def _show_success(self):
        self._clear()
        self._header(self._container)

        content = ctk.CTkFrame(self._container, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=28, pady=24)

        card = self._card(content)
        card.pack(fill="x", pady=(20, 10))

        ctk.CTkLabel(card, text="✓",
                     font=ctk.CTkFont(size=44, weight="bold"),
                     text_color=SUCCESS).pack(pady=(28, 4))
        ctk.CTkLabel(card, text="ELECTION CREATED",
                     font=ctk.CTkFont(family=FONT, size=16, weight="bold"),
                     text_color=SUCCESS).pack(pady=(0, 10))

        ctk.CTkFrame(card, fg_color=BORDER, height=1).pack(fill="x", padx=24)

        summary = (f"{len(self._candidates)} candidates  •  {len(self._voters)} voters\n\n"
                   f"Candidates: {', '.join(self._candidates)}\n"
                   f"Voters: {', '.join(self._voters)}\n\n"
                   f"Each voter must now run Generate Keys\n"
                   f"to create their RSA key pair.")
        ctk.CTkLabel(card, text=summary,
                     font=ctk.CTkFont(family=FONT, size=12),
                     text_color=TEXT, wraplength=420, justify="center"
                     ).pack(padx=24, pady=(14, 6))

        ctk.CTkLabel(card, text=f"Files saved to: {DATA_DIR}",
                     font=ctk.CTkFont(family=FONT, size=10),
                     text_color=TEXT_SUB).pack(pady=(0, 20))

        btn_row = ctk.CTkFrame(content, fg_color="transparent")
        btn_row.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(btn_row, text="New Setup", height=42, corner_radius=8,
                      fg_color=ACCENT, hover_color=ACCENT_HV,
                      font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
                      command=self._reset_and_setup
                      ).pack(side="left", expand=True, fill="x", padx=(0, 4))

        ctk.CTkButton(btn_row, text="Close", height=42, corner_radius=8,
                      fg_color=BORDER, hover_color="#D1D5DB", text_color=TEXT,
                      font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
                      command=self.destroy
                      ).pack(side="left", expand=True, fill="x", padx=(4, 0))

    def _reset_and_setup(self):
        self._candidates = []
        self._voters = []
        self._show_setup_page()


if __name__ == "__main__":
    app = SetupApp()
    app.mainloop()
