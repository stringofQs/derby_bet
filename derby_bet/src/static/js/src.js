document.addEventListener("DOMContentLoaded", () => {
    console.log('src.js file loaded successfully.');
    setInterval(fetchDashboardData, 5000);  // Sets dashboard refresh rate at 5 seconds
    fetchDashboardData();  // Initialize
})

function createTd(content) {
    let td = document.createElement('td');
    td.appendChild(document.createTextNode(content));
    return td;
}

function createTh(content) {
    let th = document.createElement('th');
    th.appendChild(document.createTextNode(content));
    return th
}

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
    panel.innerHTML = '';
    let table = document.createElement('table');
    let headerTr = document.createElement('tr');
    headerTr.appendChild(createTh('Player Name'));
    headerTr.appendChild(createTh('Available Bids'));
    table.appendChild(headerTr);

    players.forEach(plyr => {
        const tr = document.createElement('tr');
        tr.appendChild(createTd(plyr['player_name']));
        tr.appendChild(createTd(plyr['bids']['available']))
        table.appendChild(tr);        
    });

    panel.appendChild(table);
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

