import urllib.request
import re
import json
import time

def get_channel_videos(channel_id):
    # כתובת ה-RSS הרשמית של ערוץ יוטיוב
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(rss_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as res:
            content = res.read().decode('utf-8')
            # שליפת מזהי וידאו וכותרות
            video_ids = re.findall(r'<yt:videoId>(.*?)</yt:videoId>', content)
            titles = re.findall(r'<title>(.*?)</title>', content)[1:] # מתעלם מכותרת הערוץ
            return [{"id": v, "title": t} for v, t in zip(video_ids, titles)]
    except Exception as e:
        print(f"Error fetching RSS for {channel_id}: {e}")
        return []

def run():
    print("📡 סורק באמצעות RSS (ללא עוגיות - חסין חסימות)...")
    
    try:
        with open('final_history_final.json', 'r', encoding='utf-8') as f:
            history = json.load(f)
    except:
        print("❌ לא נמצא קובץ היסטוריה!")
        return

    seen = {v['id'] for v in history}
    new_candidates = []

    # נסרוק את 15 הסרטונים האחרונים כדי למצוא את הערוצים שלהם
    for entry in history[:15]:
        print(f"🔎 מחפש ערוץ עבור: {entry['title'][:30]}...")
        try:
            url = f"https://www.youtube.com/watch?v={entry['id']}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as res:
                html = res.read().decode('utf-8', errors='ignore')
                # מחפש את מזהה הערוץ בתוך ה-HTML
                channel_match = re.search(r'"channelId":"(UC[a-zA-Z0-9_-]{22})"', html)
                
                if channel_match:
                    channel_id = channel_match.group(1)
                    videos = get_channel_videos(channel_id)
                    for v in videos:
                        if v['id'] not in seen:
                            print(f"   ✨ מצאתי סרטון חדש: {v['title']}")
                            new_candidates.append(v)
                            seen.add(v['id'])
        except:
            continue
        
        if len(new_candidates) > 50: break
        time.sleep(1)

    with open('pending_check.json', 'w', encoding='utf-8') as f:
        json.dump(new_candidates, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ הצלחנו! נמצאו {len(new_candidates)} מועמדים.")

if __name__ == "__main__":
    run()
