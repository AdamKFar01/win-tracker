import sqlite3
import os
import sys

# This script updates your database to the latest schema
# Run this ONCE before starting the app with the new version

db_path = 'wintracker.db'

if not os.path.exists(db_path):
    print("❌ Error: wintracker.db not found!")
    print("Make sure you're running this in the win-tracker folder")
    sys.exit(1)

conn = sqlite3.connect(db_path)
c = conn.cursor()

print("🔄 Starting database migration...")
print()

# Function to check if column exists
def column_exists(table, column):
    c.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in c.fetchall()]
    return column in columns

# Function to check if table exists
def table_exists(table):
    c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
    return c.fetchone() is not None

# 1. Update wins table
print("📝 Checking wins table...")
if not column_exists('wins', 'description'):
    try:
        c.execute("ALTER TABLE wins ADD COLUMN description TEXT DEFAULT ''")
        conn.commit()
        print("   ✅ Added 'description' column to wins")
    except Exception as e:
        print(f"   ⚠️  Warning: {e}")
else:
    print("   ✅ Wins table already has description column")

# 2. Update tasks table
print("📝 Checking tasks table...")
if not column_exists('tasks', 'task_type'):
    try:
        c.execute("ALTER TABLE tasks ADD COLUMN task_type TEXT DEFAULT 'task'")
        conn.commit()
        print("   ✅ Added 'task_type' column")
    except Exception as e:
        print(f"   ⚠️  Warning: {e}")
else:
    print("   ✅ Tasks table already has task_type")

if not column_exists('tasks', 'period'):
    try:
        c.execute("ALTER TABLE tasks ADD COLUMN period TEXT DEFAULT 'today'")
        conn.commit()
        print("   ✅ Added 'period' column")
    except Exception as e:
        print(f"   ⚠️  Warning: {e}")
else:
    print("   ✅ Tasks table already has period")

if not column_exists('tasks', 'moved_to_old'):
    try:
        c.execute("ALTER TABLE tasks ADD COLUMN moved_to_old INTEGER DEFAULT 0")
        conn.commit()
        print("   ✅ Added 'moved_to_old' column")
    except Exception as e:
        print(f"   ⚠️  Warning: {e}")
else:
    print("   ✅ Tasks table already has moved_to_old")

# 3. Create activities table
print("📝 Checking activities table...")
if not table_exists('activities'):
    try:
        c.execute('''CREATE TABLE activities
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      category TEXT NOT NULL,
                      name TEXT NOT NULL,
                      points INTEGER NOT NULL)''')
        conn.commit()
        print("   ✅ Created activities table")
    except Exception as e:
        print(f"   ⚠️  Warning: {e}")
else:
    print("   ✅ Activities table exists")

# 4. Create calendar_events table
print("📝 Checking calendar_events table...")
if not table_exists('calendar_events'):
    try:
        c.execute('''CREATE TABLE calendar_events
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
        print("   ✅ Created calendar_events table")
    except Exception as e:
        print(f"   ⚠️  Warning: {e}")
else:
    print("   ✅ Calendar_events table exists")

# 5. Check reminders table
print("📝 Checking reminders table...")
if table_exists('reminders'):
    if not column_exists('reminders', 'reminder_type'):
        print("   ⚠️  Reminders table needs restructuring")
        print("   📝 Creating new reminders table...")
        try:
            c.execute("DROP TABLE IF EXISTS reminders_old")
            c.execute("ALTER TABLE reminders RENAME TO reminders_old")
            c.execute('''CREATE TABLE reminders
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          reminder TEXT NOT NULL,
                          reminder_type TEXT DEFAULT 'daily',
                          time TEXT,
                          date TEXT,
                          repeat TEXT,
                          active INTEGER DEFAULT 1,
                          created_at TEXT NOT NULL)''')
            # Try to migrate old data if possible
            try:
                c.execute('''INSERT INTO reminders (reminder, time, repeat, active, created_at)
                             SELECT reminder, time, repeat, active, created_at FROM reminders_old''')
                c.execute("DROP TABLE reminders_old")
                print("   ✅ Migrated old reminder data")
            except:
                print("   ⚠️  Could not migrate old reminders (table structure too different)")
            conn.commit()
            print("   ✅ Reminders table updated")
        except Exception as e:
            print(f"   ⚠️  Warning: {e}")
    else:
        # Check for recurring column (added in later version)
        if not column_exists('reminders', 'recurring'):
            try:
                c.execute("ALTER TABLE reminders ADD COLUMN recurring INTEGER DEFAULT 0")
                conn.commit()
                print("   ✅ Added 'recurring' column to reminders")
            except Exception as e:
                print(f"   ⚠️  Warning: {e}")
        else:
            print("   ✅ Reminders table is up to date")
else:
    c.execute('''CREATE TABLE reminders
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  reminder TEXT NOT NULL,
                  reminder_type TEXT DEFAULT 'daily',
                  time TEXT,
                  date TEXT,
                  repeat TEXT,
                  active INTEGER DEFAULT 1,
                  created_at TEXT NOT NULL)''')
    conn.commit()
    print("   ✅ Created reminders table")

conn.close()

print()
print("=" * 50)
print("✅ DATABASE MIGRATION COMPLETE!")
print("=" * 50)
print()
print("Your database is now up to date.")
print("You can start the app with: ./start.sh")
print()

