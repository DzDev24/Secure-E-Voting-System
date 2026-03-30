"""
admin_gui.py – Clean light-themed admin interface (CustomTkinter).

All confirmations and messages are shown inline — no popup dialogs.

Run:  python admin_gui.py
"""

import json
import os
import threading
import customtkinter as ctk

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

    def _header(self, parent):
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
        total_offset = 20
        if step >= steps:
            widget.pack_configure(pady=(12, 8))
            return
        t = step / steps
        eased = 1 - (1 - t) ** 3
        offset = int(total_offset * (1 - eased))
        widget.pack_configure(pady=(12 + offset, 8))
        self.after(delay, self._fade_in, widget, steps, delay, step + 1)

    # ══════════════════════════════════════════════════════════════════════
    #  Dashboard
    # ══════════════════════════════════════════════════════════════════════

    def _show_dashboard(self, status_msg=None, status_color=None):
        self._clear()
        self._header(self._container)

        content = ctk.CTkFrame(self._container, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=28, pady=16)

        # Inline status message (replaces messageboxes)
        if status_msg:
            msg_frame = ctk.CTkFrame(content, fg_color="#F0FDF4" if status_color == SUCCESS
                                     else "#FEF3C7" if status_color == WARNING
                                     else "#FEF2F2",
                                     corner_radius=8, border_width=1,
                                     border_color="#BBF7D0" if status_color == SUCCESS
                                     else "#FDE68A" if status_color == WARNING
                                     else "#FECACA")
            msg_frame.pack(fill="x", pady=(0, 10))
            ctk.CTkLabel(msg_frame, text=status_msg,
                         font=ctk.CTkFont(family=FONT, size=11),
                         text_color=status_color or TEXT, wraplength=480,
                         justify="left").pack(padx=16, pady=10)

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
        # Also check if election was auto-closed (100% turnout)
        if self._is_election_closed():
            self._show_final_results(self._load_results_data())
            return
        self._refresh_display()
        self._poll_id = self.after(30000, self._auto_refresh)

    def _refresh_display(self):
        """Fetch results in a background thread to avoid freezing the UI."""
        def _fetch():
            try:
                resp = get_results()
                self.after(0, self._on_results_fetched, resp, None)
            except Exception as exc:
                self.after(0, self._on_results_fetched, None, exc)

        threading.Thread(target=_fetch, daemon=True).start()

    def _on_results_fetched(self, resp, error):
        """Handle results on the main thread after background fetch."""
        # Check if election was auto-closed while we were fetching
        if self._is_election_closed():
            self._show_final_results(self._load_results_data())
            return
        if not hasattr(self, "_results_inner") or not self._results_inner.winfo_exists():
            return
        for w in self._results_inner.winfo_children():
            w.destroy()

        if error is not None:
            msg = ("Cannot connect to the voting server.\n"
                   "Make sure voting_server.py is running."
                   if isinstance(error, ConnectionRefusedError)
                   else f"Error: {error}")
            ctk.CTkLabel(self._results_inner, text=msg,
                         font=ctk.CTkFont(family=FONT, size=12),
                         text_color=ERROR, justify="center").pack(pady=24)
            return

        tally = resp.get("tally", {})
        total = resp.get("total_votes", 0)
        registered = resp.get("total_registered", self._total_registered)
        rnd = resp.get("round", 1)

        if hasattr(self, "_round_label") and self._round_label.winfo_exists():
            self._round_label.configure(
                text=f"ROUND {rnd}  (Runoff)" if rnd > 1 else "ROUND 1")

        self._draw_tally(self._results_inner, tally, total, registered)

    def _draw_tally(self, parent, tally, total, registered):
        if total == 0:
            ctk.CTkLabel(parent, text="No votes have been cast yet.",
                         font=ctk.CTkFont(family=FONT, size=12),
                         text_color=TEXT_SUB).pack(pady=(12, 0))
        else:
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
        try:
            if not widget.winfo_exists():
                return
            total_steps = 35
            if step >= total_steps:
                widget.place_configure(relwidth=target)
                return
            t = step / total_steps
            eased = 1 - (1 - t) ** 3
            new_width = 0.005 + (target - 0.005) * eased
            widget.place_configure(relwidth=new_width)
            self.after(30, self._animate_bar, widget, new_width, target, step + 1)
        except Exception:
            pass  # Widget was destroyed, stop animation silently

    # ══════════════════════════════════════════════════════════════════════
    #  Final Results
    # ══════════════════════════════════════════════════════════════════════

    def _show_final_results(self, data):
        self._clear()
        self._header(self._container)

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
    #  Inline Confirmation Pages (replace all messageboxes)
    # ══════════════════════════════════════════════════════════════════════

    def _show_confirm_page(self, title, message, on_confirm, on_cancel,
                           confirm_text="Confirm", confirm_color=ACCENT,
                           cancel_text="Cancel"):
        """Generic inline confirmation page."""
        self._clear()
        self._header(self._container)

        content = ctk.CTkFrame(self._container, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=28, pady=24)

        card = self._card(content, title)
        card.pack(fill="x", pady=(12, 8))

        ctk.CTkLabel(card, text=message,
                     font=ctk.CTkFont(family=FONT, size=12),
                     text_color=TEXT, wraplength=440, justify="left"
                     ).pack(fill="x", padx=24, pady=(0, 20))

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=(0, 24))

        ctk.CTkButton(btn_row, text=confirm_text, height=44, corner_radius=8,
                      fg_color=confirm_color,
                      hover_color="#B91C1C" if confirm_color == ERROR else ACCENT_HV,
                      font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
                      command=on_confirm
                      ).pack(side="left", expand=True, fill="x", padx=(0, 4))

        ctk.CTkButton(btn_row, text=cancel_text, height=44, corner_radius=8,
                      fg_color=BORDER, hover_color="#D1D5DB", text_color=TEXT,
                      font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
                      command=on_cancel
                      ).pack(side="left", expand=True, fill="x", padx=(4, 0))

        self._fade_in(card)

    # ══════════════════════════════════════════════════════════════════════
    #  Actions
    # ══════════════════════════════════════════════════════════════════════

    def _on_end_election(self):
        self._show_confirm_page(
            "END ELECTION",
            "Are you sure you want to end the election?\n\n"
            "If there is a tie, a runoff round will start instead.",
            on_confirm=self._do_end_election,
            on_cancel=self._show_dashboard,
            confirm_text="End Election",
            confirm_color=ERROR,
            cancel_text="Go Back",
        )

    def _do_end_election(self):
        """Run close_election in a background thread to avoid UI freeze."""
        def _close():
            try:
                resp = close_election()
                self.after(0, self._on_election_closed, resp, None)
            except Exception as exc:
                self.after(0, self._on_election_closed, None, exc)

        threading.Thread(target=_close, daemon=True).start()

    def _on_election_closed(self, resp, error):
        """Handle close_election response on the main thread."""
        if error is not None:
            msg = ("Cannot connect to the voting server."
                   if isinstance(error, ConnectionRefusedError)
                   else f"Unexpected error: {error}")
            self._show_dashboard(status_msg=msg, status_color=ERROR)
            return

        status = resp.get("status", "")

        if status == "runoff":
            rnd = resp.get("round", 2)
            cands = resp.get("candidates", [])
            self._show_dashboard(
                status_msg=f"Tie detected among: {', '.join(cands)}. "
                           f"Round {rnd} has started — all voters may vote again.",
                status_color=WARNING)
            return

        if status == "rejected":
            self._show_dashboard(
                status_msg=resp.get("message", "Cannot close election."),
                status_color=WARNING)
            return

        data = self._load_results_data()
        self._show_final_results(data)

    def _on_reset(self):
        """Show reset options page with three choices inline."""
        self._clear()
        self._header(self._container)

        content = ctk.CTkFrame(self._container, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=28, pady=24)

        card = self._card(content, "RESET ELECTION")
        card.pack(fill="x", pady=(12, 8))

        ctk.CTkLabel(card, text="Choose a reset option:",
                     font=ctk.CTkFont(family=FONT, size=12),
                     text_color=TEXT).pack(fill="x", padx=24, pady=(0, 16))

        # Option 1 — Reset votes only
        ctk.CTkButton(card, text="Reset Votes Only",
                      height=44, corner_radius=8,
                      fg_color=WARNING, hover_color="#B45309",
                      font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
                      command=self._do_reset_votes
                      ).pack(fill="x", padx=24, pady=(0, 4))
        ctk.CTkLabel(card, text="Clears all votes. Keeps voters and candidates.",
                     font=ctk.CTkFont(family=FONT, size=11),
                     text_color=TEXT_SUB).pack(padx=24, pady=(0, 14))

        # Option 2 — Full reset
        ctk.CTkButton(card, text="Delete All Data",
                      height=44, corner_radius=8,
                      fg_color=ERROR, hover_color="#B91C1C",
                      font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
                      command=self._confirm_full_reset
                      ).pack(fill="x", padx=24, pady=(0, 4))
        ctk.CTkLabel(card, text="Deletes everything: keys, voters, candidates, results.",
                     font=ctk.CTkFont(family=FONT, size=11),
                     text_color=TEXT_SUB).pack(padx=24, pady=(0, 14))

        # Cancel
        ctk.CTkButton(card, text="Cancel", height=44, corner_radius=8,
                      fg_color=BORDER, hover_color="#D1D5DB", text_color=TEXT,
                      font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
                      command=self._go_back_from_reset
                      ).pack(fill="x", padx=24, pady=(0, 24))

        self._fade_in(card)

    def _go_back_from_reset(self):
        if self._is_election_closed():
            self._show_final_results(self._load_results_data())
        else:
            self._show_dashboard()

    def _do_reset_votes(self):
        reset_votes()
        self._show_dashboard(
            status_msg="Vote results have been cleared. Restart the server to apply changes.",
            status_color=SUCCESS)

    def _confirm_full_reset(self):
        self._show_confirm_page(
            "CONFIRM FULL RESET",
            "This will delete ALL election data:\n\n"
            "• Server keys\n• Voter keys\n"
            "• Candidates\n• Results\n\n"
            "You will need to run admin_setup.py again.",
            on_confirm=self._do_full_reset,
            on_cancel=self._on_reset,
            confirm_text="Delete Everything",
            confirm_color=ERROR,
            cancel_text="Go Back",
        )

    def _do_full_reset(self):
        reset_all()
        self._total_registered = 0
        if os.path.isdir(DATA_DIR):
            self._show_dashboard(
                status_msg="All election data has been deleted. Run admin_setup.py to set up a new election.",
                status_color=SUCCESS)
        else:
            self._show_dashboard(
                status_msg="All election data has been deleted. Run admin_setup.py to set up a new election.",
                status_color=SUCCESS)


if __name__ == "__main__":
    app = AdminApp()
    app.mainloop()
