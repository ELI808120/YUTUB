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
    print(f"🚀 Autonomous Hyper-Crawler v3 Started. Workers: {MAX_WORKERS}")
    
    # 1. טעינת היסטוריה
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f: history = json.load(f)
    except: history = []
    
    brain = SmartFilter(history)
    crawler = CloudCrawler()
    candidates = []
    
    # 2. יצירת רשימת משימות חכמה
    tasks = []
    
    # א. גיוון: 10 נושאים אקראיים מהרשימה הקבועה (כדי לא לאבד כיוון)
    tasks.extend([('search', s) for s in random.sample(SAFE_SEEDS, min(len(SAFE_SEEDS), 10))])
    
    # ב. המוח האוטונומי:
    if history:
        # 1. משימות "קשורים" (Related) ל-15 האחרונים שנטפרי אישרה
        for item in history[:15]:
            tasks.append(('related', item['id']))
            
        # 2. יצירת מילות חיפוש חדשות מהכותרות של ההיסטוריה
        dynamic_queries = set()
        for item in history[:40]: # מסתכל על 40 האחרונים
            title = item.get('title', '')
            # חילוץ מילים בעברית ובאנגלית (מעל 3 אותיות)
            words = re.findall(r'\b[\u0590-\u05EA]{4,}\b|\b[a-zA-Z]{4,}\b', title)
            
            if len(words) >= 2:
                # יוצר צירוף של 2 מילים אקראיות מתוך הכותרת ומחפש אותן
                phrase = " ".join(random.sample(words, 2))
                dynamic_queries.add(phrase)
        
        # מוסיף 20 שאילתות שהבוט המציא לבד
        for q in random.sample(list(dynamic_queries), min(len(dynamic_queries), 20)):
            tasks.append(('search', q))
            print(f"🧠 Autonomous Query: {q}")

    print(f"📋 Total Tasks: {len(tasks)}. Starting swarm...")

    # 

    # 3. הרצה במקביל (נשאר כפי שהיה)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_task = {}
        for task_type, value in tasks:
            if crawler.is_time_up(): break
            func = crawler.search_keyword if task_type == 'search' else crawler.get_related
            future = executor.submit(func, value)
            future_to_task[future] = f"{task_type}:{value[:15]}"

        for future in as_completed(future_to_task):
            try:
                data = future.result()
                if data:
                    for vid in data:
                        if brain.is_new(vid['id']):
                            score = brain.score(vid['title'])
                            if score > 0:
                                candidates.append({"id": vid['id'], "title": vid['title'], "score": score})
            except: pass

    # 4. עיבוד סופי ושמירה
    unique_candidates = {v['id']: v for v in candidates}.values()
    final_list = list(unique_candidates)
    final_list.sort(key=lambda x: x['score'], reverse=True)
    
    final_output = final_list[:800]
    print(f"💾 DONE. Collected {len(candidates)} raw -> Saving {len(final_output)} best candidates.")
    
    with open(PENDING_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)
if __name__ == "__main__":
    main()
