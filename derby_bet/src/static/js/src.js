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
    const minutesUntil = Math.floor((postTime - now) / 60000);
    const secondsUntil = ((postTime - now) / 1000);
    // TODO: @PF This is currently going into negative seconds for 30 seconds, then flips to positive
    const secondsRemaining = Math.round(((secondsUntil / 60) - minutesUntil) * 60);

    const raceInfo = createElem('div', 'race-info')

    const raceNumber = createElem('div', 'race-number', `Race ${currentRace.race_id}`);
    const raceDescription = createElem('div', 'race-description', currentRace.race_description);
    const postTimeDiv = createElem('div', 'post-time', `Post time in ${minutesUntil} min. and ${secondsRemaining} sec.`);

    raceInfo.appendChild(raceNumber);
    raceInfo.appendChild(raceDescription);
    raceInfo.appendChild(postTimeDiv);

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

    // TODO: @PF Need to add current race odds for each post position

    return;
}


// ============================================================================
// ADMIN MODAL FUNCTIONALITY
// ============================================================================

const ADMIN_PASSCODE = '0502'; // Change this to your desired passcode

// Get modal elements
const adminBtn = document.getElementById('admin-btn');
const adminModal = document.getElementById('admin-modal');
const closeModalBtn = document.getElementById('close-modal');
const closeAdminBtn = document.getElementById('close-admin');
const submitPasscode = document.getElementById('submit-passcode');
const passcodeInput = document.getElementById('passcode');
const passcodeScreen = document.getElementById('passcode-screen');
const adminPanel = document.getElementById('admin-panel');
const passcodeError = document.getElementById('passcode-error');

// Open modal
adminBtn.addEventListener('click', () => {
    adminModal.classList.add('active');
    passcodeInput.value = '';
    passcodeError.textContent = '';
});

// Close modal
function closeModal() {
    adminModal.classList.remove('active');
    passcodeScreen.style.display = 'block';
    adminPanel.style.display = 'none';
    passcodeInput.value = '';
    passcodeError.textContent = '';
}

closeModalBtn.addEventListener('click', closeModal);
closeAdminBtn.addEventListener('click', closeModal);

// Close on outside click
adminModal.addEventListener('click', (e) => {
    if (e.target === adminModal) {
        closeModal();
    }
});

// Submit passcode
submitPasscode.addEventListener('click', checkPasscode);
passcodeInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        checkPasscode();
    }
});

function checkPasscode() {
    const entered = passcodeInput.value;
    
    if (entered === ADMIN_PASSCODE) {
        passcodeScreen.style.display = 'none';
        adminPanel.style.display = 'block';
        passcodeError.textContent = '';
    } else {
        passcodeError.textContent = 'Incorrect passcode';
        passcodeInput.value = '';
    }
}
