"""
Neo4j Graph Database Handler
Validated graph operations with entity resolution
"""
from datetime import datetime
from neo4j import GraphDatabase
from config import NEO4J_CONFIG
from ontology import ontology


class ValidatedNeo4jGraph:
    """Neo4j graph with strict validation and entity resolution"""
    
    def __init__(self, entity_resolver=None):
        self.driver = None
        self.entity_resolver = entity_resolver
        self._connect()
    
    def set_entity_resolver(self, entity_resolver):
        """Set entity resolver after initialization"""
        self.entity_resolver = entity_resolver
    
    def _connect(self):
        """Establish connection to Neo4j"""
        try:
            self.driver = GraphDatabase.driver(
                NEO4J_CONFIG['uri'],
                auth=(NEO4J_CONFIG['user'], NEO4J_CONFIG['password'])
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            print("✅ Neo4j connected")
            self._init_schema()
        except Exception as e:
            print(f"⚠️  Neo4j connection failed: {e}")
            self.driver = None
    
    def _init_schema(self):
        """Initialize schema with constraints and indexes"""
        if not self.driver:
            return
        
        with self.driver.session() as session:
            # Unique constraint
            session.run(
                "CREATE CONSTRAINT entity_canonical_id IF NOT EXISTS "
                "FOR (e:Entity) REQUIRE e.canonical_id IS UNIQUE"
            )
            # Indexes for faster queries
            session.run("CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)")
            session.run("CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)")
            session.run("CREATE INDEX entity_confidence IF NOT EXISTS FOR (e:Entity) ON (e.confidence)")
        
        print("✅ Neo4j schema initialized")
    
    def add_validated_entity(self, name, entity_type, properties, confidence):
        """Add entity with validation and resolution"""
        if not self.driver:
            return None
        
        if not self.entity_resolver:
            print("⚠️  Entity resolver not set")
            return None
        
        # Validate against ontology
        is_valid, message = ontology.validate_entity(entity_type, properties)
        if not is_valid:
            print(f"⚠️  Entity validation failed: {message}")
            return None
        
        # Resolve to canonical form
        canonical_id, resolution_confidence, is_new = self.entity_resolver.resolve_entity(
            name, entity_type
        )
        
        # Combine confidences
        final_confidence = confidence * resolution_confidence
        
        # Build properties
        props = properties.copy()
        props.update({
            'canonical_id': canonical_id,
            'name': name,
            'type': entity_type,
            'confidence': final_confidence,
            'is_canonical': is_new,
            'created_at': datetime.now().isoformat()
        })
        
        # Add to graph
        with self.driver.session() as session:
            session.run("""
                MERGE (e:Entity {canonical_id: $canonical_id})
                SET e += $props
            """, {'canonical_id': canonical_id, 'props': props})
        
        return canonical_id
    
    def add_validated_relationship(self, source_name, target_name, 
                                   source_type, target_type, rel_type, 
                                   properties, confidence, evidence):
        """Add relationship with validation"""
        if not self.driver:
            return False
        
        if not self.entity_resolver:
            print("⚠️  Entity resolver not set")
            return False
        
        # Validate relationship
        is_valid, message = ontology.validate_relationship(
            rel_type, source_type, target_type, properties
        )
        if not is_valid:
            print(f"⚠️  Relationship validation failed: {message}")
            return False
        
        # Resolve entities
        source_id, _, _ = self.entity_resolver.resolve_entity(source_name, source_type)
        target_id, _, _ = self.entity_resolver.resolve_entity(target_name, target_type)
        
        # Build properties
        props = properties.copy()
        props.update({
            'confidence': confidence,
            'evidence': evidence,
            'created_at': datetime.now().isoformat()
        })
        
        # Add to graph
        with self.driver.session() as session:
            session.run(f"""
                MATCH (source:Entity {{canonical_id: $source_id}})
                MATCH (target:Entity {{canonical_id: $target_id}})
                MERGE (source)-[r:{rel_type}]->(target)
                SET r += $props
            """, {
                'source_id': source_id,
                'target_id': target_id,
                'props': props
            })
        
        return True
    
    def search_entities(self, query, limit=10):
        """Search entities by name (case-insensitive)"""
        if not self.driver:
            return []
        
        results = []
        with self.driver.session() as session:
            res = session.run("""
                MATCH (e:Entity)
                WHERE toLower(e.name) CONTAINS toLower($q)
                RETURN e.name AS name, e.type AS type, e.confidence AS confidence
                LIMIT $limit
            """, {'q': query, 'limit': limit})
            
            for record in res:
                results.append({
                    'name': record['name'],
                    'type': record['type'],
                    'confidence': record.get('confidence')
                })
        
        return results
    
    def get_statistics(self):
        """Get graph statistics"""
        if not self.driver:
            return {'total_entities': 0, 'total_relationships': 0}
        
        with self.driver.session() as session:
            entity_result = session.run("MATCH (e:Entity) RETURN count(e) as count").single()
            rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()
            
            return {
                'total_entities': entity_result['count'] if entity_result else 0,
                'total_relationships': rel_result['count'] if rel_result else 0
            }
    
    def close(self):
        """Close the database connection"""
        if self.driver:
            self.driver.close()
            print("Neo4j connection closed")


# Factory function - create instance in graphrag_app.py
def create_neo4j_graph(entity_resolver=None):
    return ValidatedNeo4jGraph(entity_resolver)
