// Knowledge Graph Explorer
const API_BASE = window.location.origin + '/api';

// Load graph on startup
fetch(`${API_BASE}/graph/structure`)
    .then(res => res.json())
    .then(data => {
        console.log('Graph data:', data);
        if (data && data.nodes) {
            renderGraph(data);
        }
    })
    .catch(err => console.error('Failed to load graph:', err));

function renderGraph(data) {
    const container = document.getElementById('dependencyGraph');
    if (!container) return;
    
    // Clear container
    container.innerHTML = '';
    
    const svg = d3.select(container)
        .append('svg')
        .attr('width', '100%')
        .attr('height', '100%')
        .attr('viewBox', '0 0 800 600');
    
    const simulation = d3.forceSimulation(data.nodes)
        .force('link', d3.forceLink(data.links).id(d => d.id))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(400, 300));
    
    const link = svg.append('g')
        .selectAll('line')
        .data(data.links)
        .enter().append('line')
        .style('stroke', '#999')
        .style('stroke-opacity', 0.6);
    
    const node = svg.append('g')
        .selectAll('circle')
        .data(data.nodes)
        .enter().append('circle')
        .attr('r', 10)
        .style('fill', '#69b3ff')
        .style('cursor', 'pointer')
        .on('click', (event, d) => {
            document.getElementById('nodeDetails').innerHTML = `
                <h3 class="font-bold">${d.name}</h3>
                <p>Type: ${d.type}</p>
                <p>Path: ${d.path}</p>
            `;
        });
    
    const label = svg.append('g')
        .selectAll('text')
        .data(data.nodes)
        .enter().append('text')
        .text(d => d.name)
        .style('font-size', '10px')
        .style('fill', '#fff');
    
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
}

// Global functions for onclick handlers
window.performSearch = function() {
    const input = document.getElementById('searchInput');
    if (!input.value) return;
    
    fetch(`${API_BASE}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: input.value })
    })
    .then(res => res.json())
    .then(data => {
        console.log('Search results:', data);
        alert(`Found ${data.results?.length || 0} results`);
    })
    .catch(err => console.error('Search failed:', err));
};

window.analyzeCodebase = function() {
    fetch(`${API_BASE}/analyze/codebase`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            console.log('Analysis:', data);
            alert('Analysis started');
        })
        .catch(err => console.error('Analysis failed:', err));
};

window.switchTab = function(tab) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    // Show selected tab
    const tabEl = document.getElementById(`${tab}View`);
    if (tabEl) tabEl.classList.remove('hidden');
};

window.openClaudeTerminal = function() {
    document.getElementById('claudeModal').classList.remove('hidden');
};

window.closeClaudeTerminal = function() {
    document.getElementById('claudeModal').classList.add('hidden');
};