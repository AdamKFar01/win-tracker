# Win Tracker App

A personal productivity tracker to help you reach daily goals across 5 categories: Physical, Mental, Health, Social, and Mood.

## Features
- **Dashboard**: Track daily wins across 5 categories with a 1000 point goal (200 per category)
- **Tasks**: Manage your to-do list with due dates
- **Finance**: Track income and expenses
- **Calendar**: View progress over time (coming soon)
- **Reminders**: Set up recurring reminders (coming soon)

## Setup Instructions

### 1. Install Python
Make sure you have Python 3.7+ installed. Check with:
```bash
python3 --version
```

### 2. Install Flask
```bash
pip3 install flask
```

### 3. Run the App
Navigate to the win-tracker folder and run:
```bash
cd win-tracker
python3 app.py
```

### 4. Open in Browser
The app will start at: http://localhost:5000

Open this URL in your web browser (Chrome, Safari, etc.)

## How to Use

### Logging Wins
1. Select a category (Physical, Mental, Health, Social, Mood)
2. Choose an activity from the dropdown (or add your own later)
3. Enter duration in minutes (optional)
4. Points are auto-suggested based on activity
5. Click "Add Win"

### Points System
- Each category has a goal of 200 points/day
- Total daily goal: 1000 points
- Activities have preset point values based on importance and typical duration
- You can adjust points based on actual time spent

### Tasks
- Add tasks with optional due dates
- Check off completed tasks
- Delete tasks you no longer need

### Finance Tracker
- Log income and expenses
- View total balance
- Track recent transactions

## Customization

### Adding More Activities
Edit the `activities` object in `/static/js/app.js` to add more preset activities with point values.

### Changing Point Goals
Currently set to 200 per category (1000 total). You can modify these in the HTML or add settings later.

### Styling
Edit `/static/css/style.css` to change colors, fonts, and layout.

## Data Storage
- All data is stored in `wintracker.db` (SQLite database)
- Database is created automatically on first run
- Located in the win-tracker folder
- Back up this file to preserve your data

## Development Mode
- The app runs with `debug=True` by default
- Changes to HTML/CSS/JS files: Just refresh the browser
- Changes to Python files: Restart the app (Ctrl+C, then run again)

## Future Features
- Calendar view with monthly/weekly breakdown
- Reminders with notifications
- Weekly/monthly reports
- Data export (CSV/PDF)
- Charts and graphs for progress tracking
- Custom activity creation from the UI
