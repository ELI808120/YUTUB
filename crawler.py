import urllib.request
import json
import re
import time
import os

# מילות מפתח לתיעדוף
PLUS_WORDS = ["שיעור", "תורה", "הרב", "גמרא", "הלכה", "תכנות", "מדריך", "יהדות", "מוסר", "חסידות", "דף היומי", "קבלה"]
MINUS_WORDS = ["זמרת", "סרט", "כאן 11", "מוזיקה", "קליפ", "חדשות", "ספורט"]

def get_video_info(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    # Headers שמחקים דפדפן אמיתי כדי לקבל את כל הנתונים
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'he-IL,he;q=0.9,en-US;q=0.8'
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as res:
            content = res.read().decode('utf-8', errors='ignore')
            
            # חילוץ כותרת מהמטא-דאטה
            title_match = re.search(r'"title":"(.*?)"', content)
            title = title_match.group(1) if title_match else ""
            
            # חילוץ מזהי וידאו מתוך ה-JSON המוסתר (ytInitialData)
            # זה מוצא סרטונים מהמלצות, מהערוץ ומפלייליסטים בצד
            related_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', content)
            
            return title, list(set(related_ids))
    except Exception as e:
        print(f"Error fetching {video_id}: {e}")
        return None, []

def calculate_score(title):
    if not title: return 0
    score = 0
    for w in PLUS_WORDS:
        if w in title: score += 50
    for w in MINUS_WORDS:
        if w in title: score -= 100
    return score

def run():
    print("🚀 מתחיל סריקה עמוקה...")
    try:
        with open('final_history_final.json', 'r', encoding='utf-8') as f:
            verified_data = json.load(f)
    except Exception as e:
        print(f"❌ שגיאה בטעינת הקובץ: {e}")
        return

    seen_ids = {v['id'] for v in verified_data}
    new_candidates = []

    # סורק את 30 הסרטונים הראשונים כדי למצוא מסה של מועמדים
    for entry in verified_data[:30]:
        print(f"📡 סורק סרטונים קשורים ל: {entry['title'][:40]}...")
        _, related = get_video_info(entry['id'])
        
        for r_id in related:
            if r_id not in seen_ids:
                r_title, _ = get_video_info(r_id)
                if r_title:
                    score = calculate_score(r_title)
                    # אנחנו לוקחים כל מה שלא קיבל ציון שלילי חזק
                    if score >= 0:
                        new_candidates.append({
                            "id": r_id, 
                            "title": r_title, 
                            "score": score,
                            "url": f"https://www.youtube.com/watch?v={r_id}"
                        })
                        print(f"   ✨ נמצא מועמד: {r_title[:50]} (Score: {score})")
                seen_ids.add(r_id)
                
                # הגבלה כדי שה-Action לא ירוץ שעות
                if len(new_candidates) > 300:
                    break
        if len(new_candidates) > 300: break
        time.sleep(1)

    # מיון לפי רלוונטיות
    new_candidates.sort(key=lambda x: x['score'], reverse=True)

    with open('pending_check.json', 'w', encoding='utf-8') as f:
        json.dump(new_candidates, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ הצלחנו! נוצר תור עם {len(new_candidates)} מועמדים ב-pending_check.json")

if __name__ == "__main__":
    run()
