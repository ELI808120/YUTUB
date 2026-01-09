import urllib.request
import re
import json
import time
import random

def get_channel_videos(channel_id):
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(rss_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as res:
            content = res.read().decode('utf-8')
            video_ids = re.findall(r'<yt:videoId>(.*?)</yt:videoId>', content)
            titles = re.findall(r'<title>(.*?)</title>', content)[1:]
            return [{"id": v, "title": t.replace('"', "'")} for v, t in zip(video_ids, titles)]
    except:
        return []

def run():
    print("🚀 מנוע סריקה עוצמתי (RSS + Recommendations) הופעל...")
    
    try:
        with open('final_history_final.json', 'r', encoding='utf-8') as f:
            history = json.load(f)
    except: return

    try:
        with open('pending_check.json', 'r', encoding='utf-8') as f:
            new_candidates = json.load(f)
    except:
        new_candidates = []

    seen = {v['id'] for v in history}
    pending_ids = {v['id'] for v in new_candidates}

    # דוגם 50 סרטונים מההיסטוריה כדי לפתוח רדיוס סריקה ענק
    sample_size = min(len(history), 50)
    random_samples = random.sample(history, sample_size)

    for entry in random_samples:
        print(f"🔎 סורק עומק עבור: {entry['title'][:40]}...")
        try:
            url = f"https://www.youtube.com/watch?v={entry['id']}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as res:
                html = res.read().decode('utf-8', errors='ignore')
                
                # 1. חילוץ סרטונים מומלצים מהדף (Related Videos) - זה מביא המון תוכן חדש!
                recommended = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
                for r_id in recommended[:10]: # לוקח את 10 ההמלצות הראשונות מכל סרטון
                    if r_id not in seen and r_id not in pending_ids:
                        # בגלל שאין לנו כותרת להמלצות מה-Regex הזה, נשים כותרת זמנית
                        new_candidates.append({"id": r_id, "title": "סרטון מומלץ (צריך בדיקה)"})
                        pending_ids.add(r_id)

                # 2. חילוץ ערוץ המקור וסריקת כל ה-RSS שלו
                channel_match = re.search(r'"channelId":"(UC[a-zA-Z0-9_-]{22})"', html)
                if channel_match:
                    videos = get_channel_videos(channel_match.group(1))
                    for v in videos:
                        if v['id'] not in seen and v['id'] not in pending_ids:
                            print(f"   ✨ נמצא סרטון מהערוץ: {v['title']}")
                            new_candidates.append(v)
                            pending_ids.add(v['id'])
                            
        except Exception as e:
            continue
        
        # מגבלה: אם הגענו ל-300 סרטונים, עוצרים כדי שיהיה לך כח לבדוק
        if len(new_candidates) > 300: 
            print("⚠️ הגענו למכסה של 300 סרטונים בתור. עוצרים.")
            break
        
        time.sleep(0.2) # מהירות גבוהה יותר

    with open('pending_check.json', 'w', encoding='utf-8') as f:
        json.dump(new_candidates, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ הצלחנו! בתור מחכים כרגע {len(new_candidates)} סרטונים לבדיקת ה-AAA שלך.")

if __name__ == "__main__":
    run()
