import urllib.request
import json
import re
import time
import os

# הגדרות האלגוריתם
PLUS_WORDS = ["שיעור", "תורה", "הרב", "גמרא", "הלכה", "תכנות", "מדריך", "יהדות"]
MINUS_WORDS = ["זמרת", "סרט", "כאן 11", "מוזיקה", "קליפ", "חדשות"]

def get_video_info(video_id):
    """חילוץ כותרת וסרטונים קשורים בשיטה שעבדה בדיפנאוט"""
    url = f"https://www.youtube.com/watch?v={video_id}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as res:
            content = res.read().decode('utf-8', errors='ignore')
            
            # חילוץ כותרת
            title_match = re.search(r'<title>(.*?)</title>', content)
            title = title_match.group(1).replace(" - YouTube", "") if title_match else ""
            
            # חילוץ מזהי וידאו קשורים
            related_ids = list(set(re.findall(r'watch\?v=([a-zA-Z0-9_-]{11})', content)))
            return title, related_ids
    except:
        return None, []

def calculate_score(title):
    score = 0
    for w in PLUS_WORDS:
        if w in title: score += 50
    for w in MINUS_WORDS:
        if w in title: score -= 100
    return score

def run():
    # קריאת המאגר הקיים (הקובץ שהעלית קודם)
    with open('final_history_final.json', 'r', encoding='utf-8') as f:
        verified_data = json.load(f)

    seen_ids = {v['id'] for v in verified_data}
    new_queue = []

    # סורק סרטונים קשורים מהמקורות הכי חדשים שלנו
    for entry in verified_data[:10]: 
        print(f"🔍 בודק סביבת סרטון: {entry['title']}")
        _, related = get_video_info(entry['id'])
        
        for r_id in related:
            if r_id not in seen_ids:
                title, _ = get_video_info(r_id)
                if title:
                    score = calculate_score(title)
                    new_queue.append({"id": r_id, "title": title, "score": score, "status": "pending"})
                    seen_ids.add(r_id)
        time.sleep(1)

    # מיון לפי הציון הגבוה ביותר
    new_queue.sort(key=lambda x: x['score'], reverse=True)

    # שמירה לקובץ שהמחשב בבית יקרא
    with open('pending_check.json', 'w', encoding='utf-8') as f:
        json.dump(new_queue, f, indent=2, ensure_ascii=False)
    
    print(f"✨ נוצר תור חדש עם {len(new_queue)} מועמדים.")

if __name__ == "__main__":
    run()
