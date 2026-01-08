"""
LLM-Based Entity Extraction with Validation
Extracts entities with confidence scores and detects hallucinations
"""
import re
import json
from langchain_core.prompts import ChatPromptTemplate
from ontology import ontology


class ValidatedEntityExtractor:
    """
    Extract entities using LLM with confidence scores and validation.
    Detects and flags potential hallucinations.
    """
    
    def __init__(self, llm):
        self.llm = llm
        self.extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a security entity extraction expert. Extract ONLY entities that are explicitly mentioned in the text.

CRITICAL RULES:
1. DO NOT invent or infer entities not explicitly stated
2. Include a confidence score (0.0-1.0) for each entity
3. Mark uncertain extractions with confidence < 0.7
4. Extract relationships ONLY if both entities are clearly mentioned
5. Use exact text spans from the document

Output format (JSON):
{{
  "entities": [
    {{
      "name": "exact name from text",
      "type": "SecurityControl|Asset|Threat|ComplianceControl",
      "subtype": "specific subtype",
      "confidence": 0.0-1.0,
      "text_span": "surrounding context from document",
      "properties": {{}}
    }}
  ],
  "relationships": [
    {{
      "source": "entity name",
      "target": "entity name",
      "type": "PROTECTS|MITIGATES|DEPENDS_ON|THREATENS|IMPLEMENTS",
      "confidence": 0.0-1.0,
      "evidence": "quote from text showing this relationship",
      "properties": {{}}
    }}
  ]
}}

Text to analyze: {text}"""),
            ("human", "Extract entities and relationships with confidence scores.")
        ])
    
    def extract_with_validation(self, text, min_confidence=0.7):
        """
        Extract entities with validation and hallucination detection.
        Returns dict with entities, relationships, and validation_errors.
        """
        try:
            # Get LLM extraction (limit context to avoid token limits)
            prompt = self.extraction_prompt.format(text=text[:2000])
            response = self.llm.invoke(prompt)
            
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Extract JSON from response (handle markdown formatting)
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = content
            
            try:
                extraction = json.loads(json_str)
            except json.JSONDecodeError:
                print("⚠️  Failed to parse LLM response as JSON")
                return {'entities': [], 'relationships': [], 'validation_errors': ['JSON parse error']}
            
            validated_entities = []
            validated_relationships = []
            validation_errors = []
            
            # Validate entities
            for entity in extraction.get('entities', []):
                confidence = entity.get('confidence', 0.0)
                
                # Skip low-confidence extractions
                if confidence < min_confidence:
                    validation_errors.append(
                        f"Low confidence entity: {entity.get('name')} ({confidence})"
                    )
                    continue
                
                # Validate against ontology
                is_valid, message = ontology.validate_entity(
                    entity.get('type'),
                    entity.get('properties', {})
                )
                
                if is_valid:
                    validated_entities.append(entity)
                else:
                    validation_errors.append(f"Invalid entity {entity.get('name')}: {message}")
            
            # Validate relationships
            for rel in extraction.get('relationships', []):
                confidence = rel.get('confidence', 0.0)
                
                # Skip low-confidence
                if confidence < min_confidence:
                    validation_errors.append(
                        f"Low confidence relationship: {rel.get('type')} ({confidence})"
                    )
                    continue
                
                # Check if evidence exists
                if not rel.get('evidence'):
                    validation_errors.append(
                        f"Relationship {rel.get('type')} has no evidence - possible hallucination"
                    )
                    continue
                
                # Verify evidence is actually in the text
                if rel.get('evidence') not in text:
                    validation_errors.append(
                        f"Relationship evidence not found in text - hallucination detected"
                    )
                    continue
                
                validated_relationships.append(rel)
            
            return {
                'entities': validated_entities,
                'relationships': validated_relationships,
                'validation_errors': validation_errors
            }
        
        except Exception as e:
            print(f"Extraction error: {e}")
            return {'entities': [], 'relationships': [], 'validation_errors': [str(e)]}
