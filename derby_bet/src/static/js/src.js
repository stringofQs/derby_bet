document.addEventListener("DOMContentLoaded", () => {
    // Fetch race info once on load (countdown runs in JS from there)
    fetchRaceInfo();

    // Fetch live-updating data immediately, then on a 5-second interval
    fetchPlayers();
    fetchOdds();
    setInterval(fetchPlayers, 5000);
    setInterval(fetchOdds, 5000);

    // SSE for race finalization events pushed from the backend
    setupEventSource();

    // Initialize the wager feed to idle state (no historical endpoint)
    initIssueLog();
});


// ============================================================================
// ELEMENT HELPERS
// ============================================================================

function createElem(tag, className = '', textContent = '') {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (textContent) el.textContent = textContent;
    return el;
}

function clearElement(element) {
    while (element.firstChild) {
        element.removeChild(element.firstChild);
    }
}


// ============================================================================
// DATA FETCHING
// ============================================================================

async function fetchRaceInfo() {
    try {
        const response = await fetch('/api/race-info');
        const data = await response.json();
        if (data._success) {
            updateCurrentRacePanel(data.current_race);
            updatePreviousRacePanel(data.previous_race);
            updateRaceSchedulePanel(data.race_schedule);
        } else {
            console.error('Backend error fetching race info:', data._message);
        }
    } catch (err) {
        console.error('Error fetching race info:', err);
    }
}

async function fetchPlayers() {
    try {
        const response = await fetch('/api/players');
        const data = await response.json();
        if (data._success) {
            updatePlayersPanel(data.lead_players);
            updateAvailPanel(data.all_players);
        } else {
            console.error('Backend error fetching players:', data._message);
        }
    } catch (err) {
        console.error('Error fetching players:', err);
    }
}

async function fetchOdds() {
    try {
        const response = await fetch('/api/odds');
        const data = await response.json();
        if (data._success) {
            updateCurrentRacePoolPanel(data.current_race_pool);
        } else {
            console.error('Backend error fetching odds:', data._message);
        }
    } catch (err) {
        console.error('Error fetching odds:', err);
    }
}

function setupEventSource() {
    const eventSource = new EventSource('/api/events');

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'race_finalized') {
            updateCurrentRacePanel(data.current_race);
            updatePreviousRacePanel(data.previous_race);
            updateRaceSchedulePanel(data.race_schedule);
        } else if (data.type === 'wager_processed') {
            data.results.forEach(wager => addIssueLogEntry(wager));
        }
    };

    eventSource.onerror = () => {
        console.warn('SSE connection lost — browser will retry automatically.');
    };
}


// ============================================================================
// COUNTDOWN
// ============================================================================

let countdownInterval = null;
let currentPostTime = null;

function startCountdown(postTimeStr) {
    currentPostTime = new Date(postTimeStr);
    if (countdownInterval) clearInterval(countdownInterval);
    tickCountdown();
    countdownInterval = setInterval(tickCountdown, 1000);
}

function tickCountdown() {
    const postTimeEl = document.querySelector('#current-race-panel .post-time');
    if (!postTimeEl || !currentPostTime) return;

    const totalSeconds = Math.floor((currentPostTime - new Date()) / 1000);

    if (totalSeconds <= 0) {
        postTimeEl.textContent = 'Post time reached!';
        clearInterval(countdownInterval);
        return;
    }

    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    postTimeEl.textContent = `Post time in ${minutes} min. and ${seconds} sec.`;
}


// ============================================================================
// PANEL UPDATES
// ============================================================================

function updatePlayersPanel(players) {
    const panel = document.getElementById('players-panel');
    clearElement(panel);

    if (!players || players.length === 0) {
        panel.appendChild(createElem('div', 'no-data', 'No leaders yet...'));
        return;
    }

    players.forEach((plyr, index) => {
        const item = createElem('div', 'player-item');

        const rank = createElem('span', 'rank', String(index + 1));
        const name = createElem('span', 'player-name', plyr.player_name);
        const balance = createElem('span', 'player-balance', String(plyr.bids.won));

        item.appendChild(rank);
        item.appendChild(name);
        item.appendChild(balance);
        panel.appendChild(item);
    });
}

function updateAvailPanel(players) {
    const panel = document.getElementById('players-available-panel');
    clearElement(panel);

    if (!players || players.length === 0) {
        panel.appendChild(createElem('div', 'no-data', 'No players available bids...'));
        return;
    }

    players.forEach((plyr, index) => {
        const item = createElem('div', 'player-item-small');
        
        const name = createElem('span', 'player-name', plyr.player_name);
        const balance = createElem('span', 'player-balance', String(plyr.bids.available));

        item.appendChild(name);
        item.appendChild(balance);
        panel.appendChild(item);
    });
}

function updateCurrentRacePanel(currentRace) {
    const panel = document.getElementById('current-race-panel');
    clearElement(panel);

    if (!currentRace) {
        panel.appendChild(createElem('div', 'no-data', 'No upcoming race'));
        return;
    }

    const raceInfo = createElem('div', 'race-info');

    const raceLabel = createElem('div', 'race-label');
    raceLabel.appendChild(createElem('span', 'race-number', `(Race ${currentRace.race_id})`));
    raceLabel.appendChild(createElem('span', 'race-label-sep', ' '));
    raceLabel.appendChild(createElem('span', 'race-description', currentRace.race_description));
    raceInfo.appendChild(raceLabel);

    raceInfo.appendChild(createElem('div', 'post-time', ''));
    panel.appendChild(raceInfo);

    startCountdown(currentRace.post_time);
}

function updatePreviousRacePanel(previousRace) {
    const panel = document.getElementById('previous-race-panel');
    clearElement(panel);

    if (!previousRace || Object.keys(previousRace).length === 0) {
        panel.appendChild(createElem('div', 'no-data', 'No previous race results yet'));
        return;
    }

    const header = createElem('div', 'results-header');
    header.appendChild(createElem('div', 'race-description', previousRace.race_description));
    panel.appendChild(header);

    const positions = createElem('div', 'finish-positions');

    const placeDefs = [
        { label: '1st — Win',   post: previousRace.win },
        { label: '2nd — Place', post: previousRace.place },
        { label: '3rd — Show',  post: previousRace.show }
    ];

    placeDefs.forEach(({ label, post }) => {
        const posDiv = createElem('div', 'position');
        posDiv.appendChild(createElem('div', 'position-label', label));
        posDiv.appendChild(createElem('div', 'position-horse', post != null ? `#${post}` : '—'));
        positions.appendChild(posDiv);
    });

    panel.appendChild(positions);
}

function updateRaceSchedulePanel(raceSchedule) {
    const panel = document.getElementById('schedule-panel');
    clearElement(panel);

    if (!raceSchedule || raceSchedule.length === 0) {
        panel.appendChild(createElem('div', 'no-data', 'No races scheduled'));
        return
    }

    raceSchedule.forEach((rce) => {
        const item = createElem('div', 'schedule-item');
        const raceNum = createElem('span', null, `Race ${rce.race_id}`);
        const postTimeVal = new Date(rce.post_time);
        const postTime = createElem('span', null, postTimeVal.toLocaleTimeString());
        item.appendChild(raceNum);
        item.appendChild(postTime);
        panel.appendChild(item);
    });
}

function updateCurrentRacePoolPanel(poolData) {
    const panel = document.getElementById('current-race-pool-panel');
    clearElement(panel);

    const pools = poolData || {};

    const columnDefs = [
        { label: 'Win',   key: 'win',   fillClass: 'pool-fill-win' },
        { label: 'Place', key: 'place', fillClass: 'pool-fill-place' },
        { label: 'Show',  key: 'show',  fillClass: 'pool-fill-show' },
    ];

    const grid = createElem('div', 'pools-grid');

    columnDefs.forEach(({ label, key, fillClass }) => {
        const poolMap = pools[key] || {};
        const total   = Object.values(poolMap).reduce((s, v) => s + v, 0);

        const col = createElem('div', 'pool-column');

        const header = createElem('div', 'pool-column-header', label);
        header.appendChild(createElem('div', 'pool-column-total', total > 0 ? `${total} bids` : 'no bids'));
        col.appendChild(header);

        for (let post = 1; post <= 20; post++) {
            const amount = poolMap[String(post)] || 0;

            const row = createElem('div', 'horse-row');
            row.appendChild(createElem('span', 'horse-row-number', `#${post}`));

            const bar  = createElem('div', 'pool-bar');
            const fill = createElem('div', `pool-fill ${fillClass}`);
            fill.style.width = total > 0 ? `${Math.round(amount / total * 100)}%` : '0%';
            bar.appendChild(fill);
            row.appendChild(bar);

            // Multiplier: total pool / bids on this post.
            // For win this is exact; for place/show it is the upper-bound since
            // the pool is shared among the top 2 or top 3 finishers.
            const multiplier = (amount > 0 && total > 0)
                ? `${(total / amount).toFixed(1)}x`
                : '—';
            row.appendChild(createElem('span', 'horse-row-amount', multiplier));
            col.appendChild(row);
        }

        grid.appendChild(col);
    });

    panel.appendChild(grid);
}


function initIssueLog() {
    const panel = document.getElementById('issue-log-list');
    clearElement(panel);
    panel.appendChild(createElem('div', 'no-data', 'Waiting for wagers...'));
}

function addIssueLogEntry(wager) {
    const panel = document.getElementById('issue-log-list');

    // Remove the idle placeholder on first real entry
    const placeholder = panel.querySelector('.no-data');
    if (placeholder) panel.removeChild(placeholder);

    const entry = createElem('div', `issue-entry ${wager.valid ? 'success' : 'error'}`);

    const header = createElem('div', 'issue-entry-header');
    header.appendChild(createElem('span', 'issue-status', wager.valid ? '✓' : '✗'));
    header.appendChild(createElem('span', 'issue-player', wager.player_name));
    header.appendChild(createElem('span', 'issue-race', `Race ${wager.race_number}`));
    entry.appendChild(header);

    if (wager.valid && wager.bets && wager.bets.length > 0) {
        const betsText = wager.bets.map(b => `${b.type} #${b.post} (${b.bid})`).join(' · ');
        entry.appendChild(createElem('div', 'issue-detail', betsText));
    } else if (wager.valid) {
        entry.appendChild(createElem('div', 'issue-detail', `${wager.total_bid} bids placed`));
    } else {
        entry.appendChild(createElem('div', 'issue-detail error-text', wager.errors));
    }

    const time = new Date(wager.timestamp);
    entry.appendChild(createElem('div', 'issue-time', time.toLocaleTimeString()));

    // Prepend so newest entries appear at the top
    panel.insertBefore(entry, panel.firstChild);
}


// ============================================================================
// ADMIN MODAL
// ============================================================================

const ADMIN_PASSCODE = '0502';

const adminBtn        = document.getElementById('admin-btn');
const adminModal      = document.getElementById('admin-modal');
const closeModalBtn   = document.getElementById('close-modal');
const closeAdminBtn   = document.getElementById('close-admin');
const submitPasscode  = document.getElementById('submit-passcode');
const passcodeInput   = document.getElementById('passcode');
const passcodeScreen  = document.getElementById('passcode-screen');
const adminPanel      = document.getElementById('admin-panel');
const passcodeError   = document.getElementById('passcode-error');

adminBtn.addEventListener('click', () => {
    adminModal.classList.add('active');
    passcodeInput.value = '';
    passcodeError.textContent = '';
});

function closeModal() {
    adminModal.classList.remove('active');
    passcodeScreen.style.display = 'block';
    adminPanel.style.display = 'none';
    passcodeInput.value = '';
    passcodeError.textContent = '';
}

closeModalBtn.addEventListener('click', closeModal);
closeAdminBtn.addEventListener('click', closeModal);

adminModal.addEventListener('click', (e) => {
    if (e.target === adminModal) closeModal();
});

submitPasscode.addEventListener('click', checkPasscode);
passcodeInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') checkPasscode();
});

function checkPasscode() {
    if (passcodeInput.value === ADMIN_PASSCODE) {
        passcodeScreen.style.display = 'none';
        adminPanel.style.display = 'block';
        passcodeError.textContent = '';
    } else {
        passcodeError.textContent = 'Incorrect passcode';
        passcodeInput.value = '';
    }
}

// Finalize race form submission
document.getElementById('submit-race-results').addEventListener('click', () => {
    const feedbackEl = document.getElementById('finalize-feedback');
    feedbackEl.className = 'admin-feedback';
    feedbackEl.textContent = '';

    const raceNum  = parseInt(document.getElementById('race-number').value);
    const winPost  = parseInt(document.getElementById('win-horse').value);
    const placePost = parseInt(document.getElementById('place-horse').value);
    const showPost = parseInt(document.getElementById('show-horse').value);

    if (!raceNum || !winPost || !placePost || !showPost) {
        feedbackEl.className = 'admin-feedback error';
        feedbackEl.textContent = 'Please fill in all fields.';
        return;
    }

    fetch('/api/admin/finalize-race', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            race_number: raceNum,
            win_post:    winPost,
            place_post:  placePost,
            show_post:   showPost
        })
    })
    .then(r => r.json())
    .then(data => {
        feedbackEl.className = data._success ? 'admin-feedback success' : 'admin-feedback error';
        feedbackEl.textContent = data._message;
    })
    .catch(err => {
        feedbackEl.className = 'admin-feedback error';
        feedbackEl.textContent = 'Request failed.';
        console.error('Error finalizing race:', err);
    });
});

document.getElementById('add-new-player').addEventListener('click', () => {
    const feedbackEl = document.getElementById('new-player-feedback');
    feedbackEl.className = 'admin-feedback';
    feedbackEl.textContent = '';

    const playerName = document.getElementById('new-player-name').value;

    if (!playerName || playerName.length === 0) {
        feedbackEl.className = 'admin-feedback error'
        feedbackEl.textContent = 'Please fill in player name field.';
        return;
    }

    fetch('/api/admin/add-player', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            player_name: playerName
        })
    })
    .then(r => r.json())
    .then(data => {
        feedbackEl.className = data._success ? 'admin-feedback success' : 'admin-feedback error';
        feedbackEl.textContent = data._message;
        const playerElem = document.getElementById('new-player-name');
        playerElem.textContent = '';
    })
    .catch(err => {
        feedbackEl.className = 'admin-feedback error';
        feedbackEl.textContent = 'Request failed.';
        console.error('Error adding new player:', err);
    });
});