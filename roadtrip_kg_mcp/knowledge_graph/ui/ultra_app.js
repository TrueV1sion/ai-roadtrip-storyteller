// ULTRA Knowledge Graph Explorer - Full functionality

const API_BASE = window.location.origin + '/api';
const WS_URL = 'ws://' + window.location.host + '/ws';

// Global state
let ws = null;
let graphData = null;
let fileTree = null;
let currentView = 'graph';
let selectedNode = null;
let impactHeatmap = null;

// Initialize WebSocket with proper error handling
function initWebSocket() {
    ws = new WebSocket(WS_URL);
    
    ws.onopen = () => {
        console.log('✅ WebSocket connected');
        ws.send(JSON.stringify({type: 'ping'}));
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'analysis_complete') {
            console.log('📊 Analysis complete:', data.stats);
            loadGraphData();
        }
    };
    
    ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
    };
    
    ws.onclose = () => {
        console.log('🔌 WebSocket disconnected, reconnecting...');
        setTimeout(initWebSocket, 3000);
    };
}

// Load all data on startup
async function initialize() {
    console.log('🚀 Initializing ULTRA Knowledge Graph');
    
    // Load graph data
    await loadGraphData();
    
    // Load file tree
    await loadFileTree();
    
    // Initialize WebSocket
    initWebSocket();
    
    // Set up search
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') performSearch();
        });
    }
}

// Load graph data
async function loadGraphData() {
    try {
        const response = await fetch(`${API_BASE}/graph/structure`);
        graphData = await response.json();
        console.log(`📊 Loaded ${graphData.nodes.length} nodes, ${graphData.links.length} links`);
        
        if (currentView === 'graph') {
            renderDependencyGraph();
        }
    } catch (error) {
        console.error('Failed to load graph:', error);
    }
}

// Load file tree
async function loadFileTree() {
    try {
        const response = await fetch(`${API_BASE}/file-tree`);
        fileTree = await response.json();
        renderFileTree();
    } catch (error) {
        console.error('Failed to load file tree:', error);
    }
}

// Render file tree in sidebar
function renderFileTree() {
    const container = document.getElementById('fileTree');
    if (!container || !fileTree) return;
    
    container.innerHTML = renderTreeNode(fileTree);
    
    // Add click handlers
    container.querySelectorAll('.file-item').forEach(item => {
        item.addEventListener('click', async (e) => {
            e.stopPropagation();
            const path = item.dataset.path;
            if (path) {
                await selectFile(path);
            }
        });
    });
}

function renderTreeNode(node, level = 0) {
    if (node.type === 'file') {
        const icon = getFileIcon(node.ext);
        return `<div class="file-item pl-${level * 4} py-1 hover:bg-gray-700 cursor-pointer" data-path="${node.path}">
            <i class="${icon} mr-2"></i>${node.name}
        </div>`;
    } else {
        let html = `<div class="folder-item pl-${level * 4} py-1">
            <i class="fas fa-folder mr-2 text-yellow-400"></i>${node.name}
        </div>`;
        if (node.children) {
            html += node.children.map(child => renderTreeNode(child, level + 1)).join('');
        }
        return html;
    }
}

function getFileIcon(ext) {
    const icons = {
        '.py': 'fab fa-python text-blue-400',
        '.js': 'fab fa-js text-yellow-400',
        '.ts': 'fab fa-js text-blue-400',
        '.tsx': 'fab fa-react text-cyan-400',
        '.jsx': 'fab fa-react text-cyan-400'
    };
    return icons[ext] || 'fas fa-file text-gray-400';
}

// Select and display file
async function selectFile(path) {
    try {
        const response = await fetch(`${API_BASE}/file/${path}`);
        const data = await response.json();
        
        // Find node in graph
        const node = graphData.nodes.find(n => n.id === path);
        if (node) {
            selectNode(node.id);
        }
        
        // Could display file content in a modal or sidebar
        console.log(`Selected file: ${path}`);
    } catch (error) {
        console.error('Failed to load file:', error);
    }
}

// Enhanced dependency graph with real data
function renderDependencyGraph() {
    const container = document.getElementById('dependencyGraph');
    if (!container || !graphData) return;
    
    container.innerHTML = '';
    
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    const svg = d3.select(container)
        .append('svg')
        .attr('width', width)
        .attr('height', height);
    
    // Add zoom
    const g = svg.append('g');
    const zoom = d3.zoom()
        .scaleExtent([0.1, 10])
        .on('zoom', (event) => {
            g.attr('transform', event.transform);
        });
    svg.call(zoom);
    
    // Color scale for node types
    const colorScale = d3.scaleOrdinal()
        .domain(['file', 'class', 'function', 'module'])
        .range(['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b']);
    
    // Size scale for node importance
    const sizeScale = d3.scaleLinear()
        .domain([0, d3.max(graphData.nodes, d => d.lines || 1)])
        .range([5, 20]);
    
    // Force simulation
    const simulation = d3.forceSimulation(graphData.nodes)
        .force('link', d3.forceLink(graphData.links)
            .id(d => d.id)
            .distance(d => d.type === 'contains' ? 50 : 100))
        .force('charge', d3.forceManyBody().strength(-500))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(d => sizeScale(d.lines || 1) + 5));
    
    // Draw links
    const link = g.append('g')
        .attr('class', 'links')
        .selectAll('line')
        .data(graphData.links)
        .enter().append('line')
        .attr('stroke', d => {
            const colors = {
                'imports': '#64748b',
                'contains': '#94a3b8',
                'inherits': '#f59e0b',
                'uses': '#10b981'
            };
            return colors[d.type] || '#475569';
        })
        .attr('stroke-opacity', 0.6)
        .attr('stroke-width', d => d.type === 'contains' ? 1 : 2);
    
    // Draw nodes
    const node = g.append('g')
        .attr('class', 'nodes')
        .selectAll('circle')
        .data(graphData.nodes)
        .enter().append('circle')
        .attr('r', d => sizeScale(d.lines || 1))
        .attr('fill', d => colorScale(d.type))
        .attr('stroke', '#fff')
        .attr('stroke-width', 2)
        .style('cursor', 'pointer')
        .on('click', (event, d) => {
            event.stopPropagation();
            selectNode(d.id);
        })
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));
    
    // Add labels
    const label = g.append('g')
        .attr('class', 'labels')
        .selectAll('text')
        .data(graphData.nodes)
        .enter().append('text')
        .text(d => d.name)
        .style('font-size', '10px')
        .style('fill', '#e2e8f0')
        .style('pointer-events', 'none');
    
    // Add tooltips
    node.append('title')
        .text(d => `${d.name}\nType: ${d.type}\nPath: ${d.path}${d.lines ? `\nLines: ${d.lines}` : ''}`);
    
    // Update positions
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
            .attr('x', d => d.x + 12)
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
    
    // Fit to view
    setTimeout(() => {
        const bounds = g.node().getBBox();
        const fullWidth = width;
        const fullHeight = height;
        const widthScale = fullWidth / bounds.width;
        const heightScale = fullHeight / bounds.height;
        const scale = 0.8 * Math.min(widthScale, heightScale);
        const translate = [fullWidth / 2 - scale * (bounds.x + bounds.width / 2),
                          fullHeight / 2 - scale * (bounds.y + bounds.height / 2)];
        
        svg.call(zoom.transform, d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale));
    }, 500);
}

// Select node and show details
async function selectNode(nodeId) {
    selectedNode = nodeId;
    
    // Highlight in graph
    d3.selectAll('.nodes circle')
        .attr('opacity', d => d.id === nodeId ? 1 : 0.3)
        .attr('stroke-width', d => d.id === nodeId ? 4 : 2);
    
    // Show details
    const node = graphData.nodes.find(n => n.id === nodeId);
    if (!node) return;
    
    const details = document.getElementById('nodeDetails');
    details.innerHTML = `
        <h3 class="font-bold text-lg mb-2">${node.name}</h3>
        <div class="space-y-1 text-sm">
            <div><span class="text-gray-400">Type:</span> <span class="capitalize">${node.type}</span></div>
            <div><span class="text-gray-400">Path:</span> <code class="text-xs bg-gray-700 px-1 rounded">${node.path}</code></div>
            ${node.lines ? `<div><span class="text-gray-400">Lines:</span> ${node.lines}</div>` : ''}
            ${node.line ? `<div><span class="text-gray-400">Line:</span> ${node.line}</div>` : ''}
        </div>
    `;
    
    // Load impact analysis
    try {
        const response = await fetch(`${API_BASE}/impact/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ node_id: nodeId, max_depth: 5 })
        });
        const impact = await response.json();
        displayImpactSummary(impact.summary);
        
        // Store for heatmap
        impactHeatmap = impact;
        
    } catch (error) {
        console.error('Failed to load impact:', error);
    }
}

// Display impact summary
function displayImpactSummary(summary) {
    const container = document.getElementById('impactSummary');
    container.classList.remove('hidden');
    
    document.getElementById('highImpactCount').textContent = summary.impact_distribution.high;
    document.getElementById('mediumImpactCount').textContent = summary.impact_distribution.medium;
    document.getElementById('lowImpactCount').textContent = summary.impact_distribution.low;
}

// Render impact heatmap
function renderImpactHeatmap() {
    const container = document.getElementById('impactHeatmap');
    if (!container || !impactHeatmap) {
        container.innerHTML = '<p class="text-center text-gray-400 mt-20">Select a node to see impact analysis</p>';
        return;
    }
    
    container.innerHTML = '';
    
    // Create heatmap grid
    const impactNodes = impactHeatmap.impact_nodes;
    if (impactNodes.length === 0) {
        container.innerHTML = '<p class="text-center text-gray-400 mt-20">No impact found</p>';
        return;
    }
    
    // Group by file
    const fileImpacts = {};
    impactNodes.forEach(node => {
        const file = node.path.split(':')[0];
        if (!fileImpacts[file]) {
            fileImpacts[file] = [];
        }
        fileImpacts[file].push(node);
    });
    
    // Create grid
    const grid = document.createElement('div');
    grid.className = 'grid grid-cols-4 gap-2 p-4';
    
    Object.entries(fileImpacts).forEach(([file, nodes]) => {
        const maxImpact = Math.max(...nodes.map(n => n.impact_score));
        const cell = document.createElement('div');
        cell.className = `heatmap-cell p-4 rounded cursor-pointer text-center ${
            maxImpact > 0.7 ? 'impact-high' : 
            maxImpact > 0.3 ? 'impact-medium' : 
            'impact-low'
        }`;
        cell.innerHTML = `
            <div class="font-semibold text-sm">${file.split('/').pop()}</div>
            <div class="text-xs mt-1">${nodes.length} items</div>
            <div class="text-xs">Impact: ${(maxImpact * 100).toFixed(0)}%</div>
        `;
        cell.addEventListener('click', () => {
            alert(`File: ${file}\nImpacted items: ${nodes.map(n => n.name).join(', ')}`);
        });
        grid.appendChild(cell);
    });
    
    container.appendChild(grid);
}

// Render architecture diagram
function renderArchitectureDiagram() {
    const container = document.getElementById('architectureDiagram');
    if (!container || !graphData) {
        container.innerHTML = '<p class="text-center text-gray-400 mt-20">No architecture data available</p>';
        return;
    }
    
    container.innerHTML = '';
    
    // Group nodes by directory
    const layers = {};
    graphData.nodes.forEach(node => {
        if (node.type === 'file') {
            const parts = node.path.split('/');
            const layer = parts[0] || 'root';
            if (!layers[layer]) {
                layers[layer] = [];
            }
            layers[layer].push(node);
        }
    });
    
    // Create layered architecture view
    const svg = d3.select(container)
        .append('svg')
        .attr('width', '100%')
        .attr('height', '100%')
        .attr('viewBox', '0 0 800 600');
    
    const layerNames = Object.keys(layers);
    const layerHeight = 500 / layerNames.length;
    
    layerNames.forEach((layer, i) => {
        // Draw layer
        const g = svg.append('g')
            .attr('transform', `translate(50, ${50 + i * layerHeight})`);
        
        g.append('rect')
            .attr('width', 700)
            .attr('height', layerHeight - 10)
            .attr('fill', '#1e293b')
            .attr('stroke', '#475569')
            .attr('rx', 5);
        
        g.append('text')
            .attr('x', 10)
            .attr('y', 20)
            .text(layer)
            .style('fill', '#e2e8f0')
            .style('font-weight', 'bold');
        
        // Add components
        const components = layers[layer].slice(0, 5); // Limit for display
        components.forEach((comp, j) => {
            g.append('rect')
                .attr('x', 20 + j * 130)
                .attr('y', 40)
                .attr('width', 120)
                .attr('height', 40)
                .attr('fill', '#3b82f6')
                .attr('rx', 3)
                .style('cursor', 'pointer')
                .on('click', () => selectNode(comp.id));
            
            g.append('text')
                .attr('x', 80 + j * 130)
                .attr('y', 65)
                .text(comp.name.substring(0, 15))
                .style('fill', '#fff')
                .style('font-size', '12px')
                .style('text-anchor', 'middle');
        });
        
        if (layers[layer].length > 5) {
            g.append('text')
                .attr('x', 680)
                .attr('y', 65)
                .text(`+${layers[layer].length - 5} more`)
                .style('fill', '#94a3b8')
                .style('font-size', '12px');
        }
    });
}

// Enhanced search with results display
async function performSearch() {
    const input = document.getElementById('searchInput');
    if (!input || !input.value) return;
    
    try {
        const response = await fetch(`${API_BASE}/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: input.value, limit: 20 })
        });
        const data = await response.json();
        
        displaySearchResults(data.results);
    } catch (error) {
        console.error('Search failed:', error);
    }
}

// Display search results
function displaySearchResults(results) {
    const details = document.getElementById('nodeDetails');
    
    if (!results || results.length === 0) {
        details.innerHTML = '<p class="text-gray-400">No results found</p>';
        return;
    }
    
    details.innerHTML = `
        <h3 class="font-bold text-lg mb-3">Search Results (${results.length})</h3>
        <div class="space-y-2 max-h-96 overflow-y-auto">
            ${results.map(r => `
                <div class="bg-gray-700 p-3 rounded cursor-pointer hover:bg-gray-600" 
                     onclick="selectNode('${r.id}')">
                    <div class="font-semibold">${r.name}</div>
                    <div class="text-sm text-gray-400">${r.path}</div>
                    <div class="text-xs text-blue-400">
                        Score: ${r.relevance_score.toFixed(2)} | 
                        ${r.occurrences} occurrences
                    </div>
                    ${r.matching_lines ? `
                        <div class="mt-1 text-xs">
                            ${r.matching_lines.map(l => 
                                `<div class="text-gray-500">Line ${l.line}: ${l.text}</div>`
                            ).join('')}
                        </div>
                    ` : ''}
                </div>
            `).join('')}
        </div>
    `;
    
    // Highlight in graph
    if (graphData) {
        const resultIds = new Set(results.map(r => r.id));
        d3.selectAll('.nodes circle')
            .attr('opacity', d => resultIds.has(d.id) ? 1 : 0.2)
            .attr('stroke', d => resultIds.has(d.id) ? '#fbbf24' : '#fff')
            .attr('stroke-width', d => resultIds.has(d.id) ? 3 : 2);
    }
}

// Switch tabs with proper rendering
window.switchTab = function(tab) {
    currentView = tab;
    
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('bg-gray-700');
    });
    event.target.classList.add('bg-gray-700');
    
    // Hide all views
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.add('hidden');
    });
    
    // Show selected view
    const viewEl = document.getElementById(`${tab}View`);
    if (viewEl) {
        viewEl.classList.remove('hidden');
    }
    
    // Render appropriate content
    switch (tab) {
        case 'graph':
            if (graphData) renderDependencyGraph();
            break;
        case 'heatmap':
            renderImpactHeatmap();
            break;
        case 'architecture':
            renderArchitectureDiagram();
            break;
    }
};

// Analyze codebase
window.analyzeCodebase = async function() {
    try {
        const response = await fetch(`${API_BASE}/analyze/codebase`, { method: 'POST' });
        const data = await response.json();
        console.log('Analysis started:', data);
        alert('Codebase analysis started. This may take a moment...');
    } catch (error) {
        console.error('Analysis failed:', error);
    }
};

// Claude terminal functions
window.openClaudeTerminal = function() {
    document.getElementById('claudeModal').classList.remove('hidden');
    // Could integrate actual Claude CLI here
};

window.closeClaudeTerminal = function() {
    document.getElementById('claudeModal').classList.add('hidden');
};

// Make search available globally
window.performSearch = performSearch;
window.selectNode = selectNode;

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initialize);