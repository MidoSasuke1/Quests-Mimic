import sys
import time
import tkinter as tk

# Read arguments: sys.argv[1] = Game Name, sys.argv[2] = Duration in Minutes
game_title = sys.argv[1] if len(sys.argv) > 1 else "Active Quest Process"
try:
    duration_mins = int(sys.argv[2]) if len(sys.argv) > 2 else 15
except ValueError:
    duration_mins = 15

total_seconds = duration_mins * 60
start_time = time.time()

root = tk.Tk()
root.title(game_title)
root.geometry("380x180")
root.resizable(False, False)
root.configure(bg="#1e1f22")

# Game Title
lbl_title = tk.Label(
    root,
    text=game_title,
    font=("Segoe UI", 13, "bold"),
    fg="#5865F2",
    bg="#1e1f22"
)
lbl_title.pack(pady=(15, 2))

# Subtitle / Hint
lbl_hint = tk.Label(
    root,
    text="Discord Quest Simulator (Stream or keep open)",
    font=("Segoe UI", 9),
    fg="#949ba4",
    bg="#1e1f22"
)
lbl_hint.pack(pady=(0, 10))

# Live Countdown in the game window
lbl_timer = tk.Label(
    root,
    text=f"00:00 / {duration_mins:02d}:00",
    font=("Segoe UI", 18, "bold"),
    fg="#23a55a",
    bg="#1e1f22"
)
lbl_timer.pack(pady=5)

def update_timer():
    elapsed = int(time.time() - start_time)
    mins = elapsed // 60
    secs = elapsed % 60
    tot_m = total_seconds // 60
    tot_s = total_seconds % 60

    if elapsed >= total_seconds:
        lbl_timer.config(text=f"{tot_m:02d}:00 - Completed!", fg="#5865F2")
    else:
        lbl_timer.config(text=f"{mins:02d}:{secs:02d} / {tot_m:02d}:{tot_s:02d}")
        root.after(1000, update_timer)

update_timer()
root.mainloop()
