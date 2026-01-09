import json
import subprocess
import re

def get_related_videos_with_ytdlp(video_id):
    """משתמש ב-yt-dlp כדי להוציא המלצות - הכי קרוב לדפדפן אמיתי"""
    cmd = [
        'yt-dlp', 
        '--get-id', 
        '--flat-playlist', 
        '--print', 'title,id',
        f'https://www.youtube.com/watch?v={video_id}'
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        lines = result.stdout.strip().split('\n')
        found = []
        # yt-dlp מוציא שורות של כותרת ואז ID
        for line in lines:
            if line: found.append(line)
        return found
    except:
        return []

def run():
    print("🚀 Starting Professional Crawl with yt-dlp...")
    with open('final_history_final.json', 'r', encoding='utf-8') as f:
        verified = json.load(f)
    
    new_candidates = []
    seen = {v['id'] for v in verified}

    for entry in verified[:5]: # ננסה 5 מקורות ראשונים
        print(f"📡 Extracting from: {entry['title']}")
        # yt-dlp מוציא המון מידע, אנחנו נחלץ מזהה וידאו
        results = get_related_videos_with_ytdlp(entry['id'])
        for res in results:
            # מחפש מזהה וידאו (11 תווים) בתוך הפלט
            match = re.search(r'([a-zA-Z0-9_-]{11})', res)
            if match:
                v_id = match.group(1)
                if v_id not in seen:
                    new_candidates.append({"id": v_id, "title": res, "score": 100})
                    seen.add(v_id)
        
    with open('pending_check.json', 'w', encoding='utf-8') as f:
        json.dump(new_candidates, f, indent=2, ensure_ascii=False)
    print(f"✅ Found {len(new_candidates)} candidates!")

if __name__ == "__main__":
    run()
