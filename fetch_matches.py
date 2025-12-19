import http.client
import json
import csv
from datetime import datetime

conn = http.client.HTTPSConnection("v3.football.api-sports.io")
headers = {'x-apisports-key': "fe2cf4696f3c278253a3bb3be01d5ec2"}

leagues = {
    "Belgian Cup": 147,
    "Belgian Super Cup": 519,
    "Bundesliga": 78,
    "Community Shield": 528,
    "Copa del Rey": 143,
    "Coppa Italia": 137,
    "DFB Pokal": 81,
    "DFL Super Cup": 529,
    "Eredivisie": 88,
    "FA Cup": 45,
    "KNVB Cup": 90,
    "La Liga": 140,
    "League Cup": 48,
    "Primeira Liga": 94,
    "Ligue 1": 61,
    "Portuguese League Cup": 97,
    "Portuguese Super Cup": 550,
    "Premier League": 39,
    "Pro League": 144,
    "Super Lig": 203,
    "Supercopa de Espana": 556,
    "Supercoppa Italiana": 547,
    "Taca de Portugal": 96,
    "Trophee des Champions": 526,
    "Turkish Cup": 206,
    "Turkish Super Cup": 551,
    "UEFA Champions League": 2,
    "UEFA Europa Conference League": 848,
    "UEFA Europa League": 3,
    "UEFA Super Cup": 531,
}

all_matches = []

print("Maçlar çekiliyor...")
for league_name, league_id in leagues.items():
    print(f"  {league_name}...", end=" ", flush=True)
    
    conn.request("GET", f"/fixtures?league={league_id}&season=2025&status=FT", headers=headers)
    res = conn.getresponse()
    data = json.loads(res.read().decode("utf-8"))
    
    matches = data.get('response', [])
    print(f"{len(matches)} maç")
    
    for m in matches:
        fixture = m['fixture']
        league = m['league']
        teams = m['teams']
        goals = m['goals']
        score = m['score']
        
        all_matches.append({
            'fixture_id': fixture['id'],
            'date': fixture['date'][:10],
            'time': fixture['date'][11:16],
            'league_id': league['id'],
            'league_name': league['name'],
            'country': league['country'],
            'round': league.get('round', ''),
            'home_team_id': teams['home']['id'],
            'home_team': teams['home']['name'],
            'away_team_id': teams['away']['id'],
            'away_team': teams['away']['name'],
            'home_goals': goals['home'],
            'away_goals': goals['away'],
            'ht_home': score['halftime']['home'],
            'ht_away': score['halftime']['away'],
            'ft_home': score['fulltime']['home'],
            'ft_away': score['fulltime']['away'],
        })

# CSV'ye yaz
csv_file = 'matches_2025.csv'
with open(csv_file, 'w', newline='', encoding='utf-8') as f:
    if all_matches:
        writer = csv.DictWriter(f, fieldnames=all_matches[0].keys())
        writer.writeheader()
        writer.writerows(all_matches)

print(f"\n✓ Toplam {len(all_matches)} maç '{csv_file}' dosyasına kaydedildi.")
