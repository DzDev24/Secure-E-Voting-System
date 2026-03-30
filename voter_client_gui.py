"""
voter_client_gui.py – Clean light-themed voter client (CustomTkinter).

Run:  python voter_client_gui.py
"""

import json
import os
import customtkinter as ctk
from tkinter import messagebox

from voter_client import cast_vote

# ─── Theme ───────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("light")

# ─── Palette ─────────────────────────────────────────────────────────────────
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
DATA_DIR        = os.path.join(os.path.dirname(__file__), "data")
CANDIDATES_FILE = os.path.join(DATA_DIR, "candidates.json")
VOTERS_FILE     = os.path.join(DATA_DIR, "voters.json")
RESULTS_FILE    = os.path.join(DATA_DIR, "results.json")

FONT = "Segoe UI"


class VoterApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("Secure E-Voting System")
        self.geometry("520x600")
        self.minsize(460, 520)
        self.configure(fg_color=BG)

        self._voter_id = None
        self._voter_name = None
        self._candidates = []
        self._voters = {}
        self._current_round = 1
        self._poll_id = None

        self._load_data()

        self._container = ctk.CTkFrame(self, fg_color="transparent")
        self._container.pack(fill="both", expand=True)

        if self._is_election_closed():
            self._show_closed_message()
        else:
            self._show_login_page()

    # ── helpers ──────────────────────────────────────────────────────────

    def _load_data(self):
        missing = False
        try:
            with open(CANDIDATES_FILE) as f:
                self._candidates = json.load(f)
        except FileNotFoundError:
            messagebox.showerror("Setup Error",
                                 "Candidates file not found.\nRun admin_setup.py first.")
            missing = True
        try:
            with open(VOTERS_FILE) as f:
                self._voters = json.load(f)
        except FileNotFoundError:
            messagebox.showerror("Setup Error",
                                 "Voter registry not found.\nRun admin_setup.py first.")
            missing = True
        if missing:
            self.destroy()
            raise SystemExit(1)
        if os.path.exists(RESULTS_FILE):
            try:
                with open(RESULTS_FILE) as f:
                    data = json.load(f)
                active = data.get("active_candidates")
                if active:
                    self._candidates = active
            except (json.JSONDecodeError, FileNotFoundError):
                pass

    def _is_election_closed(self):
        if os.path.exists(RESULTS_FILE):
            try:
                with open(RESULTS_FILE) as f:
                    return json.load(f).get("election_closed", False)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return False

    def _has_voted(self, vid):
        if os.path.exists(RESULTS_FILE):
            try:
                with open(RESULTS_FILE) as f:
                    return vid in json.load(f).get("voted_ids", [])
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return False

    def _reload_state(self):
        self._current_round = 1
        if os.path.exists(RESULTS_FILE):
            try:
                with open(RESULTS_FILE) as f:
                    data = json.load(f)
                active = data.get("active_candidates")
                if active:
                    self._candidates = active
                self._current_round = data.get("round", 1)
            except (json.JSONDecodeError, FileNotFoundError):
                pass

    def _poll_state(self):
        old_round = getattr(self, "_current_round", 1)
        self._reload_state()
        if self._is_election_closed():
            self._show_closed_message()
            return
        if self._current_round != old_round:
            self._show_login_page()
            return
        self._poll_id = self.after(3000, self._poll_state)

    def _clear(self):
        if self._poll_id:
            self.after_cancel(self._poll_id)
            self._poll_id = None
        for w in self._container.winfo_children():
            w.destroy()

    # ── shared widgets ───────────────────────────────────────────────────

    def _header(self, parent, subtitle=""):
        h = 74 if subtitle else 60
        hdr = ctk.CTkFrame(parent, fg_color=HEADER_BG, corner_radius=0, height=h)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="SECURE E-VOTING SYSTEM",
                     font=ctk.CTkFont(family=FONT, size=18, weight="bold"),
                     text_color=HEADER_FG).pack(pady=(14, 1))
        if subtitle:
            ctk.CTkLabel(hdr, text=subtitle,
                         font=ctk.CTkFont(family=FONT, size=11),
                         text_color="#94A3B8").pack()

    def _card(self, parent, title=""):
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=12,
                            border_width=1, border_color=BORDER)
        if title:
            ctk.CTkLabel(card, text=title,
                         font=ctk.CTkFont(family=FONT, size=12, weight="bold"),
                         text_color=TEXT, anchor="w").pack(fill="x", padx=24, pady=(20, 6))
            ctk.CTkFrame(card, fg_color=BORDER, height=1).pack(fill="x", padx=24, pady=(0, 12))
        return card

    def _fade_in(self, widget, steps=14, delay=35, step=0):
        """Card slide-up with ease-out cubic curve."""
        total_offset = 30  # pixels to slide from
        if step >= steps:
            widget.pack_configure(pady=(20, 10))
            return
        t = step / steps
        eased = 1 - (1 - t) ** 3  # ease-out cubic
        offset = int(total_offset * (1 - eased))
        widget.pack_configure(pady=(20 + offset, 10))
        self.after(delay, self._fade_in, widget, steps, delay, step + 1)

    # ══════════════════════════════════════════════════════════════════════
    #  Election Closed
    # ══════════════════════════════════════════════════════════════════════

    def _show_closed_message(self):
        self._clear()
        self._header(self._container, "Election Closed")
        content = ctk.CTkFrame(self._container, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=36, pady=24)
        card = self._card(content)
        card.pack(fill="x")
        ctk.CTkLabel(card, text="ELECTION HAS ENDED",
                     font=ctk.CTkFont(family=FONT, size=16, weight="bold"),
                     text_color=TEXT_SUB).pack(pady=(28, 8))
        ctk.CTkLabel(card, text="The voting period is over. Contact the administrator for results.",
                     font=ctk.CTkFont(family=FONT, size=12),
                     text_color=TEXT_SUB, wraplength=360, justify="center").pack(pady=(0, 24))
        ctk.CTkButton(card, text="Exit", height=42, corner_radius=8,
                      fg_color=BORDER, hover_color="#D1D5DB", text_color=TEXT,
                      font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
                      command=self.destroy).pack(fill="x", padx=24, pady=(0, 24))

    # ══════════════════════════════════════════════════════════════════════
    #  Login
    # ══════════════════════════════════════════════════════════════════════

    def _show_login_page(self):
        self._reload_state()
        if self._is_election_closed():
            self._show_closed_message()
            return
        self._clear()
        self._voter_id = self._voter_name = None

        sub = f"Runoff — Round {self._current_round}" if self._current_round > 1 else ""
        self._header(self._container, subtitle=sub)

        content = ctk.CTkFrame(self._container, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=36, pady=24)

        card = self._card(content, "VOTER AUTHENTICATION")
        card.pack(fill="x", pady=(20, 10))

        # Voter ID label + description inline
        ctk.CTkLabel(card, text="Voter ID — Enter your ID to access the ballot",
                     font=ctk.CTkFont(family=FONT, size=12),
                     text_color=TEXT_SUB, anchor="w"
                     ).pack(fill="x", padx=24, pady=(0, 6))

        self._login_var = ctk.StringVar()
        entry = ctk.CTkEntry(card, textvariable=self._login_var,
                             placeholder_text="e.g. STU_001",
                             height=42, corner_radius=8,
                             font=ctk.CTkFont(family=FONT, size=13),
                             border_color=BORDER, fg_color="#F9FAFB")
        entry.pack(fill="x", padx=24, pady=(0, 14))
        entry.focus_set()
        entry.bind("<Return>", lambda e: self._on_login())

        ctk.CTkButton(card, text="Log In", height=44, corner_radius=8,
                      fg_color=ACCENT, hover_color=ACCENT_HV,
                      font=ctk.CTkFont(family=FONT, size=14, weight="bold"),
                      command=self._on_login).pack(fill="x", padx=24)

        self._login_msg = ctk.StringVar()
        ctk.CTkLabel(card, textvariable=self._login_msg,
                     font=ctk.CTkFont(family=FONT, size=11),
                     text_color=ERROR, wraplength=360
                     ).pack(fill="x", padx=24, pady=(8, 20))

        self._fade_in(card)
        self._poll_state()

    def _on_login(self):
        vid = self._login_var.get().strip()
        if not vid:
            self._login_msg.set("Please enter your Voter ID.")
            return
        if vid not in self._voters:
            self._login_msg.set(f"Voter ID '{vid}' not found in the registry.")
            return
        if self._has_voted(vid):
            self._login_msg.set(f"Voter '{vid}' has already cast their vote.")
            return
        self._voter_id = vid
        self._voter_name = self._voters[vid].get("name", vid)
        self._show_voting_page()

    # ══════════════════════════════════════════════════════════════════════
    #  Voting
    # ══════════════════════════════════════════════════════════════════════

    def _show_voting_page(self):
        self._reload_state()
        if self._is_election_closed():
            self._show_closed_message()
            return
        self._clear()

        sub = f"Runoff — Round {self._current_round}" if self._current_round > 1 else ""
        self._header(self._container, subtitle=sub)

        content = ctk.CTkFrame(self._container, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=36, pady=16)

        # Top bar
        bar = ctk.CTkFrame(content, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(bar, text=f"{self._voter_name}  ({self._voter_id})",
                     font=ctk.CTkFont(family=FONT, size=12),
                     text_color=TEXT_SUB).pack(side="left")
        ctk.CTkButton(bar, text="Log Out", width=72, height=28, corner_radius=6,
                      fg_color="transparent", hover_color=BORDER,
                      border_width=1, border_color=BORDER, text_color=TEXT_SUB,
                      font=ctk.CTkFont(family=FONT, size=11),
                      command=self._show_login_page).pack(side="right")

        # Ballot card
        card = self._card(content, "SELECT YOUR CANDIDATE")
        card.pack(fill="both", expand=True)

        ctk.CTkLabel(card, text="Choose one candidate from the list below.",
                     font=ctk.CTkFont(family=FONT, size=12),
                     text_color=TEXT_SUB, anchor="w"
                     ).pack(fill="x", padx=24, pady=(0, 10))

        # Candidates — plain frame, no scrollbar
        cand_frame = ctk.CTkFrame(card, fg_color="transparent")
        cand_frame.pack(fill="both", expand=True, padx=16, pady=(0, 6))

        self._cand_var = ctk.StringVar(value="")
        for c in self._candidates:
            ctk.CTkRadioButton(
                cand_frame, text=f"  {c}", variable=self._cand_var, value=c,
                font=ctk.CTkFont(family=FONT, size=13),
                fg_color=ACCENT, hover_color=ACCENT_HV,
                border_color="#D1D5DB", text_color=TEXT,
                radiobutton_width=18, radiobutton_height=18,
            ).pack(fill="x", padx=10, pady=5, anchor="w")

        # Cast button
        self._vote_btn = ctk.CTkButton(
            card, text="Cast Vote", height=44, corner_radius=8,
            fg_color=ACCENT, hover_color=ACCENT_HV,
            font=ctk.CTkFont(family=FONT, size=14, weight="bold"),
            command=self._on_cast_vote,
        )
        self._vote_btn.pack(fill="x", padx=24, pady=(6, 4))

        self._vote_msg = ctk.StringVar()
        ctk.CTkLabel(card, textvariable=self._vote_msg,
                     font=ctk.CTkFont(family=FONT, size=11),
                     text_color=WARNING, wraplength=360
                     ).pack(fill="x", padx=24, pady=(4, 16))

        self._fade_in(card)

    def _on_cast_vote(self):
        cand = self._cand_var.get()
        if not cand:
            self._vote_msg.set("Please select a candidate before voting.")
            return
        if not messagebox.askyesno(
            "Confirm Vote",
            f"You are about to cast your vote for:\n\n"
            f"    {cand}\n\nThis action cannot be undone. Proceed?",
        ):
            return
        self._vote_msg.set("Encrypting and signing vote ...")
        self._vote_btn.configure(state="disabled")
        self.update_idletasks()

        try:
            resp = cast_vote(self._voter_id, cand)
        except KeyError as exc:
            self._show_result("error", str(exc))
            return
        except ConnectionRefusedError:
            self._show_result("error",
                              "Cannot connect to the voting server.\n"
                              "Make sure voting_server.py is running.")
            return
        except Exception as exc:
            self._show_result("error", f"Unexpected error: {exc}")
            return

        st = resp.get("status", "unknown")
        msg = resp.get("message", "No response from server.")
        self._show_result("success" if st == "accepted" else "rejected", msg)

    # ══════════════════════════════════════════════════════════════════════
    #  Result
    # ══════════════════════════════════════════════════════════════════════

    def _show_result(self, kind, message):
        self._clear()
        self._header(self._container)

        content = ctk.CTkFrame(self._container, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=36, pady=24)

        card = self._card(content)
        card.pack(fill="x", pady=(20, 10))

        icon, title, color = {
            "success":  ("✓", "VOTE ACCEPTED",  SUCCESS),
            "rejected": ("✗", "VOTE REJECTED",  WARNING),
            "error":    ("!", "ERROR",           ERROR),
        }.get(kind, ("?", "UNKNOWN", TEXT_SUB))

        ctk.CTkLabel(card, text=icon,
                     font=ctk.CTkFont(size=44, weight="bold"),
                     text_color=color).pack(pady=(24, 2))
        ctk.CTkLabel(card, text=title,
                     font=ctk.CTkFont(family=FONT, size=16, weight="bold"),
                     text_color=color).pack(pady=(0, 10))
        ctk.CTkFrame(card, fg_color=BORDER, height=1).pack(fill="x", padx=24, pady=(0, 12))
        ctk.CTkLabel(card, text=message,
                     font=ctk.CTkFont(family=FONT, size=12),
                     text_color=TEXT, wraplength=380, justify="center"
                     ).pack(padx=24, pady=(0, 4))
        if self._voter_id:
            ctk.CTkLabel(card, text=f"Voter: {self._voter_name} ({self._voter_id})",
                         font=ctk.CTkFont(family=FONT, size=11),
                         text_color=TEXT_SUB).pack(pady=(2, 16))

        ctk.CTkButton(card, text="Log Out", height=42, corner_radius=8,
                      fg_color=BORDER, hover_color="#D1D5DB", text_color=TEXT,
                      font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
                      command=self._show_login_page
                      ).pack(fill="x", padx=24, pady=(0, 24))

        self._fade_in(card)


if __name__ == "__main__":
    app = VoterApp()
    app.mainloop()
