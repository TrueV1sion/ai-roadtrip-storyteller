"""
Neo4j Graph Database Interface for Code Knowledge Graph
"""
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from neo4j import GraphDatabase, Driver
import chromadb
from chromadb.config import Settings
import hashlib
import json


@dataclass
class CodeNode:
    """Represents a code entity in the graph"""
    id: str
    type: str  # file, class, function, variable, etc.
    name: str
    path: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


@dataclass
class CodeRelationship:
    """Represents a relationship between code entities"""
    source_id: str
    target_id: str
    type: str  # imports, calls, extends, modifies, etc.
    metadata: Dict[str, Any]


class KnowledgeGraphDB:
    """Main database interface for the code knowledge graph"""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str,
                 chroma_persist_dir: str = "./chroma_db"):
        # Neo4j for graph relationships
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        # ChromaDB for vector embeddings
        self.chroma_client = chromadb.PersistentClient(
            path=chroma_persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        self.vector_collection = self.chroma_client.get_or_create_collection(
            name="code_embeddings",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Initialize schema
        self._init_schema()
    
    def _init_schema(self):
        """Initialize graph database schema"""
        with self.driver.session() as session:
            # Create indexes for performance
            session.run("""
                CREATE INDEX code_id IF NOT EXISTS FOR (n:Code) ON (n.id)
            """)
            session.run("""
                CREATE INDEX code_path IF NOT EXISTS FOR (n:Code) ON (n.path)
            """)
            session.run("""
                CREATE INDEX code_type IF NOT EXISTS FOR (n:Code) ON (n.type)
            """)
            
            # Create constraints
            session.run("""
                CREATE CONSTRAINT unique_code_id IF NOT EXISTS 
                FOR (n:Code) REQUIRE n.id IS UNIQUE
            """)
    
    def add_code_node(self, node: CodeNode) -> str:
        """Add a code node to the graph"""
        with self.driver.session() as session:
            result = session.run("""
                MERGE (n:Code {id: $id})
                SET n.type = $type,
                    n.name = $name,
                    n.path = $path,
                    n.content = $content,
                    n.metadata = $metadata,
                    n.updated_at = timestamp()
                RETURN n.id as id
            """, 
                id=node.id,
                type=node.type,
                name=node.name,
                path=node.path,
                content=node.content,
                metadata=json.dumps(node.metadata)
            )
            
            # Store embedding in ChromaDB if provided
            if node.embedding:
                self.vector_collection.upsert(
                    ids=[node.id],
                    embeddings=[node.embedding],
                    metadatas=[{
                        "type": node.type,
                        "name": node.name,
                        "path": node.path
                    }],
                    documents=[node.content[:1000]]  # Store snippet for context
                )
            
            return result.single()["id"]
    
    def add_relationship(self, rel: CodeRelationship) -> bool:
        """Add a relationship between code nodes"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (a:Code {id: $source_id})
                MATCH (b:Code {id: $target_id})
                MERGE (a)-[r:RELATES {type: $type}]->(b)
                SET r.metadata = $metadata,
                    r.updated_at = timestamp()
                RETURN r
            """,
                source_id=rel.source_id,
                target_id=rel.target_id,
                type=rel.type,
                metadata=json.dumps(rel.metadata)
            )
            return result.single() is not None
    
    def find_impact_nodes(self, node_id: str, depth: int = 3) -> List[Dict[str, Any]]:
        """Find all nodes that could be impacted by changes to the given node"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (start:Code {id: $node_id})
                CALL apoc.path.subgraphAll(start, {
                    maxLevel: $depth,
                    relationshipFilter: "IMPORTS|CALLS|EXTENDS|USES|MODIFIES"
                })
                YIELD nodes, relationships
                UNWIND nodes as node
                RETURN DISTINCT node.id as id, 
                       node.type as type,
                       node.name as name,
                       node.path as path,
                       size([(node)-[]-() | 1]) as impact_score
                ORDER BY impact_score DESC
            """, node_id=node_id, depth=depth)
            
            return [dict(record) for record in result]
    
    def semantic_search(self, query: str, embedding: List[float], 
                       limit: int = 10) -> List[Tuple[str, float]]:
        """Search for similar code using vector embeddings"""
        results = self.vector_collection.query(
            query_embeddings=[embedding],
            n_results=limit
        )
        
        if results['ids']:
            return list(zip(results['ids'][0], results['distances'][0]))
        return []
    
    def get_node_context(self, node_id: str) -> Dict[str, Any]:
        """Get full context for a node including relationships"""
        with self.driver.session() as session:
            # Get node details
            node_result = session.run("""
                MATCH (n:Code {id: $node_id})
                RETURN n
            """, node_id=node_id).single()
            
            if not node_result:
                return {}
            
            # Get relationships
            rel_result = session.run("""
                MATCH (n:Code {id: $node_id})-[r]-(m:Code)
                RETURN type(r) as rel_type, 
                       r.type as rel_subtype,
                       m.id as connected_id,
                       m.name as connected_name,
                       m.type as connected_type,
                       CASE 
                           WHEN startNode(r) = n THEN 'outgoing'
                           ELSE 'incoming'
                       END as direction
            """, node_id=node_id)
            
            node_data = dict(node_result["n"])
            node_data["relationships"] = [dict(r) for r in rel_result]
            
            return node_data
    
    def add_agent_note(self, agent_id: str, node_id: str, note: str, 
                      note_type: str = "observation") -> str:
        """Add an agent note to a code node"""
        note_id = hashlib.sha256(f"{agent_id}:{node_id}:{note}".encode()).hexdigest()[:16]
        
        with self.driver.session() as session:
            session.run("""
                MATCH (n:Code {id: $node_id})
                CREATE (note:AgentNote {
                    id: $note_id,
                    agent_id: $agent_id,
                    content: $note,
                    type: $note_type,
                    created_at: timestamp()
                })
                CREATE (note)-[:ABOUT]->(n)
            """, 
                node_id=node_id,
                note_id=note_id,
                agent_id=agent_id,
                note=note,
                note_type=note_type
            )
        
        return note_id
    
    def get_agent_notes(self, node_id: Optional[str] = None, 
                       agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get agent notes, optionally filtered by node or agent"""
        query = "MATCH (note:AgentNote)"
        conditions = []
        params = {}
        
        if node_id:
            query += "-[:ABOUT]->(n:Code {id: $node_id})"
            params["node_id"] = node_id
        
        if agent_id:
            conditions.append("note.agent_id = $agent_id")
            params["agent_id"] = agent_id
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " RETURN note ORDER BY note.created_at DESC"
        
        with self.driver.session() as session:
            result = session.run(query, **params)
            return [dict(r["note"]) for r in result]
    
    def close(self):
        """Close database connections"""
        self.driver.close()