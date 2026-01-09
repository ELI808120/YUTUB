import json
import subprocess
import os

def get_related_videos(video_id):
    # הפקודה המדויקת לשימוש ב-yt-dlp עם עוגיות
    cmd = [
        'yt-dlp',
        '--cookies', 'cookies.txt',
        '--flat-playlist',
        '--print', 'id',
        '--print', 'title',
        f'https://www.youtube.com/watch?v={video_id}'
    ]
    try:
        # yt-dlp עוקף את חסימות ה-Bot של יוטיוב
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        lines = result.stdout.strip().split('\n')
        
        candidates = []
        for i in range(0, len(lines), 2):
            if i+1 < len(lines):
                v_id = lines[i]
                title = lines[i+1]
                if len(v_id) == 11:
                    candidates.append({"id": v_id, "title": title})
        return candidates
    except Exception as e:
        print(f"Error for {video_id}: {e}")
        return []

def run():
    if not os.path.exists('cookies.txt'):
        print("❌ שגיאה קריטית: קובץ cookies.txt לא נמצא בתיקיית המאגר!")
        return

    print("🍪 מפעיל סורק מבוסס עוגיות ו-yt-dlp...")
    
    try:
        with open('final_history_final.json', 'r', encoding='utf-8') as f:
            history = json.load(f)
    except Exception as e:
        print(f"❌ שגיאה בטעינת היסטוריה: {e}")
        return

    seen = {v['id'] for v in history}
    new_queue = []

    # סורק את 5 הסרטונים הראשונים כדי לבדוק שהשיטה עובדת
    for entry in history[:5]:
        print(f"🔍 שואב המלצות עבור: {entry['title'][:40]}")
        related = get_related_videos(entry['id'])
        
        for item in related:
            if item['id'] not in seen:
                print(f"   ✨ מצאתי מועמד: {item['title']}")
                new_queue.append(item)
                seen.add(item['id'])
        
        if len(new_queue) > 50: break

    with open('pending_check.json', 'w', encoding='utf-8') as f:
        json.dump(new_queue, f, indent=2, ensure_ascii=False)
    
    print(f"✅ סיום! נמצאו {len(new_queue)} מועמדים.")

if __name__ == "__main__":
    run()
