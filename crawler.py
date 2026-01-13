import urllib.request
import urllib.parse
import json
import time
import re
import os
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# =============================================================================
# CONFIGURATION
# =============================================================================
HISTORY_FILE = "final_history_final.json"
PENDING_FILE = "pending_check.json"
BLOCK_LOG = "block_patterns.json"

# הגבלת זמן קשיחה (8 דקות ריצה נטו, משאיר 2 דקות לשמירה בגיטהב)
MAX_RUNTIME = 480 
MAX_WORKERS = 10  # מספר התהליכונים במקביל

# מילות מפתח ממוקדות לתוכן שעובר סינון (מדע, טבע, לימודים, טכנולוגיה)
SAFE_SEEDS = [
    "How it's made documentary", "Python tutorial for beginners", 
    "National Geographic 4K", "Science experiments at home", 
    "Woodworking tips", "Restoration projects", "Space facts 2024",
    "History of technology", "Learn English conversation", "Physics explained"
]

class SmartFilter:
    def __init__(self, history):
        self.bad_words = ['gaming', 'stream', 'live', 'fortnite', 'minecraft', 'tiktok', 'shorts', 'music', 'official video']
        self.good_words = ['tutorial', 'guide', 'lesson', 'documentary', 'science', 'tech', 'review', 'build', 'restoration']
        self.history_ids = {item['id'] for item in history}

    def score(self, title):
        title_lower = title.lower()
        # סינון גס - אם מכיל מילה בעייתית, זרוק מיד
        if any(bad in title_lower for bad in self.bad_words):
            return -100
        
        score = 0
        if any(good in title_lower for good in self.good_words):
            score += 50
        
        # תמיכה בעברית (בונוס גבוה)
        if any("\u0590" <= c <= "\u05EA" for c in title):
            score += 80
            
        return score

    def is_new(self, v_id):
        return v_id not in self.history_ids

class CloudCrawler:
    def __init__(self):
        self.start_time = time.time()
        self.ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    def is_time_up(self):
        return (time.time() - self.start_time) > MAX_RUNTIME

    def fetch_html(self, url):
        if self.is_time_up(): return None
        try:
            req = urllib.request.Request(url, headers={'User-Agent': self.ua})
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.read().decode('utf-8', errors='ignore')
        except:
            return None

    def search_keyword(self, query):
        """מבצע חיפוש ומחזיר תוצאות"""
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        html = self.fetch_html(url)
        if not html: return []
        return self._extract_data(html)

    def get_related(self, video_id):
        """מביא המלצות מסרטון קיים"""
        url = f"https://www.youtube.com/watch?v={video_id}"
        html = self.fetch_html(url)
        if not html: return []
        return self._extract_data(html)

    def _extract_data(self, html):
        """חילוץ מהיר באמצעות Regex"""
        results = []
        # תבנית שמחלצת ID ו-Title
        pattern = r'"videoId":"([a-zA-Z0-9_-]{11})".*?"title":\{"runs":\[\{"text":"(.*?)"\}\]'
        matches = re.findall(pattern, html)
        for vid, title in matches:
            results.append({"id": vid, "title": title})
        return results

def main():
    print(f"🚀 Crawler Started. Time Limit: {MAX_RUNTIME}s")
    
    # 1. טעינת נתונים
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f: history = json.load(f)
    except: history = []
    
    brain = SmartFilter(history)
    crawler = CloudCrawler()
    candidates = []
    
    # 2. בניית רשימת משימות (Tasks)
    tasks = []
    
    # א. חיפושים מבוססי מילות מפתח
    for seed in random.sample(SAFE_SEEDS, 5): 
        tasks.append(('search', seed))
        
    # ב. חיפוש סביב הצלחות עבר (הכי חשוב!)
    # לוקח 5 סרטונים אחרונים מההיסטוריה ומחפש דומים להם
    if history:
        recent_successes = history[:5]
        for item in recent_successes:
            tasks.append(('related', item['id']))

    print(f"📋 Generated {len(tasks)} harvesting tasks. Executing parallel crawl...")

    # 3. ביצוע סריקה במקביל (Multi-threading)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_task = {}
        
        for task_type, value in tasks:
            if crawler.is_time_up(): break
            
            if task_type == 'search':
                future = executor.submit(crawler.search_keyword, value)
            else:
                future = executor.submit(crawler.get_related, value)
            future_to_task[future] = f"{task_type}:{value}"

        # איסוף תוצאות בזמן אמת
        for future in as_completed(future_to_task):
            task_name = future_to_task[future]
            try:
                data = future.result()
                if data:
                    print(f"   ✅ {task_name} -> Found {len(data)} videos")
                    for vid in data:
                        if brain.is_new(vid['id']):
                            score = brain.score(vid['title'])
                            if score > 0: # שומר רק אם הציון חיובי
                                candidates.append({
                                    "id": vid['id'],
                                    "title": vid['title'],
                                    "score": score
                                })
            except Exception as e:
                print(f"   ❌ Error in {task_name}: {e}")

            if crawler.is_time_up():
                print("⏳ Time limit reached! Stopping crawler...")
                break

    # 4. סינון סופי, הסרת כפילויות ומיון
    # הסרת כפילויות לפי ID
    unique_candidates = {v['id']: v for v in candidates}.values()
    final_list = list(unique_candidates)
    
    # מיון: הכי מבטיח למעלה
    final_list.sort(key=lambda x: x['score'], reverse=True)
    
    # חיתוך לכמות סבירה (כדי לא להעמיס על הסורק המקומי)
    final_output = final_list[:300]

    print(f"💾 Saving {len(final_output)} candidates to {PENDING_FILE}")
    
    with open(PENDING_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
