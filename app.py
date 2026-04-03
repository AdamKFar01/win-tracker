from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import sqlite3
import json
import os

app = Flask(__name__)

DB_PATH = os.environ.get(
    'WINNERSTRACKBUILDER_DB',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wintracker.db')
)

# Database setup
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Wins table
    c.execute('''CREATE TABLE IF NOT EXISTS wins
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  category TEXT NOT NULL,
                  activity TEXT NOT NULL,
                  description TEXT,
                  points INTEGER NOT NULL,
                  duration INTEGER,
                  date TEXT NOT NULL,
                  timestamp TEXT NOT NULL)''')
    
    # Tasks table
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  task TEXT NOT NULL,
                  task_type TEXT DEFAULT 'task',
                  period TEXT DEFAULT 'today',
                  completed INTEGER DEFAULT 0,
                  due_date TEXT,
                  created_at TEXT NOT NULL,
                  moved_to_old INTEGER DEFAULT 0)''')
    
    # Reminders table
    c.execute('''CREATE TABLE IF NOT EXISTS reminders
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  reminder TEXT NOT NULL,
                  reminder_type TEXT DEFAULT 'daily',
                  time TEXT,
                  date TEXT,
                  repeat TEXT,
                  active INTEGER DEFAULT 1,
                  created_at TEXT NOT NULL,
                  recurring INTEGER DEFAULT 0)''')

    # Add recurring column if it doesn't exist (for existing databases)
    try:
        c.execute("ALTER TABLE reminders ADD COLUMN recurring INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass  # Column already exists
    
    # Finance table
    c.execute('''CREATE TABLE IF NOT EXISTS finance
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  type TEXT NOT NULL,
                  amount REAL NOT NULL,
                  category TEXT,
                  description TEXT,
                  date TEXT NOT NULL)''')
    
    # Activities table
    c.execute('''CREATE TABLE IF NOT EXISTS activities
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  category TEXT NOT NULL,
                  name TEXT NOT NULL,
                  points INTEGER NOT NULL)''')
    
    # Calendar events table (separate from activities)
    c.execute('''CREATE TABLE IF NOT EXISTS calendar_events
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  date TEXT NOT NULL,
                  start_time TEXT,
                  end_time TEXT,
                  category TEXT NOT NULL,
                  importance TEXT DEFAULT 'normal',
                  description TEXT,
                  created_at TEXT NOT NULL)''')
    
    # Pillar scores table (one persistent row per user)
    c.execute('''CREATE TABLE IF NOT EXISTS pillar_scores
                 (id INTEGER PRIMARY KEY,
                  physical REAL DEFAULT 0,
                  work REAL DEFAULT 0,
                  health REAL DEFAULT 0,
                  relationships REAL DEFAULT 0,
                  mindset REAL DEFAULT 0)''')
    c.execute('INSERT OR IGNORE INTO pillar_scores (id) VALUES (1)')

    # Health metrics table (one persistent row)
    c.execute('''CREATE TABLE IF NOT EXISTS health_metrics
                 (id INTEGER PRIMARY KEY,
                  weight_kg REAL DEFAULT 0,
                  height_cm REAL DEFAULT 0,
                  age INTEGER DEFAULT 0,
                  sex TEXT DEFAULT 'male',
                  exercise_intensity TEXT DEFAULT 'sedentary',
                  calorie_target INTEGER DEFAULT 0,
                  protein_target INTEGER DEFAULT 0,
                  carb_target INTEGER DEFAULT 0,
                  fat_target INTEGER DEFAULT 0)''')
    c.execute('INSERT OR IGNORE INTO health_metrics (id) VALUES (1)')

    # Food log table
    c.execute('''CREATE TABLE IF NOT EXISTS food_log
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT NOT NULL,
                  meal TEXT NOT NULL,
                  food_name TEXT NOT NULL,
                  calories INTEGER DEFAULT 0,
                  protein_g REAL DEFAULT 0,
                  carbs_g REAL DEFAULT 0,
                  fat_g REAL DEFAULT 0,
                  created_at TEXT NOT NULL)''')

    # Activity log table
    c.execute('''CREATE TABLE IF NOT EXISTS activity_log
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT NOT NULL,
                  activity_type TEXT NOT NULL,
                  duration_mins INTEGER DEFAULT 0,
                  intensity TEXT DEFAULT 'moderate',
                  calories_burned INTEGER DEFAULT 0,
                  created_at TEXT NOT NULL)''')

    # Daily goals table
    c.execute('''CREATE TABLE IF NOT EXISTS daily_goals
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT NOT NULL UNIQUE,
                  goal_1_text TEXT DEFAULT '',
                  goal_1_complete INTEGER DEFAULT 0,
                  goal_2_text TEXT DEFAULT '',
                  goal_2_complete INTEGER DEFAULT 0,
                  goal_3_text TEXT DEFAULT '',
                  goal_3_complete INTEGER DEFAULT 0)''')

    # Weight log table (one entry per date)
    c.execute('''CREATE TABLE IF NOT EXISTS weight_log
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT NOT NULL UNIQUE,
                  weight_kg REAL NOT NULL,
                  created_at TEXT NOT NULL)''')

    # XP log table
    c.execute('''CREATE TABLE IF NOT EXISTS xp_log
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT NOT NULL,
                  change INTEGER NOT NULL,
                  reason TEXT NOT NULL)''')

    # User stats table (single persistent row)
    c.execute('''CREATE TABLE IF NOT EXISTS user_stats
                 (id INTEGER PRIMARY KEY,
                  total_xp INTEGER DEFAULT 0,
                  streak_days INTEGER DEFAULT 0,
                  last_win_day TEXT DEFAULT '',
                  last_penalty_date TEXT DEFAULT '',
                  savings_threshold_crossed INTEGER DEFAULT 0)''')
    c.execute('INSERT OR IGNORE INTO user_stats (id) VALUES (1)')

    # xp_reward column on tasks (for goal types)
    try:
        c.execute("ALTER TABLE tasks ADD COLUMN xp_reward INTEGER DEFAULT 0")
    except Exception:
        pass  # Column already exists

    conn.commit()
    conn.close()

# Initialize database on startup
init_db()


def _compute_level(total_xp):
    """Return (level, xp_in_level, xp_for_next_level) using 5000×1.1^n curve."""
    level = 0
    threshold = 5000
    remaining = total_xp
    while remaining >= threshold:
        remaining -= threshold
        level += 1
        threshold = int(threshold * 1.1)
    return level, remaining, threshold


def award_xp(c, change, reason):
    """Insert into xp_log and update total_xp, applying streak multiplier on gains."""
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute('SELECT total_xp, streak_days FROM user_stats WHERE id = 1')
    row = c.fetchone()
    streak_days = row[1] if row else 0
    actual_change = int(change * 1.25) if (streak_days >= 2 and change > 0) else change
    c.execute('INSERT INTO xp_log (date, change, reason) VALUES (?, ?, ?)',
              (today, actual_change, reason))
    c.execute('UPDATE user_stats SET total_xp = total_xp + ? WHERE id = 1', (actual_change,))
    return actual_change


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/wins', methods=['GET', 'POST', 'DELETE'])
def wins():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        c.execute('''INSERT INTO wins (category, activity, description, points, duration, date, timestamp)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (data['category'], data['activity'], data.get('description', ''),
                   data['points'], data.get('duration', 0), data['date'], datetime.now().isoformat()))
        award_xp(c, data['points'], f"Win: {data['activity']}")
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        win_id = request.args.get('id')
        c.execute('DELETE FROM wins WHERE id = ?', (win_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    else:
        # Get wins for a specific date or today
        date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        c.execute('SELECT * FROM wins WHERE date = ?', (date,))
        wins = c.fetchall()
        conn.close()
        
        wins_list = []
        for win in wins:
            wins_list.append({
                'id': win[0],
                'category': win[1],
                'activity': win[2],
                'points': win[3],
                'duration': win[4],
                'date': win[5],
                'timestamp': win[6],
                'description': win[7] if len(win) > 7 else ''
            })
        
        return jsonify(wins_list)

@app.route('/api/daily-summary')
def daily_summary():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get points by category
    c.execute('''SELECT category, SUM(points) FROM wins 
                 WHERE date = ? GROUP BY category''', (date,))
    results = c.fetchall()
    conn.close()
    
    summary = {
        'physical': 0,
        'work': 0,
        'health': 0,
        'relationships': 0,
        'mindset': 0,
        'total': 0
    }
    
    for row in results:
        category = row[0].lower()
        points = row[1]
        if category in summary:
            summary[category] = points
            summary['total'] += points
    
    return jsonify(summary)

@app.route('/api/week-data')
def week_data():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    week_data = []
    for i in range(7):
        date = (datetime.now() - timedelta(days=6-i)).strftime('%Y-%m-%d')
        c.execute('SELECT SUM(points) FROM wins WHERE date = ?', (date,))
        result = c.fetchone()
        total = result[0] if result[0] else 0

        c.execute('''SELECT goal_1_text, goal_1_complete, goal_2_text, goal_2_complete,
                            goal_3_text, goal_3_complete
                     FROM daily_goals WHERE date = ?''', (date,))
        grow = c.fetchone()
        if grow:
            goals_all_done = bool(grow[0]) and bool(grow[1]) and \
                             bool(grow[2]) and bool(grow[3]) and \
                             bool(grow[4]) and bool(grow[5])
        else:
            goals_all_done = False

        week_data.append({'date': date, 'points': total, 'goals_all_done': goals_all_done})

    conn.close()
    return jsonify(week_data)


@app.route('/api/daily-goals', methods=['GET', 'POST'])
def daily_goals_api():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'POST':
        data = request.json
        # Fetch previous completion state to detect newly-completed goals
        c.execute('SELECT goal_1_complete, goal_2_complete, goal_3_complete FROM daily_goals WHERE date = ?',
                  (data['date'],))
        old_row = c.fetchone()
        old_complete = [old_row[0] if old_row else 0,
                        old_row[1] if old_row else 0,
                        old_row[2] if old_row else 0]

        new_complete = [int(data.get('goal_1_complete', 0)),
                        int(data.get('goal_2_complete', 0)),
                        int(data.get('goal_3_complete', 0))]
        new_texts = [data.get('goal_1_text', ''),
                     data.get('goal_2_text', ''),
                     data.get('goal_3_text', '')]

        c.execute('''INSERT OR REPLACE INTO daily_goals
                     (date, goal_1_text, goal_1_complete, goal_2_text, goal_2_complete,
                      goal_3_text, goal_3_complete)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (data['date'],
                   new_texts[0], new_complete[0],
                   new_texts[1], new_complete[1],
                   new_texts[2], new_complete[2]))

        # Award +100 XP per newly completed goal (only for today's date)
        today = datetime.now().strftime('%Y-%m-%d')
        if data['date'] == today:
            for i in range(3):
                if new_complete[i] == 1 and old_complete[i] == 0 and new_texts[i]:
                    award_xp(c, 100, f"Goal {i+1} completed")

        conn.commit()
        conn.close()
        return jsonify({'success': True})

    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    c.execute('SELECT * FROM daily_goals WHERE date = ?', (date,))
    row = c.fetchone()
    conn.close()

    if row:
        return jsonify({
            'date': row[1],
            'goal_1_text': row[2], 'goal_1_complete': bool(row[3]),
            'goal_2_text': row[4], 'goal_2_complete': bool(row[5]),
            'goal_3_text': row[6], 'goal_3_complete': bool(row[7])
        })
    return jsonify({
        'date': date,
        'goal_1_text': '', 'goal_1_complete': False,
        'goal_2_text': '', 'goal_2_complete': False,
        'goal_3_text': '', 'goal_3_complete': False
    })

@app.route('/api/tasks', methods=['GET', 'POST', 'PUT', 'DELETE'])
def tasks():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        task_type = data.get('task_type', 'task')
        period = data.get('period', 'today')
        
        # Calculate due date based on period
        due_date = data.get('due_date')
        if not due_date and period == 'today':
            due_date = datetime.now().strftime('%Y-%m-%d')
        elif not due_date and period == 'weekly':
            due_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        elif not due_date and period == 'monthly':
            due_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        c.execute('''INSERT INTO tasks (task, task_type, period, due_date, created_at, xp_reward)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (data['task'], task_type, period, due_date, datetime.now().isoformat(),
                   data.get('xp_reward', 0)))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    elif request.method == 'PUT':
        data = request.json
        c.execute('SELECT completed, xp_reward, task FROM tasks WHERE id = ?', (data['id'],))
        old = c.fetchone()
        c.execute('UPDATE tasks SET completed = ? WHERE id = ?',
                  (data['completed'], data['id']))
        # Award XP when newly completed and xp_reward is set
        if data['completed'] == 1 and old and old[0] == 0 and old[1] and old[1] > 0:
            award_xp(c, old[1], f"Goal: {old[2][:50]}")
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        task_id = request.args.get('id')
        c.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    else:
        task_type = request.args.get('type', 'task')
        period = request.args.get('period', 'all')
        now = datetime.now()

        if period == 'old':
            today = now.strftime('%Y-%m-%d')
            c.execute('''SELECT * FROM tasks
                        WHERE task_type = ? AND due_date < ?
                        ORDER BY due_date DESC''', (task_type, today))
        elif period == 'all':
            c.execute('SELECT * FROM tasks WHERE task_type = ? ORDER BY completed, due_date', (task_type,))
        elif period == 'weekly':
            # Reset every Monday — only show goals created since this Monday
            week_start = (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')
            c.execute('''SELECT * FROM tasks WHERE task_type = ? AND period = ?
                         AND DATE(created_at) >= ? ORDER BY completed, created_at''',
                     (task_type, period, week_start))
        elif period == 'monthly':
            month_start = now.replace(day=1).strftime('%Y-%m-%d')
            c.execute('''SELECT * FROM tasks WHERE task_type = ? AND period = ?
                         AND DATE(created_at) >= ? ORDER BY completed, created_at''',
                     (task_type, period, month_start))
        elif period == 'yearly':
            year_start = now.replace(month=1, day=1).strftime('%Y-%m-%d')
            c.execute('''SELECT * FROM tasks WHERE task_type = ? AND period = ?
                         AND DATE(created_at) >= ? ORDER BY completed, created_at''',
                     (task_type, period, year_start))
        else:
            c.execute('SELECT * FROM tasks WHERE task_type = ? AND period = ? ORDER BY completed, due_date',
                     (task_type, period))
        
        tasks = c.fetchall()
        conn.close()
        
        tasks_list = []
        for task in tasks:
            tasks_list.append({
                'id': task[0],
                'task': task[1],
                'task_type': task[2],
                'period': task[3],
                'completed': task[4],
                'due_date': task[5],
                'created_at': task[6],
                'moved_to_old': task[7] if len(task) > 7 else 0,
                'xp_reward': task[8] if len(task) > 8 else 0
            })
        
        return jsonify(tasks_list)

@app.route('/api/finance', methods=['GET', 'POST'])
def finance():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        c.execute('''INSERT INTO finance (type, amount, category, description, date)
                     VALUES (?, ?, ?, ?, ?)''',
                  (data['type'], data['amount'], data.get('category'),
                   data.get('description'), data['date']))

        # XP for income (savings) deposits
        if data['type'] == 'income':
            deposit_xp = int(data['amount'])
            if deposit_xp > 0:
                award_xp(c, deposit_xp, f"Savings deposit £{data['amount']:.2f}")
            # Check if a new £1000 savings threshold has been crossed
            c.execute('SELECT savings_threshold_crossed FROM user_stats WHERE id = 1')
            stat_row = c.fetchone()
            prev_threshold = stat_row[0] if stat_row else 0
            c.execute("SELECT SUM(amount) FROM finance WHERE type = 'income'")
            total_row = c.fetchone()
            total_income = total_row[0] if total_row[0] else 0
            new_threshold = int(total_income // 1000)
            if new_threshold > prev_threshold:
                for t in range(prev_threshold + 1, new_threshold + 1):
                    award_xp(c, 1000, f"£{t * 1000} savings milestone!")
                c.execute('UPDATE user_stats SET savings_threshold_crossed = ? WHERE id = 1',
                          (new_threshold,))

        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    else:
        c.execute('SELECT * FROM finance ORDER BY date DESC')
        records = c.fetchall()
        conn.close()
        
        finance_list = []
        for record in records:
            finance_list.append({
                'id': record[0],
                'type': record[1],
                'amount': record[2],
                'category': record[3],
                'description': record[4],
                'date': record[5]
            })
        
        return jsonify(finance_list)

@app.route('/api/activities', methods=['GET', 'POST', 'PUT', 'DELETE'])
def activities_api():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        c.execute('''INSERT INTO activities (category, name, points)
                     VALUES (?, ?, ?)''',
                  (data['category'], data['name'], data['points']))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    elif request.method == 'PUT':
        data = request.json
        c.execute('UPDATE activities SET name = ?, points = ? WHERE id = ?',
                  (data['name'], data['points'], data['id']))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        activity_id = request.args.get('id')
        c.execute('DELETE FROM activities WHERE id = ?', (activity_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    else:
        # GET all activities
        c.execute('SELECT * FROM activities ORDER BY category, name')
        activities = c.fetchall()
        conn.close()
        
        activities_list = []
        for activity in activities:
            activities_list.append({
                'id': activity[0],
                'category': activity[1],
                'name': activity[2],
                'points': activity[3]
            })
        
        return jsonify(activities_list)

@app.route('/api/reminders', methods=['GET', 'POST', 'PUT', 'DELETE'])
def reminders_api():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        c.execute('''INSERT INTO reminders (reminder, reminder_type, time, date, repeat, active, created_at, recurring)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (data['reminder'], data.get('reminder_type', 'daily'), data.get('time'),
                   data.get('date'), data.get('repeat'), 1, datetime.now().isoformat(),
                   data.get('recurring', 0)))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    elif request.method == 'PUT':
        data = request.json
        if 'active' in data:
            c.execute('UPDATE reminders SET active = ? WHERE id = ?',
                      (data['active'], data['id']))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        reminder_id = request.args.get('id')
        c.execute('DELETE FROM reminders WHERE id = ?', (reminder_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    else:
        reminder_type = request.args.get('type', 'all')
        if reminder_type == 'all':
            c.execute('SELECT * FROM reminders WHERE active = 1 ORDER BY reminder_type, time')
        else:
            c.execute('SELECT * FROM reminders WHERE reminder_type = ? AND active = 1 ORDER BY time',
                     (reminder_type,))
        
        reminders = c.fetchall()
        conn.close()
        
        reminders_list = []
        for reminder in reminders:
            reminders_list.append({
                'id': reminder[0],
                'reminder': reminder[1],
                'reminder_type': reminder[2],
                'time': reminder[3],
                'date': reminder[4] if len(reminder) > 4 else None,
                'repeat': reminder[5] if len(reminder) > 5 else None,
                'active': reminder[6] if len(reminder) > 6 else 1,
                'recurring': reminder[8] if len(reminder) > 8 else 0
            })
        
        return jsonify(reminders_list)

@app.route('/api/calendar-events', methods=['GET', 'POST', 'PUT', 'DELETE'])
def calendar_events_api():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        c.execute('''INSERT INTO calendar_events (title, date, start_time, end_time, category, importance, description, created_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (data['title'], data['date'], data.get('start_time'), data.get('end_time'),
                   data['category'], data.get('importance', 'normal'), data.get('description', ''),
                   datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    elif request.method == 'PUT':
        data = request.json
        c.execute('''UPDATE calendar_events 
                     SET title = ?, date = ?, start_time = ?, end_time = ?, category = ?, importance = ?, description = ?
                     WHERE id = ?''',
                  (data['title'], data['date'], data.get('start_time'), data.get('end_time'),
                   data['category'], data.get('importance', 'normal'), data.get('description', ''), data['id']))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        event_id = request.args.get('id')
        c.execute('DELETE FROM calendar_events WHERE id = ?', (event_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    else:
        # GET events for a specific month or all
        month = request.args.get('month')
        year = request.args.get('year')
        
        if month and year:
            c.execute('SELECT * FROM calendar_events WHERE strftime("%Y-%m", date) = ? ORDER BY date, start_time',
                     (f"{year}-{month.zfill(2)}",))
        else:
            c.execute('SELECT * FROM calendar_events ORDER BY date, start_time')
        
        events = c.fetchall()
        conn.close()
        
        events_list = []
        for event in events:
            events_list.append({
                'id': event[0],
                'title': event[1],
                'date': event[2],
                'start_time': event[3],
                'end_time': event[4],
                'category': event[5],
                'importance': event[6],
                'description': event[7]
            })
        
        return jsonify(events_list)

@app.route('/api/month-data')
def month_data():
    year = request.args.get('year')
    month = request.args.get('month')
    if not year or not month:
        return jsonify({})

    month_str = f"{year}-{month.zfill(2)}"
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        '''SELECT date, SUM(points) FROM wins
           WHERE strftime('%Y-%m', date) = ?
           GROUP BY date''',
        (month_str,)
    )
    points_rows = c.fetchall()

    c.execute(
        '''SELECT date, goal_1_text, goal_1_complete, goal_2_text, goal_2_complete,
                  goal_3_text, goal_3_complete
           FROM daily_goals WHERE strftime('%Y-%m', date) = ?''',
        (month_str,)
    )
    goals_rows = c.fetchall()
    conn.close()

    goals_map = {}
    for row in goals_rows:
        goals_map[row[0]] = bool(row[1]) and bool(row[2]) and \
                             bool(row[3]) and bool(row[4]) and \
                             bool(row[5]) and bool(row[6])

    result = {}
    for date, pts in points_rows:
        result[date] = {'points': pts, 'goals_all_done': goals_map.get(date, False)}

    return jsonify(result)


@app.route('/api/pillar-scores', methods=['GET', 'POST'])
def pillar_scores_api():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'POST':
        data = request.json
        c.execute('''INSERT OR REPLACE INTO pillar_scores
                     (id, physical, work, health, relationships, mindset)
                     VALUES (1, ?, ?, ?, ?, ?)''',
                  (data.get('physical', 0), data.get('work', 0),
                   data.get('health', 0), data.get('relationships', 0),
                   data.get('mindset', 0)))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

    c.execute('SELECT physical, work, health, relationships, mindset FROM pillar_scores WHERE id = 1')
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({'physical': row[0], 'work': row[1], 'health': row[2],
                        'relationships': row[3], 'mindset': row[4]})
    return jsonify({'physical': 0, 'work': 0, 'health': 0, 'relationships': 0, 'mindset': 0})


@app.route('/api/health-metrics', methods=['GET', 'POST'])
def health_metrics_api():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'POST':
        data = request.json
        c.execute('''INSERT OR REPLACE INTO health_metrics
                     (id, weight_kg, height_cm, age, sex, exercise_intensity,
                      calorie_target, protein_target, carb_target, fat_target)
                     VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (data.get('weight_kg', 0), data.get('height_cm', 0),
                   data.get('age', 0), data.get('sex', 'male'),
                   data.get('exercise_intensity', 'sedentary'),
                   data.get('calorie_target', 0), data.get('protein_target', 0),
                   data.get('carb_target', 0), data.get('fat_target', 0)))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

    c.execute('SELECT * FROM health_metrics WHERE id = 1')
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({
            'weight_kg': row[1], 'height_cm': row[2], 'age': row[3],
            'sex': row[4], 'exercise_intensity': row[5],
            'calorie_target': row[6], 'protein_target': row[7],
            'carb_target': row[8], 'fat_target': row[9]
        })
    return jsonify({
        'weight_kg': 0, 'height_cm': 0, 'age': 0, 'sex': 'male',
        'exercise_intensity': 'sedentary',
        'calorie_target': 0, 'protein_target': 0, 'carb_target': 0, 'fat_target': 0
    })


@app.route('/api/food-log', methods=['GET', 'POST', 'DELETE'])
def food_log_api():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'POST':
        data = request.json
        entry_date = data['date']
        c.execute('''INSERT INTO food_log
                     (date, meal, food_name, calories, protein_g, carbs_g, fat_g, created_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (entry_date, data['meal'], data['food_name'],
                   data.get('calories', 0), data.get('protein_g', 0),
                   data.get('carbs_g', 0), data.get('fat_g', 0),
                   datetime.now().isoformat()))
        conn.commit()
        # Check if protein target is met for today
        c.execute('SELECT SUM(protein_g) FROM food_log WHERE date = ?', (entry_date,))
        total_protein = c.fetchone()[0] or 0
        c.execute('SELECT protein_target FROM health_metrics WHERE id = 1')
        m = c.fetchone()
        protein_target = m[0] if m else 0
        if protein_target > 0 and total_protein >= protein_target:
            c.execute("SELECT COUNT(*) FROM xp_log WHERE DATE(date) = ? AND reason LIKE 'Protein goal%'",
                     (entry_date,))
            if c.fetchone()[0] == 0:
                award_xp(c, int(protein_target), f'Protein goal met ({int(total_protein)}g)')
                conn.commit()
        conn.close()
        return jsonify({'success': True})

    if request.method == 'DELETE':
        entry_id = request.args.get('id')
        c.execute('DELETE FROM food_log WHERE id = ?', (entry_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    c.execute('SELECT * FROM food_log WHERE date = ? ORDER BY meal, created_at', (date,))
    rows = c.fetchall()
    conn.close()
    return jsonify([{
        'id': r[0], 'date': r[1], 'meal': r[2], 'food_name': r[3],
        'calories': r[4], 'protein_g': r[5], 'carbs_g': r[6], 'fat_g': r[7]
    } for r in rows])


@app.route('/api/activity-log', methods=['GET', 'POST', 'DELETE'])
def activity_log_api():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'POST':
        data = request.json
        c.execute('''INSERT INTO activity_log
                     (date, activity_type, duration_mins, intensity, calories_burned, created_at)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (data['date'], data['activity_type'], data.get('duration_mins', 0),
                   data.get('intensity', 'moderate'), data.get('calories_burned', 0),
                   datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

    if request.method == 'DELETE':
        entry_id = request.args.get('id')
        c.execute('DELETE FROM activity_log WHERE id = ?', (entry_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    c.execute('SELECT * FROM activity_log WHERE date = ? ORDER BY created_at', (date,))
    rows = c.fetchall()
    conn.close()
    return jsonify([{
        'id': r[0], 'date': r[1], 'activity_type': r[2],
        'duration_mins': r[3], 'intensity': r[4], 'calories_burned': r[5]
    } for r in rows])


@app.route('/api/weight-log', methods=['GET', 'POST', 'DELETE'])
def weight_log_api():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'POST':
        data = request.json
        c.execute('''INSERT OR REPLACE INTO weight_log (date, weight_kg, created_at)
                     VALUES (?, ?, ?)''',
                  (data['date'], data['weight_kg'], datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

    if request.method == 'DELETE':
        entry_id = request.args.get('id')
        c.execute('DELETE FROM weight_log WHERE id = ?', (entry_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

    c.execute('SELECT id, date, weight_kg FROM weight_log ORDER BY date ASC')
    rows = c.fetchall()
    conn.close()
    return jsonify([{'id': r[0], 'date': r[1], 'weight_kg': r[2]} for r in rows])


@app.route('/api/xp', methods=['GET'])
def xp_api():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT total_xp, streak_days FROM user_stats WHERE id = 1')
    row = c.fetchone()
    total_xp = row[0] if row else 0
    streak_days = row[1] if row else 0
    # Add current finance total balance as a starter XP boost
    c.execute('''SELECT COALESCE(SUM(CASE
        WHEN type='income'             THEN amount
        WHEN type='expense'            THEN -amount
        WHEN type='crypto_investment'  THEN amount
        WHEN type='crypto_withdrawal'  THEN -amount
        ELSE 0 END), 0) FROM finance''')
    balance = c.fetchone()[0] or 0
    conn.close()
    effective_xp = total_xp + max(0, int(balance))
    level, xp_in_level, xp_for_next = _compute_level(effective_xp)
    multiplier = 1.25 if streak_days >= 2 else 1.0
    return jsonify({
        'total_xp': effective_xp,
        'level': level,
        'xp_in_level': xp_in_level,
        'xp_for_next': xp_for_next,
        'streak_days': streak_days,
        'multiplier': multiplier
    })


@app.route('/api/xp/log', methods=['GET'])
def xp_log_api():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, date, change, reason FROM xp_log ORDER BY id DESC LIMIT 20')
    rows = c.fetchall()
    conn.close()
    return jsonify([{'id': r[0], 'date': r[1], 'change': r[2], 'reason': r[3]} for r in rows])


@app.route('/api/xp/complete-day', methods=['POST'])
def xp_complete_day():
    """Award +200 bonus XP and update streak when today is a win day."""
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('SELECT last_win_day, streak_days FROM user_stats WHERE id = 1')
    row = c.fetchone()
    last_win_day = row[0] if row else ''
    streak_days = row[1] if row else 0

    if last_win_day == today:
        conn.close()
        return jsonify({'success': True, 'already_counted': True})

    # Verify today actually qualifies
    c.execute('SELECT SUM(points) FROM wins WHERE date = ?', (today,))
    pts_row = c.fetchone()
    today_points = pts_row[0] if pts_row[0] else 0

    c.execute('''SELECT goal_1_text, goal_1_complete, goal_2_text, goal_2_complete,
                        goal_3_text, goal_3_complete
                 FROM daily_goals WHERE date = ?''', (today,))
    grow = c.fetchone()
    goals_done = bool(grow and grow[0] and grow[1] and grow[2] and grow[3] and grow[4] and grow[5])

    if today_points < 1000 or not goals_done:
        conn.close()
        return jsonify({'success': False, 'reason': 'conditions not met'})

    # Update streak
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    if last_win_day == yesterday:
        new_streak = streak_days + 1
    else:
        new_streak = 1

    c.execute('UPDATE user_stats SET last_win_day = ?, streak_days = ? WHERE id = 1',
              (today, new_streak))
    award_xp(c, 200, "Perfect day bonus (1000pts + all 3 goals)")
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'streak': new_streak})


@app.route('/api/xp/daily-check', methods=['POST'])
def xp_daily_check():
    """Apply streak penalty if yesterday was a missed day. Call once per app load."""
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    day_before = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('SELECT last_penalty_date, last_win_day, streak_days FROM user_stats WHERE id = 1')
    row = c.fetchone()
    last_penalty_date = row[0] if row else ''
    last_win_day = row[1] if row else ''
    streak_days = row[2] if row else 0

    # Only penalise once per day, and only if user has had at least one win day
    if last_penalty_date == today or not last_win_day:
        conn.close()
        return jsonify({'success': True, 'skipped': True})

    def day_was_win(date):
        c.execute('SELECT SUM(points) FROM wins WHERE date = ?', (date,))
        p = c.fetchone()[0] or 0
        c.execute('''SELECT goal_1_text, goal_1_complete, goal_2_text, goal_2_complete,
                            goal_3_text, goal_3_complete
                     FROM daily_goals WHERE date = ?''', (date,))
        g = c.fetchone()
        return p >= 1000 and bool(g and g[0] and g[1] and g[2] and g[3] and g[4] and g[5])

    c.execute('UPDATE user_stats SET last_penalty_date = ? WHERE id = 1', (today,))

    if not day_was_win(yesterday):
        # Missed yesterday
        if not day_was_win(day_before):
            # Two consecutive missed days → -1000 XP
            award_xp(c, -100, "Missed 2 consecutive days penalty")
        else:
            award_xp(c, -50, "Missed yesterday penalty")
        # Reset streak
        c.execute('UPDATE user_stats SET streak_days = 0 WHERE id = 1')

    conn.commit()
    conn.close()
    return jsonify({'success': True})


if __name__ == '__main__':
    app.run(debug=True, port=5001)
