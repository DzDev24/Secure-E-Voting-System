"""
admin_gui.py – Clean light-themed admin interface (CustomTkinter).

Run:  python admin_gui.py
"""

import json
import os
import customtkinter as ctk
from tkinter import messagebox

from voter_client import close_election, get_results, reset_votes, reset_all

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
PURPLE    = "#7C3AED"
PURPLE_HV = "#6D28D9"

BAR_COLORS = ["#4F46E5", "#0891B2", "#DB2777", "#7C3AED", "#059669",
              "#D97706", "#EA580C", "#DC2626", "#0284C7", "#9333EA"]

# ─── Paths ───────────────────────────────────────────────────────────────────
DATA_DIR     = os.path.join(os.path.dirname(__file__), "data")
RESULTS_FILE = os.path.join(DATA_DIR, "results.json")
VOTERS_FILE  = os.path.join(DATA_DIR, "voters.json")

FONT = "Segoe UI"


class AdminApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("E-Voting Admin Panel")
        self.geometry("580x680")
        self.minsize(500, 580)
        self.configure(fg_color=BG)

        self._poll_id = None
        self._container = ctk.CTkFrame(self, fg_color="transparent")
        self._container.pack(fill="both", expand=True)

        self._total_registered = 0
        try:
            with open(VOTERS_FILE) as f:
                self._total_registered = len(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        if self._is_election_closed():
            self._show_final_results(self._load_results_data())
        else:
            self._show_dashboard()

    # ── helpers ──────────────────────────────────────────────────────────

    def _is_election_closed(self):
        if os.path.exists(RESULTS_FILE):
            try:
                with open(RESULTS_FILE) as f:
                    return json.load(f).get("election_closed", False)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return False

    def _load_results_data(self):
        if os.path.exists(RESULTS_FILE):
            try:
                with open(RESULTS_FILE) as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return {}

    def _clear(self):
        if self._poll_id:
            self.after_cancel(self._poll_id)
            self._poll_id = None
        for w in self._container.winfo_children():
            w.destroy()

    # ── shared widgets ───────────────────────────────────────────────────

    def _header(self, parent, subtitle=""):
        hdr = ctk.CTkFrame(parent, fg_color=HEADER_BG, corner_radius=0, height=60)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="ADMIN PANEL",
                     font=ctk.CTkFont(family=FONT, size=18, weight="bold"),
                     text_color=HEADER_FG).pack(pady=(16, 2))

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
        if step == 0:
            pass
        fraction = step / steps
        offset = int(8 * (1 - fraction))
        if step < steps:
            widget.pack_configure(pady=(offset + 12, 8))
            self.after(delay, self._fade_in, widget, steps, delay, step + 1)
        else:
            widget.pack_configure(pady=(12, 8))

    # ══════════════════════════════════════════════════════════════════════
    #  Dashboard
    # ══════════════════════════════════════════════════════════════════════

    def _show_dashboard(self):
        self._clear()
        self._header(self._container, "Secure E-Voting System")

        content = ctk.CTkFrame(self._container, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=28, pady=16)

        # Round label
        self._round_label = ctk.CTkLabel(
            content, text="",
            font=ctk.CTkFont(family=FONT, size=11, weight="bold"),
            text_color=PURPLE)
        self._round_label.pack(anchor="w", pady=(0, 6))

        # Results card
        card = self._card(content, "ELECTION RESULTS")
        card.pack(fill="both", expand=True, pady=(0, 8))

        self._results_inner = ctk.CTkFrame(card, fg_color="transparent")
        self._results_inner.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        self._refresh_display()

        # Button bar
        bar = ctk.CTkFrame(content, fg_color="transparent")
        bar.pack(fill="x", pady=(6, 0))

        ctk.CTkButton(bar, text="Refresh", height=38, corner_radius=8,
                      fg_color=ACCENT, hover_color=ACCENT_HV,
                      font=ctk.CTkFont(family=FONT, size=12, weight="bold"),
                      command=self._refresh_display, width=110
                      ).pack(side="left")

        ctk.CTkButton(bar, text="End Election", height=38, corner_radius=8,
                      fg_color=ERROR, hover_color="#B91C1C",
                      font=ctk.CTkFont(family=FONT, size=12, weight="bold"),
                      command=self._on_end_election, width=120
                      ).pack(side="left", padx=(8, 0))

        ctk.CTkButton(bar, text="Reset Election", height=38, corner_radius=8,
                      fg_color=PURPLE, hover_color=PURPLE_HV,
                      font=ctk.CTkFont(family=FONT, size=12, weight="bold"),
                      command=self._on_reset, width=120
                      ).pack(side="right")

        self._auto_refresh()

    def _auto_refresh(self):
        self._refresh_display()
        self._poll_id = self.after(30000, self._auto_refresh)

    def _refresh_display(self):
        for w in self._results_inner.winfo_children():
            w.destroy()

        try:
            resp = get_results()
            tally = resp.get("tally", {})
            total = resp.get("total_votes", 0)
            registered = resp.get("total_registered", self._total_registered)
            rnd = resp.get("round", 1)
        except ConnectionRefusedError:
            ctk.CTkLabel(self._results_inner,
                         text="Cannot connect to the voting server.\n"
                              "Make sure voting_server.py is running.",
                         font=ctk.CTkFont(family=FONT, size=12),
                         text_color=ERROR, justify="center").pack(pady=24)
            return
        except Exception as exc:
            ctk.CTkLabel(self._results_inner, text=f"Error: {exc}",
                         font=ctk.CTkFont(family=FONT, size=12),
                         text_color=ERROR).pack(pady=24)
            return

        if hasattr(self, "_round_label"):
            self._round_label.configure(
                text=f"ROUND {rnd}  (Runoff)" if rnd > 1 else "ROUND 1")

        self._draw_tally(self._results_inner, tally, total, registered)

    def _draw_tally(self, parent, tally, total, registered):
        if total == 0:
            ctk.CTkLabel(parent, text="No votes have been cast yet.",
                         font=ctk.CTkFont(family=FONT, size=12),
                         text_color=TEXT_SUB).pack(pady=(12, 0))
        else:
            max_v = max(tally.values(), default=1) or 1
            for i, (candidate, count) in enumerate(tally.items()):
                color = BAR_COLORS[i % len(BAR_COLORS)]
                pct = int(100 * count / total) if total else 0

                row = ctk.CTkFrame(parent, fg_color="transparent")
                row.pack(fill="x", pady=5)

                info = ctk.CTkFrame(row, fg_color="transparent")
                info.pack(fill="x")
                ctk.CTkLabel(info, text=candidate,
                             font=ctk.CTkFont(family=FONT, size=12),
                             text_color=TEXT, anchor="w").pack(side="left")
                ctk.CTkLabel(info,
                             text=f"{count} vote{'s' if count != 1 else ''}  ({pct}%)",
                             font=ctk.CTkFont(family=FONT, size=11),
                             text_color=TEXT_SUB, anchor="e").pack(side="right")

                # Animated bar — width = actual percentage of total votes
                bar_bg = ctk.CTkFrame(row, fg_color="#F3F4F6", height=12,
                                      corner_radius=6)
                bar_bg.pack(fill="x", pady=(3, 0))
                bar_bg.pack_propagate(False)

                target = count / total if total else 0
                if target > 0:
                    bar_fill = ctk.CTkFrame(bar_bg, fg_color=color,
                                            corner_radius=6)
                    bar_fill.place(relx=0, rely=0, relwidth=0.005, relheight=1)
                    self.after(120 * i, self._animate_bar, bar_fill, 0.005, target, 0)

        # Turnout
        ctk.CTkFrame(parent, fg_color=BORDER, height=1).pack(fill="x", pady=(14, 10))
        turnout_pct = int(100 * total / registered) if registered else 0

        t_row = ctk.CTkFrame(parent, fg_color="transparent")
        t_row.pack(fill="x")
        ctk.CTkLabel(t_row, text="Voter Turnout",
                     font=ctk.CTkFont(family=FONT, size=12, weight="bold"),
                     text_color=TEXT).pack(side="left")
        ctk.CTkLabel(t_row,
                     text=f"{total} / {registered} voters  ({turnout_pct}%)",
                     font=ctk.CTkFont(family=FONT, size=11),
                     text_color=TEXT_SUB).pack(side="right")

        t_color = SUCCESS if turnout_pct >= 50 else WARNING
        t_bar_bg = ctk.CTkFrame(parent, fg_color="#F3F4F6", height=8,
                                corner_radius=4)
        t_bar_bg.pack(fill="x", pady=(6, 2))
        t_bar_bg.pack_propagate(False)

        if turnout_pct > 0:
            t_fill = ctk.CTkFrame(t_bar_bg, fg_color=t_color, corner_radius=4)
            t_fill.place(relx=0, rely=0, relwidth=0.01, relheight=1)
            self._animate_bar(t_fill, 0.01, min(turnout_pct / 100, 1.0))

    def _animate_bar(self, widget, current, target, step=0):
        """Smoothly grow a bar with ease-out curve."""
        total_steps = 35
        if step >= total_steps:
            widget.place_configure(relwidth=target)
            return
        t = step / total_steps
        eased = 1 - (1 - t) ** 3
        new_width = 0.005 + (target - 0.005) * eased
        widget.place_configure(relwidth=new_width)
        self.after(30, self._animate_bar, widget, new_width, target, step + 1)

    # ══════════════════════════════════════════════════════════════════════
    #  Final Results
    # ══════════════════════════════════════════════════════════════════════

    def _show_final_results(self, data):
        self._clear()
        self._header(self._container, "Election Closed")

        content = ctk.CTkFrame(self._container, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=28, pady=16)

        card = self._card(content, "FINAL RESULTS")
        card.pack(fill="both", expand=True, pady=(12, 8))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        tally = data.get("tally", {})
        total = sum(tally.values())
        registered = self._total_registered or len(data.get("voted_ids", []))
        rnd = data.get("round", 1)

        if rnd > 1:
            ctk.CTkLabel(inner, text=f"Decided in Round {rnd}",
                         font=ctk.CTkFont(family=FONT, size=11, weight="bold"),
                         text_color=PURPLE).pack(anchor="w", pady=(0, 6))

        self._draw_tally(inner, tally, total, registered)

        if tally:
            winner = max(tally, key=tally.get)
            win_frame = ctk.CTkFrame(inner, fg_color="#F0FDF4", corner_radius=10,
                                     border_width=1, border_color="#BBF7D0")
            win_frame.pack(fill="x", pady=(12, 0))
            ctk.CTkLabel(win_frame, text=f"Winner:  {winner}",
                         font=ctk.CTkFont(family=FONT, size=15, weight="bold"),
                         text_color=SUCCESS).pack(pady=12)

        btn_row = ctk.CTkFrame(content, fg_color="transparent")
        btn_row.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(btn_row, text="Reset Election", height=42, corner_radius=8,
                      fg_color=ERROR, hover_color="#B91C1C",
                      font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
                      command=self._on_reset).pack(side="left", expand=True, fill="x",
                                                    padx=(0, 4))
        ctk.CTkButton(btn_row, text="Exit", height=42, corner_radius=8,
                      fg_color=BORDER, hover_color="#D1D5DB", text_color=TEXT,
                      font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
                      command=self.destroy).pack(side="left", expand=True, fill="x",
                                                  padx=(4, 0))

    # ══════════════════════════════════════════════════════════════════════
    #  Actions
    # ══════════════════════════════════════════════════════════════════════

    def _on_end_election(self):
        if not messagebox.askyesno(
            "End Election",
            "Are you sure you want to end the election?\n\n"
            "If there is a tie, a runoff round will start instead.",
        ):
            return
        try:
            resp = close_election()
        except ConnectionRefusedError:
            messagebox.showerror("Connection Error",
                                 "Cannot connect to the voting server.")
            return
        except Exception as exc:
            messagebox.showerror("Error", f"Unexpected error:\n{exc}")
            return

        status = resp.get("status", "")

        if status == "runoff":
            rnd = resp.get("round", 2)
            cands = resp.get("candidates", [])
            messagebox.showinfo(
                "Runoff Round",
                f"Tie detected among: {', '.join(cands)}\n\n"
                f"Eliminated candidates with fewer votes.\n"
                f"Round {rnd} has started — all voters may vote again.\n\n"
                f"The voter client will update automatically.",
            )
            self._show_dashboard()
            return

        if status == "rejected":
            messagebox.showwarning("Cannot Close", resp.get("message", ""))
            return

        data = self._load_results_data()
        self._show_final_results(data)

    def _on_reset(self):
        choice = messagebox.askyesnocancel(
            "Reset Election",
            "Do you want to reset the election data?\n\n"
            "YES  — Delete votes only (keep voters & candidates)\n"
            "NO   — Delete ALL data (voters, candidates, keys, votes)\n"
            "CANCEL — Do nothing",
        )
        if choice is None:
            return
        if choice:
            reset_votes()
            messagebox.showinfo("Reset Complete",
                                "Vote results have been cleared.\n"
                                "Restart the server to apply changes.")
        else:
            if not messagebox.askyesno(
                "Confirm Full Reset",
                "This will delete ALL election data:\n"
                "• Server keys\n• Voter keys\n"
                "• Candidates\n• Results\n\n"
                "You will need to run admin_setup.py again.\nProceed?",
            ):
                return
            reset_all()
            self._total_registered = 0
            messagebox.showinfo("Reset Complete",
                                "All election data has been deleted.\n"
                                "Run admin_setup.py to set up a new election.")
        if os.path.isdir(DATA_DIR):
            self._show_dashboard()
        else:
            self.destroy()


if __name__ == "__main__":
    app = AdminApp()
    app.mainloop()
