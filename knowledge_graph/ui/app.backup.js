// Knowledge Graph Explorer - Main Application

// API Configuration
const API_BASE = 'http://localhost:8000/api';
const WS_URL = 'ws://localhost:8000/ws';

// Global state
let currentNode = null;
let graphData = null;
let impactData = null;
let ws = null;

// Initialize WebSocket connection
function initWebSocket() {
    ws = new WebSocket(WS_URL);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
        showNotification('Connected to Knowledge Graph', 'success');
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleRealtimeUpdate(data);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        showNotification('Connection error', 'error');
    };
    
    ws.onclose = () => {
        console.log('WebSocket disconnected');
        // Reconnect after 3 seconds
        setTimeout(initWebSocket, 3000);
    };
}

// Handle real-time updates
function handleRealtimeUpdate(data) {
    switch (data.type) {
        case 'analysis_complete':
            showNotification('Codebase analysis complete', 'success');
            loadGraphData();
            break;
        case 'code_updated':
            showNotification(`File updated: ${data.file}`, 'info');
            if (data.impact_summary) {
                updateImpactDisplay(data.impact_summary);
            }
            break;
        case 'analysis_error':
            showNotification(`Analysis error: ${data.error}`, 'error');
            break;
    }
}

// Analyze codebase
async function analyzeCodebase() {
    try {
        const response = await fetch(`${API_BASE}/analyze/codebase`, {
            method: 'POST'
        });
        const data = await response.json();
        showNotification('Codebase analysis started', 'info');
    } catch (error) {
        showNotification('Failed to start analysis', 'error');
    }
}

// Perform semantic search
async function performSearch() {
    const query = document.getElementById('searchInput').value;
    if (!query) return;
    
    try {
        const response = await fetch(`${API_BASE}/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, limit: 20 })
        });
        const data = await response.json();
        displaySearchResults(data.results);
    } catch (error) {
        showNotification('Search failed', 'error');
    }
}

// Display search results
function displaySearchResults(results) {
    // Highlight nodes in graph
    if (graphData) {
        const resultIds = new Set(results.map(r => r.id));
        d3.selectAll('.node')
            .classed('highlighted', d => resultIds.has(d.id))
            .style('opacity', d => resultIds.has(d.id) ? 1 : 0.3);
    }
    
    // Show results in sidebar
    const details = document.getElementById('nodeDetails');
    details.innerHTML = `
        <h3 class="font-semibold mb-2">Search Results (${results.length})</h3>
        <div class="space-y-2 max-h-64 overflow-y-auto">
            ${results.map(r => `
                <div class="bg-gray-700 p-2 rounded cursor-pointer hover:bg-gray-600" 
                     onclick="selectNode('${r.id}')">
                    <div class="font-semibold">${r.name}</div>
                    <div class="text-sm text-gray-400">${r.path}</div>
                    <div class="text-xs text-blue-400">Score: ${r.relevance_score.toFixed(3)}</div>
                </div>
            `).join('')}
        </div>
    `;
}

// Load graph data
async function loadGraphData() {
    try {
        const response = await fetch(`${API_BASE}/graph/structure`);
        graphData = await response.json();
        renderDependencyGraph();
    } catch (error) {
        showNotification('Failed to load graph data', 'error');
    }
}

// Render dependency graph using D3.js
function renderDependencyGraph() {
    const container = document.getElementById('dependencyGraph');
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    // Clear existing graph
    d3.select(container).selectAll('*').remove();
    
    const svg = d3.select(container)
        .append('svg')
        .attr('width', width)
        .attr('height', height);
    
    // Add zoom behavior
    const g = svg.append('g');
    svg.call(d3.zoom()
        .scaleExtent([0.1, 10])
        .on('zoom', (event) => {
            g.attr('transform', event.transform);
        }));
    
    // Force simulation
    const simulation = d3.forceSimulation(graphData.nodes)
        .force('link', d3.forceLink(graphData.links).id(d => d.id))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2));
    
    // Draw links
    const link = g.append('g')
        .selectAll('line')
        .data(graphData.links)
        .enter().append('line')
        .attr('class', 'link')
        .style('stroke', '#64748b')
        .style('stroke-opacity', 0.6)
        .style('stroke-width', d => Math.sqrt(d.weight || 1));
    
    // Draw nodes
    const node = g.append('g')
        .selectAll('circle')
        .data(graphData.nodes)
        .enter().append('circle')
        .attr('class', 'node')
        .attr('r', d => getNodeSize(d))
        .style('fill', d => getNodeColor(d))
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));
    
    // Add labels
    const label = g.append('g')
        .selectAll('text')
        .data(graphData.nodes)
        .enter().append('text')
        .text(d => d.name)
        .style('font-size', '10px')
        .style('fill', '#e2e8f0');
    
    // Node click handler
    node.on('click', (event, d) => {
        selectNode(d.id);
    });
    
    // Update positions on tick
    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
        
        node
            .attr('cx', d => d.x)
            .attr('cy', d => d.y);
        
        label
            .attr('x', d => d.x + 10)
            .attr('y', d => d.y + 3);
    });
    
    // Drag functions
    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }
    
    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }
    
    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
}

// Get node size based on type
function getNodeSize(node) {
    const sizes = {
        'file': 10,
        'class': 8,
        'function': 6,
        'method': 5
    };
    return sizes[node.type] || 4;
}

// Get node color based on type
function getNodeColor(node) {
    const colors = {
        'file': '#3b82f6',
        'class': '#8b5cf6',
        'function': '#10b981',
        'method': '#f59e0b'
    };
    return colors[node.type] || '#6b7280';
}

// Select a node
async function selectNode(nodeId) {
    currentNode = nodeId;
    
    // Highlight selected node
    d3.selectAll('.node')
        .style('stroke', d => d.id === nodeId ? '#fff' : 'none')
        .style('stroke-width', d => d.id === nodeId ? 2 : 0);
    
    // Load node details
    try {
        // Get impact analysis
        const impactResponse = await fetch(`${API_BASE}/impact/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ node_id: nodeId, max_depth: 5 })
        });
        impactData = await impactResponse.json();
        
        // Get agent notes
        const notesResponse = await fetch(`${API_BASE}/agent/notes/${nodeId}`);
        const notesData = await notesResponse.json();
        
        // Update displays
        updateNodeDetails(nodeId);
        updateImpactDisplay(impactData.summary);
        updateAgentNotes(notesData.notes);
        
        if (document.querySelector('[data-tab="heatmap"]').classList.contains('active')) {
            renderImpactHeatmap();
        }
    } catch (error) {
        showNotification('Failed to load node details', 'error');
    }
}

// Update node details display
function updateNodeDetails(nodeId) {
    const node = graphData.nodes.find(n => n.id === nodeId);
    if (!node) return;
    
    const details = document.getElementById('nodeDetails');
    details.innerHTML = `
        <h3 class="font-semibold mb-2">${node.name}</h3>
        <div class="space-y-1 text-sm">
            <div><span class="text-gray-400">Type:</span> ${node.type}</div>
            <div><span class="text-gray-400">Path:</span> ${node.path}</div>
            ${node.lines ? `<div><span class="text-gray-400">Lines:</span> ${node.lines}</div>` : ''}
            ${node.imports ? `<div><span class="text-gray-400">Imports:</span> ${node.imports}</div>` : ''}
            ${node.exports ? `<div><span class="text-gray-400">Exports:</span> ${node.exports}</div>` : ''}
        </div>
    `;
}

// Update impact display
function updateImpactDisplay(summary) {
    document.getElementById('impactSummary').classList.remove('hidden');
    document.getElementById('highImpactCount').textContent = summary.impact_distribution.high;
    document.getElementById('mediumImpactCount').textContent = summary.impact_distribution.medium;
    document.getElementById('lowImpactCount').textContent = summary.impact_distribution.low;
    
    // Update critical paths
    if (summary.critical_paths && summary.critical_paths.length > 0) {
        document.getElementById('criticalPaths').classList.remove('hidden');
        document.getElementById('pathsList').innerHTML = summary.critical_paths.map(path => `
            <div class="text-gray-300">→ ${path.path}</div>
        `).join('');
    }
}

// Update agent notes
function updateAgentNotes(notes) {
    const container = document.getElementById('agentNotes');
    if (notes.length === 0) {
        container.innerHTML = '<p class="text-gray-400 text-sm">No agent observations yet</p>';
        return;
    }
    
    container.innerHTML = notes.map(note => `
        <div class="bg-gray-700 p-2 rounded text-sm">
            <div class="flex justify-between mb-1">
                <span class="font-semibold">${note.agent_id}</span>
                <span class="text-xs text-gray-400">${formatTime(note.created_at)}</span>
            </div>
            <div>${note.content}</div>
        </div>
    `).join('');
}

// Render impact heatmap
function renderImpactHeatmap() {
    if (!impactData) return;
    
    const container = document.getElementById('impactHeatmap');
    
    // Prepare data for heatmap
    const files = Object.keys(impactData.file_impacts);
    const values = files.map(f => [impactData.file_impacts[f]]);
    
    const data = [{
        z: values,
        x: ['Impact'],
        y: files,
        type: 'heatmap',
        colorscale: 'RdYlGn',
        reversescale: true
    }];
    
    const layout = {
        title: 'File Impact Heatmap',
        paper_bgcolor: '#0f172a',
        plot_bgcolor: '#0f172a',
        font: { color: '#e2e8f0' },
        margin: { l: 200 }
    };
    
    Plotly.newPlot(container, data, layout);
}

// Switch tabs
function switchTab(tab) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active', 'bg-gray-700');
    });
    event.target.classList.add('active', 'bg-gray-700');
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.add('hidden');
    });
    document.getElementById(`${tab}View`).classList.remove('hidden');
    
    // Render appropriate visualization
    switch (tab) {
        case 'graph':
            if (graphData) renderDependencyGraph();
            break;
        case 'heatmap':
            if (impactData) renderImpactHeatmap();
            break;
        case 'architecture':
            renderArchitectureDiagram();
            break;
    }
}

// Open Claude terminal
function openClaudeTerminal() {
    document.getElementById('claudeModal').classList.remove('hidden');
    initializeClaudeTerminal();
}

// Close Claude terminal
function closeClaudeTerminal() {
    document.getElementById('claudeModal').classList.add('hidden');
}

// Initialize Claude terminal
function initializeClaudeTerminal() {
    const terminal = document.getElementById('claudeTerminal');
    terminal.innerHTML = `
        <div class="mb-2">Claude Code Terminal - Connected to Knowledge Graph</div>
        <div class="mb-2">Type 'help' for available commands</div>
        <div class="flex">
            <span class="mr-2">$</span>
            <input type="text" class="bg-transparent outline-none flex-1" 
                   placeholder="Enter command..." 
                   onkeypress="handleTerminalCommand(event)">
        </div>
    `;
}

// Handle terminal commands
function handleTerminalCommand(event) {
    if (event.key === 'Enter') {
        const input = event.target;
        const command = input.value;
        
        // Add command to terminal
        const terminal = document.getElementById('claudeTerminal');
        const output = document.createElement('div');
        output.innerHTML = `<div class="mb-1">$ ${command}</div>`;
        terminal.insertBefore(output, terminal.lastElementChild);
        
        // Process command
        processClaudeCommand(command, output);
        
        // Clear input
        input.value = '';
    }
}

// Process Claude commands
async function processClaudeCommand(command, outputElement) {
    // This would integrate with actual Claude Code SDK
    // For now, simulate some commands
    
    switch (command.split(' ')[0]) {
        case 'help':
            outputElement.innerHTML += `
                <div class="text-green-400">Available commands:</div>
                <div>analyze [file] - Analyze a specific file</div>
                <div>impact [node] - Show impact analysis</div>
                <div>search [query] - Semantic search</div>
                <div>explain [node] - Get AI explanation</div>
            `;
            break;
        case 'analyze':
            outputElement.innerHTML += '<div class="text-yellow-400">Analyzing...</div>';
            // Would call actual analysis
            break;
        case 'impact':
            if (currentNode) {
                outputElement.innerHTML += `<div class="text-blue-400">Impact analysis for ${currentNode}</div>`;
            } else {
                outputElement.innerHTML += '<div class="text-red-400">No node selected</div>';
            }
            break;
        default:
            outputElement.innerHTML += '<div class="text-red-400">Unknown command</div>';
    }
}

// Show notification
function showNotification(message, type = 'info') {
    // Simple notification - could be enhanced with a toast library
    console.log(`[${type.toUpperCase()}] ${message}`);
}

// Format time
function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    initWebSocket();
    loadGraphData();
    
    // Set up search on Enter
    document.getElementById('searchInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });
});