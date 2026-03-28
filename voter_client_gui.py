"""
voter_client_gui.py – Tkinter-based GUI voter client (bonus).

Provides a professional graphical interface for the e-voting system with:
  - Voter authentication screen (login with voter ID verification)
  - Ballot casting with candidate radio-button selection
  - Vote confirmation / rejection display
  - Admin controls (close election and view final results)

Run:
    python voter_client_gui.py
"""

import json
import os
import tkinter as tk
from tkinter import messagebox, ttk

from voter_client import (
    cast_vote, close_election, get_results, reset_votes, reset_all,
)

# ─── Data paths ──────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CANDIDATES_FILE = os.path.join(DATA_DIR, "candidates.json")
VOTERS_FILE = os.path.join(DATA_DIR, "voters.json")

# ─── Design tokens ───────────────────────────────────────────────────────────
COLORS = {
    "bg":           "#F0F2F5",
    "card":         "#FFFFFF",
    "header_bg":    "#1E293B",
    "header_fg":    "#FFFFFF",
    "header_sub":   "#94A3B8",
    "primary":      "#2563EB",
    "primary_hov":  "#1D4ED8",
    "success":      "#16A34A",
    "error":        "#DC2626",
    "warning":      "#D97706",
    "text":         "#1E293B",
    "text_sub":     "#64748B",
    "border":       "#E2E8F0",
    "input_bg":     "#F8FAFC",
    "admin":        "#7C3AED",
    "admin_hov":    "#6D28D9",
}
FONT = "Segoe UI"


# ─── Application ─────────────────────────────────────────────────────────────

class VoterApp(tk.Tk):
    """Multi-page voter client application."""

    def __init__(self):
        super().__init__()
        self.title("Secure E-Voting System")
        self.geometry("520x640")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])

        # State
        self._voter_id = None
        self._voter_name = None
        self._candidates = []
        self._voters = {}

        self._load_data()

        # Root container
        self._container = tk.Frame(self, bg=COLORS["bg"])
        self._container.pack(fill="both", expand=True)

        self._show_login_page()

    # ── data helpers ─────────────────────────────────────────────────────

    def _load_data(self):
        """Load candidates and voter registry from data/ directory."""
        try:
            with open(CANDIDATES_FILE) as f:
                self._candidates = json.load(f)
        except FileNotFoundError:
            messagebox.showerror(
                "Setup Error",
                "Candidates file not found.\nRun admin_setup.py first.",
            )
        try:
            with open(VOTERS_FILE) as f:
                self._voters = json.load(f)
        except FileNotFoundError:
            messagebox.showerror(
                "Setup Error",
                "Voter registry not found.\nRun admin_setup.py first.",
            )

    # ── widget builders ──────────────────────────────────────────────────

    def _clear(self):
        for w in self._container.winfo_children():
            w.destroy()

    def _header(self, parent, subtitle=""):
        frm = tk.Frame(parent, bg=COLORS["header_bg"], height=80)
        frm.pack(fill="x")
        frm.pack_propagate(False)
        tk.Label(
            frm, text="SECURE E-VOTING SYSTEM",
            font=(FONT, 16, "bold"),
            bg=COLORS["header_bg"], fg=COLORS["header_fg"],
        ).pack(pady=(18, 2))
        if subtitle:
            tk.Label(
                frm, text=subtitle, font=(FONT, 10),
                bg=COLORS["header_bg"], fg=COLORS["header_sub"],
            ).pack()

    def _card(self, parent, title=""):
        outer = tk.Frame(parent, bg=COLORS["border"], padx=1, pady=1)
        inner = tk.Frame(outer, bg=COLORS["card"], padx=24, pady=20)
        inner.pack(fill="both", expand=True)
        if title:
            tk.Label(
                inner, text=title, font=(FONT, 11, "bold"),
                bg=COLORS["card"], fg=COLORS["text"], anchor="w",
            ).pack(fill="x", pady=(0, 10))
            tk.Frame(inner, bg=COLORS["border"], height=1).pack(
                fill="x", pady=(0, 10),
            )
        return outer, inner

    def _action_btn(self, parent, text, bg, bg_hov, command, **kw):
        btn = tk.Button(
            parent, text=text, font=(FONT, 11, "bold"),
            bg=bg, fg="white", activebackground=bg_hov,
            activeforeground="white", relief="flat",
            cursor="hand2", command=command, **kw,
        )
        return btn

    # ══════════════════════════════════════════════════════════════════════
    #  PAGE 1 – Login
    # ══════════════════════════════════════════════════════════════════════

    def _show_login_page(self):
        self._clear()
        self._voter_id = self._voter_name = None

        self._header(self._container, "Class Representative Election")

        content = tk.Frame(self._container, bg=COLORS["bg"])
        content.pack(fill="both", expand=True, padx=32, pady=24)

        card_o, card = self._card(content, "VOTER AUTHENTICATION")
        card_o.pack(fill="x", pady=(0, 16))

        tk.Label(
            card,
            text="Enter your voter ID to authenticate\nand access the ballot.",
            font=(FONT, 9), bg=COLORS["card"],
            fg=COLORS["text_sub"], justify="left",
        ).pack(fill="x", pady=(0, 16))

        tk.Label(
            card, text="Voter ID", font=(FONT, 9, "bold"),
            bg=COLORS["card"], fg=COLORS["text"], anchor="w",
        ).pack(fill="x")

        self._login_var = tk.StringVar()
        entry = tk.Entry(
            card, textvariable=self._login_var,
            font=(FONT, 11), bg=COLORS["input_bg"],
            relief="solid", bd=1,
        )
        entry.pack(fill="x", pady=(4, 16), ipady=6)
        entry.focus_set()
        entry.bind("<Return>", lambda e: self._on_login())

        self._action_btn(
            card, "Log In",
            COLORS["primary"], COLORS["primary_hov"],
            self._on_login,
        ).pack(fill="x", ipady=8)

        self._login_msg = tk.StringVar()
        self._login_lbl = tk.Label(
            card, textvariable=self._login_msg,
            font=(FONT, 9), bg=COLORS["card"],
            fg=COLORS["error"], wraplength=350,
        )
        self._login_lbl.pack(fill="x", pady=(8, 0))

        # Admin section
        adm = tk.Frame(content, bg=COLORS["bg"])
        adm.pack(fill="x", pady=(8, 0))
        tk.Frame(adm, bg=COLORS["border"], height=1).pack(
            fill="x", pady=(0, 12),
        )
        tk.Label(
            adm, text="Administration", font=(FONT, 9),
            bg=COLORS["bg"], fg=COLORS["text_sub"],
        ).pack()
        adm_btns = tk.Frame(adm, bg=COLORS["bg"])
        adm_btns.pack(pady=(6, 0))
        self._action_btn(
            adm_btns, "View Live Results",
            COLORS["admin"], COLORS["admin_hov"],
            self._show_live_results_page,
        ).pack(side="left", padx=(0, 8), ipadx=12, ipady=4)
        self._action_btn(
            adm_btns, "Reset Election",
            COLORS["error"], "#B91C1C",
            self._on_reset_election,
        ).pack(side="left", ipadx=12, ipady=4)

    def _on_login(self):
        vid = self._login_var.get().strip()
        if not vid:
            self._login_msg.set("Please enter your Voter ID.")
            return
        if vid not in self._voters:
            self._login_msg.set(
                f"Voter ID '{vid}' not found in the registry."
            )
            return
        self._voter_id = vid
        self._voter_name = self._voters[vid].get("name", vid)
        self._show_voting_page()

    # ══════════════════════════════════════════════════════════════════════
    #  PAGE 2 – Voting
    # ══════════════════════════════════════════════════════════════════════

    def _show_voting_page(self):
        self._clear()
        self._header(self._container)

        content = tk.Frame(self._container, bg=COLORS["bg"])
        content.pack(fill="both", expand=True, padx=32, pady=24)

        # Info bar
        bar = tk.Frame(content, bg=COLORS["bg"])
        bar.pack(fill="x", pady=(0, 12))
        tk.Label(
            bar,
            text=f"Logged in as:  {self._voter_name}  ({self._voter_id})",
            font=(FONT, 10), bg=COLORS["bg"], fg=COLORS["text"],
        ).pack(side="left")
        logout = tk.Label(
            bar, text="Log Out", font=(FONT, 9, "underline"),
            bg=COLORS["bg"], fg=COLORS["primary"], cursor="hand2",
        )
        logout.pack(side="right")
        logout.bind("<Button-1>", lambda e: self._show_login_page())

        # Ballot card
        card_o, card = self._card(content, "SELECT YOUR CANDIDATE")
        card_o.pack(fill="both", expand=True)

        tk.Label(
            card, text="Choose one candidate from the list below.",
            font=(FONT, 9), bg=COLORS["card"], fg=COLORS["text_sub"],
        ).pack(fill="x", pady=(0, 12))

        self._cand_var = tk.StringVar(value="")
        for c in self._candidates:
            tk.Radiobutton(
                card, text=c, variable=self._cand_var, value=c,
                font=(FONT, 11), bg=COLORS["card"], fg=COLORS["text"],
                activebackground=COLORS["card"],
                selectcolor=COLORS["input_bg"],
                anchor="w", padx=8, pady=4,
            ).pack(fill="x")

        tk.Frame(card, bg=COLORS["card"], height=16).pack()

        self._vote_btn = self._action_btn(
            card, "Cast Vote",
            COLORS["primary"], COLORS["primary_hov"],
            self._on_cast_vote,
        )
        self._vote_btn.pack(fill="x", ipady=8)

        self._vote_msg = tk.StringVar()
        self._vote_lbl = tk.Label(
            card, textvariable=self._vote_msg,
            font=(FONT, 9), bg=COLORS["card"],
            fg=COLORS["text_sub"], wraplength=350,
        )
        self._vote_lbl.pack(fill="x", pady=(8, 0))

    def _on_cast_vote(self):
        cand = self._cand_var.get()
        if not cand:
            self._vote_msg.set("Please select a candidate before voting.")
            self._vote_lbl.config(fg=COLORS["warning"])
            return

        if not messagebox.askyesno(
            "Confirm Vote",
            f"You are about to cast your vote for:\n\n"
            f"    {cand}\n\n"
            f"This action cannot be undone. Proceed?",
        ):
            return

        self._vote_msg.set("Encrypting and signing vote ...")
        self._vote_lbl.config(fg=COLORS["primary"])
        self._vote_btn.config(state="disabled")
        self.update_idletasks()

        try:
            resp = cast_vote(self._voter_id, cand)
        except KeyError as exc:
            self._show_result_page("error", str(exc))
            return
        except ConnectionRefusedError:
            self._show_result_page(
                "error",
                "Cannot connect to the voting server.\n"
                "Make sure voting_server.py is running.",
            )
            return
        except Exception as exc:
            self._show_result_page("error", f"Unexpected error: {exc}")
            return

        st = resp.get("status", "unknown")
        msg = resp.get("message", "No response from server.")
        if st == "accepted":
            self._show_result_page("success", msg)
        else:
            self._show_result_page("rejected", msg)

    # ══════════════════════════════════════════════════════════════════════
    #  PAGE 3 – Vote result
    # ══════════════════════════════════════════════════════════════════════

    def _show_result_page(self, kind, message):
        self._clear()
        self._header(self._container)

        content = tk.Frame(self._container, bg=COLORS["bg"])
        content.pack(fill="both", expand=True, padx=32, pady=24)

        icon, title, color = {
            "success":  ("OK", "VOTE ACCEPTED",  COLORS["success"]),
            "rejected": ("X",  "VOTE REJECTED",  COLORS["warning"]),
            "error":    ("!",  "ERROR",           COLORS["error"]),
        }.get(kind, ("?", "UNKNOWN", COLORS["text_sub"]))

        card_o, card = self._card(content)
        card_o.pack(fill="x")

        tk.Label(
            card, text=icon, font=(FONT, 36, "bold"),
            bg=COLORS["card"], fg=color,
        ).pack(pady=(8, 4))
        tk.Label(
            card, text=title, font=(FONT, 14, "bold"),
            bg=COLORS["card"], fg=color,
        ).pack(pady=(0, 12))
        tk.Frame(card, bg=COLORS["border"], height=1).pack(
            fill="x", pady=(0, 12),
        )
        tk.Label(
            card, text=message, font=(FONT, 10),
            bg=COLORS["card"], fg=COLORS["text"],
            wraplength=380, justify="center",
        ).pack(pady=(0, 8))

        if self._voter_id:
            tk.Label(
                card,
                text=f"Voter: {self._voter_name} ({self._voter_id})",
                font=(FONT, 9), bg=COLORS["card"],
                fg=COLORS["text_sub"],
            ).pack(pady=(4, 16))

        self._action_btn(
            card, "Log Out",
            COLORS["text_sub"], COLORS["text"],
            self._show_login_page, width=20,
        ).pack(ipady=6)

    # ══════════════════════════════════════════════════════════════════════
    #  Admin – close election
    # ══════════════════════════════════════════════════════════════════════

    def _on_close_election(self):
        if not messagebox.askyesno(
            "Close Election",
            "Are you sure you want to close the election?\n\n"
            "No more votes will be accepted after this.",
        ):
            return
        try:
            resp = close_election()
        except ConnectionRefusedError:
            messagebox.showerror(
                "Connection Error",
                "Cannot connect to the voting server.\n"
                "Make sure voting_server.py is running.",
            )
            return
        except Exception as exc:
            messagebox.showerror("Error", f"Unexpected error:\n{exc}")
            return

        self._show_election_results(
            resp.get("message", "No results returned."),
        )

    def _show_election_results(self, results_text):
        self._clear()
        self._header(self._container, "Election Closed")

        content = tk.Frame(self._container, bg=COLORS["bg"])
        content.pack(fill="both", expand=True, padx=32, pady=24)

        card_o, card = self._card(content, "FINAL RESULTS")
        card_o.pack(fill="both", expand=True)

        txt = tk.Text(
            card, font=("Consolas", 11),
            bg=COLORS["input_bg"], fg=COLORS["text"],
            relief="solid", bd=1, wrap="word",
            height=12, padx=12, pady=12,
        )
        txt.pack(fill="both", expand=True, pady=(0, 16))
        txt.insert("1.0", results_text)
        txt.config(state="disabled")

        self._action_btn(
            card, "Exit Application",
            COLORS["text_sub"], COLORS["text"],
            self.destroy, width=20,
        ).pack(ipady=6)


    # ══════════════════════════════════════════════════════════════════════
    #  Admin – Live Results
    # ══════════════════════════════════════════════════════════════════════

    def _show_live_results_page(self):
        """Display live election results with refresh and end controls."""
        self._clear()
        self._header(self._container, "Live Results")

        content = tk.Frame(self._container, bg=COLORS["bg"])
        content.pack(fill="both", expand=True, padx=32, pady=24)

        card_o, card = self._card(content, "ELECTION RESULTS")
        card_o.pack(fill="both", expand=True)

        # Inner frame rebuilt on each refresh
        self._results_inner = tk.Frame(card, bg=COLORS["card"])
        self._results_inner.pack(fill="both", expand=True)

        self._refresh_results_display()

        # Button bar
        bar = tk.Frame(content, bg=COLORS["bg"])
        bar.pack(fill="x", pady=(12, 0))

        self._action_btn(
            bar, "Refresh",
            COLORS["primary"], COLORS["primary_hov"],
            self._refresh_results_display,
        ).pack(side="left", ipadx=16, ipady=4)

        self._action_btn(
            bar, "End Election",
            COLORS["error"], "#B91C1C",
            self._on_close_election,
        ).pack(side="left", padx=(8, 0), ipadx=16, ipady=4)

        self._action_btn(
            bar, "Back",
            COLORS["text_sub"], COLORS["text"],
            self._show_login_page,
        ).pack(side="right", ipadx=16, ipady=4)

    def _refresh_results_display(self):
        """Fetch results from the server and redraw the tally."""
        for w in self._results_inner.winfo_children():
            w.destroy()

        try:
            resp = get_results()
            tally = resp.get("tally", {})
            total = resp.get("total_votes", 0)
        except ConnectionRefusedError:
            tk.Label(
                self._results_inner,
                text="Cannot connect to the voting server.\n"
                     "Make sure voting_server.py is running.",
                font=(FONT, 10), bg=COLORS["card"], fg=COLORS["error"],
                justify="center",
            ).pack(pady=20)
            return
        except Exception as exc:
            tk.Label(
                self._results_inner, text=f"Error: {exc}",
                font=(FONT, 10), bg=COLORS["card"], fg=COLORS["error"],
            ).pack(pady=20)
            return

        if total == 0:
            tk.Label(
                self._results_inner,
                text="No votes have been cast yet.",
                font=(FONT, 10), bg=COLORS["card"],
                fg=COLORS["text_sub"],
            ).pack(pady=20)
            return

        max_v = max(tally.values(), default=1) or 1

        for candidate, count in tally.items():
            row = tk.Frame(self._results_inner, bg=COLORS["card"])
            row.pack(fill="x", pady=5)

            tk.Label(
                row, text=candidate, font=(FONT, 10),
                bg=COLORS["card"], fg=COLORS["text"],
                width=14, anchor="w",
            ).pack(side="left")

            bar_bg = tk.Frame(
                row, bg=COLORS["border"], height=22, width=200,
            )
            bar_bg.pack(side="left", padx=(8, 8))
            bar_bg.pack_propagate(False)

            bar_w = int(200 * count / max_v)
            if bar_w > 0:
                tk.Frame(
                    bar_bg, bg=COLORS["primary"], width=bar_w,
                ).pack(side="left", fill="y")

            pct = int(100 * count / total) if total else 0
            tk.Label(
                row,
                text=f"{count} vote{'s' if count != 1 else ''}  ({pct}%)",
                font=(FONT, 9), bg=COLORS["card"], fg=COLORS["text_sub"],
            ).pack(side="left")

        tk.Frame(
            self._results_inner, bg=COLORS["border"], height=1,
        ).pack(fill="x", pady=(12, 8))

        tk.Label(
            self._results_inner,
            text=f"Total votes cast: {total}",
            font=(FONT, 10, "bold"), bg=COLORS["card"], fg=COLORS["text"],
        ).pack()

    # ══════════════════════════════════════════════════════════════════════
    #  Admin – Reset Election
    # ══════════════════════════════════════════════════════════════════════

    def _on_reset_election(self):
        """Reset election data — votes only or full wipe."""
        choice = messagebox.askyesnocancel(
            "Reset Election",
            "Do you want to reset the election data?\n\n"
            "YES  \u2014 Delete votes only (keep voters & candidates)\n"
            "NO   \u2014 Delete ALL data (voters, candidates, keys, votes)\n"
            "CANCEL \u2014 Do nothing",
        )
        if choice is None:
            return

        if choice:  # YES — votes only
            reset_votes()
            messagebox.showinfo(
                "Reset Complete",
                "Vote results have been cleared.\n"
                "Restart the server to apply changes.",
            )
        else:  # NO — full reset
            if not messagebox.askyesno(
                "Confirm Full Reset",
                "This will delete ALL election data:\n"
                "\u2022 Server keys\n\u2022 Voter keys\n"
                "\u2022 Candidates\n\u2022 Results\n\n"
                "You will need to run admin_setup.py again.\n"
                "Proceed?",
            ):
                return
            reset_all()
            self._candidates = []
            self._voters = {}
            messagebox.showinfo(
                "Reset Complete",
                "All election data has been deleted.\n"
                "Run admin_setup.py to set up a new election.",
            )


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = VoterApp()
    app.mainloop()
