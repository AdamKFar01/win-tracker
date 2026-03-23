from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import sqlite3
import json
import os

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wintracker.db')

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
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/sw.js')
def service_worker():
    response = app.send_static_file('js/sw.js')
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Service-Worker-Allowed'] = '/'
    return response

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
                'description': win[3],
                'points': win[4],
                'duration': win[5],
                'date': win[6],
                'timestamp': win[7]
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
        'mental': 0,
        'health': 0,
        'social': 0,
        'mood': 0,
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
    # Get data for the last 7 days
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    week_data = []
    for i in range(7):
        date = (datetime.now() - timedelta(days=6-i)).strftime('%Y-%m-%d')
        c.execute('SELECT SUM(points) FROM wins WHERE date = ?', (date,))
        result = c.fetchone()
        total = result[0] if result[0] else 0
        week_data.append({'date': date, 'points': total})
    
    conn.close()
    return jsonify(week_data)

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
        
        c.execute('''INSERT INTO tasks (task, task_type, period, due_date, created_at)
                     VALUES (?, ?, ?, ?, ?)''',
                  (data['task'], task_type, period, due_date, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    elif request.method == 'PUT':
        data = request.json
        c.execute('UPDATE tasks SET completed = ? WHERE id = ?',
                  (data['completed'], data['id']))
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
        
        if period == 'old':
            # Get expired tasks
            today = datetime.now().strftime('%Y-%m-%d')
            c.execute('''SELECT * FROM tasks 
                        WHERE task_type = ? AND due_date < ? 
                        ORDER BY due_date DESC''', (task_type, today))
        elif period == 'all':
            c.execute('SELECT * FROM tasks WHERE task_type = ? ORDER BY completed, due_date', (task_type,))
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
                'moved_to_old': task[7] if len(task) > 7 else 0
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

if __name__ == '__main__':
    app.run(debug=True, port=5001)
