"""
Security Ontology Definition
Strict schema for security domain entities and relationships
"""

class SecurityOntology:
    """
    Strict schema for security domain.
    Prevents "noisy hairball" of unvalidated relationships.
    """
    
    ENTITY_TYPES = {
        'SecurityControl': {
            'subtypes': ['firewall', 'waf', 'ids', 'ips', 'encryption', 'mfa', 'acl'],
            'required_properties': ['name', 'type'],
            'optional_properties': ['vendor', 'version', 'status'],
            'validation': lambda x: len(x.get('name', '')) > 2
        },
        'Asset': {
            'subtypes': ['database', 'server', 'application', 'network', 'storage'],
            'required_properties': ['name', 'type', 'criticality'],
            'optional_properties': ['location', 'owner', 'data_classification'],
            'validation': lambda x: x.get('criticality') in ['critical', 'high', 'medium', 'low']
        },
        'Threat': {
            'subtypes': ['malware', 'ddos', 'injection', 'social_engineering'],
            'required_properties': ['name', 'type', 'severity'],
            'optional_properties': ['mitre_id', 'cve_id'],
            'validation': lambda x: x.get('severity') in ['critical', 'high', 'medium', 'low']
        },
        'ComplianceControl': {
            'subtypes': ['nist', 'iso27001', 'pci_dss', 'hipaa'],
            'required_properties': ['framework', 'control_id'],
            'optional_properties': ['description', 'status'],
            'validation': lambda x: bool(x.get('control_id'))
        }
    }
    
    RELATIONSHIP_TYPES = {
        'PROTECTS': {
            'from': ['SecurityControl'],
            'to': ['Asset'],
            'required_properties': ['confidence'],
            'validation': lambda x: 0.0 <= x.get('confidence', 0) <= 1.0
        },
        'MITIGATES': {
            'from': ['SecurityControl'],
            'to': ['Threat'],
            'required_properties': ['effectiveness'],
            'validation': lambda x: x.get('effectiveness') in ['full', 'partial', 'minimal']
        },
        'DEPENDS_ON': {
            'from': ['Asset'],
            'to': ['Asset'],
            'required_properties': ['dependency_type'],
            'validation': lambda x: x.get('dependency_type') in ['network', 'data', 'service']
        },
        'THREATENS': {
            'from': ['Threat'],
            'to': ['Asset'],
            'required_properties': ['likelihood', 'impact'],
            'validation': lambda x: all(0.0 <= x.get(k, 0) <= 1.0 for k in ['likelihood', 'impact'])
        },
        'IMPLEMENTS': {
            'from': ['SecurityControl'],
            'to': ['ComplianceControl'],
            'required_properties': ['compliance_status'],
            'validation': lambda x: x.get('compliance_status') in ['compliant', 'partial', 'non_compliant']
        }
    }
    
    @classmethod
    def validate_entity(cls, entity_type, properties):
        """Validate entity against ontology schema"""
        if entity_type not in cls.ENTITY_TYPES:
            return False, f"Invalid entity type: {entity_type}"
        
        schema = cls.ENTITY_TYPES[entity_type]
        
        for prop in schema['required_properties']:
            if prop not in properties:
                return False, f"Missing required property: {prop}"
        
        if not schema['validation'](properties):
            return False, "Entity validation failed"
        
        return True, "Valid"
    
    @classmethod
    def validate_relationship(cls, rel_type, from_entity_type, to_entity_type, properties):
        """Validate relationship against ontology schema"""
        if rel_type not in cls.RELATIONSHIP_TYPES:
            return False, f"Invalid relationship type: {rel_type}"
        
        schema = cls.RELATIONSHIP_TYPES[rel_type]
        
        if from_entity_type not in schema['from']:
            return False, f"{rel_type} cannot start from {from_entity_type}"
        
        if to_entity_type not in schema['to']:
            return False, f"{rel_type} cannot go to {to_entity_type}"
        
        for prop in schema['required_properties']:
            if prop not in properties:
                return False, f"Missing required property: {prop}"
        
        if not schema['validation'](properties):
            return False, "Relationship validation failed"
        
        return True, "Valid"


# Singleton instance
ontology = SecurityOntology()
