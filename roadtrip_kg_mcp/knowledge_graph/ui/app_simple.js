// Knowledge Graph Explorer - Simplified Version

const API_BASE = window.location.origin + '/api';

// Global state
let graphData = null;

// Load and render graph
async function loadGraph() {
    try {
        const response = await fetch(`${API_BASE}/graph/structure`);
        graphData = await response.json();
        console.log('Graph loaded:', graphData);
        
        if (graphData && graphData.nodes) {
            renderGraph();
        }
    } catch (error) {
        console.error('Failed to load graph:', error);
    }
}

// Simple graph rendering
function renderGraph() {
    const container = document.getElementById('dependencyGraph');
    if (!container) return;
    
    const width = 800;
    const height = 600;
    
    // Clear existing
    d3.select(container).selectAll('*').remove();
    
    const svg = d3.select(container)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .style('background', '#1a1a1a');
    
    // Simple force simulation
    const simulation = d3.forceSimulation(graphData.nodes)
        .force('link', d3.forceLink(graphData.links).id(d => d.id))
        .force('charge', d3.forceManyBody().strength(-200))
        .force('center', d3.forceCenter(width / 2, height / 2));
    
    // Draw links
    const link = svg.append('g')
        .selectAll('line')
        .data(graphData.links)
        .enter().append('line')
        .style('stroke', '#666')
        .style('stroke-width', 1);
    
    // Draw nodes
    const node = svg.append('g')
        .selectAll('circle')
        .data(graphData.nodes)
        .enter().append('circle')
        .attr('r', 8)
        .style('fill', '#4a9eff')
        .style('cursor', 'pointer');
    
    // Node click handler
    node.on('click', function(event, d) {
        console.log('Node clicked:', d);
        showNodeDetails(d);
    });
    
    // Add drag behavior
    node.call(d3.drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended));
    
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
    });
    
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

// Show node details
function showNodeDetails(node) {
    const details = document.getElementById('nodeDetails');
    if (details) {
        details.innerHTML = `
            <h3>${node.name}</h3>
            <p>Type: ${node.type}</p>
            <p>Path: ${node.path}</p>
        `;
    }
}

// Search functionality
async function performSearch() {
    const input = document.getElementById('searchInput');
    if (!input || !input.value) return;
    
    console.log('Searching for:', input.value);
    
    try {
        const response = await fetch(`${API_BASE}/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: input.value, limit: 10 })
        });
        const data = await response.json();
        console.log('Search results:', data);
        
        if (data.results && data.results.length > 0) {
            alert(`Found ${data.results.length} results. First: ${data.results[0].name}`);
        } else {
            alert('No results found');
        }
    } catch (error) {
        console.error('Search failed:', error);
    }
}

// Analyze codebase
async function analyzeCodebase() {
    console.log('Starting analysis...');
    
    try {
        const response = await fetch(`${API_BASE}/analyze/codebase`, {
            method: 'POST'
        });
        const data = await response.json();
        console.log('Analysis response:', data);
        alert('Analysis started: ' + JSON.stringify(data));
    } catch (error) {
        console.error('Analysis failed:', error);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing Knowledge Graph...');
    
    // Load graph
    loadGraph();
    
    // Set up search
    const searchBtn = document.querySelector('button[onclick="performSearch()"]');
    if (searchBtn) {
        searchBtn.onclick = performSearch;
    }
    
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') performSearch();
        });
    }
    
    // Set up analyze button
    const analyzeBtn = document.querySelector('button[onclick="analyzeCodebase()"]');
    if (analyzeBtn) {
        analyzeBtn.onclick = analyzeCodebase;
    }
    
    console.log('Setup complete');
});

// Make functions globally available
window.performSearch = performSearch;
window.analyzeCodebase = analyzeCodebase;
window.showNodeDetails = showNodeDetails;