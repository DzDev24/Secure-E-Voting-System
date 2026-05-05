"""
admin_gui.py – Administrative Control Panel (CustomTkinter).

Features:
  1. Start / Stop the TCP server.
  2. Auto-poll live election results.
  3. Visualize results via animated bar charts.
  4. Perform partial resets (reset tally but keep keys) or full factory resets.

Run:  python admin_gui.py
"""

import os
import shutil
import threading
import customtkinter as ctk

from voter_client import close_election, get_results, reset_votes
from voting_server import VotingServer


ctk.set_appearance_mode("light")


BG        = "#F3F4F6"
CARD      = "#FFFFFF"
BORDER    = "#E5E7EB"
ACCENT    = "#4F46E5"
ACCENT_HV = "#4338CA"
SUCCESS   = "#059669"
ERROR     = "#DC2626"
ERROR_HV  = "#B91C1C"
WARNING   = "#D97706"
TEXT      = "#111827"
TEXT_SUB  = "#6B7280"
HEADER_BG = "#1E293B"
HEADER_FG = "#FFFFFF"

# Array of colors for the animated bar charts
CHART_COLORS = ["#4F46E5", "#0891B2", "#059669", "#D97706", "#DC2626", "#7C3AED", "#BE185D"]

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
RESULTS_FILE = os.path.join(DATA_DIR, "results.json")
FONT = "Segoe UI"


class AdminApp(ctk.CTk):
    """Main application window for the admin dashboard."""

    def __init__(self):
        super().__init__()
        self.title("Admin Panel")
        self.geometry("640x740")
        self.minsize(580, 680)
        self.configure(fg_color=BG)

        # Variables to track server background thread
        self._server = None
        self._server_thread = None
        self._poll_id = None
        self._is_server_running = False
        
        # Store chart dictionary to update bars smoothly instead of redrawing
        self._bar_widgets = {}

        self._container = ctk.CTkFrame(self, fg_color="transparent")
        self._container.pack(fill="both", expand=True)

        self._show_dashboard()


    def _header(self, parent):
        bar = ctk.CTkFrame(parent, fg_color=HEADER_BG, height=60, corner_radius=0)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        ctk.CTkLabel(bar, text="Admin Control Panel",
                     font=ctk.CTkFont(family=FONT, size=16, weight="bold"),
                     text_color=HEADER_FG).pack(side="left", padx=20)

    def _card(self, parent, title=None):
        frame = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=12,
                             border_width=1, border_color=BORDER)
        if title:
            hdr = ctk.CTkFrame(frame, fg_color="transparent")
            hdr.pack(fill="x", padx=20, pady=(16, 8))
            ctk.CTkLabel(hdr, text=title,
                         font=ctk.CTkFont(family=FONT, size=11, weight="bold"),
                         text_color=TEXT_SUB).pack(side="left")
            ctk.CTkFrame(frame, fg_color=BORDER, height=1).pack(fill="x", padx=16)
        return frame

    def _clear(self):
        if self._poll_id:
            self.after_cancel(self._poll_id)
            self._poll_id = None
        for w in self._container.winfo_children():
            w.destroy()


    def _show_dashboard(self):
        self._clear()
        self._header(self._container)

        content = ctk.CTkFrame(self._container, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=28, pady=20)

        # ----------------------------------------------------
        # Top Panel: Server Controls
        # ----------------------------------------------------
        ctrl_card = self._card(content)
        ctrl_card.pack(fill="x", pady=(0, 16))
        
        ctrl_inner = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        ctrl_inner.pack(fill="x", padx=20, pady=16)

        self._status_label = ctk.CTkLabel(
            ctrl_inner, text="Server Stopped",
            font=ctk.CTkFont(family=FONT, size=15, weight="bold"),
            text_color=ERROR
        )
        self._status_label.pack(side="left")

        # Dynamic string for system messages (e.g. "Error starting server")
        self._msg_var = ctk.StringVar()
        ctk.CTkLabel(ctrl_inner, textvariable=self._msg_var,
                     font=ctk.CTkFont(family=FONT, size=11),
                     text_color=WARNING).pack(side="left", padx=16)

        self._start_btn = ctk.CTkButton(
            ctrl_inner, text="Start Server", width=110, height=36, corner_radius=8,
            fg_color=ACCENT, hover_color=ACCENT_HV,
            font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
            command=self._toggle_server
        )
        self._start_btn.pack(side="right")

        # ----------------------------------------------------
        # Middle Panel: Live Results Dashboard
        # ----------------------------------------------------
        self._res_card = self._card(content, "LIVE ELECTION RESULTS")
        self._res_card.pack(fill="both", expand=True, pady=(0, 16))

        # Stats bar below the results title
        stats_frame = ctk.CTkFrame(self._res_card, fg_color="#F9FAFB", corner_radius=8,
                                   border_width=1, border_color=BORDER)
        stats_frame.pack(fill="x", padx=20, pady=16)

        # Grid system for stats alignment
        stats_frame.grid_columnconfigure((0,1,2), weight=1)

        self._stat_turnout = ctk.StringVar(value="0 / 0")
        self._stat_round = ctk.StringVar(value="Round 1")
        self._stat_status = ctk.StringVar(value="Inactive")

        # Create three little stat boxes
        self._make_stat(stats_frame, "Turnout", self._stat_turnout, 0)
        self._make_stat(stats_frame, "Election Round", self._stat_round, 1)
        self._make_stat(stats_frame, "Status", self._stat_status, 2)

        # Container for the animated bar charts
        self._chart_frame = ctk.CTkScrollableFrame(
            self._res_card, fg_color="transparent",
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color="#D1D5DB"
        )
        self._chart_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self._bar_widgets = {}

        # ----------------------------------------------------
        # Bottom Panel: Danger Zone Actions
        # ----------------------------------------------------
        action_card = self._card(content, "ELECTION MANAGEMENT")
        action_card.pack(fill="x")
        
        acts = ctk.CTkFrame(action_card, fg_color="transparent")
        acts.pack(fill="x", padx=20, pady=16)

        self._close_btn = ctk.CTkButton(
            acts, text="End Election", width=120, height=36, corner_radius=8,
            fg_color=ERROR, hover_color=ERROR_HV,
            font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
            command=self._on_close_election, state="disabled"
        )
        self._close_btn.pack(side="left", padx=(0, 10))

        ctk.CTkButton(acts, text="Reset Tally (Keep Keys)", width=160, height=36,
                      corner_radius=8, fg_color=BORDER, hover_color="#D1D5DB", text_color=TEXT,
                      font=ctk.CTkFont(family=FONT, size=12, weight="bold"),
                      command=self._on_reset_tally
                      ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(acts, text="Factory Reset", width=120, height=36,
                      corner_radius=8, fg_color=BORDER, hover_color="#D1D5DB", text_color=ERROR,
                      font=ctk.CTkFont(family=FONT, size=12, weight="bold"),
                      command=self._on_factory_reset
                      ).pack(side="left")

        # Auto-poll the server for live results every 2 seconds
        self._poll_results()

    def _make_stat(self, parent, label, var, col):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=0, column=col, pady=10)
        ctk.CTkLabel(f, text=label, font=ctk.CTkFont(family=FONT, size=10),
                     text_color=TEXT_SUB).pack()
        ctk.CTkLabel(f, textvariable=var, font=ctk.CTkFont(family=FONT, size=16, weight="bold"),
                     text_color=TEXT).pack()


    def _toggle_server(self):
        """Starts or stops the TCP VotingServer in the background."""
        self._msg_var.set("")
        if self._is_server_running:
            self._stop_server()
        else:
            self._start_server()

    def _start_server(self):
        try:
            # Instantiate the server
            self._server = VotingServer()
            
            # Start it in a background thread so the GUI doesn't freeze waiting for sockets
            self._server_thread = threading.Thread(target=self._server.start, daemon=True)
            self._server_thread.start()
            
            self._is_server_running = True
            self._status_label.configure(text="Server Running", text_color=SUCCESS)
            self._start_btn.configure(text="Stop Server", fg_color=BORDER, text_color=TEXT, hover_color="#D1D5DB")
            self._close_btn.configure(state="normal")
            
        except FileNotFoundError as e:
            self._msg_var.set("Missing config. Run Election Setup.")
        except OSError as e:
            self._msg_var.set(f"Port error: {e}")
        except Exception as e:
            self._msg_var.set(f"Error: {e}")

    def _stop_server(self):
        if self._server:
            # Signal the server loop to exit safely
            self._server.stop()
            # Wait up to 3 seconds for the server thread to finish safely
            if self._server_thread:
                self._server_thread.join(timeout=3)
                
        self._is_server_running = False
        self._status_label.configure(text="Server Stopped", text_color=ERROR)
        self._start_btn.configure(text="Start Server", fg_color=ACCENT, text_color=HEADER_FG, hover_color=ACCENT_HV)
        self._close_btn.configure(state="disabled")


    def _poll_results(self):
        """Timer loop that fetches live results if the server is running."""
        if self._is_server_running:
            # We do the network fetch in a background thread to prevent UI stutter
            threading.Thread(target=self._fetch_results_task, daemon=True).start()
        
        # Schedule the next poll in 2000 ms (2 seconds)
        self._poll_id = self.after(2000, self._poll_results)

    def _fetch_results_task(self):
        """Background thread connecting via TCP to the server."""
        try:
            resp = get_results()
            if resp.get("status") == "ok":
                # Push the results to the UI thread
                self.after(0, lambda: self._update_ui_with_results(resp))
        except Exception:
            pass  # Silent fail is fine, it will try again in 2 seconds

    def _update_ui_with_results(self, data):
        """Updates the dashboard charts with new polling data."""
        tally = data.get("tally", {})
        total_votes = data.get("total_votes", 0)
        total_registered = data.get("total_registered", 0)
        rnd = data.get("round", 1)
        active = data.get("active_candidates", [])

        # Update text stats
        self._stat_turnout.set(f"{total_votes} / {total_registered}")
        self._stat_round.set(f"Round {rnd}")
        if total_registered > 0 and total_votes >= total_registered:
            self._stat_status.set("100% Turnout")
        else:
            self._stat_status.set("Live Voting")

        # Determine winner conditionally
        max_v = max(tally.values()) if tally else 0
        winners = [c for c, v in tally.items() if v == max_v] if max_v > 0 else []

        # Remove bars for candidates who were eliminated in a runoff
        for cand in list(self._bar_widgets.keys()):
            if cand not in active:
                self._bar_widgets[cand]["frame"].destroy()
                del self._bar_widgets[cand]

        # Ensure all active candidates have a UI bar
        for i, cand in enumerate(active):
            if cand not in self._bar_widgets:
                self._add_candidate_bar(cand, CHART_COLORS[i % len(CHART_COLORS)])
            
            # Animate the bar filling up
            self._update_candidate_bar(cand, tally.get(cand, 0), total_votes, cand in winners and len(winners) == 1)

    def _add_candidate_bar(self, cand_name, color):
        """Creates the physical GUI elements for a candidate's vote bar."""
        row = ctk.CTkFrame(self._chart_frame, fg_color="transparent")
        row.pack(fill="x", pady=8)

        # Container for text (Name on left, Vote Count on right)
        top = ctk.CTkFrame(row, fg_color="transparent", height=20)
        top.pack(fill="x")
        top.pack_propagate(False)

        name_lbl = ctk.CTkLabel(top, text=cand_name, font=ctk.CTkFont(family=FONT, size=13, weight="bold"), text_color=TEXT)
        name_lbl.pack(side="left")

        val_lbl = ctk.CTkLabel(top, text="0 votes (0%)", font=ctk.CTkFont(family=FONT, size=12), text_color=TEXT_SUB)
        val_lbl.pack(side="right")

        # Container for the progress bar background
        track = ctk.CTkFrame(row, fg_color="#F3F4F6", height=16, corner_radius=8, border_width=1, border_color=BORDER)
        track.pack(fill="x", pady=(4, 0))

        # The actual colored filling element
        bar = ctk.CTkFrame(track, fg_color=color, width=0, height=16, corner_radius=8)
        bar.pack(side="left", fill="y")
        
        # Save references so we can update them without destroying them
        self._bar_widgets[cand_name] = {
            "frame": row,
            "name_lbl": name_lbl,
            "val_lbl": val_lbl,
            "track": track,
            "bar": bar,
            "color": color,
            "current_width": 0
        }

    def _update_candidate_bar(self, cand_name, votes, total, is_winner):
        """Updates an existing bar chart with new numbers and smooth animations."""
        w = self._bar_widgets[cand_name]
        pct = (votes / total * 100) if total > 0 else 0
        w["val_lbl"].configure(text=f"{votes} votes ({pct:.1f}%)")

        if is_winner:
            w["name_lbl"].configure(text=f"🏆 {cand_name}")
        else:
            w["name_lbl"].configure(text=cand_name)

        # Tkinter requires updating pending events so widget width calculation is correct
        self.update_idletasks()
        track_w = w["track"].winfo_width()
        # Cap the bar width at track_w to prevent glitching outside bounds
        target_w = min(int((pct / 100) * track_w), track_w) if track_w > 10 else 0
        
        # Start the animation process to grow/shrink the bar smoothly
        self._animate_bar(cand_name, target_w)

    def _animate_bar(self, cand_name, target_w):
        """Smoothly interpolates the width of the bar over a few milliseconds."""
        if cand_name not in self._bar_widgets: return
        w = self._bar_widgets[cand_name]
        curr = w["current_width"]
        
        if abs(curr - target_w) <= 1:
            w["bar"].configure(width=target_w)
            w["current_width"] = target_w
            return

        # Move 15% of the distance each step (ease-out effect)
        new_w = curr + (target_w - curr) * 0.15
        try:
            w["bar"].configure(width=int(new_w))
            w["current_width"] = new_w
            self.after(20, self._animate_bar, cand_name, target_w)
        except Exception:
            pass # Widget might have been destroyed if user changed screen rapidly


    def _on_close_election(self):
        """Sends the close_election command to the server via TCP."""
        try:
            resp = close_election()
            st = resp.get("status")
            if st == "runoff":
                self._msg_var.set("Tie detected! Auto-starting runoff.")
            elif st == "closed":
                self._msg_var.set("Election closed successfully.")
                self._stop_server()
                self._stat_status.set("Closed")
            else:
                self._msg_var.set(resp.get("message", "Error closing."))
        except Exception as e:
            self._msg_var.set(f"Close failed: {e}")

    def _on_reset_tally(self):
        """Deletes only the results file. Server must be stopped first."""
        if self._is_server_running:
            self._msg_var.set("Stop the server first to reset tally.")
            return
        # This deletes data/results.json
        reset_votes()
        self._msg_var.set("Tally reset. Voters can vote again.")
        self._clear_charts()
        self._stat_turnout.set("0 / 0")
        self._stat_round.set("Round 1")
        self._stat_status.set("Inactive")

    def _on_factory_reset(self):
        """Danger Zone! Deletes the entire data directory."""
        if self._is_server_running:
            self._msg_var.set("Stop the server first to factory reset.")
            return
        if os.path.exists(DATA_DIR):
            shutil.rmtree(DATA_DIR)  # Destroys the whole folder
        self._msg_var.set("Factory reset complete. Please run Election Setup.")
        self._clear_charts()
        self._stat_turnout.set("N/A")
        self._stat_round.set("N/A")

    def _clear_charts(self):
        for w in self._bar_widgets.values():
            w["frame"].destroy()
        self._bar_widgets.clear()


if __name__ == "__main__":
    app = AdminApp()
    app.mainloop()
