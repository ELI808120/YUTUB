import urllib.request
import json
import re
import time

def get_video_info(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'he-IL,he'
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as res:
            content = res.read().decode('utf-8', errors='ignore')
            
            # חילוץ כותרת
            title_match = re.search(r'<title>(.*?)</title>', content)
            title = title_match.group(1).replace(" - YouTube", "") if title_match else ""
            
            # חיפוש כל ה-Video IDs שקיימים בדף (המפתח להצלחה)
            # ביוטיוב מזהה וידאו הוא תמיד 11 תווים שמופיעים אחרי "videoId":"
            found_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', content)
            
            # גיבוי: חיפוש מזהים בתוך קישורי v=
            found_ids += re.findall(r'v=([a-zA-Z0-9_-]{11})', content)
            
            return title, list(set(found_ids))
    except Exception as e:
        print(f"Error {video_id}: {e}")
        return None, []

def calculate_score(title):
    if not title: return 0
    # מילים שנותנות ניקוד גבוה
    plus = ["שיעור", "תורה", "הרב", "גמרא", "הלכה", "תכנות", "מדריך", "יהדות", "קבלה", "מוסר"]
    # מילים שפוסלות סרטון
    minus = ["זמרת", "סרט", "כאן 11", "מוזיקה", "קליפ", "חדשות"]
    
    score = 0
    title_low = title.lower()
    for w in plus:
        if w in title_low: score += 100
    for w in minus:
        if w in title_low: score -= 200
    return score

def run():
    print("🚀 מתחיל סריקת עומק...")
    with open('final_history_final.json', 'r', encoding='utf-8') as f:
        verified_data = json.load(f)

    seen_ids = {v['id'] for v in verified_data}
    new_candidates = []

    # נסרוק 20 סרטונים מההיסטוריה כדי למצוא המלצות
    for entry in verified_data[:20]:
        print(f"📡 בודק סביבת: {entry['title'][:40]}...")
        _, related = get_video_info(entry['id'])
        
        for r_id in related:
            if r_id not in seen_ids:
                # בדיקה מהירה של הכותרת של המועמד
                r_title, _ = get_video_info(r_id)
                if r_title:
                    score = calculate_score(r_title)
                    if score >= 0: # רק סרטונים חיוביים או נייטרליים
                        new_candidates.append({"id": r_id, "title": r_title, "score": score})
                        print(f"   ✨ מועמד נמצא: {r_title[:50]} (ציון: {score})")
                seen_ids.add(r_id)
                
                if len(new_candidates) > 100: break
        if len(new_candidates) > 100: break
        time.sleep(1)

    # מיון לפי הציון הכי גבוה
    new_candidates.sort(key=lambda x: x['score'], reverse=True)

    with open('pending_check.json', 'w', encoding='utf-8') as f:
        json.dump(new_candidates, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ הצלחנו! {len(new_candidates)} מועמדים מחכים לבדיקה בבית.")

if __name__ == "__main__":
    run()
