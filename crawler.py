import urllib.request
import re
import json
import time
import random
import os
import base64
import xml.etree.ElementTree as ET
from datetime import datetime

# =============================================================================
# CONFIGURATION & GLOBAL CONSTANTS
# =============================================================================
REPO = "ELI808120/YUTUB"
HISTORY_FILE = "final_history_final.json"
PENDING_FILE = "pending_check.json"
BLOCK_LOG = "block_patterns.json"
MAX_CANDIDATES = 600
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# =============================================================================
# CORE AI ENGINE - ADAPTIVE LEARNING CLASS
# =============================================================================
class BrainEngine:
    """
    מנוע הלמידה המרכזי. 
    מנתח הסתברויות על בסיס הצלחות (History) וכישלונות (Block Log).
    """
    def __init__(self, history, blocked_words):
        self.pos_model = self._build_model(history)
        self.neg_model = blocked_words
        self.safe_anchors = ['repair', 'diy', 'how', 'setup', 'tutorial', 'unboxing', 'review', 'lesson', 'fix', 'tech']
        self.hard_blocks = ['music', 'song', 'official', 'lyrics', 'dance', 'vlog', 'prank', 'movie', 'trailer']

    def _build_model(self, data):
        model = {}
        for item in data[:400]: # למידה מ-400 הצלחות אחרונות
            words = self.tokenize(item.get('title', ''))
            for w in words:
                model[w] = model.get(w, 0) + 1
        return model

    def tokenize(self, text):
        return re.findall(r'\b\w{3,}\b', text.lower())

    def get_score(self, title):
        title_low = title.lower()
        
        # 1. בדיקת חסימות קשיחות (סינון מיידי)
        if any(block in title_low for block in self.hard_blocks):
            return -1000

        words = self.tokenize(title_low)
        if not words: return 0

        # 2. חישוב ציון חיובי (מבוסס היסטוריה + עוגנים)
        pos_score = sum(self.pos_model.get(w, 0) for w in words)
        anchor_bonus = sum(20 for w in words if w in self.safe_anchors)
        
        # 3. חישוב ציון שלילי (מבוסס Block Log שהמחשב המקומי שלח)
        neg_score = sum(self.neg_model.get(w, 0) for w in words)

        # 4. נוסחת ההסתברות (הסקה בייסיאנית לייט)
        # ציון סופי = (חיובי + בונוס עוגן + קרדיט התחלתי) חלקי (שלילי + 1)
        final_score = (pos_score + anchor_bonus + 10) / (neg_score + 1)
        
        return round(final_score, 2)

# =============================================================================
# YOUTUBE DATA AGGREGATOR
# =============================================================================
class YouTubeCrawlHandler:
    """
    אחראי על איסוף נתונים אגרסיבי מיוטיוב: המלצות, RSS וחיפוש.
    """
    @staticmethod
    def get_html(url):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req, timeout=15) as res:
                return res.read().decode('utf-8', errors='ignore')
        except: return ""

    def get_recommendations(self, video_id):
        html = self.get_html(f"https://www.youtube.com/watch?v={video_id}")
        # Regex מורכב לחילוץ כותרת + ID + מזהה ערוץ
        video_data = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})".*?"title":\{"runs":\[\{"text":"(.*?)"\}\].*?"channelId":"(UC[a-zA-Z0-9_-]{22})"', html)
        return [{"id": v[0], "title": v[1], "channelId": v[2]} for v in video_data]

    def get_channel_latest(self, channel_id):
        """סריקת RSS של ערוץ - הדרך המהירה ביותר לקבל סרטונים חדשים"""
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        html = self.get_html(url)
        try:
            video_ids = re.findall(r'<yt:videoId>(.*?)</yt:videoId>', html)
            titles = re.findall(r'<title>(.*?)</title>', html)[1:] # דילוג על שם הערוץ
            return [{"id": v, "title": t} for v, t in zip(video_ids, titles)]
        except: return []

# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================
def run_system():
    print(f"--- Starting Advanced AI Scraper v3.0 [{datetime.now().strftime('%H:%M:%S')}] ---")
    
    # 1. Load Learning Data
    def load_json(path):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)
        return [] if "history" in path else {}

    history = load_json(HISTORY_FILE)
    blocked_words = load_json(BLOCK_LOG)
    
    if not history:
        print("❌ Error: No history found. AI cannot learn.")
        return

    # 2. Initialize Engines
    brain = BrainEngine(history, blocked_words)
    crawler = YouTubeCrawlHandler()
    seen_ids = {v['id'] for v in history}
    new_candidates = []
    processed_channels = set()

    # 3. Strategic Seed Selection
    # משלב הצלחות אחרונות עם סרטונים אקראיים מהעבר כדי למנוע "בועה"
    seeds = history[:15]
    if len(history) > 30:
        seeds += random.sample(history[15:], 10)

    # 4. The Crawl Loop
    for seed in seeds:
        print(f"📡 Exploring around: {seed.get('title', 'Unknown')[:30]}...")
        recs = crawler.get_recommendations(seed['id'])
        
        for r in recs:
            if r['id'] in seen_ids: continue
            
            score = brain.get_score(r['title'])
            
            # אם מצאנו סרטון עם ציון גבוה במיוחד, נסרוק את כל הערוץ שלו!
            if score > 15 and r['channelId'] not in processed_channels:
                print(f"  🔥 High-Quality Channel Detected! Scanning channel: {r['channelId']}")
                channel_vids = crawler.get_channel_latest(r['channelId'])
                for cv in channel_vids:
                    if cv['id'] not in seen_ids:
                        cv['score'] = brain.get_score(cv['title'])
                        new_candidates.append(cv)
                        seen_ids.add(cv['id'])
                processed_channels.add(r['channelId'])

            # הוספת המלצה רגילה אם הציון עובר סף
            if score > 0.8: # סף גמיש ללמידה
                r['score'] = score
                new_candidates.append(r)
                seen_ids.add(r['id'])
        
        if len(new_candidates) >= MAX_CANDIDATES: break
        time.sleep(0.1)

    # 5. Result Optimization
    # מיון לפי הציון של ה-AI - הטובים ביותר יהיו בראש הרשימה
    new_candidates.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # שמירה ל-JSON
    output = [{"id": v['id'], "title": v['title']} for v in new_candidates]
    with open(PENDING_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"✅ Mission Accomplished: {len(output)} high-probability videos found.")
    print(f"📊 Brain Stats: {len(brain.pos_model)} positive terms, {len(blocked_words)} negative terms.")

if __name__ == "__main__":
    run_system()
