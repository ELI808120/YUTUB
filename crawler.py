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
MAX_RUNTIME = 450  # משאיר זמן בטוח לשמירה
MAX_WORKERS = 20   # העלינו ל-20 תהליכים במקביל!

# רשימת חיפוש ענקית ומגוונת
SAFE_SEEDS = [
    # Hebrew - גבוה בסיכויי פתיחה
    "איך עובד מנוע", "ניסויים מדעיים לילדים", "לימוד אנגלית למתחילים", 
    "היסטוריה של ארץ ישראל", "מדריך פייתון", "קורס אקסל", "שיפוץ רהיטים",
    "הכנת לחם מחמצת", "צילום טבע", "מערכת השמש",
    
    # Tech & Science
    "How it's made full episodes", "Engineering documentary", "Restoration projects",
    "Python tutorial 2024", "SpaceX launch 4K", "Physics explained",
    "Mega structures documentary", "Ancient civilizations", "Future technology",
    
    # DIY & Skills
    "Woodworking joints", "Home repair diy", "Drawing tutorial for beginners",
    "Oil painting techniques", "Survival skills", "Gardening tips",
    
    # Educational
    "Math tricks", "Learn Spanish", "History of World War 2", "Deep sea exploration"
]

class SmartFilter:
    def __init__(self, history):
        # מילים שפוסלות מיד
        self.bad_words = [
            'gaming', 'stream', 'live', 'fortnite', 'minecraft', 'roblox',
            'tiktok', 'shorts', 'music video', 'official video', 'trailer',
            'reaction', 'prank', 'challenge', 'vlog'
        ]
        # מילים שמעלות ציון (מורחב)
        self.good_words = [
            'tutorial', 'guide', 'lesson', 'documentary', 'science', 'tech', 
            'review', 'build', 'make', 'restoration', 'history', 'lecture',
            'course', 'learn', 'study', 'experiment', 'analysis', 'how to',
            'מדריך', 'לימוד', 'שיעור', 'הרצאה', 'הסבר', 'קורס', 'תיקון'
        ]
        self.history_ids = {item['id'] for item in history}

    def score(self, title):
        title_lower = title.lower()
        
        # סינון שלילי
        if any(bad in title_lower for bad in self.bad_words):
            return -100
        
        score = 0
        # בונוס על מילים טובות
        if any(good in title_lower for good in self.good_words):
            score += 50
        
        # בונוס על עברית (נטפרי אוהב עברית)
        if any("\u0590" <= c <= "\u05EA" for c in title):
            score += 60
            
        # אם אין מילה רעה, ואין מילה טובה - תן ניקוד קטן כדי לתת צ'אנס
        if score == 0:
            score = 10 
            
        return score

    def is_new(self, v_id):
        return v_id not in self.history_ids

class CloudCrawler:
    def __init__(self):
        self.start_time = time.time()
        self.ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0'

    def is_time_up(self):
        return (time.time() - self.start_time) > MAX_RUNTIME

    def fetch_html(self, url):
        if self.is_time_up(): return None
        try:
            req = urllib.request.Request(url, headers={'User-Agent': self.ua})
            with urllib.request.urlopen(req, timeout=8) as response:
                return response.read().decode('utf-8', errors='ignore')
        except: return None

    def search_keyword(self, query):
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        html = self.fetch_html(url)
        return self._extract_data(html) if html else []

    def get_related(self, video_id):
        url = f"https://www.youtube.com/watch?v={video_id}"
        html = self.fetch_html(url)
        return self._extract_data(html) if html else []

    def _extract_data(self, html):
        results = []
        # Regex מהיר ויעיל
        pattern = r'"videoId":"([a-zA-Z0-9_-]{11})".*?"title":\{"runs":\[\{"text":"(.*?)"\}\]'
        # מנקה כפילויות ברמת הדף הנוכחי
        seen_on_page = set()
        for vid, title in re.findall(pattern, html):
            if vid not in seen_on_page:
                results.append({"id": vid, "title": title})
                seen_on_page.add(vid)
        return results

def main():
    print(f"🚀 Hyper-Crawler v2 Started. Workers: {MAX_WORKERS}")
    
    # 1. Load History
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f: history = json.load(f)
    except: history = []
    
    brain = SmartFilter(history)
    crawler = CloudCrawler()
    candidates = []
    
    # 2. Generate Massive Task List
    tasks = []
    
    # א. מגרילים 25 נושאים מתוך הרשימה (במקום 5)
    selected_seeds = random.sample(SAFE_SEEDS, min(len(SAFE_SEEDS), 25))
    for seed in selected_seeds: 
        tasks.append(('search', seed))
        
    # ב. סריקת עומק על ההיסטוריה (עד 10 סרטונים אחרונים)
    if history:
        for item in history[:10]:
            tasks.append(('related', item['id']))

    print(f"📋 Loaded {len(tasks)} heavy tasks. Starting swarm...")

    # 3. Parallel Execution
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_task = {}
        for task_type, value in tasks:
            if crawler.is_time_up(): break
            
            func = crawler.search_keyword if task_type == 'search' else crawler.get_related
            future = executor.submit(func, value)
            future_to_task[future] = f"{task_type}:{value[:15]}"

        for future in as_completed(future_to_task):
            task_name = future_to_task[future]
            try:
                data = future.result()
                if data:
                    print(f"   🔹 {task_name}.. -> {len(data)} vids")
                    for vid in data:
                        if brain.is_new(vid['id']):
                            score = brain.score(vid['title'])
                            if score > 0:
                                candidates.append({
                                    "id": vid['id'], 
                                    "title": vid['title'], 
                                    "score": score
                                })
            except: pass

            if crawler.is_time_up(): break

    # 4. Final Processing
    # מסדרים לפי ציון ומעיפים כפילויות
    unique_candidates = {v['id']: v for v in candidates}.values()
    final_list = list(unique_candidates)
    final_list.sort(key=lambda x: x['score'], reverse=True)
    
    # מגדילים את המכסה ל-800 מועמדים
    final_output = final_list[:800]

    print(f"💾 DONE. Collected {len(candidates)} raw -> Saving {len(final_output)} best candidates.")
    
    with open(PENDING_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
