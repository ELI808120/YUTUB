import urllib.request
import json
import re
import time

# מילות מפתח לתיעדוף
PLUS_WORDS = ["שיעור", "תורה", "הרב", "גמרא", "הלכה", "תכנות", "מדריך", "יהדות", "מוסר", "חסידות", "דף היומי"]
MINUS_WORDS = ["זמרת", "סרט", "כאן 11", "מוזיקה", "קליפ", "חדשות", "ספורט", "סרטון רשמי"]

def get_video_info(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as res:
            content = res.read().decode('utf-8', errors='ignore')
            
            title_match = re.search(r'<title>(.*?)</title>', content)
            title = title_match.group(1).replace(" - YouTube", "") if title_match else ""
            
            # חיפוש אגרסיבי של כל מזהה וידאו (11 תווים) שמופיע אחרי watch?v=
            related_ids = re.findall(r'watch\?v=([a-zA-Z0-9_-]{11})', content)
            
            # חיפוש מזהי וידאו בתוך אובייקטי JSON שיוטיוב מחביא בדף
            json_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', content)
            
            all_found = list(set(related_ids + json_ids))
            return title, all_found
    except:
        return None, []

def calculate_score(title):
    score = 0
    title_low = title.lower()
    for w in PLUS_WORDS:
        if w in title_low: score += 50
    for w in MINUS_WORDS:
        if w in title_low: score -= 100
    return score

def run():
    try:
        with open('final_history_final.json', 'r', encoding='utf-8') as f:
            verified_data = json.load(f)
    except FileNotFoundError:
        print("❌ קובץ המקור לא נמצא!")
        return

    seen_ids = {v['id'] for v in verified_data}
    new_candidates = []

    # עובר על 20 סרטונים מאושרים כדי למצוא המלצות
    for entry in verified_data[:20]:
        print(f"📡 סורק סביבת סרטון: {entry['title']}")
        _, related = get_video_info(entry['id'])
        
        for r_id in related:
            if r_id not in seen_ids:
                r_title, _ = get_video_info(r_id)
                if r_title:
                    score = calculate_score(r_title)
                    # מכניסים לתור רק סרטונים עם פוטנציאל חיובי (כדי לא להציף בזבל)
                    if score >= 0:
                        new_candidates.append({"id": r_id, "title": r_title, "score": score})
                        print(f"   ✨ נמצא מועמד: {r_title} (ציון: {score})")
                seen_ids.add(r_id)
                if len(new_candidates) > 200: break # מגבלה לכל ריצה כדי לא לחרוג מזמן ה-Action
        time.sleep(1)

    new_candidates.sort(key=lambda x: x['score'], reverse=True)

    with open('pending_check.json', 'w', encoding='utf-8') as f:
        json.dump(new_candidates, f, indent=2, ensure_ascii=False)
    
    print(f"✅ סיום! נוצר תור עם {len(new_candidates)} מועמדים לבדיקה בבית.")

if __name__ == "__main__":
    run()
