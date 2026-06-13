// State Variables
let currentSessionHistory = [];

// DOM Elements
const sidebar = document.getElementById('sidebar');
const dashboard = document.getElementById('dashboard');
const toggleSidebarBtn = document.getElementById('toggleSidebarBtn');
const closeSidebarBtn = document.getElementById('closeSidebarBtn');
const toggleDashboardBtn = document.getElementById('toggleDashboardBtn');
const newChatBtn = document.getElementById('newChatBtn');
const historyList = document.getElementById('historyList');
const messagesStream = document.getElementById('messagesStream');
const chatForm = document.getElementById('chatForm');
const queryInput = document.getElementById('queryInput');
const atmaModeSelector = document.getElementById('atmaModeSelector');

// Diagnostic Elements
const diagLatency = document.getElementById('diagLatency');
const diagMemory = document.getElementById('diagMemory');
const verificationBadge = document.getElementById('verificationBadge');
const operatorsChips = document.getElementById('operatorsChips');
const verifiedFactsList = document.getElementById('verifiedFactsList');
const rejectedFactsList = document.getElementById('rejectedFactsList');

// Global Stats
const sysAtmaMode = document.getElementById('sysAtmaMode');
const sysModelName = document.getElementById('sysModelName');
const sysPassRate = document.getElementById('sysPassRate');
const sbTotalRuns = document.getElementById('sbTotalRuns');
const sbAvgLatency = document.getElementById('sbAvgLatency');

// Page Load Initialization
window.addEventListener('DOMContentLoaded', () => {
    loadHistory();
    loadGlobalStats();
    setupEventListeners();
});

// Setup Layout and Action Triggers
function setupEventListeners() {
    // Sidebar toggle (Mobile/Desktop)
    toggleSidebarBtn.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
    });
    
    closeSidebarBtn.addEventListener('click', () => {
        sidebar.classList.add('collapsed');
    });

    // Diagnostics Dashboard toggle
    toggleDashboardBtn.addEventListener('click', () => {
        dashboard.classList.toggle('collapsed');
        toggleDashboardBtn.classList.toggle('active');
    });

    // Reset Chat Stream
    newChatBtn.addEventListener('click', startNewSession);

    // Chat Submission Form
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        submitQuery();
    });
}

// Start a fresh, clean chat session
function startNewSession() {
    messagesStream.innerHTML = `
        <div class="welcome-container">
            <div class="welcome-card">
                <div class="welcome-icon-glow">
                    <svg class="welcome-logo" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/>
                        <path d="M12 6v12M6 12h12M7.5 7.5l9 9M16.5 7.5l-9 9"/>
                    </svg>
                </div>
                <h2>Colony of Minds AI</h2>
                <p class="welcome-desc">A composition-based operator designed to verify and speak facts, avoiding LLM hallucinations by leveraging specialized deterministic suboperators.</p>
                
                <div class="suggestions-grid">
                    <div class="suggestion-card" onclick="useSuggestion('calculate 18% of 25000 and explain it')">
                        <span class="sug-tag">Math & Explanations</span>
                        <p class="sug-text">"calculate 18% of 25000 and explain it"</p>
                    </div>
                    <div class="suggestion-card" onclick="useSuggestion('remember my email is operator@colony.ai')">
                        <span class="sug-tag">Durable Memory</span>
                        <p class="sug-text">"remember my email is operator@colony.ai"</p>
                    </div>
                    <div class="suggestion-card" onclick="useSuggestion('what is my email?')">
                        <span class="sug-tag">Memory Recall</span>
                        <p class="sug-text">"what is my email?"</p>
                    </div>
                    <div class="suggestion-card" onclick="useSuggestion('what is the current time?')">
                        <span class="sug-tag">Safe Tool Execution</span>
                        <p class="sug-text">"what is the current time?"</p>
                    </div>
                </div>
            </div>
        </div>
    `;
    resetDiagnostics();
}

// Preset suggestion click handler
window.useSuggestion = function(text) {
    queryInput.value = text;
    submitQuery();
};

// Reset diagnostics panel values
function resetDiagnostics() {
    diagLatency.textContent = "0.00 ms";
    diagMemory.textContent = "0.00 MB";
    
    verificationBadge.textContent = "No active session";
    verificationBadge.className = "verification-badge neutral";
    
    operatorsChips.innerHTML = '<span class="no-data-txt">No suboperators active</span>';
    verifiedFactsList.innerHTML = '<span class="no-data-txt">No verified facts recorded in this run</span>';
    rejectedFactsList.innerHTML = '<span class="no-data-txt">No facts rejected in this run</span>';
}

// Retrieve past interactions from SQLite memory
async function loadHistory() {
    try {
        const response = await fetch('/api/history?limit=15');
        if (!response.ok) throw new Error("History fetch failed");
        
        const history = await response.json();
        currentSessionHistory = history;
        renderHistoryList(history);
    } catch (err) {
        historyList.innerHTML = `<div class="history-loading">Error loading history: ${err.message}</div>`;
    }
}

// Retrieve global system stats
async function loadGlobalStats() {
    try {
        const response = await fetch('/api/stats');
        if (!response.ok) throw new Error("Stats fetch failed");
        
        const stats = await response.json();
        
        // Update dashboard elements
        sysAtmaMode.textContent = stats.atma_default_mode === 'model' ? 'LLM' : 'Template';
        sysModelName.textContent = stats.default_model !== 'None' ? stats.default_model : 'Template Fallback';
        
        // Update pass rate
        if (stats.total_queries > 0) {
            const passRate = (stats.verified_queries / stats.total_queries) * 100;
            sysPassRate.textContent = `${passRate.toFixed(1)}%`;
        } else {
            sysPassRate.textContent = "100%";
        }
        
        // Update sidebar header stats
        sbTotalRuns.textContent = stats.total_queries;
        sbAvgLatency.textContent = `${Math.round(stats.average_latency_ms)} ms`;
        
        // Sync atma mode dropdown selection
        atmaModeSelector.value = stats.atma_default_mode;
    } catch (err) {
        console.error("Error updating global stats:", err);
    }
}

// Render the history items list in the sidebar
function renderHistoryList(items) {
    if (!items || items.length === 0) {
        historyList.innerHTML = '<div class="history-loading">No history found in database.</div>';
        return;
    }
    
    historyList.innerHTML = '<div class="history-section-title">Recent Chats</div>';
    
    items.forEach((item, index) => {
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';
        historyItem.addEventListener('click', () => recallHistorySession(item));
        
        const timeClean = item.timestamp ? item.timestamp.substring(11, 16) : '--:--';
        const isVer = item.verified;
        
        historyItem.innerHTML = `
            <span class="history-item-query">${escapeHTML(item.query)}</span>
            <div class="history-item-meta">
                <span>${timeClean}</span>
                <span class="history-status-indicator ${isVer ? 'verified' : 'rejected'}">
                    ${isVer ? 'Verified' : 'Rejected'}
                </span>
            </div>
        `;
        historyList.appendChild(historyItem);
    });
}

// Display a clicked historical session chat bubble and load its stats
function recallHistorySession(item) {
    // Render as a single chat interaction
    messagesStream.innerHTML = '';
    
    appendMessageBubble('user', item.query);
    appendMessageBubble('colony', item.response);
    
    // Mock diagnostic information from history payload if available
    resetDiagnostics();
    
    // Approximate metrics based on logged data
    diagLatency.textContent = "Cached (historical)";
    diagMemory.textContent = "-- MB";
    
    // Status Badge
    if (item.verified) {
        verificationBadge.textContent = "VERIFIED PASS";
        verificationBadge.className = "verification-badge passed";
    } else {
        verificationBadge.textContent = "REJECTED FAILURE";
        verificationBadge.className = "verification-badge rejected";
    }
    
    // Render active operators if saved
    if (item.routed_operators) {
        operatorsChips.innerHTML = '';
        item.routed_operators.forEach(op => {
            const chip = document.createElement('span');
            chip.className = `op-chip ${op}`;
            chip.textContent = op;
            operatorsChips.appendChild(chip);
        });
    }
}

// Send user query to backend HTTP endpoint
async function submitQuery() {
    const query = queryInput.value.trim();
    if (!query) return;
    
    // Reset inputs
    queryInput.value = '';
    queryInput.disabled = true;
    
    // Remove welcome card if present
    const welcome = messagesStream.querySelector('.welcome-container');
    if (welcome) {
        welcome.remove();
    }
    
    // 1. Add User bubble to stream
    appendMessageBubble('user', query);
    
    // 2. Add Colony loading indicator bubble
    const typingBubble = appendTypingIndicator();
    scrollToBottom();
    
    try {
        const atmaMode = atmaModeSelector.value;
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                atma_mode: atmaMode
            })
        });
        
        if (!response.ok) throw new Error("Operator Pipeline execution failed.");
        
        const data = await response.json();
        
        // 3. Remove typing indicator and append Colony verified answer
        typingBubble.remove();
        appendMessageBubble('colony', data.response);
        scrollToBottom();
        
        // 4. Update Diagnostics Panel
        updateDiagnosticsPanel(data);
        
        // 5. Refresh sidebar list and global stats
        loadHistory();
        loadGlobalStats();
        
    } catch (err) {
        typingBubble.remove();
        appendMessageBubble('colony', `[!] Pipeline Failure: ${err.message}`);
        scrollToBottom();
    } finally {
        queryInput.disabled = false;
        queryInput.focus();
    }
}

// Update the diagnostics side-panel with the run metrics and verification facts
function updateDiagnosticsPanel(data) {
    diagLatency.textContent = `${data.latency_ms} ms`;
    diagMemory.textContent = `${data.memory_mb} MB`;
    
    // Safety Status Badge
    if (data.verified) {
        verificationBadge.textContent = "VERIFIED PASS";
        verificationBadge.className = "verification-badge passed";
    } else {
        verificationBadge.textContent = "REJECTED FAILURE";
        verificationBadge.className = "verification-badge rejected";
    }
    
    // Suboperators active
    operatorsChips.innerHTML = '';
    if (data.routed_operators && data.routed_operators.length > 0) {
        data.routed_operators.forEach(op => {
            const chip = document.createElement('span');
            chip.className = `op-chip ${op}`;
            chip.textContent = op;
            operatorsChips.appendChild(chip);
        });
    } else {
        operatorsChips.innerHTML = '<span class="no-data-txt">No suboperators active</span>';
    }
    
    // Render verified facts list
    verifiedFactsList.innerHTML = '';
    if (data.verified_facts && data.verified_facts.length > 0) {
        data.verified_facts.forEach(fact => {
            const item = document.createElement('div');
            item.className = 'fact-item';
            
            // Format title
            const factType = fact.type ? fact.type.toUpperCase() : 'FACT';
            const operator = fact.operator ? fact.operator : 'unknown';
            
            item.innerHTML = `
                <div class="fact-item-title">
                    <span>${escapeHTML(factType)}</span>
                    <span class="fact-item-src">${escapeHTML(operator)}</span>
                </div>
                <div class="fact-item-body">${formatFactBody(fact)}</div>
            `;
            verifiedFactsList.appendChild(item);
        });
    } else {
        verifiedFactsList.innerHTML = '<span class="no-data-txt">No verified facts recorded in this run</span>';
    }
    
    // Render rejected facts list
    rejectedFactsList.innerHTML = '';
    if (data.rejected_facts && data.rejected_facts.length > 0) {
        data.rejected_facts.forEach(rej => {
            const item = document.createElement('div');
            item.className = 'fact-item';
            
            const operator = rej.operator ? rej.operator : 'unknown';
            const reason = rej.reason ? rej.reason : 'Failed verification check';
            
            item.innerHTML = `
                <div class="fact-item-title">
                    <span>REJECTED CODE</span>
                    <span class="fact-item-src">${escapeHTML(operator)}</span>
                </div>
                <div class="fact-item-body">
                    <strong>Reason:</strong> ${escapeHTML(reason)}<br>
                    <strong>Input:</strong> ${escapeHTML(JSON.stringify(rej.fact || rej))}
                </div>
            `;
            rejectedFactsList.appendChild(item);
        });
    } else {
        rejectedFactsList.innerHTML = '<span class="no-data-txt">No facts rejected in this run</span>';
    }
}

// Custom parser to format a fact JSON neatly
function formatFactBody(fact) {
    let html = '';
    if (fact.type === 'calculation') {
        html = `<code>${escapeHTML(fact.expression)}</code> = <strong>${escapeHTML(String(fact.result))}</strong>`;
    } else if (fact.type === 'stored_preference' || fact.type === 'retrieved_preference') {
        html = `Stored preference: <code>${escapeHTML(fact.key)}</code> = <strong>${escapeHTML(String(fact.value))}</strong>`;
    } else if (fact.type === 'tool_call') {
        html = `Called tool: <code>${escapeHTML(fact.tool)}</code><br><span class="fact-item-src">Output: ${escapeHTML(String(fact.output))}</span>`;
    } else {
        // Fallback dump
        const cleanFact = { ...fact };
        delete cleanFact.type;
        delete cleanFact.operator;
        html = `<code>${escapeHTML(JSON.stringify(cleanFact))}</code>`;
    }
    return html;
}

// Append a message bubble to the chat stream
function appendMessageBubble(sender, text) {
    const msgRow = document.createElement('div');
    msgRow.className = `msg-row ${sender}`;
    
    const msgBubble = document.createElement('div');
    msgBubble.className = 'msg-bubble';
    msgBubble.innerHTML = formatResponseText(text);
    
    msgRow.appendChild(msgBubble);
    messagesStream.appendChild(msgRow);
    return msgRow;
}

// Append a temporary loading typing indicator bubble
function appendTypingIndicator() {
    const msgRow = document.createElement('div');
    msgRow.className = 'msg-row colony';
    
    const msgBubble = document.createElement('div');
    msgBubble.className = 'msg-bubble';
    
    const dots = document.createElement('div');
    dots.className = 'typing-dots';
    dots.innerHTML = '<span></span><span></span><span></span>';
    
    msgBubble.appendChild(dots);
    msgRow.appendChild(msgBubble);
    messagesStream.appendChild(msgRow);
    return msgRow;
}

// Smooth scroll to the bottom of the chat stream
function scrollToBottom() {
    messagesStream.scrollTop = messagesStream.scrollHeight;
}

// Simple HTML escaper
function escapeHTML(str) {
    if (!str) return '';
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Simple markdown formatter helper for code and formatting tags
function formatResponseText(text) {
    // 1. Escape HTML
    let formatted = escapeHTML(text);
    
    // 2. Translate triple-backtick markdown blocks into pre/code elements
    formatted = formatted.replace(/```([\s\S]*?)```/g, (match, code) => {
        return `<pre><code>${code.trim()}</code></pre>`;
    });
    
    // 3. Translate inline single backticks into code elements
    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // 4. Translate double-asterisks (bold) into strong elements
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    
    // 5. Linebreaks to html breaks
    return formatted.replace(/\n/g, '<br>');
}
