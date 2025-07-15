"""
Change impact analysis and heatmap generation
"""
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import networkx as nx
import numpy as np


@dataclass
class ImpactNode:
    """Node in the impact graph"""
    id: str
    path: str
    type: str
    name: str
    impact_score: float = 0.0
    direct_impacts: int = 0
    indirect_impacts: int = 0
    depth: int = 0


@dataclass
class ImpactHeatmap:
    """Heatmap showing change impact across codebase"""
    source_node: str
    impact_nodes: List[ImpactNode]
    impact_matrix: np.ndarray
    file_impacts: Dict[str, float]
    critical_paths: List[List[str]]


class ImpactAnalyzer:
    """Analyze and visualize change impact across codebase"""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.impact_cache = {}
    
    def build_dependency_graph(self, entities: List, relationships: List[Tuple[str, str, str]]):
        """Build NetworkX graph from entities and relationships"""
        # Add nodes
        for entity in entities:
            self.graph.add_node(
                entity.id,
                path=entity.path,
                type=entity.type,
                name=entity.name,
                content=entity.content
            )
        
        # Add edges with weights based on relationship type
        relationship_weights = {
            "imports": 0.8,
            "calls": 0.9,
            "extends": 1.0,
            "modifies": 1.0,
            "uses": 0.7,
            "defined_in": 0.5,
            "test_for": 0.6
        }
        
        for source, target, rel_type in relationships:
            weight = relationship_weights.get(rel_type, 0.5)
            if source in self.graph and target in self.graph:
                self.graph.add_edge(source, target, type=rel_type, weight=weight)
    
    def analyze_change_impact(self, changed_node_id: str, max_depth: int = 5) -> ImpactHeatmap:
        """Analyze impact of changes to a specific node"""
        if changed_node_id not in self.graph:
            return ImpactHeatmap(
                source_node=changed_node_id,
                impact_nodes=[],
                impact_matrix=np.array([]),
                file_impacts={},
                critical_paths=[]
            )
        
        # Check cache
        cache_key = f"{changed_node_id}:{max_depth}"
        if cache_key in self.impact_cache:
            return self.impact_cache[cache_key]
        
        # Calculate impact propagation
        impact_nodes = self._calculate_impact_propagation(changed_node_id, max_depth)
        
        # Group impacts by file
        file_impacts = self._aggregate_file_impacts(impact_nodes)
        
        # Find critical paths
        critical_paths = self._find_critical_paths(changed_node_id, impact_nodes)
        
        # Build impact matrix
        impact_matrix = self._build_impact_matrix(impact_nodes)
        
        heatmap = ImpactHeatmap(
            source_node=changed_node_id,
            impact_nodes=impact_nodes,
            impact_matrix=impact_matrix,
            file_impacts=file_impacts,
            critical_paths=critical_paths
        )
        
        # Cache result
        self.impact_cache[cache_key] = heatmap
        
        return heatmap
    
    def _calculate_impact_propagation(self, source_id: str, max_depth: int) -> List[ImpactNode]:
        """Calculate impact propagation using BFS with decay"""
        impact_nodes = []
        visited = set()
        queue = [(source_id, 0, 1.0)]  # (node_id, depth, impact_score)
        
        # Impact decay factor per level
        decay_factor = 0.7
        
        while queue:
            node_id, depth, impact_score = queue.pop(0)
            
            if node_id in visited or depth > max_depth:
                continue
            
            visited.add(node_id)
            
            # Get node data
            node_data = self.graph.nodes[node_id]
            
            # Count direct and indirect impacts
            direct_impacts = len(list(self.graph.successors(node_id)))
            indirect_impacts = len(nx.descendants(self.graph, node_id)) - direct_impacts
            
            impact_node = ImpactNode(
                id=node_id,
                path=node_data['path'],
                type=node_data['type'],
                name=node_data['name'],
                impact_score=impact_score,
                direct_impacts=direct_impacts,
                indirect_impacts=indirect_impacts,
                depth=depth
            )
            
            impact_nodes.append(impact_node)
            
            # Propagate to dependent nodes
            for successor in self.graph.successors(node_id):
                edge_data = self.graph.edges[node_id, successor]
                edge_weight = edge_data.get('weight', 0.5)
                next_impact = impact_score * decay_factor * edge_weight
                
                if next_impact > 0.1:  # Threshold to prevent infinite propagation
                    queue.append((successor, depth + 1, next_impact))
        
        # Sort by impact score
        impact_nodes.sort(key=lambda x: x.impact_score, reverse=True)
        
        return impact_nodes
    
    def _aggregate_file_impacts(self, impact_nodes: List[ImpactNode]) -> Dict[str, float]:
        """Aggregate impact scores by file"""
        file_impacts = defaultdict(float)
        file_node_counts = defaultdict(int)
        
        for node in impact_nodes:
            file_impacts[node.path] += node.impact_score
            file_node_counts[node.path] += 1
        
        # Normalize by number of impacted nodes in each file
        for file_path in file_impacts:
            file_impacts[file_path] = file_impacts[file_path] / max(1, file_node_counts[file_path])
        
        return dict(sorted(file_impacts.items(), key=lambda x: x[1], reverse=True))
    
    def _find_critical_paths(self, source_id: str, impact_nodes: List[ImpactNode], 
                           num_paths: int = 5) -> List[List[str]]:
        """Find the most critical impact paths"""
        critical_paths = []
        target_nodes = [node.id for node in impact_nodes[:10]]  # Top 10 impacted nodes
        
        for target in target_nodes:
            if target == source_id:
                continue
            
            try:
                # Find shortest path (most direct impact)
                path = nx.shortest_path(self.graph, source_id, target)
                
                # Calculate path impact score
                path_score = 1.0
                for i in range(len(path) - 1):
                    if self.graph.has_edge(path[i], path[i + 1]):
                        edge_weight = self.graph.edges[path[i], path[i + 1]].get('weight', 0.5)
                        path_score *= edge_weight
                
                critical_paths.append((path, path_score))
            except nx.NetworkXNoPath:
                continue
        
        # Sort by path score and return top paths
        critical_paths.sort(key=lambda x: x[1], reverse=True)
        return [path for path, _ in critical_paths[:num_paths]]
    
    def _build_impact_matrix(self, impact_nodes: List[ImpactNode]) -> np.ndarray:
        """Build impact matrix for visualization"""
        if not impact_nodes:
            return np.array([])
        
        # Group nodes by file
        file_nodes = defaultdict(list)
        for node in impact_nodes:
            file_nodes[node.path].append(node)
        
        # Build matrix
        files = sorted(file_nodes.keys())
        matrix_size = len(files)
        impact_matrix = np.zeros((matrix_size, matrix_size))
        
        # Fill matrix with impact relationships
        for i, file1 in enumerate(files):
            for j, file2 in enumerate(files):
                if i == j:
                    # Self impact is sum of node impacts in file
                    impact_matrix[i, j] = sum(node.impact_score for node in file_nodes[file1])
                else:
                    # Cross-file impact
                    impact = 0.0
                    for node1 in file_nodes[file1]:
                        for node2 in file_nodes[file2]:
                            if self.graph.has_edge(node1.id, node2.id):
                                edge_data = self.graph.edges[node1.id, node2.id]
                                impact += edge_data.get('weight', 0.5)
                    impact_matrix[i, j] = impact
        
        return impact_matrix
    
    def get_impact_summary(self, heatmap: ImpactHeatmap) -> Dict[str, Any]:
        """Get human-readable impact summary"""
        return {
            "source_node": heatmap.source_node,
            "total_impacted_nodes": len(heatmap.impact_nodes),
            "total_impacted_files": len(heatmap.file_impacts),
            "high_impact_files": [
                {"path": path, "score": score}
                for path, score in list(heatmap.file_impacts.items())[:5]
            ],
            "critical_paths": [
                {
                    "path": " -> ".join(self.graph.nodes[node_id]['name'] for node_id in path),
                    "length": len(path)
                }
                for path in heatmap.critical_paths
            ],
            "impact_distribution": {
                "high": len([n for n in heatmap.impact_nodes if n.impact_score > 0.7]),
                "medium": len([n for n in heatmap.impact_nodes if 0.3 < n.impact_score <= 0.7]),
                "low": len([n for n in heatmap.impact_nodes if n.impact_score <= 0.3])
            }
        }