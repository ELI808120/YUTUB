import urllib.request
import re
import json
import time

# קבצים לניהול הלמידה
PENDING_FILE = "pending_check.json"
HISTORY_FILE = "final_history_final.json"
BLOCK_LOG = "block_patterns.json" # קובץ שהמחשב האישי שלך יעדכן עם מילים שגרמו לחסימה

def get_video_data(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as res:
            html = res.read().decode('utf-8', errors='ignore')
            # חילוץ כותרות, מזהי וידאו ואפילו אורך (Duration) אם קיים
            data = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})".*?"title":\{"runs":\[\{"text":"(.*?)"\}\]', html)
            return [{"id": v[0], "title": v[1]} for v in data]
    except: return []

def run_sophisticated_scan():
    print("🧠 אתחול מערכת למידה אדפטיבית...")
    
    # 1. טעינת בסיס הנתונים
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
        # טעינת המילים ש"המחשב המורה" סימן כחסומות
        with open(BLOCK_LOG, 'r', encoding='utf-8') as f:
            blocked_words = json.load(f)
    except:
        history, blocked_words = [], {}

    # 2. בניית מודל הסתברותי (TF-IDF Lite)
    pos_model = {}
    for item in history[:500]:
        words = re.findall(r'\b\w{3,}\b', item.get('title', '').lower())
        for w in words: pos_model[w] = pos_model.get(w, 0) + 1

    seen = {v['id'] for v in history}
    new_candidates = []
    
    # 3. בחירת זרעים בצורה אסטרטגית (ה-5 הכי חדשים + 5 אקראיים מהעבר)
    seeds = history[:10] + random.sample(history, min(len(history), 10))
    
    for seed in seeds:
        print(f"📡 סורק אופקים סביב: {seed.get('title', 'Unknown')[:25]}...")
        recommendations = get_video_data(seed['id'])
        
        for rec in recommendations:
            if rec['id'] in seen: continue
            
            title_low = rec['title'].lower()
            title_words = re.findall(r'\b\w{3,}\b', title_low)
            
            # --- חישוב הציון המתוחכם ---
            pos_score = sum(pos_model.get(w, 0) for w in title_words)
            neg_score = sum(blocked_words.get(w, 0) for w in title_words)
            
            # נוסחת ההחלטה: (הסתברות חיובית / (הסתברות שלילית + 1))
            final_prob = (pos_score + 5) / (neg_score + 1)
            
            # בונוסים על מילות מפתח טכניות
            if any(tech in title_low for tech in ['tutorial', 'fix', 'how', 'course', 'setup']):
                final_prob *= 2
            
            # אם ההסתברות גבוהה מ-1.5 (כלומר החיובי מנצח את השלילי משמעותית)
            if final_prob > 1.2:
                new_candidates.append(rec)
                seen.add(rec['id'])
        
        if len(new_candidates) > 600: break
        time.sleep(0.2)

    with open(PENDING_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_candidates, f, indent=2, ensure_ascii=False)
    
    print(f"🎯 סריקה הושלמה. נמצאו {len(new_candidates)} סרטונים בעלי סבירות פתיחה גבוהה.")

if __name__ == "__main__":
    import random
    run_sophisticated_scan()
