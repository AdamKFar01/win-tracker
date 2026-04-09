# WinnersTrack

A personal productivity and life tracker. Runs locally — no cloud, no accounts.

## Stack

- Python 3 + Flask, SQLite, Vanilla JS/HTML/CSS, Chart.js

## Run

```bash
./start.sh
# → http://localhost:5000
```

Or: `python3 app.py`

## Tabs

- **Dashboard** — Log daily wins by category (Physical, Work, Health, Relationships, Mindset). XP system, weekly bar chart, per-pillar trend chart.
- **Health** — Food log (breakfast, lunch, dinner, snacks), body metrics, daily weight tracking, weekly nutrition chart.
- **Tasks** — Today / Weekly / Monthly tasks with XP on completion.
- **Goals** — Weekly, Monthly, Yearly, Lifelong goals + Mastered Recipes.
- **Calendar** — Events by date with category and priority.
- **Reminders** — One-time, daily, or recurring reminders with urgency alerts.
- **Finance** — Income/expense tracker with running balance.

## Data

All data is stored in `wintracker.db` (SQLite, local). Excluded from git — back it up manually.

To update an existing database schema:

```bash
python3 migrate_database.py
```
