# 🎮 Wordle Bot System

Production-ready Telegram bot for automated Wordle gameplay with anti-ban protection.

## ✅ Core Features Implemented
- ✅ Multi-user isolated sessions
- ✅ Manual play/stop control (`/play`, `/stop`)
- ✅ Safe disconnect with session persistence
- ✅ Force join channel verification
- ✅ Anti-ban pacing (human-like delays)
- ✅ Modular architecture ready for VPS/Render deployment

## ⚠️ Critical Notice
This bot works with **Wordle clones or self-hosted games only**. Official NYT Wordle has aggressive anti-bot measures that will ban accounts.

## 🚀 Deployment

### Environment Setup
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt


###Start Me Powered By Nexacoders
python3 bot.py