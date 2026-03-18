import requests
import json
import time

def fetch_all_mlb_players():
    """
    Fetch all Live MLB players from The Show 26 API
    """
    base_url = "https://mlb26.theshow.com/apis/items.json"
    all_players = []
    page = 1

    print("🔄 Starting MLB player data fetch...")

    while True:
        print(f"📄 Fetching page {page}...")

        # Make request with required parameters
        params = {
            'type': 'mlb_card',
            'series': 'Live',
            'page': page
        }

        try:
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()  # Raise exception for bad status codes

            data = response.json()

            # Add players from this page
            if 'items' in data and data['items']:
                all_players.extend(data['items'])
                print(f"✅ Page {page}: Found {len(data['items'])} players")

                # Check if we've reached the last page
                if page >= data.get('total_pages', 1):
                    print(f"🏁 Reached final page ({data.get('total_pages', 1)} total pages)")
                    break

                page += 1

                # Be nice to the API - small delay between requests
                time.sleep(0.5)

            else:
                print("⚠️ No items found in response, stopping")
                break

        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching page {page}: {e}")
            # Try a few more times before giving up
            if page == 1:
                print("❌ Failed to fetch first page, aborting")
                return []
            else:
                print("⚠️ Stopping at error, returning data collected so far")
                break
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON on page {page}: {e}")
            break

    print(f"✅ Total players fetched: {len(all_players)}")
    return all_players

def clean_player_data(players):
    """
    Clean and filter player data to only include specific fields
    """
    print("🧹 Cleaning and filtering player data...")

    seen_uuids = set()
    clean_players = []

    # Fields we want to keep
    desired_fields = ['uuid', 'name', 'team', 'rarity', 'ovr','series']

    for player in players:
        # Skip if we've seen this UUID before
        if player.get('uuid') in seen_uuids:
            continue

        # Skip if missing required fields
        if not all(key in player for key in ['uuid', 'name', 'team']):
            continue

        # Create clean player object with only desired fields
        clean_player = {}
        for field in desired_fields:
            clean_player[field] = player.get(field, None)

        # Skip if any required field is missing
        if not all(clean_player[field] is not None for field in ['uuid', 'name', 'team']):
            continue

        seen_uuids.add(player['uuid'])
        clean_players.append(clean_player)

    print(f"✅ Cleaned data: {len(clean_players)} unique players")
    return clean_players

def save_players_json(players, filename='players_mlb26.json'):
    """
    Save players to JSON file
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(players, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved {len(players)} players to {filename}")

        # Show some sample data
        if players:
            print("📋 Sample players:")
            for i, player in enumerate(players[:5]):
                ovr_text = f" (OVR: {player.get('ovr', 'N/A')})" if player.get('ovr') else ""
                rarity_text = f" [{player.get('rarity', 'N/A')}]" if player.get('rarity') else ""
                print(f"  {i+1}. {player['name']} - {player['team']}{rarity_text}{ovr_text} (UUID: {player['uuid'][:8]}...)")

    except Exception as e:
        print(f"❌ Error saving to {filename}: {e}")

def main():
    """
    Main function to fetch and save MLB player data
    """
    print("🚀 MLB The Show 26 Player Data Fetcher")
    print("=" * 50)

    # Fetch all players
    players = fetch_all_mlb_players()

    if not players:
        print("❌ No players fetched, exiting")
        return

    # Clean the data
    clean_players = clean_player_data(players)

    if not clean_players:
        print("❌ No clean players after processing, exiting")
        return

    # Save to JSON
    save_players_json(clean_players)

    print("🎉 Data fetch complete!")

if __name__ == "__main__":
    main()
