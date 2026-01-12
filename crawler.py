import urllib.request
import re
import json
import time
import random
import os
import base64
from datetime import datetime

# =============================================================================
# CONFIGURATION & GLOBAL CONSTANTS
# =============================================================================
REPO = "ELI808120/YUTUB"
HISTORY_FILE = "final_history_final.json"
PENDING_FILE = "pending_check.json"
BLOCK_LOG = "block_patterns.json"
MAX_CANDIDATES = 1000 
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

SEARCH_KEYWORDS = [
    "National Geographic Documentary", "Space Exploration 4K", "Science Experiment",
    "Cooking Recipe Tutorial", "Nature Relaxation 8K", "Woodworking Projects",
    "History Channel Full Episodes", "Tech Review 2024", "DIY Home Repair",
    "How to Program Python", "Physics Explained", "Animal Planet Wildlife"
]

class BrainEngine:
    def __init__(self, history, blocked_words):
        self.pos_model = self._build_model(history)
        self.neg_model = blocked_words
        self.safe_anchors = ['science', 'nature', 'documentary', 'tutorial', 'how to', 'lesson', 'expert', 'study']
        self.hard_blocks = ['gaming', 'minecraft', 'roblox', 'funny moments', 'shorts', 'tiktok', 'music video']

    def _build_model(self, data):
        model = {}
        for item in data[-1000:]: 
            words = self.tokenize(item.get('title', ''))
            for w in words:
                model[w] = model.get(w, 0) + 1
        return model

    def tokenize(self, text):
        return re.findall(r'\b\w{3,}\b', text.lower())

    def get_score(self, title):
        title_low = title.lower()
        if any(block in title_low for block in self.hard_blocks): return -1000
        words = self.tokenize(title_low)
        if not words: return 0
        pos_score = sum(self.pos_model.get(w, 0) for w in words)
        anchor_bonus = sum(30 for w in words if w in self.safe_anchors)
        neg_score = sum(self.neg_model.get(w, 0) for w in words)
        return (pos_score + anchor_bonus + 15) / (neg_score + 1)

class YouTubeCrawlHandler:
    @staticmethod
    def get_html(url):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req, timeout=15) as res:
                return res.read().decode('utf-8', errors='ignore')
        except: return ""

    def search_youtube(self, query):
        query_enc = urllib.parse.quote(query)
        html = self.get_html(f"https://www.youtube.com/results?search_query={query_enc}")
        return re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})".*?"title":\{"runs":\[\{"text":"(.*?)"\}\].*?"channelId":"(UC[a-zA-Z0-9_-]{22})"', html)

    def get_recommendations(self, video_id):
        html = self.get_html(f"https://www.youtube.com/watch?v={video_id}")
        return re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})".*?"title":\{"runs":\[\{"text":"(.*?)"\}\].*?"channelId":"(UC[a-zA-Z0-9_-]{22})"', html)

    def get_channel_videos(self, channel_id):
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        xml_content = self.get_html(url)
        video_ids = re.findall(r'<yt:videoId>(.*?)</yt:videoId>', xml_content)
        titles = re.findall(r'<title>(.*?)</title>', xml_content)[1:]
        return [{"id": v, "title": t} for v, t in zip(video_ids, titles)]

def run_system():
    start_time = time.time()
    MAX_RUNTIME_SECONDS = 600  # הגבלה ל-10 דקות
    
    print(f"--- Launching MAMMOTH CRAWLER v5.1 [{datetime.now().strftime('%H:%M:%S')}] ---")
    
    def is_time_up():
        return (time.time() - start_time) > MAX_RUNTIME_SECONDS

    def load_json(path):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)
        return [] if "history" in path else {}

    history = load_json(HISTORY_FILE)
    blocked_words = load_json(BLOCK_LOG)
    brain = BrainEngine(history, blocked_words)
    crawler = YouTubeCrawlHandler()
    seen_ids = {v['id'] for v in history}
    new_candidates = []

    try:
        # 1. שלב ראשון: חיפוש רחב
        print("🔎 Phase 1: Broad Search...")
        for kw in random.sample(SEARCH_KEYWORDS, 4):
            if is_time_up(): break
            print(f"   Searching for: {kw}")
            results = crawler.search_youtube(kw)
            for vid_id, title, chan_id in results:
                if is_time_up(): break
                if vid_id not in seen_ids:
                    new_candidates.append({
                        "id": vid_id, 
                        "title": title, 
                        "score": brain.get_score(title)
                    })
                    seen_ids.add(vid_id)

        # 2. שלב שני: איסוף מהיר מערוצים
        print("📡 Phase 2: Rapid Deep Crawl & Channel Harvesting...")
        seeds = random.sample(history, min(len(history), 20))
        for seed in seeds:
            if is_time_up() or len(new_candidates) >= MAX_CANDIDATES:
                break
                
            recs = crawler.get_recommendations(seed['id'])
            for vid_id, title, chan_id in recs:
                if is_time_up(): break
                if vid_id in seen_ids: continue
                
                score = brain.get_score(title)
                if score > 5:
                    print(f"   High score ({score:.2f}) found! Harvesting channel: {chan_id}")
                    chan_vids = crawler.get_channel_videos(chan_id)
                    for cv in chan_vids:
                        if is_time_up(): break # בדיקת זמן בתוך לולאת הערוץ
                        if cv['id'] not in seen_ids:
                            cv['score'] = brain.get_score(cv['title'])
                            new_candidates.append(cv)
                            seen_ids.add(cv['id'])
                elif score > 0.5:
                    new_candidates.append({"id": vid_id, "title": title, "score": score})
                    seen_ids.add(vid_id)

    finally:
        # --- שמירה וסיכום (מבוצע תמיד, גם אם הזמן נגמר) ---
        print(f"💾 Time is up or finished! Processing {len(new_candidates)} candidates collected so far...")
        new_candidates.sort(key=lambda x: x.get('score', 0), reverse=True)
        final_output = [{"id": v['id'], "title": v['title']} for v in new_candidates[:MAX_CANDIDATES]]
        
        with open(PENDING_FILE, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)

        elapsed = int(time.time() - start_time)
        print(f"✅ Mission Finished in {elapsed}s: {len(final_output)} candidates ready.")

if __name__ == "__main__":
    run_system()
