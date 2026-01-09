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
    print("🚀 מנוע סריקה ויראלי הופעל - מחפש הממוווון סרטונים...")
    
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

    # דוגם 40 סרטונים מההיסטוריה כנקודות מוצא
    sample_size = min(len(history), 40)
    random_samples = random.sample(history, sample_size)

    for entry in random_samples:
        print(f"🔎 סורק עומק והמלצות: {entry['title'][:40]}...")
        try:
            url = f"https://www.youtube.com/watch?v={entry['id']}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as res:
                html = res.read().decode('utf-8', errors='ignore')
                
                # 1. חילוץ המון המלצות (עד 40 מכל דף)
                recommended = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
                for r_id in recommended[:40]: 
                    if r_id not in seen and r_id not in pending_ids:
                        new_candidates.append({"id": r_id, "title": "סרטון מומלץ (חדש)"})
                        pending_ids.add(r_id)

                # 2. חילוץ ערוצים מומלצים וסריקת ה-RSS שלהם
                # זה גורם לסורק "לקפוץ" לערוצים דומים
                extra_channels = re.findall(r'"channelId":"(UC[a-zA-Z0-9_-]{22})"', html)
                for ex_cid in list(set(extra_channels))[:3]: 
                    ex_videos = get_channel_videos(ex_cid)
                    for ev in ex_videos:
                        if ev['id'] not in seen and ev['id'] not in pending_ids:
                            print(f"   ✨ מצאתי ערוץ חדש וסרטון: {ev['title'][:30]}")
                            new_candidates.append(ev)
                            pending_ids.add(ev['id'])
                            
        except Exception as e:
            continue
        
        # מכסה גבוהה מאוד כדי שתקבל "הרבה ממש הרבה"
        if len(new_candidates) > 500: 
            print("🔥 הגענו למעל 500 סרטונים! עוצרים.")
            break
        
        time.sleep(0.1)

    with open('pending_check.json', 'w', encoding='utf-8') as f:
        json.dump(new_candidates, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ סיום! בתור מחכים כרגע {len(new_candidates)} סרטונים לבדיקת ה-AAA שלך.")

if __name__ == "__main__":
    run()
