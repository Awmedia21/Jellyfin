import os
import requests
from datetime import datetime

JELLYFIN_URL = os.environ.get("JELLYFIN_URL").rstrip("/")
JELLYFIN_API_KEY = os.environ.get("JELLYFIN_API_KEY")
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

MESSAGE_ID_FILE = "message_id.txt"

headers = {
    "Authorization": f'MediaBrowser Token="{JELLYFIN_API_KEY}"',
    "Content-Type": "application/json"
}

# 1. Fetch Item Counts from Jellyfin API
counts_res = requests.get(f"{JELLYFIN_URL}/Items/Counts", headers=headers)
counts_res.raise_for_status()
counts = counts_res.json()

movie_count = counts.get("MovieCount", 0)
series_count = counts.get("SeriesCount", 0)
episode_count = counts.get("EpisodeCount", 0)

# 2. Fetch 4K Counts
items_res = requests.get(
    f"{JELLYFIN_URL}/Items",
    headers=headers,
    params={
        "Recursive": True,
        "MinWidth": 3800,
        "IncludeItemTypes": "Movie,Series"
    }
)
items_res.raise_for_status()
items_data = items_res.json().get("Items", [])

movies_4k = sum(1 for i in items_data if i.get("Type") == "Movie")
series_4k = sum(1 for i in items_data if i.get("Type") == "Series")

# 3. Build Formatted Discord Embed
current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

payload = {
    "embeds": [
        {
            "title": "📊 JELLYFIN LIBRARY STATS",
            "color": 11164867,
            "fields": [
                {"name": "🎬 Movies", "value": f"**{movie_count:,}**", "inline": True},
                {"name": "🎬 Movies 4K", "value": f"**{movies_4k:,}**", "inline": True},
                {"name": "\u200b", "value": "\u200b", "inline": True},
                {"name": "📺 TV Shows", "value": f"**{series_count:,}**", "inline": True},
                {"name": "📺 TV Shows 4K", "value": f"**{series_4k:,}**", "inline": True},
                {"name": "📁 Total Episodes", "value": f"**{episode_count:,}**", "inline": True}
            ],
            "footer": {
                "text": f"Media Hub • Auto-updated at {current_time}"
            }
        }
    ]
}

# 4. Smart Update: Edit existing message or post a new one
message_id = None
if os.path.exists(MESSAGE_ID_FILE):
    with open(MESSAGE_ID_FILE, "r") as f:
        message_id = f.read().strip()

success = False
if message_id:
    edit_url = f"{WEBHOOK_URL}/messages/{message_id}"
    res = requests.patch(edit_url, json=payload)
    if res.status_code == 200:
        success = True
        print("Successfully updated existing Discord library stats message.")

if not success:
    # Post fresh message and wait for response to capture its ID
    post_url = f"{WEBHOOK_URL}?wait=true"
    res = requests.post(post_url, json=payload)
    res.raise_for_status()
    new_msg = res.json()
    message_id = new_msg["id"]
    with open(MESSAGE_ID_FILE, "w") as f:
        f.write(str(message_id))
    print("Posted new Discord library stats message and saved ID.")
