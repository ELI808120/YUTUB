import urllib.request
import json
import re
import time

def get_video_info(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    # Headers חזקים יותר כדי להיראות כמו כרום אמיתי
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'he-IL,he;q=0.9,en-US;q=0.8'
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as res:
            content = res.read().decode('utf-8', errors='ignore')
            
            # חילוץ כותרת - שיטה גמישה
            title_match = re.search(r'<title>(.*?)</title>', content)
            title = title_match.group(1).replace(" - YouTube", "") if title_match else ""
            
            # חיפוש אגרסיבי: כל מזהה וידאו של יוטיוב מורכב מ-11 תווים (אותיות, מספרים, מקף וקו תחתי)
            # אנחנו מחפשים כל מה שמופיע אחרי watch?v= או בתוך שדות JSON
            found_ids = re.findall(r'v=([a-zA-Z0-9_-]{11})', content)
            found_ids += re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', content)
            
            return title, list(set(found_ids))
    except Exception as e:
        print(f"Error {video_id}: {e}")
        return None, []

def calculate_score(title):
    if not title: return 0
    plus = ["שיעור", "תורה", "הרב", "גמרא", "הלכה", "תכנות", "מדריך", "יהדות", "קבלה"]
    minus = ["זמרת", "סרט", "כאן 11", "מוזיקה", "קליפ"]
    score = 0
    for w in plus:
        if w in title: score += 50
    for w in minus:
        if w in title: score -= 100
    return score

def run():
    print("🚀 מתחיל סריקה...")
    with open('final_history_final.json', 'r', encoding='utf-8') as f:
        verified_data = json.load(f)

    seen_ids = {v['id'] for v in verified_data}
    new_candidates = []

    # נסרוק את 15 הסרטונים הראשונים
    for entry in verified_data[:15]:
        print(f"📡 סורק: {entry['title'][:30]}")
        _, related = get_video_info(entry['id'])
        
        for r_id in related:
            if r_id not in seen_ids:
                r_title, _ = get_video_info(r_id)
                if r_title:
                    score = calculate_score(r_title)
                    # נכניס לתור כל מה שלא קיבל ציון שלילי
                    if score >= 0:
                        new_candidates.append({"id": r_id, "title": r_title, "score": score})
                        print(f"   ✨ מצאתי: {r_title[:40]}")
                seen_ids.add(r_id)
                if len(new_candidates) > 50: break
        if len(new_candidates) > 50: break
        time.sleep(2)

    new_candidates.sort(key=lambda x: x['score'], reverse=True)
    with open('pending_check.json', 'w', encoding='utf-8') as f:
        json.dump(new_candidates, f, indent=2, ensure_ascii=False)
    print(f"✅ סיום! נמצאו {len(new_candidates)} מועמדים.")

if __name__ == "__main__":
    run()
