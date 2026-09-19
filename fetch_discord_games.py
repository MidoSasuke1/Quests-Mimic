import os
import json
import urllib.request

API_URL = "https://discord.com/api/v10/applications/detectable"
OUTPUT_DIR = "games"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "games.json")

def fetch_and_build_database():
    print("Connecting to Discord's Master Game Registry...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    req = urllib.request.Request(API_URL, headers=headers)

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"Failed to fetch data from Discord: {e}")
        return

    print(f"Downloaded {len(data)} raw application entries from Discord.")

    verified_games = []
    seen_names = set()

    for app in data:
        game_name = app.get("name", "").strip()
        if not game_name or game_name.lower() in seen_names:
            continue

        executables = app.get("executables", [])
        if not executables:
            continue

        # Look for Windows (win32) executable
        target_exe = None
        for ex in executables:
            if ex.get("os") == "win32":
                target_exe = ex.get("name")
                # Prefer non-launcher executables if available
                if not ex.get("is_launcher", False):
                    break

        if not target_exe:
            continue

        # Standardize path separators
        clean_path = target_exe.replace("/", "\\")

        # Split folder and exe
        if "\\" in clean_path:
            subfolder, exe_name = clean_path.rsplit("\\", 1)
        else:
            subfolder = ""
            exe_name = clean_path

        themes = app.get("themes", [])
        category = themes[0] if themes else "Game"

        verified_games.append({
            "name": game_name,
            "exe": exe_name,
            "subfolder": subfolder,
            "category": category
        })
        seen_names.add(game_name.lower())

    # Sort alphabetically
    verified_games.sort(key=lambda x: x["name"].lower())

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Save to a single high-performance master file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(verified_games, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Successfully saved {len(verified_games)} verified games into '{OUTPUT_FILE}'.")

if __name__ == "__main__":
    fetch_and_build_database()
