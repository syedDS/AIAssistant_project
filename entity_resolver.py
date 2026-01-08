"""
Entity Resolution Engine
Solves the "J. Smith vs John Smith" problem
Implements fuzzy matching, alias detection, and entity linking
"""
import os
import re
import json
import hashlib
from datetime import datetime
from difflib import SequenceMatcher
from config import ENTITY_CACHE


class EntityResolver:
    """
    Resolves entity names to canonical forms.
    Handles abbreviations, aliases, and fuzzy matching.
    """
    
    def __init__(self, cache_file=ENTITY_CACHE):
        self.cache_file = cache_file
        self.entity_aliases = self._load_cache()
        self.canonical_entities = {}
    
    def _load_cache(self):
        """Load entity resolution cache from disk"""
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_cache(self):
        """Save entity resolution cache to disk"""
        with open(self.cache_file, 'w') as f:
            json.dump(self.entity_aliases, f, indent=2)
    
    def normalize_entity_name(self, name):
        """Normalize entity name for comparison"""
        normalized = name.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = re.sub(r'[^\w\s-]', '', normalized)
        
        # Expand common abbreviations
        abbreviations = {
            'db': 'database',
            'srv': 'server',
            'app': 'application',
            'fw': 'firewall',
            'lb': 'load balancer',
        }
        
        for abbr, full in abbreviations.items():
            normalized = re.sub(rf'\b{abbr}\b', full, normalized)
        
        return normalized
    
    def similarity_score(self, name1, name2):
        """Calculate similarity between two entity names"""
        norm1 = self.normalize_entity_name(name1)
        norm2 = self.normalize_entity_name(name2)
        
        if norm1 == norm2:
            return 1.0
        
        ratio = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Boost if one contains the other
        if norm1 in norm2 or norm2 in norm1:
            ratio = max(ratio, 0.85)
        
        # Check for abbreviation patterns
        if self._is_abbreviation_match(norm1, norm2):
            ratio = max(ratio, 0.9)
        
        return ratio
    
    def _is_abbreviation_match(self, name1, name2):
        """Check if one name is an abbreviation of another"""
        words1 = name1.split()
        words2 = name2.split()
        
        if len(words1) != len(words2):
            return False
        
        for w1, w2 in zip(words1, words2):
            if len(w1) == 1 or len(w2) == 1:
                if not (w1[0] == w2[0]):
                    return False
            elif w1 != w2:
                return False
        
        return True
    
    def resolve_entity(self, name, entity_type, threshold=0.85):
        """
        Resolve entity to canonical form.
        Returns: (canonical_id, confidence, is_new)
        """
        cache_key = f"{entity_type}:{name}"
        
        # Check cache first
        if cache_key in self.entity_aliases:
            return self.entity_aliases[cache_key], 1.0, False
        
        # Find best match among existing entities
        best_match = None
        best_score = 0.0
        
        for existing_key, canonical_id in self.entity_aliases.items():
            if not existing_key.startswith(f"{entity_type}:"):
                continue
            
            existing_name = existing_key.split(':', 1)[1]
            score = self.similarity_score(name, existing_name)
            
            if score > best_score:
                best_score = score
                best_match = canonical_id
        
        # Reuse existing if good match found
        if best_score >= threshold:
            self.entity_aliases[cache_key] = best_match
            self.save_cache()
            return best_match, best_score, False
        
        # Create new canonical entity
        canonical_id = self._generate_canonical_id(name, entity_type)
        self.entity_aliases[cache_key] = canonical_id
        self.canonical_entities[canonical_id] = {
            'primary_name': name,
            'type': entity_type,
            'aliases': [name],
            'created_at': datetime.now().isoformat()
        }
        self.save_cache()
        
        return canonical_id, 1.0, True
    
    def _generate_canonical_id(self, name, entity_type):
        """Generate unique canonical ID"""
        normalized = self.normalize_entity_name(name)
        hash_suffix = hashlib.md5(
            f"{entity_type}:{normalized}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:8]
        return f"{entity_type}_{normalized.replace(' ', '_')}_{hash_suffix}"
    
    def add_alias(self, canonical_id, alias):
        """Add alias to existing entity"""
        if canonical_id in self.canonical_entities:
            self.canonical_entities[canonical_id]['aliases'].append(alias)
            self.save_cache()


# Create instance in graphrag_app.py to avoid circular imports
def create_resolver():
    return EntityResolver()
