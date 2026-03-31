// ── Theme toggle ────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('themeToggle');
    if (localStorage.getItem('theme') === 'light') {
        document.documentElement.classList.add('light-mode');
        themeToggle.textContent = '☽';
    }
    themeToggle.addEventListener('click', () => {
        const isLight = document.documentElement.classList.toggle('light-mode');
        localStorage.setItem('theme', isLight ? 'light' : 'dark');
        themeToggle.textContent = isLight ? '☽' : '☀';
        // Rebuild charts with new colour palette
        if (pillarsChartInstance) {
            pillarsChartInstance.destroy();
            pillarsChartInstance = null;
        }
        loadDailySummary();
        loadWeekChart();
    });
});

// Returns today's date as YYYY-MM-DD in local time (not UTC)
function getLocalDateString() {
    const d = new Date();
    return dateToLocalString(d);
}

function dateToLocalString(d) {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

// Activity presets with suggested points - now stored in database
let activities = {
    physical: [],
    work: [],
    health: [],
    relationships: [],
    mindset: []
};

// Default activities (will be added to DB if empty)
const defaultActivities = {
    physical: [
        { name: 'Gym session', points: 50 },
        { name: 'Football', points: 60 },
        { name: 'Volleyball', points: 50 },
        { name: 'Running', points: 40 },
        { name: 'Stretching', points: 20 },
        { name: 'Cycling', points: 40 },
        { name: 'Swimming', points: 60 }
    ],
    work: [
        { name: 'Studied well', points: 80 },
        { name: 'Focused work session', points: 70 },
        { name: 'Learned something new', points: 60 },
        { name: 'Read a book', points: 50 },
        { name: 'Completed a project task', points: 60 },
        { name: 'Attended a lecture', points: 40 }
    ],
    health: [
        { name: 'Good diet (no junk food)', points: 50 },
        { name: 'No Pepsi/soda', points: 30 },
        { name: 'Drank enough water', points: 20 },
        { name: 'Slept 8+ hours', points: 60 },
        { name: 'Took vitamins', points: 10 },
    ],
    relationships: [
        { name: 'Made new friends', points: 80 },
        { name: 'Went out with friends', points: 60 },
        { name: 'Had meaningful conversation', points: 50 },
        { name: 'Helped someone', points: 40 },
        { name: 'Attended social event', points: 70 }
    ],
    mindset: [
        { name: 'Cold shower', points: 30 },
        { name: 'Meditation', points: 40 },
        { name: 'Felt confident', points: 50 },
        { name: 'Felt motivated', points: 50 },
        { name: 'Felt grateful', points: 35 },
        { name: 'Felt productive', points: 45 },
        { name: 'Felt anxious', points: 10 },
        { name: 'Felt stressed', points: 10 }
    ]
};

// Load activities from database
async function loadActivitiesFromDatabase() {
    try {
        const response = await fetch('/api/activities');
        const dbActivities = await response.json();
        
        // If database is empty, populate with defaults
        if (dbActivities.length === 0) {
            await populateDefaultActivities();
            await loadActivitiesFromDatabase(); // Reload after populating
            return;
        }
        
        // Clear current activities
        activities = {
            physical: [],
            work: [],
            health: [],
            relationships: [],
            mindset: []
        };
        
        // Organize by category
        dbActivities.forEach(activity => {
            if (activities[activity.category]) {
                activities[activity.category].push({
                    id: activity.id,
                    name: activity.name,
                    points: activity.points
                });
            }
        });
    } catch (error) {
        console.error('Error loading activities:', error);
    }
}

// Populate database with default activities
async function populateDefaultActivities() {
    for (const category in defaultActivities) {
        for (const activity of defaultActivities[category]) {
            await fetch('/api/activities', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    category: category,
                    name: activity.name,
                    points: activity.points
                })
            });
        }
    }
}

// Activity Management
document.getElementById('manageCategory').addEventListener('change', (e) => {
    const category = e.target.value;
    const manager = document.getElementById('activityManager');
    
    if (category) {
        manager.style.display = 'block';
        displayActivitiesForCategory(category);
    } else {
        manager.style.display = 'none';
    }
});

function displayActivitiesForCategory(category) {
    const activitiesList = document.getElementById('activitiesList');
    activitiesList.innerHTML = '';
    
    if (!activities[category] || activities[category].length === 0) {
        activitiesList.innerHTML = '<p style="color: #8b92b0;">No activities yet.</p>';
        return;
    }
    
    activities[category].forEach((activity) => {
        const activityItem = document.createElement('div');
        activityItem.className = 'activity-item';
        activityItem.id = `activity-${activity.id}`;
        
        activityItem.innerHTML = `
            <div class="activity-item-info">
                <span class="activity-item-name">${activity.name}</span>
                <span class="activity-item-points">${activity.points} pts</span>
            </div>
            <div class="activity-item-actions">
                <button class="btn-edit" onclick="editActivity(${activity.id}, '${category}')">Edit</button>
                <button class="btn-delete-activity" onclick="deleteActivity(${activity.id}, '${category}')">Delete</button>
            </div>
        `;
        
        activitiesList.appendChild(activityItem);
    });
}

// Add new activity
document.getElementById('addActivityForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const category = document.getElementById('manageCategory').value;
    const name = document.getElementById('newActivityName').value;
    const points = parseInt(document.getElementById('newActivityPoints').value);
    
    try {
        const response = await fetch('/api/activities', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category, name, points })
        });
        
        if (response.ok) {
            await loadActivitiesFromDatabase();
            displayActivitiesForCategory(category);
            updateActivityDropdown(category);
            
            // Reset form
            document.getElementById('newActivityName').value = '';
            document.getElementById('newActivityPoints').value = '';
        }
    } catch (error) {
        console.error('Error adding activity:', error);
    }
});

async function editActivity(activityId, category) {
    const activity = activities[category].find(a => a.id === activityId);
    if (!activity) return;
    
    const newName = prompt('Edit activity name:', activity.name);
    if (newName === null) return; // User cancelled
    
    const newPoints = prompt('Edit points:', activity.points);
    if (newPoints === null) return; // User cancelled
    
    const pointsNum = parseInt(newPoints);
    if (isNaN(pointsNum) || pointsNum < 0) {
        alert('Please enter a valid number for points');
        return;
    }
    
    try {
        const response = await fetch('/api/activities', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: activityId, name: newName, points: pointsNum })
        });
        
        if (response.ok) {
            await loadActivitiesFromDatabase();
            displayActivitiesForCategory(category);
            updateActivityDropdown(category);
        }
    } catch (error) {
        console.error('Error editing activity:', error);
    }
}

async function deleteActivity(activityId, category) {
    if (!confirm('Are you sure you want to delete this activity?')) return;
    
    try {
        const response = await fetch(`/api/activities?id=${activityId}`, { method: 'DELETE' });
        
        if (response.ok) {
            await loadActivitiesFromDatabase();
            displayActivitiesForCategory(category);
            updateActivityDropdown(category);
        }
    } catch (error) {
        console.error('Error deleting activity:', error);
    }
}

function updateActivityDropdown(category) {
    const activitySelect = document.getElementById('activity');
    const currentCategory = document.getElementById('category').value;

    // Only update if we're viewing the same category
    if (currentCategory === category) {
        activitySelect.innerHTML = '<option value="">Select activity</option>';

        if (activities[category]) {
            activities[category].forEach(activity => {
                const option = document.createElement('option');
                option.value = activity.name;
                option.textContent = activity.name;
                option.dataset.points = activity.points;
                activitySelect.appendChild(option);
            });
        }
        const otherOpt = document.createElement('option');
        otherOpt.value = 'other';
        otherOpt.textContent = 'Other…';
        activitySelect.appendChild(otherOpt);
    }
}

// Tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        btn.classList.add('active');
        document.getElementById(btn.dataset.tab).classList.add('active');
    });
});

// Set current date
const dateInput = document.getElementById('currentDate');
dateInput.value = getLocalDateString();

// Date change listener
dateInput.addEventListener('change', () => {
    loadDailySummary();
    loadWins();
});

// Category change listener - populate activities
document.getElementById('category').addEventListener('change', (e) => {
    const category = e.target.value;
    const activitySelect = document.getElementById('activity');
    const categoryOther = document.getElementById('categoryOther');

    // Show/hide custom category text input
    if (category === 'other') {
        categoryOther.classList.add('visible');
        categoryOther.required = true;
    } else {
        categoryOther.classList.remove('visible');
        categoryOther.required = false;
        categoryOther.value = '';
    }

    activitySelect.innerHTML = '<option value="">Select activity</option>';

    if (category && category !== 'other' && activities[category]) {
        activities[category].forEach(activity => {
            const option = document.createElement('option');
            option.value = activity.name;
            option.textContent = activity.name;
            option.dataset.points = activity.points;
            activitySelect.appendChild(option);
        });
    }
    // Always append "Other" option at the bottom
    const otherOpt = document.createElement('option');
    otherOpt.value = 'other';
    otherOpt.textContent = 'Other…';
    activitySelect.appendChild(otherOpt);
});

// Activity change listener - suggest points / show custom input
document.getElementById('activity').addEventListener('change', (e) => {
    const selectedOption = e.target.options[e.target.selectedIndex];
    const activityOther = document.getElementById('activityOther');

    if (e.target.value === 'other') {
        activityOther.classList.add('visible');
        activityOther.required = true;
        document.getElementById('points').value = '';
    } else {
        activityOther.classList.remove('visible');
        activityOther.required = false;
        activityOther.value = '';
        const suggestedPoints = selectedOption.dataset.points;
        if (suggestedPoints) {
            document.getElementById('points').value = suggestedPoints;
        }
    }
});

// Win form submission
document.getElementById('winForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    let category = document.getElementById('category').value;
    let activity = document.getElementById('activity').value;
    const duration = document.getElementById('duration').value;
    const description = document.getElementById('description').value;
    const points = document.getElementById('points').value;
    const date = dateInput.value;

    // Resolve "Other" values
    if (category === 'other') {
        category = document.getElementById('categoryOther').value.trim();
        if (!category) return;
    }
    if (activity === 'other') {
        activity = document.getElementById('activityOther').value.trim();
        if (!activity) return;
    }
    
    try {
        const response = await fetch('/api/wins', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                category,
                activity,
                duration: duration || 0,
                description: description || '',
                points: parseInt(points),
                date
            })
        });
        
        if (response.ok) {
            document.getElementById('winForm').reset();
            loadDailySummary();
            loadWins();
        }
    } catch (error) {
        console.error('Error adding win:', error);
    }
});

// Load daily summary
async function loadDailySummary() {
    const date = dateInput.value;

    try {
        const response = await fetch(`/api/daily-summary?date=${date}`);
        const summary = await response.json();

        document.getElementById('physical-points').textContent = summary.physical;
        document.getElementById('work-points').textContent = summary.work;
        document.getElementById('health-points').textContent = summary.health;
        document.getElementById('relationships-points').textContent = summary.relationships;
        document.getElementById('mindset-points').textContent = summary.mindset;
        document.getElementById('total-points').textContent = summary.total;

        loadPillarsChart(summary);
    } catch (error) {
        console.error('Error loading summary:', error);
    }
}

// Personal Pillars radar chart
let pillarsChartInstance = null;
const pillarsLogoImg = new Image();
pillarsLogoImg.src = '/static/img/icon-b.png';

function loadPillarsChart(summary) {
    const ctx = document.getElementById('pillarsChart').getContext('2d');
    const data = [
        summary.physical    || 0,
        summary.work        || 0,
        summary.health      || 0,
        summary.relationships || 0,
        summary.mindset     || 0
    ];
    const overall = data.reduce((a, b) => a + b, 0);
    document.getElementById('overallGrowth').textContent = `Overall Growth: ${overall} / 1000`;

    const logoPlugin = {
        id: 'pillarsLogo',
        afterDraw(chart) {
            if (!pillarsLogoImg.complete) return;
            const { ctx: c } = chart;
            const cx = chart.scales.r.xCenter;
            const cy = chart.scales.r.yCenter;
            const size = 38;
            c.save();
            c.globalAlpha = 0.85;
            c.drawImage(pillarsLogoImg, cx - size / 2, cy - size / 2, size, size);
            c.restore();
        }
    };

    if (pillarsChartInstance) {
        pillarsChartInstance.data.datasets[0].data = data;
        pillarsChartInstance.update();
        return;
    }

    const isLight = document.documentElement.classList.contains('light-mode');
    const labelColor  = isLight ? '#7c3aed' : '#c084fc';
    const gridColor   = isLight ? 'rgba(124, 58, 237, 0.18)' : 'rgba(192, 132, 252, 0.2)';

    pillarsChartInstance = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['Physical', 'Work', 'Health', 'Relationships', ['Mindset', '& Discipline']],
            datasets: [{
                data,
                backgroundColor: 'rgba(192, 132, 252, 0.15)',
                borderColor: 'rgba(192, 132, 252, 0.8)',
                pointBackgroundColor: '#c084fc',
                pointBorderColor: '#c084fc',
                pointRadius: 4,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            scales: {
                r: {
                    min: 0,
                    max: 200,
                    ticks: {
                        display: false,
                        stepSize: 50
                    },
                    grid: { color: gridColor },
                    angleLines: { color: gridColor },
                    pointLabels: {
                        color: labelColor,
                        font: { family: 'Inter', size: 11 }
                    }
                }
            },
            plugins: {
                legend: { display: false }
            }
        },
        plugins: [logoPlugin]
    });
}

// Load wins list
async function loadWins() {
    const date = dateInput.value;

    // Update header to reflect selected date
    const header = document.getElementById('winsListHeader');
    if (date === getLocalDateString()) {
        header.textContent = "Today's Wins";
    } else {
        const d = new Date(date + 'T00:00:00');
        header.textContent = `Wins for ${d.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}`;
    }

    try {
        const response = await fetch(`/api/wins?date=${date}`);
        const wins = await response.json();
        
        const winsList = document.getElementById('winsList');
        winsList.innerHTML = '';
        
        if (wins.length === 0) {
            winsList.innerHTML = '<p style="color: #999;">No wins logged yet for this day.</p>';
            return;
        }
        
        wins.forEach(win => {
            const winItem = document.createElement('div');
            winItem.className = 'win-item';
            
            winItem.innerHTML = `
                <div class="win-item-info">
                    <div class="win-item-category">${win.category.toUpperCase()}</div>
                    <div>${win.activity}${win.duration ? ` (${win.duration} min)` : ''}</div>
                    ${win.description ? `<div class="win-item-description">${win.description}</div>` : ''}
                </div>
                <div class="win-item-points">+${win.points}</div>
                <button class="win-item-delete" onclick="deleteWin(${win.id})">Delete</button>
            `;
            
            winsList.appendChild(winItem);
        });
    } catch (error) {
        console.error('Error loading wins:', error);
    }
}

// Week chart
let weekChartInstance = null;
const barLogoImg = new Image();
barLogoImg.src = '/static/img/icon.png';

const barLogoPlugin = {
    id: 'barLogo',
    afterDatasetsDraw(chart) {
        if (!barLogoImg.complete) return;
        const { ctx, data } = chart;
        const dataset = chart.getDatasetMeta(0);
        const size = 22;
        dataset.data.forEach((bar, i) => {
            if (data.datasets[0].data[i] >= 1000) {
                ctx.save();
                ctx.globalAlpha = 0.85;
                ctx.drawImage(barLogoImg, bar.x - size / 2, bar.y - size - 4, size, size);
                ctx.restore();
            }
        });
    }
};

async function loadWeekChart() {
    try {
        const response = await fetch('/api/week-data');
        const data = await response.json();

        const labels = data.map(d => {
            const date = new Date(d.date + 'T00:00:00');
            return date.toLocaleDateString('en-GB', { weekday: 'short', month: 'short', day: 'numeric' });
        });
        const points = data.map(d => d.points);

        const ctx = document.getElementById('weekChart').getContext('2d');

        if (weekChartInstance) {
            weekChartInstance.destroy();
        }

        weekChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Points',
                    data: points,
                    backgroundColor: 'rgba(155, 89, 255, 0.6)',
                    borderColor: 'rgba(155, 89, 255, 1)',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 1000,
                        grid: { color: document.documentElement.classList.contains('light-mode') ? 'rgba(0,0,0,0.07)' : 'rgba(255,255,255,0.08)' },
                        ticks: { color: document.documentElement.classList.contains('light-mode') ? '#6b7280' : '#8b92b0' }
                    },
                    x: {
                        grid: { color: document.documentElement.classList.contains('light-mode') ? 'rgba(0,0,0,0.07)' : 'rgba(255,255,255,0.08)' },
                        ticks: { color: document.documentElement.classList.contains('light-mode') ? '#6b7280' : '#8b92b0' }
                    }
                }
            },
            plugins: [barLogoPlugin]
        });
    } catch (error) {
        console.error('Error loading week chart:', error);
    }
}

// Delete win function
async function deleteWin(id) {
    if (!confirm('Are you sure you want to delete this win?')) return;
    
    try {
        await fetch(`/api/wins?id=${id}`, { method: 'DELETE' });
        loadDailySummary();
        loadWins();
    } catch (error) {
        console.error('Error deleting win:', error);
    }
}

// Toggle collapsible sections
function toggleSection(sectionId) {
    const section = document.getElementById(sectionId);
    const btn = section.previousElementSibling.querySelector('.collapse-btn');
    
    if (section.classList.contains('collapsed')) {
        section.classList.remove('collapsed');
        btn.classList.remove('collapsed');
    } else {
        section.classList.add('collapsed');
        btn.classList.add('collapsed');
    }
}

// Task management functions
const taskPeriods = ['today', 'weekly', 'monthly'];
const goalPeriods = ['weekly', 'monthly', 'yearly', 'lifelong'];

// Setup all task forms
function setupTaskForms() {
    // Today's tasks
    document.getElementById('todayTaskForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await addTask(e.target.querySelector('.task-input').value, 'task', 'today');
        e.target.reset();
    });

    // Weekly tasks
    document.getElementById('weeklyTaskForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await addTask(e.target.querySelector('.task-input').value, 'task', 'weekly');
        e.target.reset();
    });

    // Monthly tasks
    document.getElementById('monthlyTaskForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await addTask(e.target.querySelector('.task-input').value, 'task', 'monthly');
        e.target.reset();
    });

    // Weekly goals
    document.getElementById('weeklyGoalForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await addTask(e.target.querySelector('.task-input').value, 'goal', 'weekly');
        e.target.reset();
    });

    // Monthly goals
    document.getElementById('monthlyGoalForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await addTask(e.target.querySelector('.task-input').value, 'goal', 'monthly');
        e.target.reset();
    });

    // Yearly goals
    document.getElementById('yearlyGoalForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await addTask(e.target.querySelector('.task-input').value, 'goal', 'yearly');
        e.target.reset();
    });

    // Lifelong goals
    document.getElementById('lifelongGoalForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await addTask(e.target.querySelector('.task-input').value, 'goal', 'lifelong');
        e.target.reset();
    });
}

async function addTask(task, taskType, period) {
    try {
        const response = await fetch('/api/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task, task_type: taskType, period })
        });
        
        if (response.ok) {
            loadAllTasks();
        }
    } catch (error) {
        console.error('Error adding task:', error);
    }
}

async function loadAllTasks() {
    // Load all task periods
    await loadTasksByPeriod('today', 'todayTasksList', 'task');
    await loadTasksByPeriod('weekly', 'weeklyTasksList', 'task');
    await loadTasksByPeriod('monthly', 'monthlyTasksList', 'task');
    await loadTasksByPeriod('old', 'oldTasksList', 'task');
    
    // Load all goal periods
    await loadTasksByPeriod('weekly', 'weeklyGoalsList', 'goal');
    await loadTasksByPeriod('monthly', 'monthlyGoalsList', 'goal');
    await loadTasksByPeriod('yearly', 'yearlyGoalsList', 'goal');
    await loadTasksByPeriod('lifelong', 'lifelongGoalsList', 'goal');
}

async function loadTasksByPeriod(period, listId, taskType) {
    try {
        const response = await fetch(`/api/tasks?type=${taskType}&period=${period}`);
        const tasks = await response.json();
        
        const tasksList = document.getElementById(listId);
        tasksList.innerHTML = '';
        
        if (tasks.length === 0) {
            tasksList.innerHTML = '<p style="color: #8b92b0; text-align: center; padding: 20px;">No items yet.</p>';
            return;
        }
        
        tasks.forEach(task => {
            const taskItem = document.createElement('div');
            taskItem.className = `task-item ${task.completed ? 'completed' : ''}`;
            
            const isOld = period === 'old';

            taskItem.innerHTML = `
                <input type="checkbox" ${task.completed ? 'checked' : ''}
                       onchange="toggleTask(${task.id}, this.checked)">
                <div class="task-item-text">${task.task}</div>
                ${task.due_date && !isOld ? `<div class="task-item-date">Due: ${task.due_date}</div>` : ''}
                ${isOld ? `<div class="task-item-date">Expired: ${task.due_date}</div>` : ''}
                <button class="task-item-delete" onclick="deleteTask(${task.id})">Delete</button>
            `;
            
            tasksList.appendChild(taskItem);
        });
    } catch (error) {
        console.error('Error loading tasks:', error);
    }
}

async function toggleTask(id, completed) {
    try {
        await fetch('/api/tasks', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id, completed: completed ? 1 : 0 })
        });
        loadAllTasks();
    } catch (error) {
        console.error('Error updating task:', error);
    }
}

async function deleteTask(id) {
    if (!confirm('Are you sure you want to delete this item?')) return;
    
    try {
        await fetch(`/api/tasks?id=${id}`, { method: 'DELETE' });
        loadAllTasks();
    } catch (error) {
        console.error('Error deleting task:', error);
    }
}

// Finance functionality
document.getElementById('financeForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const type = document.getElementById('financeType').value;
    const amount = parseFloat(document.getElementById('financeAmount').value);
    const category = document.getElementById('financeCategory').value;
    const description = document.getElementById('financeDescription').value;
    const date = document.getElementById('financeDate').value;
    
    try {
        const response = await fetch('/api/finance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type, amount, category, description, date })
        });
        
        if (response.ok) {
            document.getElementById('financeForm').reset();
            document.getElementById('financeDate').value = getLocalDateString();
            loadFinance();
        }
    } catch (error) {
        console.error('Error adding finance:', error);
    }
});

async function loadFinance() {
    try {
        const response = await fetch('/api/finance');
        const records = await response.json();
        
        let totalIncome = 0;
        let totalExpense = 0;
        
        records.forEach(record => {
            if (record.type === 'income') {
                totalIncome += record.amount;
            } else {
                totalExpense += record.amount;
            }
        });
        
        document.getElementById('totalIncome').textContent = `£${totalIncome.toFixed(2)}`;
        document.getElementById('totalExpense').textContent = `£${totalExpense.toFixed(2)}`;
        document.getElementById('balance').textContent = `£${(totalIncome - totalExpense).toFixed(2)}`;
        
        const financeList = document.getElementById('financeList');
        financeList.innerHTML = '';
        
        if (records.length === 0) {
            financeList.innerHTML = '<p style="color: #999;">No transactions yet.</p>';
            return;
        }
        
        records.slice(0, 10).forEach(record => {
            const financeItem = document.createElement('div');
            financeItem.className = `finance-item ${record.type}`;
            
            financeItem.innerHTML = `
                <div class="finance-item-info">
                    <div class="finance-item-category">${record.category || record.type}</div>
                    <div class="finance-item-description">${record.description || ''}</div>
                    <div class="finance-item-date">${record.date}</div>
                </div>
                <div class="finance-item-amount ${record.type}">
                    ${record.type === 'income' ? '+' : '-'}£${record.amount.toFixed(2)}
                </div>
            `;
            
            financeList.appendChild(financeItem);
        });
    } catch (error) {
        console.error('Error loading finance:', error);
    }
}

// Initialize finance date
document.getElementById('financeDate').value = getLocalDateString();

// Calendar functionality
let currentCalendarDate = new Date();
let selectedDate = new Date();
let calendarEvents = [];
let monthPointsData = {};

async function loadMonthData(year, month) {
    try {
        const response = await fetch(`/api/month-data?year=${year}&month=${month + 1}`);
        monthPointsData = await response.json();
    } catch (error) {
        console.error('Error loading month data:', error);
        monthPointsData = {};
    }
}

async function renderCalendar() {
    const year = currentCalendarDate.getFullYear();
    const month = currentCalendarDate.getMonth();
    await loadMonthData(year, month);
    
    // Update header
    const monthNames = ["January", "February", "March", "April", "May", "June",
                        "July", "August", "September", "October", "November", "December"];
    document.getElementById('currentMonth').textContent = `${monthNames[month]} ${year}`;
    
    // Get first day of month and number of days
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startingDayOfWeek = firstDay.getDay();
    
    // Adjust for Monday start (0 = Monday, 6 = Sunday)
    const adjustedStart = startingDayOfWeek === 0 ? 6 : startingDayOfWeek - 1;
    
    // Get previous month days
    const prevMonthLastDay = new Date(year, month, 0).getDate();
    
    const calendarDays = document.getElementById('calendarDays');
    calendarDays.innerHTML = '';
    
    // Previous month days
    for (let i = adjustedStart - 1; i >= 0; i--) {
        const day = prevMonthLastDay - i;
        const dayDiv = createDayElement(day, true, new Date(year, month - 1, day));
        calendarDays.appendChild(dayDiv);
    }
    
    // Current month days
    for (let day = 1; day <= daysInMonth; day++) {
        const date = new Date(year, month, day);
        const dayDiv = createDayElement(day, false, date);
        calendarDays.appendChild(dayDiv);
    }
    
    // Next month days
    const totalCells = calendarDays.children.length;
    const remainingCells = 42 - totalCells; // 6 rows * 7 days
    for (let day = 1; day <= remainingCells; day++) {
        const date = new Date(year, month + 1, day);
        const dayDiv = createDayElement(day, true, date);
        calendarDays.appendChild(dayDiv);
    }
}

function createDayElement(day, otherMonth, date) {
    const dayDiv = document.createElement('div');
    dayDiv.className = 'calendar-day';
    
    if (otherMonth) {
        dayDiv.classList.add('other-month');
    }
    
    // Check if today
    const today = new Date();
    if (date.toDateString() === today.toDateString()) {
        dayDiv.classList.add('today');
    }
    
    // Check if selected
    if (date.toDateString() === selectedDate.toDateString()) {
        dayDiv.classList.add('selected');
    }
    
    const dayNumber = document.createElement('div');
    dayNumber.className = 'day-number';
    dayNumber.textContent = day;
    dayDiv.appendChild(dayNumber);
    
    // Add events for this day
    const dateStr = dateToLocalString(date);
    const dayEvents = calendarEvents.filter(e => e.date === dateStr);
    
    if (dayEvents.length > 0) {
        const eventsContainer = document.createElement('div');
        eventsContainer.className = 'day-events';
        
        dayEvents.slice(0, 3).forEach(event => {
            const miniEvent = document.createElement('div');
            miniEvent.className = `mini-event importance-${event.importance}`;
            miniEvent.textContent = event.title;
            eventsContainer.appendChild(miniEvent);
        });
        
        if (dayEvents.length > 3) {
            const moreIndicator = document.createElement('div');
            moreIndicator.className = 'mini-event';
            moreIndicator.textContent = `+${dayEvents.length - 3} more`;
            eventsContainer.appendChild(moreIndicator);
        }
        
        dayDiv.appendChild(eventsContainer);
    }
    
    // Show logo badge if this past/current day reached 1000 points
    const isPastOrToday = date <= today;
    if (isPastOrToday && !otherMonth && monthPointsData[dateToLocalString(date)] >= 1000) {
        const badge = document.createElement('img');
        badge.src = '/static/img/icon.png';
        badge.className = 'day-logo-badge';
        badge.alt = '';
        dayDiv.appendChild(badge);
    }

    dayDiv.onclick = () => selectDate(date);

    return dayDiv;
}

async function selectDate(date) {
    selectedDate = new Date(date);
    await renderCalendar();
    loadEventsForSelectedDate();
    
    const dateStr = selectedDate.toLocaleDateString('en-US', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    });
    document.getElementById('selectedDate').textContent = dateStr;
}

async function previousMonth() {
    currentCalendarDate.setMonth(currentCalendarDate.getMonth() - 1);
    await renderCalendar();
}

async function nextMonth() {
    currentCalendarDate.setMonth(currentCalendarDate.getMonth() + 1);
    await renderCalendar();
}

async function goToToday() {
    currentCalendarDate = new Date();
    selectedDate = new Date();
    await renderCalendar();
    loadEventsForSelectedDate();
}

// Calendar event form
document.getElementById('calendarEventForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const title = document.getElementById('eventTitle').value;
    const date = document.getElementById('eventDate').value;
    const startTime = document.getElementById('eventStartTime').value;
    const endTime = document.getElementById('eventEndTime').value;
    const category = document.getElementById('eventCategory').value;
    const importance = document.getElementById('eventImportance').value;
    const description = document.getElementById('eventDescription').value;
    
    try {
        const response = await fetch('/api/calendar-events', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title, date, start_time: startTime, end_time: endTime,
                category, importance, description
            })
        });
        
        if (response.ok) {
            e.target.reset();
            // Set default date to today
            document.getElementById('eventDate').value = getLocalDateString();
            await loadCalendarEvents();
            await renderCalendar();
            loadEventsForSelectedDate();
        }
    } catch (error) {
        console.error('Error adding calendar event:', error);
    }
});

document.getElementById('eventDate').value = getLocalDateString();

async function loadCalendarEvents() {
    try {
        const response = await fetch('/api/calendar-events');
        calendarEvents = await response.json();
    } catch (error) {
        console.error('Error loading calendar events:', error);
    }
}

function loadEventsForSelectedDate() {
    const dateStr = dateToLocalString(selectedDate);
    const dayEvents = calendarEvents.filter(e => e.date === dateStr);
    
    const eventsList = document.getElementById('dayEventsList');
    eventsList.innerHTML = '';
    
    if (dayEvents.length === 0) {
        eventsList.innerHTML = '<p style="color: #8b92b0; text-align: center; padding: 20px;">No events for this day.</p>';
        return;
    }
    
    // Sort by time
    dayEvents.sort((a, b) => {
        if (!a.start_time) return 1;
        if (!b.start_time) return -1;
        return a.start_time.localeCompare(b.start_time);
    });
    
    dayEvents.forEach(event => {
        const eventDiv = document.createElement('div');
        eventDiv.className = `calendar-event-item importance-${event.importance}`;
        
        const timeStr = event.start_time
            ? `${event.start_time}${event.end_time ? ' - ' + event.end_time : ''}`
            : 'All day';
        
        eventDiv.innerHTML = `
            <div class="event-header">
                <div>
                    <div class="event-title">${event.title}</div>
                    <div class="event-time">${timeStr}</div>
                </div>
            </div>
            <div class="event-details">
                <span class="event-badge category">${event.category.toUpperCase()}</span>
                <span class="event-badge importance">${event.importance.toUpperCase()}</span>
            </div>
            ${event.description ? `<div class="event-description">${event.description}</div>` : ''}
            <div class="event-actions">
                <button class="btn-delete-event" onclick="deleteCalendarEvent(${event.id})">Delete</button>
            </div>
        `;
        
        eventsList.appendChild(eventDiv);
    });
}

async function deleteCalendarEvent(id) {
    if (!confirm('Are you sure you want to delete this event?')) return;

    try {
        await fetch(`/api/calendar-events?id=${id}`, { method: 'DELETE' });
        await loadCalendarEvents();
        await renderCalendar();
        loadEventsForSelectedDate();
    } catch (error) {
        console.error('Error deleting event:', error);
    }
}

// Reminders functionality
function setupReminderForms() {
    // Daily reminders
    document.getElementById('dailyReminderForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const reminder = e.target.querySelector('.task-input').value;
        const time = document.getElementById('reminderTime').value;
        await addReminder(reminder, 'daily', time);
        e.target.reset();
    });

    // One-time reminders
    document.getElementById('onetimeReminderForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const reminder = e.target.querySelector('.task-input').value;
        const date = document.getElementById('reminderDate').value;
        const time = document.getElementById('reminderTimeOnce').value;
        await addReminder(reminder, 'onetime', time, date);
        e.target.reset();
    });

    // Recurring reminders
    document.getElementById('recurringReminderForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const reminder = e.target.querySelector('.task-input').value;
        const type = document.getElementById('recurringType').value;
        const time = document.getElementById('reminderTimeRecurring').value;
        await addReminder(reminder, type, time, null, 1);
        e.target.reset();
    });
}

async function addReminder(reminder, reminderType, time, date = null, recurring = 0) {
    try {
        const response = await fetch('/api/reminders', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reminder, reminder_type: reminderType, time, date, recurring })
        });
        
        if (response.ok) {
            loadAllReminders();
        }
    } catch (error) {
        console.error('Error adding reminder:', error);
    }
}

async function loadAllReminders() {
    await loadRemindersByType('daily', 'dailyRemindersList');
    await loadRemindersByType('onetime', 'onetimeRemindersList');
    // Clear recurring list once before the multiple type calls
    document.getElementById('recurringRemindersList').innerHTML = '';
    await loadRemindersByType('daily', 'recurringRemindersList', true);
    await loadRemindersByType('weekly', 'recurringRemindersList', true);
    await loadRemindersByType('monthly', 'recurringRemindersList', true);
    // Show empty message if nothing was added
    const recurringList = document.getElementById('recurringRemindersList');
    if (recurringList.children.length === 0) {
        recurringList.innerHTML = '<p style="color: #8b92b0; text-align: center; padding: 20px;">No reminders yet.</p>';
    }
}

async function loadRemindersByType(type, listId, recurring = false) {
    try {
        const response = await fetch(`/api/reminders?type=${type}`);
        const reminders = await response.json();
        
        const remindersList = document.getElementById(listId);
        
        // For recurring, we append; for others, we replace
        if (!recurring) {
            remindersList.innerHTML = '';
        }
        
        const filteredReminders = recurring 
            ? reminders.filter(r => r.recurring === 1)
            : reminders.filter(r => r.recurring === 0 || !r.recurring);
        
        if (filteredReminders.length === 0 && !recurring) {
            remindersList.innerHTML = '<p style="color: #8b92b0; text-align: center; padding: 20px;">No reminders yet.</p>';
            return;
        }
        
        filteredReminders.forEach(reminder => {
            const reminderItem = document.createElement('div');
            reminderItem.className = 'task-item';
            
            const timeStr = reminder.time ? ` at ${reminder.time}` : '';
            const dateStr = reminder.date ? ` on ${reminder.date}` : '';
            const typeLabel = reminder.recurring ? reminder.reminder_type : '';
            
            reminderItem.innerHTML = `
                <input type="checkbox" ${!reminder.active ? 'checked' : ''} 
                       onchange="toggleReminder(${reminder.id}, this.checked)">
                <div class="task-item-text">${typeLabel} ${reminder.reminder}${timeStr}${dateStr}</div>
                <button class="task-item-delete" onclick="deleteReminder(${reminder.id})">Delete</button>
            `;
            
            remindersList.appendChild(reminderItem);
        });
    } catch (error) {
        console.error('Error loading reminders:', error);
    }
}

async function toggleReminder(id, checked) {
    try {
        await fetch('/api/reminders', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id, active: checked ? 0 : 1 })
        });
        loadAllReminders();
    } catch (error) {
        console.error('Error updating reminder:', error);
    }
}

async function deleteReminder(id) {
    if (!confirm('Are you sure you want to delete this reminder?')) return;
    
    try {
        await fetch(`/api/reminders?id=${id}`, { method: 'DELETE' });
        loadAllReminders();
    } catch (error) {
        console.error('Error deleting reminder:', error);
    }
}

// Load initial data
async function initializeApp() {
    await loadActivitiesFromDatabase();
    await loadCalendarEvents();
    await renderCalendar();
    loadEventsForSelectedDate();
    loadDailySummary();
    loadWins();
    loadWeekChart();
    setupTaskForms();
    loadAllTasks();
    loadFinance();
    setupReminderForms();
    loadAllReminders();
}

initializeApp();

