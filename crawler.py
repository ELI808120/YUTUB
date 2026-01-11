import urllib.request
import re
import json
import time
import random

# --- הגדרות קבצים ---
PENDING_FILE = "pending_check.json"
HISTORY_FILE = "final_history_final.json"

def get_channel_videos(channel_id):
    """סריקת 15 הסרטונים האחרונים של ערוץ דרך RSS (מהיר מאוד)"""
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(rss_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as res:
            content = res.read().decode('utf-8')
            video_ids = re.findall(r'<yt:videoId>(.*?)</yt:videoId>', content)
            titles = re.findall(r'<title>(.*?)</title>', content)[1:]
            return [{"id": v, "title": t} for v, t in zip(video_ids, titles)]
    except:
        return []

def get_video_data_and_channel(video_id):
    """חילוץ כותרת, מזהה ערוץ והמלצות מהדף"""
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as res:
            html = res.read().decode('utf-8', errors='ignore')
            recommendations = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})".*?"title":\{"runs":\[\{"text":"(.*?)"\}\]', html)
            channel_match = re.search(r'"channelId":"(UC[a-zA-Z0-9_-]{22})"', html)
            channel_id = channel_match.group(1) if channel_match else None
            return [{"id": v[0], "title": v[1]} for v in recommendations], channel_id
    except:
        return [], None

def build_learning_model(history):
    """בניית 'מפת מילים' של הצלחות מההיסטוריה (ה-AI של המערכת)"""
    model = {}
    for item in history[:300]: # לומד מ-300 ההצלחות האחרונות
        title = item.get('title', '').lower()
        words = re.findall(r'\b\w{4,}\b', title) # לוקח רק מילים מעל 4 אותיות
        for word in words:
            model[word] = model.get(word, 0) + 1
    return model

def calculate_smart_score(title, model):
    """ציון מבוסס למידה: ככל שהמילה נפוצה יותר בהיסטוריה, הציון עולה"""
    title_low = title.lower()
    score = 0
    
    # בדיקה מול המודל שנלמד
    title_words = re.findall(r'\b\w{4,}\b', title_low)
    for word in title_words:
        if word in model:
            score += (model[word] * 10) # בונוס על מילים מוכרות
            
    # פילטרים קבועים למניעת זבל (מבוסס נטפרי)
    bad_keywords = ['music', 'song', 'official', 'movie', 'trailer', 'vlog', 'funny', 'slime', 'makeup']
    if any(bad in title_low for bad in bad_keywords):
        score -= 100
        
    return score

def run():
    print("🚀 מתניע סורק ענן עם למידה עצמית (Self-Learning AI)...")
    
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
    except: history = []

    # בניית המודל מההיסטוריה הקיימת שלך
    learning_model = build_learning_model(history)
    print(f"🧠 המודל למד {len(learning_model)} מילים 'חיוביות' מההיסטוריה.")

    seen = {v['id'] for v in history}
    new_candidates = []
    
    # בחירת סרטוני 'מקור' (Seeds) - לוקח את הכי חדשים שנטפרי אישרה
    seeds = history[:15]
    
    for seed in seeds:
        print(f"🔎 סורק המלצות סביב: {seed.get('title', 'Unknown')[:30]}...")
        recs, channel_id = get_video_data_and_channel(seed['id'])
        
        # סריקת ערוץ איכותי
        if channel_id:
            channel_vids = get_channel_videos(channel_id)
            for cv in channel_vids:
                if cv['id'] not in seen:
                    cv_score = calculate_smart_score(cv['title'], learning_model)
                    if cv_score > -20: # בערוץ שכבר הצליח אנחנו יותר גמישים
                        new_candidates.append(cv)
                        seen.add(cv['id'])

        # סריקת המלצות כלליות
        for r in recs:
            if r['id'] not in seen:
                score = calculate_smart_score(r['title'], learning_model)
                if score > 20: # רק מה שנראה ממש מבטיח
                    print(f"  ✨ מועמד חזק (ציון {score}): {r['title'][:40]}")
                    new_candidates.append(r)
                    seen.add(r['id'])
        
        if len(new_candidates) > 500: break
        time.sleep(0.5)

    with open(PENDING_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_candidates, f, indent=2, ensure_ascii=False)
    
    print(f"✅ סיום! {len(new_candidates)} סרטונים איכותיים מוכנים לבדיקה במחשב האישי.")

if __name__ == "__main__":
    run()
