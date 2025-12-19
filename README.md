# HT 0-0 Taktigi Bot

Telegram botu - Canlı futbol maçlarında HT 0-0 fırsatlarını tespit eder.

## Özellikler

- 30 lig/kupa takibi
- 5 dakikada bir kontrol
- Akıllı zamanlama (sadece maç saatlerinde çalışır)
- İstatistik bazlı filtreleme

## Kurulum

### Lokal

```bash
export API_FOOTBALL_KEY="your_key"
export TELEGRAM_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"
python3 ht_bot.py
```

### Railway

1. GitHub'a push et
2. Railway'de "New Project" → "Deploy from GitHub"
3. Variables ekle:
   - `API_FOOTBALL_KEY`
   - `TELEGRAM_TOKEN`
   - `TELEGRAM_CHAT_ID`

## Dosyalar

- `ht_bot.py` - Ana bot
- `matches_2025.csv` - Maç verileri
- `ligler.md` - İzlenen ligler
