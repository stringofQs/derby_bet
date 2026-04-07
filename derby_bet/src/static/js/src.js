document.addEventListener("DOMContentLoaded", () => {
    console.log('src.js file loaded successfully.');
    setInterval(fetchDashboardData, 5000);  // Sets dashboard refresh rate at 5 seconds
    fetchDashboardData();  // Initialize
})

function createElem(tag, className = '', textContent = '') {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (textContent) element.textContent = textContent;
    return element
}

function clearElement(element) {
    while (element.firstChild) {
        element.removeChild(element.firstChild);
    }
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
    updateCurrentRacePanel(dashboardData.current_race);
    updateCurrentRacePoolPanel(dashboardData.current_race_pool);
    updatePreviousRacePanel(dashboardData.previous_race);
}

function updatePlayersPanel(players) {
    console.log('updatePlayersPanel()')
    console.log(players);
    const panel = document.getElementById('players-panel');
    clearElement(panel);

    if (!players || players.length === 0) {
        const noData = createElem('div', 'no-data', 'No players yet...')
        panel.appendChild(noData);
        return;
    }

    let table = document.createElement('table');
    let headerTr = document.createElement('tr');
    headerTr.appendChild(createElem('th', textContent = 'Player Name'));
    headerTr.appendChild(createElem('th', textContent = 'Available Bids'));
    table.appendChild(headerTr);

    players.forEach(plyr => {
        const tr = document.createElement('tr');
        tr.appendChild(createElem('td', textContent = plyr['player_name']));
        tr.appendChild(createElem('td', textContent = plyr['bids']['available']))
        table.appendChild(tr);        
    });

    panel.appendChild(table);
    return;
}

function updateCurrentRacePanel(currentRace) {
    console.log('updateCurrentRacePanel()');
    console.log(currentRace);
    const panel = document.getElementById('current-race-panel');
    clearElement(panel);

    if (!currentRace) {
        const noData = createElem('div', 'no-data', 'No upcoming race');
        panel.appendChild(noData);
        return;
    }
    
    const postTime = new Date(currentRace.post_time);
    const now = new Date();
    const minutesUntil = Math.round((postTime - now) / 60000);

    const raceInfo = createElem('div', 'race-info')

    const raceNumber = createElem('div', 'race-number', `Race ${currentRace.race_id}`);
    const raceDescription = createElem('div', 'race-description', currentRace.race_description);
    const postTimeDiv = createElem('div', 'post-time', `Post time in ${minutesUntil} minutes`);

    raceInfo.appendChild(raceNumber);
    raceInfo.appendChild(raceDescription);
    raceInfo.appendChild(postTimeDiv);

    // TODO: @PF Need to add current race odds for each post position

    panel.appendChild(raceInfo);

    return;
}

function updatePreviousRacePanel(previousRace) {
    console.log('updatePreviousRacePanel()');
    console.log(previousRace);
    const panel = document.getElementById('previous-race-panel');
    clearElement(panel);

    if (!previousRace)
    return;
}

function updateCurrentRacePoolPanel(currentRacePool) {
    console.log('updateCurrentRacePoolPanel()');
    console.log(currentRacePool);
    const panel = document.getElementById('current-race-pool-panel');
    clearElement(panel);

    return;
}
