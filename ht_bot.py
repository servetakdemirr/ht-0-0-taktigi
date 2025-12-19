#!/usr/bin/env python3
"""
HT 0-0 Taktigi Telegram Bot
- Günlük fikstürü çeker ve maç saatlerine göre çalışır
- HT 0-0 biten ve kriterlere uyan maçlar için bildirim gönderir
- Biten maçları CSV'ye kaydeder
"""

import http.client
import json
import csv
import time
import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict

# Istanbul timezone (UTC+3)
TZ_OFFSET = timezone(timedelta(hours=3))

def now_istanbul():
    """Istanbul saatini döndür"""
    return datetime.now(TZ_OFFSET)

# ==================== AYARLAR ====================
API_KEY = os.environ.get("API_FOOTBALL_KEY", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
CSV_FILE = "matches_2025.csv"
CHECK_INTERVAL = 300  # 5 dakika (saniye)
TIMEZONE = "Europe/Istanbul"

# İzlenecek ligler
LEAGUES = {
    147: "Belgian Cup",
    519: "Belgian Super Cup",
    78: "Bundesliga",
    528: "Community Shield",
    143: "Copa del Rey",
    137: "Coppa Italia",
    81: "DFB Pokal",
    529: "DFL Super Cup",
    88: "Eredivisie",
    45: "FA Cup",
    90: "KNVB Cup",
    140: "La Liga",
    48: "League Cup",
    94: "Primeira Liga",
    61: "Ligue 1",
    97: "Portuguese League Cup",
    550: "Portuguese Super Cup",
    39: "Premier League",
    144: "Pro League",
    203: "Süper Lig",
    556: "Supercopa de España",
    547: "Supercoppa Italiana",
    96: "Taça de Portugal",
    526: "Trophée des Champions",
    206: "Turkish Cup",
    551: "Turkish Super Cup",
    2: "UEFA Champions League",
    848: "UEFA Europa Conference League",
    3: "UEFA Europa League",
    531: "UEFA Super Cup",
}

# Bildirim gönderilmiş maçları takip et (aynı maç için tekrar bildirim gönderme)
notified_fixtures = set()

# ==================== API FONKSİYONLARI ====================

def api_request(endpoint):
    """API-Football'a istek gönder"""
    conn = http.client.HTTPSConnection("v3.football.api-sports.io")
    headers = {'x-apisports-key': API_KEY}
    conn.request("GET", endpoint, headers=headers)
    res = conn.getresponse()
    data = json.loads(res.read().decode("utf-8"))
    conn.close()
    return data

def send_telegram(message):
    """Telegram bildirimi gönder"""
    try:
        conn = http.client.HTTPSConnection("api.telegram.org")
        params = json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        })
        headers = {'Content-Type': 'application/json'}
        conn.request("POST", f"/bot{TELEGRAM_TOKEN}/sendMessage", params, headers)
        res = conn.getresponse()
        conn.close()
        return res.status == 200
    except Exception as e:
        print(f"Telegram hatası: {e}")
        return False

# ==================== VERİ FONKSİYONLARI ====================

def load_historical_data():
    """CSV'den geçmiş maç verilerini yükle"""
    team_goals = defaultdict(list)
    team_goals_home = defaultdict(list)
    team_goals_away = defaultdict(list)
    existing_fixture_ids = set()
    
    if not os.path.exists(CSV_FILE):
        return team_goals, team_goals_home, team_goals_away, existing_fixture_ids
    
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Tarihe göre sırala
    rows.sort(key=lambda x: (x['date'], x['time']))
    
    for row in rows:
        fixture_id = row['fixture_id']
        existing_fixture_ids.add(fixture_id)
        
        home_team = row['home_team_id']
        away_team = row['away_team_id']
        home_goals = int(row['home_goals'])
        away_goals = int(row['away_goals'])
        
        team_goals[home_team].append(home_goals)
        team_goals[away_team].append(away_goals)
        team_goals_home[home_team].append(home_goals)
        team_goals_away[away_team].append(away_goals)
    
    return team_goals, team_goals_home, team_goals_away, existing_fixture_ids

def calculate_features(home_team_id, away_team_id, team_goals, team_goals_home, team_goals_away):
    """Bir maç için özellikleri hesapla"""
    home_team = str(home_team_id)
    away_team = str(away_team_id)
    
    # avg_goal_home_team_home
    home_home_goals = team_goals_home.get(home_team, [])
    avg_goal_home_team_home = sum(home_home_goals) / len(home_home_goals) if home_home_goals else None
    
    # avg_goal_away_team_away
    away_away_goals = team_goals_away.get(away_team, [])
    avg_goal_away_team_away = sum(away_away_goals) / len(away_away_goals) if away_away_goals else None
    
    # avg_goal_combined_home_away
    if avg_goal_home_team_home is not None and avg_goal_away_team_away is not None:
        avg_goal_combined_home_away = avg_goal_home_team_home + avg_goal_away_team_away
    else:
        avg_goal_combined_home_away = None
    
    # home_team_no_goal_last5
    home_last5 = team_goals.get(home_team, [])[-5:]
    home_team_no_goal_last5 = 1 if len(home_last5) >= 5 and all(g == 0 for g in home_last5) else 0 if len(home_last5) >= 5 else None
    
    # away_team_no_goal_last5
    away_last5 = team_goals.get(away_team, [])[-5:]
    away_team_no_goal_last5 = 1 if len(away_last5) >= 5 and all(g == 0 for g in away_last5) else 0 if len(away_last5) >= 5 else None
    
    return {
        'avg_goal_home_team_home': avg_goal_home_team_home,
        'avg_goal_away_team_away': avg_goal_away_team_away,
        'avg_goal_combined_home_away': avg_goal_combined_home_away,
        'home_team_no_goal_last5': home_team_no_goal_last5,
        'away_team_no_goal_last5': away_team_no_goal_last5
    }

def save_finished_match(match, team_goals, team_goals_home, team_goals_away, existing_fixture_ids):
    """Biten maçı CSV'ye kaydet"""
    fixture = match['fixture']
    league = match['league']
    teams = match['teams']
    goals = match['goals']
    score = match['score']
    
    fixture_id = str(fixture['id'])
    
    # Zaten var mı kontrol et
    if fixture_id in existing_fixture_ids:
        return False
    
    # HT verisi boş mu kontrol et
    ht_home = score['halftime']['home']
    ht_away = score['halftime']['away']
    if ht_home is None or ht_away is None:
        return False
    
    home_team_id = str(teams['home']['id'])
    away_team_id = str(teams['away']['id'])
    home_goals_val = goals['home']
    away_goals_val = goals['away']
    
    # Özellikleri hesapla
    features = calculate_features(home_team_id, away_team_id, team_goals, team_goals_home, team_goals_away)
    
    # Yeni satır oluştur
    new_row = {
        'fixture_id': fixture_id,
        'date': fixture['date'][:10],
        'time': fixture['date'][11:16],
        'league_id': league['id'],
        'league_name': league['name'],
        'country': league['country'],
        'round': league.get('round', ''),
        'home_team_id': home_team_id,
        'home_team': teams['home']['name'],
        'away_team_id': away_team_id,
        'away_team': teams['away']['name'],
        'home_goals': home_goals_val,
        'away_goals': away_goals_val,
        'ht_home': ht_home,
        'ht_away': ht_away,
        'ft_home': score['fulltime']['home'],
        'ft_away': score['fulltime']['away'],
        'avg_goal_home_team': '',
        'avg_goal_away_team': '',
        'avg_goal_combined': '',
        'avg_goal_home_team_home': round(features['avg_goal_home_team_home'], 2) if features['avg_goal_home_team_home'] else '',
        'avg_goal_away_team_away': round(features['avg_goal_away_team_away'], 2) if features['avg_goal_away_team_away'] else '',
        'avg_goal_combined_home_away': round(features['avg_goal_combined_home_away'], 2) if features['avg_goal_combined_home_away'] else '',
        'home_team_no_goal_last5': features['home_team_no_goal_last5'] if features['home_team_no_goal_last5'] is not None else '',
        'away_team_no_goal_last5': features['away_team_no_goal_last5'] if features['away_team_no_goal_last5'] is not None else ''
    }
    
    # CSV'ye ekle
    fieldnames = list(new_row.keys())
    file_exists = os.path.exists(CSV_FILE)
    
    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(new_row)
    
    # Geçmiş verileri güncelle
    existing_fixture_ids.add(fixture_id)
    team_goals[home_team_id].append(home_goals_val)
    team_goals[away_team_id].append(away_goals_val)
    team_goals_home[home_team_id].append(home_goals_val)
    team_goals_away[away_team_id].append(away_goals_val)
    
    print(f"  ✓ Kaydedildi: {teams['home']['name']} {home_goals_val}-{away_goals_val} {teams['away']['name']}")
    return True

# ==================== ANA FONKSİYONLAR ====================

def check_live_matches():
    """Canlı maçları kontrol et"""
    global notified_fixtures
    
    print(f"\n[{now_istanbul().strftime('%H:%M:%S')}] Canlı maçlar kontrol ediliyor...")
    
    # Geçmiş verileri yükle
    team_goals, team_goals_home, team_goals_away, existing_fixture_ids = load_historical_data()
    
    # Canlı maçları çek
    league_ids = "-".join(str(lid) for lid in LEAGUES.keys())
    data = api_request(f"/fixtures?live={league_ids}")
    
    live_matches = data.get('response', [])
    print(f"  {len(live_matches)} canlı maç bulundu")
    
    for match in live_matches:
        fixture = match['fixture']
        fixture_id = fixture['id']
        status = fixture['status']['short']
        elapsed = fixture['status']['elapsed'] or 0
        
        league = match['league']
        teams = match['teams']
        goals = match['goals']
        score = match['score']
        
        home_team = teams['home']['name']
        away_team = teams['away']['name']
        
        # Biten maçları kaydet
        if status == 'FT':
            save_finished_match(match, team_goals, team_goals_home, team_goals_away, existing_fixture_ids)
            continue
        
        # Devre arası veya 2. yarıda mı kontrol et
        if status not in ['HT', '2H', 'ET', 'BT', 'P']:
            continue
        
        # HT 0-0 mi kontrol et
        ht_home = score['halftime']['home']
        ht_away = score['halftime']['away']
        
        if ht_home != 0 or ht_away != 0:
            continue
        
        # Daha önce bildirim gönderilmiş mi
        if fixture_id in notified_fixtures:
            continue
        
        # Özellikleri hesapla
        home_team_id = teams['home']['id']
        away_team_id = teams['away']['id']
        features = calculate_features(home_team_id, away_team_id, team_goals, team_goals_home, team_goals_away)
        
        avg_combined = features['avg_goal_combined_home_away']
        home_no_goal = features['home_team_no_goal_last5']
        away_no_goal = features['away_team_no_goal_last5']
        
        # Kriterleri kontrol et
        current_score = f"{goals['home']}-{goals['away']}"
        
        # Veri yoksa uyarı ile bildirim gönder
        if avg_combined is None:
            message = f"""⚠️ <b>HT 0-0 - Veri Yetersiz</b>

⚽ <b>{home_team}</b> vs <b>{away_team}</b>
🏆 {league['name']} ({league['country']})
📊 Skor: {current_score} (HT: 0-0)
⏱️ Dakika: {elapsed}'

⚠️ Yeterli geçmiş veri yok!"""
            if send_telegram(message):
                print(f"  ⚠ BİLDİRİM (veri yok): {home_team} vs {away_team}")
                notified_fixtures.add(fixture_id)
            continue
        
        if avg_combined <= 2.5:
            print(f"  ✗ {home_team} vs {away_team}: avg_combined={avg_combined:.2f} (<=2.5)")
            continue
        
        if home_no_goal == 1 or away_no_goal == 1:
            print(f"  ✗ {home_team} vs {away_team}: Son 5 maçta gol yok")
            continue
        
        # Son 5 maç verisi yoksa uyarı ile bildirim
        if home_no_goal is None or away_no_goal is None:
            message = f"""⚠️ <b>HT 0-0 - Kısmi Veri</b>

⚽ <b>{home_team}</b> vs <b>{away_team}</b>
🏆 {league['name']} ({league['country']})
📊 Skor: {current_score} (HT: 0-0)
⏱️ Dakika: {elapsed}'

📈 <b>İstatistikler:</b>
• Avg Goal Combined: <b>{avg_combined:.2f}</b>
⚠️ Son 5 maç verisi eksik!"""
            if send_telegram(message):
                print(f"  ⚠ BİLDİRİM (kısmi veri): {home_team} vs {away_team}")
                notified_fixtures.add(fixture_id)
            continue
        
        # TÜM KRİTERLER SAĞLANDI - Bildirim gönder!
        message = f"""🔔 <b>HT 0-0 Fırsat!</b>

⚽ <b>{home_team}</b> vs <b>{away_team}</b>
🏆 {league['name']} ({league['country']})
📊 Skor: {current_score} (HT: 0-0)
⏱️ Dakika: {elapsed}'

📈 <b>İstatistikler:</b>
• Avg Goal Combined: <b>{avg_combined:.2f}</b>
• Home Avg (Home): {features['avg_goal_home_team_home']:.2f}
• Away Avg (Away): {features['avg_goal_away_team_away']:.2f}"""
        
        if send_telegram(message):
            print(f"  ✓ BİLDİRİM: {home_team} vs {away_team}")
            notified_fixtures.add(fixture_id)
        else:
            print(f"  ✗ Bildirim gönderilemedi: {home_team} vs {away_team}")

def get_todays_fixtures():
    """Bugünkü maçları çek ve çalışma saatlerini belirle"""
    today = now_istanbul().strftime("%Y-%m-%d")
    
    all_fixtures = []
    
    # Her lig için sonraki 10 maçı çek ve bugüne ait olanları filtrele
    for league_id in LEAGUES.keys():
        data = api_request(f"/fixtures?league={league_id}&season=2025&next=10&timezone={TIMEZONE}")
        fixtures = data.get('response', [])
        for f in fixtures:
            # Sadece bugünkü maçları al
            if f['fixture']['date'][:10] == today:
                all_fixtures.append(f)
    
    if not all_fixtures:
        return None, None, []
    
    # Maç saatlerini topla
    match_times = []
    for f in all_fixtures:
        match_time = f['fixture']['date'][11:16]  # HH:MM
        match_times.append(match_time)
    
    if not match_times:
        return None, None, []
    
    # İlk ve son maç saatini bul
    match_times.sort()
    first_match = match_times[0]
    last_match = match_times[-1]
    
    # İlk maçtan 45 dk önce başla
    first_hour, first_min = map(int, first_match.split(':'))
    start_time = now_istanbul().replace(hour=first_hour, minute=first_min, second=0, microsecond=0)
    start_time = start_time - timedelta(minutes=45)
    
    # Son maçtan 2 saat sonra bitir
    last_hour, last_min = map(int, last_match.split(':'))
    end_time = now_istanbul().replace(hour=last_hour, minute=last_min, second=0, microsecond=0)
    end_time = end_time + timedelta(hours=2)
    
    return start_time, end_time, all_fixtures

def is_within_schedule(start_time, end_time):
    """Şu an çalışma saatleri içinde mi?"""
    if start_time is None or end_time is None:
        return False
    now = now_istanbul()
    return start_time <= now <= end_time

def main():
    """Ana döngü"""
    print("=" * 50)
    print("HT 0-0 TAKTİĞİ TELEGRAM BOTU (Akıllı Zamanlama)")
    print("=" * 50)
    print(f"Kontrol aralığı: {CHECK_INTERVAL // 60} dakika")
    print(f"İzlenen lig sayısı: {len(LEAGUES)}")
    print("=" * 50)
    
    last_fixture_check = None
    start_time = None
    end_time = None
    fixtures = []
    
    while True:
        now = now_istanbul()
        today = now.strftime("%Y-%m-%d")
        
        # Günde 1 kez fikstür çek
        if last_fixture_check != today:
            print(f"\n[{now.strftime('%H:%M:%S')}] Günlük fikstür çekiliyor...")
            start_time, end_time, fixtures = get_todays_fixtures()
            last_fixture_check = today
            
            if fixtures:
                print(f"  ✓ {len(fixtures)} maç bulundu")
                print(f"  ⏰ Çalışma: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}")
                send_telegram(f"📅 <b>Günlük Fikstür</b>\n\n"
                            f"📊 {len(fixtures)} maç\n"
                            f"⏰ {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}")
            else:
                print("  ✗ Bugün maç yok, bot uyuyor...")
                send_telegram("😴 Bugün izlenen liglerde maç yok.")
                # Gece yarısına kadar uyu
                sleep_until = now.replace(hour=23, minute=59, second=59)
                sleep_seconds = (sleep_until - now).total_seconds()
                if sleep_seconds > 0:
                    time.sleep(sleep_seconds)
                continue
        
        # Çalışma saatleri içinde mi?
        if is_within_schedule(start_time, end_time):
            try:
                check_live_matches()
            except Exception as e:
                print(f"Hata: {e}")
            
            print(f"  Sonraki kontrol: {CHECK_INTERVAL // 60} dakika sonra")
            time.sleep(CHECK_INTERVAL)
        else:
            # Çalışma saatleri dışında
            if now < start_time:
                wait_seconds = (start_time - now).total_seconds()
                print(f"\n[{now.strftime('%H:%M:%S')}] Maçlar başlamadı. {start_time.strftime('%H:%M')}'de başlayacak...")
                time.sleep(min(wait_seconds, 300))  # Max 5 dk bekle
            else:
                print(f"\n[{now.strftime('%H:%M:%S')}] Günlük maçlar bitti. Yarın tekrar...")
                # Gece yarısına kadar uyu
                sleep_until = now.replace(hour=23, minute=59, second=59)
                sleep_seconds = (sleep_until - now).total_seconds()
                if sleep_seconds > 0:
                    time.sleep(min(sleep_seconds, 3600))  # Max 1 saat bekle

if __name__ == "__main__":
    main()
