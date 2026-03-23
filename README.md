# 🏆 Win Tracker

A personal productivity tracker that helps you build better habits by scoring your daily wins across five life categories. Hit 200 points per category and reach your 1000-point daily goal.

---

## Features

- **Dashboard** — Log daily wins with points, duration, and notes. See your score per category and track the week with a bar chart.
- **Tasks** — Manage to-do lists split into Today, Weekly, and Monthly. Expired tasks move to an Old Tasks archive.
- **Goals** — Separate goal tracker for Weekly, Monthly, Yearly, and Lifelong goals.
- **Calendar** — Add and view events by date with categories (University, Work, Health, etc.) and priority levels.
- **Reminders** — Set Daily, One-Time, or Recurring (weekly/monthly) reminders with times.
- **Finance** — Track income and expenses, view running balance, and browse recent transactions.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3 + Flask |
| Database | SQLite (local file) |
| Frontend | Vanilla JavaScript, HTML5, CSS3 |
| Charts | Chart.js |
| Font | Orbitron (Google Fonts) |

No external database or cloud service required — everything runs locally.

---

## Installation

### Prerequisites

- Python 3.7 or higher
- pip

### Steps

**1. Clone the repository**

```bash
git clone https://github.com/AdamKFar01/win-tracker.git
cd win-tracker
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

**3. Run the app**

```bash
./start.sh
```

Or directly:

```bash
python3 app.py
```

**4. Open in your browser**

```
http://localhost:5000
```

The SQLite database (`wintracker.db`) is created automatically on first run.

---

## Usage

### Logging a Win

1. Select a date (defaults to today)
2. Pick a category — Physical, Mental, Health, Social, or Mood
3. Choose an activity from the dropdown
4. Points are auto-filled based on the activity
5. Click **Add Win**

### Managing Activities

In the Dashboard, scroll to **Manage Activities** to add, edit, or delete preset activities and their point values for each category.

### Points System

| Category | Daily Goal |
|---|---|
| 💪 Physical | 200 pts |
| ⛩️ Mental | 200 pts |
| 🥩 Health | 200 pts |
| 🃏 Social | 200 pts |
| ☯️ Mood | 200 pts |
| **Total** | **1000 pts** |

---

## Data

All data is stored locally in `wintracker.db` (SQLite). This file is excluded from git — back it up manually if needed.

To migrate an existing database to the latest schema:

```bash
python3 migrate_database.py
```

---

## Development

- Changes to HTML/CSS/JS take effect on browser refresh
- Changes to `app.py` require restarting the server (`Ctrl+C` then run again)
- Flask runs in debug mode by default on port 5000
