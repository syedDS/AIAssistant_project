"""
Guardrails Handler for GraphRAG Security Architect
Integrates NeMo Guardrails or falls back to custom security checks
"""
import re
import yaml
import os
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class SecurityLevel(Enum):
    """Security check result levels"""
    SAFE = "safe"
    WARNING = "warning"
    BLOCKED = "blocked"


@dataclass
class SecurityCheckResult:
    """Result of security check"""
    level: SecurityLevel
    message: str
    detected_issues: list
    sanitized_input: Optional[str] = None


class GuardrailsHandler:
    """
    Main handler for security guardrails.
    Works with or without NeMo Guardrails installed.
    """
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__), 
            'guardrails', 
            'config.yml'
        )
        self.config = self._load_config()
        self.nemo_available = self._check_nemo_available()
        
        if self.nemo_available:
            self._init_nemo_guardrails()
        else:
            print("⚠️ NeMo Guardrails not installed. Using built-in security checks.")
    
    def _load_config(self) -> Dict:
        """Load guardrails configuration"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        return {}
    
    def _check_nemo_available(self) -> bool:
        """Check if NeMo Guardrails is installed"""
        try:
            from nemoguardrails import LLMRails, RailsConfig
            return True
        except ImportError:
            return False
    
    def _init_nemo_guardrails(self):
        """Initialize NeMo Guardrails"""
        try:
            from nemoguardrails import LLMRails, RailsConfig
            
            guardrails_dir = os.path.dirname(self.config_path)
            self.rails_config = RailsConfig.from_path(guardrails_dir)
            self.rails = LLMRails(self.rails_config)
            print("✅ NeMo Guardrails initialized")
        except Exception as e:
            print(f"⚠️ Failed to initialize NeMo Guardrails: {e}")
            self.nemo_available = False
    
    # ========================================================================
    # MAIN CHECK METHODS
    # ========================================================================
    
    def check_input(self, user_input: str) -> SecurityCheckResult:
        """
        Check user input for security issues.
        Returns SecurityCheckResult with level, message, and issues.
        """
        issues = []
        
        # 1. Check for prompt injection
        if self._check_prompt_injection(user_input):
            return SecurityCheckResult(
                level=SecurityLevel.BLOCKED,
                message="Prompt injection attempt detected. Please rephrase your question.",
                detected_issues=["prompt_injection"]
            )
        
        # 2. Check for jailbreak attempts
        if self._check_jailbreak(user_input):
            return SecurityCheckResult(
                level=SecurityLevel.BLOCKED,
                message="I can only help with security architecture questions based on your documents.",
                detected_issues=["jailbreak_attempt"]
            )
        
        # 3. Check for malicious code requests
        if self._check_malicious_request(user_input):
            return SecurityCheckResult(
                level=SecurityLevel.BLOCKED,
                message="I cannot provide information about creating exploits or attacking systems. I'm here to help with defensive security.",
                detected_issues=["malicious_request"]
            )
        
        # 4. Check for toxic content
        if self._check_toxicity(user_input):
            return SecurityCheckResult(
                level=SecurityLevel.WARNING,
                message="Please use professional language. How can I help with your security question?",
                detected_issues=["toxic_content"]
            )
        
        # 5. Check for PII extraction attempts
        if self._check_pii_request(user_input):
            return SecurityCheckResult(
                level=SecurityLevel.BLOCKED,
                message="I cannot help extract personally identifiable information. Please consult your data protection policies.",
                detected_issues=["pii_request"]
            )
        
        # 6. Check topic relevance (optional - can be strict or lenient)
        # if self._check_off_topic(user_input):
        #     issues.append("off_topic")
        
        return SecurityCheckResult(
            level=SecurityLevel.SAFE,
            message="Input passed security checks",
            detected_issues=issues,
            sanitized_input=self._sanitize_input(user_input)
        )
    
    def check_output(self, bot_response: str) -> SecurityCheckResult:
        """
        Check bot response for security issues.
        Returns SecurityCheckResult with sanitized output if needed.
        """
        issues = []
        sanitized = bot_response
        
        # 0. Quick check for common prompt disclosure patterns
        disclosure_patterns = [
            r"^the\s+system\s+prompt\s+is",
            r"^my\s+(system\s+)?prompt\s+is",
            r"^my\s+instructions?\s+(are|is)",
            r"^here\s+(is|are)\s+(the|my)\s+(system\s+)?(prompt|instructions?)",
        ]
        
        text_lower = bot_response.lower().strip()
        for pattern in disclosure_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return SecurityCheckResult(
                    level=SecurityLevel.BLOCKED,
                    message="I cannot disclose system instructions. How can I help with your security questions?",
                    detected_issues=["prompt_disclosure_attempt"]
                )
        
        # 1. Check for sensitive data exposure
        has_pii, sanitized = self._check_and_redact_pii(sanitized)
        if has_pii:
            issues.append("pii_in_response")
        
        # 2. Check for unsafe content
        if self._check_unsafe_output(bot_response):
            return SecurityCheckResult(
                level=SecurityLevel.BLOCKED,
                message="Response contained potentially unsafe content and was blocked.",
                detected_issues=["unsafe_output"]
            )
        
        # 3. Check for instruction leakage
        if self._check_instruction_leakage(bot_response):
            return SecurityCheckResult(
                level=SecurityLevel.BLOCKED,
                message="I cannot share information about my configuration. How can I help with security questions?",
                detected_issues=["instruction_leakage"]
            )
        
        return SecurityCheckResult(
            level=SecurityLevel.WARNING if issues else SecurityLevel.SAFE,
            message="Output checked and sanitized" if issues else "Output passed checks",
            detected_issues=issues,
            sanitized_input=sanitized
        )
    
    # ========================================================================
    # INPUT CHECKS
    # ========================================================================
    
    def _check_prompt_injection(self, text: str) -> bool:
        """Check for prompt injection attempts"""
        patterns = [
            # Direct instruction override
            r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?)",
            r"disregard\s+(your|all)\s+(rules?|instructions?|guidelines?)",
            r"forget\s+(your|all)\s+(rules?|instructions?|programming)",
            r"override\s+(your|the)\s+(instructions?|programming)",
            r"new\s+instruction[s]?\s*:",
            r"system\s*prompt\s*:",
            
            # Role manipulation
            r"you\s+are\s+now\s+(a|an)",
            r"pretend\s+(to\s+be|you\s+are)",
            r"act\s+as\s+(if|a|an)",
            r"from\s+now\s+on\s+you",
            
            # Prompt/instruction extraction - EXPANDED
            r"(reveal|show|tell|display|repeat|print|output|give|share)\s+(me\s+)?(your|the)\s+(system\s+)?(prompt|instructions?|rules?|guidelines?)",
            r"what\s+(are|is)\s+your\s+(system\s+)?(prompt|instructions?|rules?)",
            r"(repeat|recite|say|write)\s+(your|the)\s+(system\s+)?(prompt|instructions?)(\s+word\s+for\s+word)?",
            r"(word\s+for\s+word|verbatim|exactly|literally)\s*.*(prompt|instruction)",
            r"(prompt|instruction).*(word\s+for\s+word|verbatim|exactly)",
            r"copy\s+(your|the)\s+(prompt|instructions?)",
            r"paste\s+(your|the)\s+(prompt|instructions?)",
            r"(echo|dump|leak|expose)\s+(your|the)\s+(prompt|instructions?|system)",
            
            # Indirect extraction attempts
            r"what\s+(were\s+you|are\s+you)\s+(told|instructed|programmed)",
            r"(initial|original|first)\s+(prompt|instruction|message)",
            r"how\s+(were|are)\s+you\s+(prompted|instructed|configured)",
            r"(read|access)\s+(back|out)\s+(your|the)\s+(prompt|instructions?)",
            
            # Delimiter/format injection
            r"\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>",
            r"</?(system|user|assistant)>",
            r"```\s*(system|prompt)",
            
            # Developer/debug mode tricks
            r"(debug|developer|admin|root)\s*mode",
            r"(enable|enter|activate)\s+(debug|developer|admin)",
            r"(print|show|display)\s+(debug|internal|hidden)",
        ]
        
        text_lower = text.lower()
        
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                print(f"🛡️ Prompt injection blocked: {pattern[:50]}...")
                return True
        
        return False
    
    def _check_jailbreak(self, text: str) -> bool:
        """Check for jailbreak attempts"""
        patterns = [
            r"\bdan\b",
            r"\bdeveloper\s*mode\b",
            r"\bjailbreak\b",
            r"\bsudo\s*mode\b",
            r"\bunrestricted\b",
            r"\buncensored\b",
            r"bypass\s+(safety|security|filter)",
            r"disable\s+(safety|security|filter)",
            r"without\s+(any\s+)?(restriction|limitation)",
            r"hypothetically.*if\s+you\s+(could|were)",
            r"for\s+(educational|research)\s+purposes?\s+only",
        ]
        
        text_lower = text.lower()
        return any(re.search(p, text_lower, re.IGNORECASE) for p in patterns)
    
    def _check_malicious_request(self, text: str) -> bool:
        """Check for malicious code requests"""
        patterns = [
            r"(write|create|generate)\s+(me\s+)?(a\s+)?(malware|virus|trojan|ransomware)",
            r"(write|create|generate)\s+(me\s+)?(a\s+)?exploit",
            r"(write|create|generate)\s+(me\s+)?(a\s+)?(reverse\s+)?shell",
            r"(write|create|generate)\s+(me\s+)?(a\s+)?keylogger",
            r"how\s+to\s+(hack|crack|break\s+into|exploit)",
            r"(sql|xss|csrf)\s*injection\s*(code|payload)",
            r"bypass\s+(authentication|authorization|firewall)",
            r"brute\s*force\s*(attack|script)",
            r"(ddos|dos)\s*(attack|tool|script)",
            r"(steal|exfiltrate)\s*(data|credentials|password)",
        ]
        
        text_lower = text.lower()
        return any(re.search(p, text_lower, re.IGNORECASE) for p in patterns)
    
    def _check_toxicity(self, text: str) -> bool:
        """Check for toxic content"""
        patterns = [
            r"\b(fuck|shit|bitch|bastard)\b",
            r"(kill|murder|hurt)\s+(yourself|you)",
            r"\b(idiot|stupid|moron|retard)\b",
        ]
        
        text_lower = text.lower()
        return any(re.search(p, text_lower, re.IGNORECASE) for p in patterns)
    
    def _check_pii_request(self, text: str) -> bool:
        """Check for PII extraction requests"""
        patterns = [
            r"(give|show|list|extract)\s+(me\s+)?(all\s+)?(ssn|social\s*security)",
            r"(give|show|list|extract)\s+(me\s+)?(all\s+)?(credit\s*card)",
            r"(give|show|list|extract)\s+(me\s+)?(all\s+)?password",
            r"(dump|export|extract)\s+(all\s+)?(user|customer)\s*(data|records)",
        ]
        
        text_lower = text.lower()
        return any(re.search(p, text_lower, re.IGNORECASE) for p in patterns)
    
    def _check_off_topic(self, text: str) -> bool:
        """Check if question is off-topic"""
        security_keywords = [
            'security', 'firewall', 'encryption', 'authentication', 'vulnerability',
            'threat', 'risk', 'compliance', 'audit', 'network', 'access', 'control',
            'protection', 'attack', 'defense', 'policy', 'nist', 'iso', 'pci',
            'database', 'server', 'application', 'api', 'cloud', 'data', 'document'
        ]
        
        text_lower = text.lower()
        return not any(kw in text_lower for kw in security_keywords)
    
    # ========================================================================
    # OUTPUT CHECKS
    # ========================================================================
    
    def _check_and_redact_pii(self, text: str) -> Tuple[bool, str]:
        """Check for and redact PII in text"""
        pii_patterns = {
            'SSN': r'\b\d{3}-\d{2}-\d{4}\b',
            'CREDIT_CARD': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            'EMAIL': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'PHONE': r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
            'API_KEY': r'(?:api[_-]?key|secret[_-]?key)\s*[=:]\s*[A-Za-z0-9_-]{20,}',
        }
        
        has_pii = False
        sanitized = text
        
        for name, pattern in pii_patterns.items():
            if re.search(pattern, sanitized, re.IGNORECASE):
                has_pii = True
                sanitized = re.sub(pattern, f"[{name}_REDACTED]", sanitized, flags=re.IGNORECASE)
        
        return has_pii, sanitized
    
    def _check_unsafe_output(self, text: str) -> bool:
        """Check for unsafe content in output"""
        patterns = [
            r"here('s| is)\s+(the|a)\s+(malware|virus|exploit)",
            r"to\s+(hack|crack|exploit)\s+",
            r"step\s*\d*\s*:\s*(hack|crack|exploit)",
        ]
        
        text_lower = text.lower()
        return any(re.search(p, text_lower, re.IGNORECASE) for p in patterns)
    
    def _check_instruction_leakage(self, text: str) -> bool:
        """Check for system instruction leakage"""
        patterns = [
            # Direct leakage
            r"my\s+system\s+prompt\s+(is|says|was)",
            r"my\s+instructions\s+(are|say|were)",
            r"i\s+was\s+(told|instructed|programmed)\s+to",
            r"my\s+rules\s+(are|say)",
            r"the\s+system\s+prompt\s+(is|says)",
            
            # Patterns that indicate prompt disclosure
            r"^the\s+system\s+prompt\s+is",
            r"^my\s+prompt\s+is",
            r"^my\s+instructions\s+are",
            r"here\s+(is|are)\s+(the|my)\s+(system\s+)?(prompt|instructions?)",
            r"(prompt|instruction)\s*(is|are)\s*[:\"]",
            
            # Common LLM self-disclosure phrases
            r"(as|according\s+to)\s+my\s+(instructions?|prompt|programming)",
            r"i\s+(am|was)\s+(configured|instructed|designed)\s+to",
            r"my\s+(original|initial)\s+(prompt|instructions?)",
            
            # Quotation of instructions
            r"[\"\'](you\s+are|you\s+must|always|never|do\s+not).*[\"\']",
        ]
        
        text_lower = text.lower()
        
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                print(f"🛡️ Instruction leakage blocked: {pattern[:50]}...")
                return True
        
        return False
    
    # ========================================================================
    # SANITIZATION
    # ========================================================================
    
    def _sanitize_input(self, text: str) -> str:
        """Sanitize user input (remove potentially dangerous content)"""
        # Remove potential code injection
        sanitized = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
        
        # Remove excessive whitespace
        sanitized = ' '.join(sanitized.split())
        
        return sanitized.strip()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Global handler instance
_guardrails_handler = None

def get_guardrails_handler() -> GuardrailsHandler:
    """Get or create global guardrails handler"""
    global _guardrails_handler
    if _guardrails_handler is None:
        _guardrails_handler = GuardrailsHandler()
    return _guardrails_handler


def check_input_security(user_input: str) -> Tuple[bool, str]:
    """
    Quick check for user input security.
    Returns (is_safe, message)
    """
    handler = get_guardrails_handler()
    result = handler.check_input(user_input)
    
    is_safe = result.level == SecurityLevel.SAFE
    return is_safe, result.message


def check_output_security(bot_response: str) -> Tuple[bool, str, str]:
    """
    Quick check for bot output security.
    Returns (is_safe, message, sanitized_output)
    """
    handler = get_guardrails_handler()
    result = handler.check_output(bot_response)
    
    is_safe = result.level == SecurityLevel.SAFE
    sanitized = result.sanitized_input or bot_response
    
    return is_safe, result.message, sanitized


# ============================================================================
# ASYNC SUPPORT (for NeMo Guardrails)
# ============================================================================

async def async_check_input(user_input: str) -> SecurityCheckResult:
    """Async version of input check"""
    handler = get_guardrails_handler()
    
    if handler.nemo_available:
        try:
            # Use NeMo Guardrails
            response = await handler.rails.generate_async(
                messages=[{"role": "user", "content": user_input}]
            )
            # Parse NeMo response
            if "blocked" in str(response).lower():
                return SecurityCheckResult(
                    level=SecurityLevel.BLOCKED,
                    message="Request blocked by guardrails",
                    detected_issues=["nemo_blocked"]
                )
        except Exception as e:
            print(f"NeMo check failed, falling back: {e}")
    
    # Fallback to built-in checks
    return handler.check_input(user_input)
