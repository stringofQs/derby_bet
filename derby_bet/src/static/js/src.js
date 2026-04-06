document.addEventListener("DOMContentLoaded", () => {
    console.log('src.js file loaded successfully.');
    setInterval(fetchDashboardData, 5000);  // Sets dashboard refresh rate at 5 seconds
    fetchDashboardData();  // Initialize
})

async function fetchDashboardData() {
    try {
        const response = await fetch('/api/dashboard-data');
        dashData = await response.json();
        if (dashData._success) {
            updateDashboard(dashData);
        } else {
            console.error('Backend error fetching dashboard data: ', dashData._message)
        }
    } catch (error) {
        console.error('Frontend error fetching dashboard data: ', error)
    }
}

function updateDashboard(dashboardData) {
    if (!dashboardData) return;

    updatePlayersPanel(dashboardData.players);
    updateCurrentRacePanel(dashboardData.current_race_pool);
    updatePreviousRacePanel(dashboardData.previous_race);
}

function updatePlayersPanel(players) {
    console.log('updatePlayersPanel()')
    console.log(players);
    const panel = document.getElementById('players-panel');
    return;
}

function updateCurrentRacePanel(currentRacePool) {
    console.log('updateCurrentRacePanel()');
    console.log(currentRacePool);
    const panel = document.getElementById('current-race-panel');
    return;
}

function updatePreviousRacePanel(previousRace) {
    console.log('updatePreviousRacePanel()');
    console.log(previousRace);
    const panel = document.getElementById('previous-race-panel');
    return;
}

