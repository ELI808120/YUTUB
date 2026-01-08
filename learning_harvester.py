import json
import re
from collections import Counter
from github import Github
import yt_dlp

# הגדרות
GITHUB_TOKEN = 'YOUR_GITHUB_TOKEN' # בסביבת גיטהב זה יגיע ממשתני סביבה
REPO_NAME = 'user/repo_name'
QUEUE_FILE = 'queue_candidates.json'
HISTORY_FILE = 'scan_history.json'

class WordLearner:
    """מחלקה שאחראית ללמוד ממקרי העבר"""
    def __init__(self, history_data):
        self.history = history_data
        self.learned_weights = {}

    def extract_words(self, text):
        # מפרק טקסט למילים, מנקה סימני פיסוק
        return [w for w in re.split(r'\s+', re.sub(r'[^\w\s]', '', text.lower())) if len(w) > 2]

    def learn(self):
        print("Learning from history...")
        open_words = Counter()
        closed_words = Counter()
        
        # 1. איסוף סטטיסטיקה
        for item in self.history:
            words = self.extract_words(item.get('title', '') + " " + item.get('description', ''))
            if item['status'] == 'open':
                open_words.update(words)
            else:
                closed_words.update(words)

        # 2. חישוב ציון לכל מילה שמופיעה מספיק פעמים
        all_words = set(open_words.keys()) | set(closed_words.keys())
        
        for word in all_words:
            o_count = open_words[word]
            c_count = closed_words[word]
            total = o_count + c_count
            
            if total < 3: continue # מתעלם ממילים נדירות מדי (רעש סטטיסטי)

            # חישוב הסתברות הצלחה (בין 0 ל-1)
            success_rate = o_count / total
            
            # המרת ההסתברות לניקוד (בין -10 ל +10)
            # אם 100% הצלחה -> +10
            # אם 50% הצלחה -> 0
            # אם 0% הצלחה -> -10
            score = (success_rate - 0.5) * 20 
            self.learned_weights[word] = round(score, 2)
            
        print(f"Learned weights for {len(self.learned_weights)} words.")
        return self.learned_weights

class SmartHarvester:
    def __init__(self, token):
        self.g = Github(token)
        self.repo = self.g.get_repo(REPO_NAME)
        self.ydl_opts = {'quiet': True, 'extract_flat': True, 'ignoreerrors': True}
        
        # משקלים בסיסיים (התחלתיים) שיקבלו חיזוק מהלמידה
        self.base_weights = {'שיעור': 5, 'תורה': 5, 'clip': -10, 'official': -5}
        self.dynamic_weights = {}

    def get_file_content(self, path):
        try:
            c = self.repo.get_contents(path)
            return json.loads(c.decoded_content.decode()), c.sha
        except: return [], None

    def calculate_smart_score(self, title, description):
        text = (str(title) + " " + str(description)).lower()
        words = [w for w in re.split(r'\s+', re.sub(r'[^\w\s]', '', text)) if len(w) > 2]
        
        score = 0
        
        # שימוש במשקלים שנלמדו
        for word in words:
            # אם המילה קיימת בלמידה - השתמש בה, אחרת חפש בבסיס
            if word in self.dynamic_weights:
                score += self.dynamic_weights[word]
            elif word in self.base_weights:
                score += self.base_weights[word]
                
        return score

    def run(self):
        # 1. טעינת היסטוריה
        history, _ = self.get_file_content(HISTORY_FILE)
        
        # 2. ביצוע למידה
        learner = WordLearner(history)
        self.dynamic_weights = learner.learn()
        
        # כאן מדפיסים דוגמה למה המחשב למד (לצורך דיבוג)
        # print("Top learned positive words:", sorted(self.dynamic_weights.items(), key=lambda x: x[1], reverse=True)[:5])
        
        # 3. מציאת סרטון מקור (Seed) - ניקח סרטון פתוח אקראי מהאחרונים
        if not history: return
        seed = next((x for x in reversed(history) if x['status'] == 'open'), None)
        if not seed: return

        print(f"Harvesting based on seed: {seed['title']}")
        
        # 4. סריקת המלצות (בדומה לקוד הקודם, רק עם הניקוד החדש)
        candidates = []
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            # חיפוש סרטונים דומים
            res = ydl.extract_info(f"ytsearch10:{seed['title']}", download=False)
            if 'entries' in res:
                for entry in res['entries']:
                    if not entry: continue
                    # בדיקה: האם הסרטון כבר נבדק בעבר?
                    if any(h['id'] == entry['id'] for h in history): continue
                    
                    final_score = self.calculate_smart_score(entry['title'], entry.get('description', ''))
                    
                    if final_score > 3: # סף כניסה
                        candidates.append({
                            'id': entry['id'],
                            'url': f"https://www.youtube.com/watch?v={entry['id']}",
                            'title': entry['title'],
                            'score': final_score,
                            'status': 'pending'
                        })

        # 5. עדכון גיטהב
        if candidates:
            queue, sha = self.get_file_content(QUEUE_FILE)
            # מיזוג ומניעת כפילויות
            existing_ids = set(item['id'] for item in queue)
            new_unique = [c for c in candidates if c['id'] not in existing_ids]
            
            if new_unique:
                queue.extend(new_unique)
                queue.sort(key=lambda x: x['score'], reverse=True)
                self.repo.update_file(QUEUE_FILE, "Smart Update", json.dumps(queue, indent=2, ensure_ascii=False), sha)
                print(f"Added {len(new_unique)} smart candidates.")

if __name__ == "__main__":
    import os
    # קריאת הטוקן ממשתני הסביבה של גיטהב
    token = os.environ.get('GH_TOKEN') 
    if not token: 
        print("No token found")
        exit()
        
    SmartHarvester(token).run()
