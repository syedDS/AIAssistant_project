"""
Custom Guardrails Actions
Implements security checks for prompt injection, jailbreaks, PII, etc.
"""
import re
from typing import Optional
from nemoguardrails.actions import action


# ============================================================================
# PROMPT INJECTION DETECTION
# ============================================================================

INJECTION_PATTERNS = [
    # Direct instruction override attempts
    r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?|guidelines?)",
    r"disregard\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?)",
    r"forget\s+(all\s+)?(your|the)\s+(instructions?|prompts?|rules?|guidelines?)",
    r"override\s+(your|the)\s+(instructions?|programming|rules?)",
    r"new\s+instruction[s]?\s*:",
    r"system\s*prompt\s*:",
    r"</?(system|user|assistant)>",
    
    # Role manipulation
    r"you\s+are\s+now\s+(a|an|the)",
    r"pretend\s+(to\s+be|you\s+are)",
    r"act\s+as\s+(if|though|a|an)",
    r"roleplay\s+as",
    r"impersonate",
    r"from\s+now\s+on\s+you\s+(are|will)",
    
    # Prompt leaking attempts - EXPANDED
    r"(show|tell|reveal|display|print|output|repeat|give|share)\s+(me\s+)?(your|the)\s+(system\s+)?(prompt|instructions?|rules?)",
    r"what\s+(are|is)\s+your\s+(system\s+)?(prompt|instructions?|rules?)",
    r"(repeat|recite|say|write|read)\s+(your|the)\s+(system\s+)?(prompt|instructions?)(\s+word\s+for\s+word)?",
    r"(word\s+for\s+word|verbatim|exactly|literally).*(prompt|instruction)",
    r"(prompt|instruction).*(word\s+for\s+word|verbatim|exactly)",
    r"(copy|paste|echo|dump|leak|expose)\s+(your|the)\s+(prompt|instructions?|system)",
    r"what\s+(were|are)\s+you\s+(told|instructed|programmed)",
    r"(initial|original|first)\s+(prompt|instruction|message)",
    r"how\s+(were|are)\s+you\s+(prompted|instructed|configured)",
    
    # Delimiter injection
    r"```\s*(system|prompt|instruction)",
    r"\[INST\]",
    r"\[/INST\]",
    r"<<SYS>>",
    r"<</SYS>>",
    
    # Encoding tricks
    r"base64\s*:",
    r"hex\s*:",
    r"rot13",
    
    # Debug/admin mode
    r"(debug|developer|admin|root)\s*mode",
    r"(enable|enter|activate)\s+(debug|developer|admin)",
]

@action()
async def check_prompt_injection(user_input: str) -> bool:
    """
    Check if user input contains prompt injection attempts.
    Returns True if injection detected.
    """
    if not user_input:
        return False
    
    text = user_input.lower()
    
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            print(f"⚠️ Prompt injection detected: {pattern}")
            return True
    
    return False


# ============================================================================
# JAILBREAK DETECTION
# ============================================================================

JAILBREAK_PATTERNS = [
    # Known jailbreak names
    r"\bdan\b",  # Do Anything Now
    r"\bdeveloper\s*mode\b",
    r"\bjailbreak\b",
    r"\bsudo\s*mode\b",
    r"\badmin\s*mode\b",
    r"\bunrestricted\s*mode\b",
    r"\bgod\s*mode\b",
    r"\buncensored\b",
    r"\bunfiltered\b",
    
    # Bypass attempts
    r"bypass\s+(your\s+)?(safety|security|filter|restriction)",
    r"disable\s+(your\s+)?(safety|security|filter|restriction)",
    r"turn\s+off\s+(safety|security|filter)",
    r"remove\s+(your\s+)?(limitation|restriction|filter)",
    r"without\s+(any\s+)?(restriction|limitation|filter)",
    
    # Hypothetical framing (common jailbreak technique)
    r"hypothetically\s+(speaking\s+)?if\s+you\s+(could|were|had)",
    r"in\s+a\s+fictional\s+(world|scenario|story)",
    r"for\s+(educational|research|academic)\s+purposes?\s+only",
    r"just\s+between\s+us",
    r"off\s+the\s+record",
]

@action()
async def check_jailbreak(user_input: str) -> bool:
    """
    Check if user input contains jailbreak attempts.
    Returns True if jailbreak detected.
    """
    if not user_input:
        return False
    
    text = user_input.lower()
    
    for pattern in JAILBREAK_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            print(f"⚠️ Jailbreak attempt detected: {pattern}")
            return True
    
    return False


# ============================================================================
# TOXICITY DETECTION
# ============================================================================

TOXIC_PATTERNS = [
    r"\b(fuck|shit|damn|ass|bitch|bastard)\b",
    r"\b(idiot|stupid|dumb|moron|retard)\b",
    r"(kill|murder|hurt|harm)\s+(yourself|you|them|him|her)",
    r"threat(en)?",
    r"(hate|despise)\s+you",
]

@action()
async def check_toxicity(user_input: str) -> bool:
    """
    Check for toxic or harmful language.
    Returns True if toxic content detected.
    """
    if not user_input:
        return False
    
    text = user_input.lower()
    
    for pattern in TOXIC_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            print(f"⚠️ Toxic content detected")
            return True
    
    return False


# ============================================================================
# PII DETECTION
# ============================================================================

PII_REQUEST_PATTERNS = [
    r"(give|show|tell|list|extract|find)\s+(me\s+)?(all\s+)?(the\s+)?(ssn|social\s*security)",
    r"(give|show|tell|list|extract|find)\s+(me\s+)?(all\s+)?(the\s+)?(credit\s*card|cc)\s*(number)?",
    r"(give|show|tell|list|extract|find)\s+(me\s+)?(all\s+)?(the\s+)?password",
    r"(give|show|tell|list|extract|find)\s+(me\s+)?(all\s+)?(the\s+)?api\s*key",
    r"(give|show|tell|list|extract|find)\s+(me\s+)?(all\s+)?(the\s+)?secret",
    r"(give|show|tell|list|extract|find)\s+(me\s+)?(all\s+)?(employees?|users?|customers?)\s*(data|info|details)",
    r"(dump|export|extract)\s+(all\s+)?(user|customer|employee)\s*(data|records?|info)",
]

PII_PATTERNS = {
    'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
    'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'phone': r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
    'password': r'(?:password|passwd|pwd)\s*[=:]\s*\S+',
    'api_key': r'(?:api[_-]?key|apikey|secret[_-]?key|token)\s*[=:]\s*[A-Za-z0-9_-]{20,}',
}

@action()
async def check_pii_request(user_input: str) -> bool:
    """
    Check if user is requesting PII extraction.
    Returns True if PII request detected.
    """
    if not user_input:
        return False
    
    text = user_input.lower()
    
    for pattern in PII_REQUEST_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            print(f"⚠️ PII request detected")
            return True
    
    return False


@action()
async def check_sensitive_data(bot_response: str) -> bool:
    """
    Check if bot response contains sensitive data.
    Returns True if sensitive data found.
    """
    if not bot_response:
        return False
    
    for name, pattern in PII_PATTERNS.items():
        if re.search(pattern, bot_response, re.IGNORECASE):
            print(f"⚠️ Sensitive data in response: {name}")
            return True
    
    return False


@action()
async def redact_sensitive_data(text: str) -> str:
    """
    Redact sensitive data from text.
    Returns text with PII redacted.
    """
    if not text:
        return text
    
    redacted = text
    
    for name, pattern in PII_PATTERNS.items():
        redacted = re.sub(pattern, f"[{name.upper()}_REDACTED]", redacted, flags=re.IGNORECASE)
    
    return redacted


# ============================================================================
# TOPIC RELEVANCE CHECK
# ============================================================================

SECURITY_KEYWORDS = [
    'security', 'firewall', 'encryption', 'authentication', 'authorization',
    'access control', 'vulnerability', 'threat', 'risk', 'compliance',
    'audit', 'penetration', 'malware', 'antivirus', 'intrusion', 'detection',
    'prevention', 'incident', 'response', 'backup', 'recovery', 'disaster',
    'policy', 'procedure', 'standard', 'framework', 'nist', 'iso', 'pci',
    'hipaa', 'gdpr', 'sox', 'network', 'endpoint', 'cloud', 'data protection',
    'ssl', 'tls', 'certificate', 'key', 'hash', 'cipher', 'vpn', 'proxy',
    'dmz', 'segmentation', 'zero trust', 'identity', 'mfa', '2fa', 'sso',
    'ldap', 'active directory', 'siem', 'log', 'monitor', 'alert',
    'database', 'server', 'application', 'api', 'web application', 'waf',
    'ids', 'ips', 'dlp', 'casb', 'edr', 'xdr', 'soar', 'protect', 'secure',
    'attack', 'defense', 'mitigation', 'control', 'safeguard'
]

@action()
async def check_topic_relevance(user_input: str) -> bool:
    """
    Check if question is related to security topics.
    Returns True if OFF-TOPIC (not security related).
    """
    if not user_input:
        return False
    
    text = user_input.lower()
    
    # Check if any security keyword is present
    for keyword in SECURITY_KEYWORDS:
        if keyword in text:
            return False  # On-topic
    
    # Check for document-related queries (always allowed)
    doc_keywords = ['document', 'file', 'upload', 'search', 'find', 'show', 'list']
    for keyword in doc_keywords:
        if keyword in text:
            return False  # On-topic
    
    # If no security or document keywords found, likely off-topic
    print(f"⚠️ Off-topic query detected")
    return True


# ============================================================================
# MALICIOUS CODE REQUEST DETECTION
# ============================================================================

MALICIOUS_PATTERNS = [
    r"(write|create|generate|give|show)\s+(me\s+)?(a\s+)?(malware|virus|trojan|worm|ransomware)",
    r"(write|create|generate|give|show)\s+(me\s+)?(a\s+)?exploit",
    r"(write|create|generate|give|show)\s+(me\s+)?(a\s+)?payload",
    r"(write|create|generate|give|show)\s+(me\s+)?(a\s+)?(reverse\s+)?shell",
    r"(write|create|generate|give|show)\s+(me\s+)?(a\s+)?keylogger",
    r"(write|create|generate|give|show)\s+(me\s+)?(a\s+)?rootkit",
    r"how\s+to\s+(hack|crack|break\s+into|exploit|attack)",
    r"(sql|xss|csrf|xxe|ssrf|rce)\s*injection\s*(code|payload|example)",
    r"bypass\s+(authentication|authorization|security|firewall|waf)",
    r"brute\s*force\s*(attack|script|tool)",
    r"(ddos|dos)\s*(attack|tool|script)",
    r"(steal|extract|exfiltrate)\s*(data|credentials|passwords?)",
]

@action()
async def check_malicious_request(user_input: str) -> bool:
    """
    Check if user is requesting malicious code or attack instructions.
    Returns True if malicious request detected.
    """
    if not user_input:
        return False
    
    text = user_input.lower()
    
    for pattern in MALICIOUS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            print(f"⚠️ Malicious request detected: {pattern}")
            return True
    
    return False


# ============================================================================
# OUTPUT SAFETY CHECKS
# ============================================================================

UNSAFE_OUTPUT_PATTERNS = [
    r"(here\'s|here\s+is)\s+(the|a)\s+(malware|virus|exploit|payload)",
    r"to\s+(hack|crack|exploit|attack)\s+",
    r"(step|instruction)\s*\d*\s*:\s*(hack|crack|exploit|break\s+into)",
    r"```\s*(python|bash|sh|cmd|powershell)?\s*\n.*?(exploit|payload|shell|hack)",
]

HALLUCINATION_MARKERS = [
    r"as\s+an\s+ai\s+(language\s+)?model",
    r"i\s+don\'t\s+have\s+(access|the\s+ability)",
    r"i\s+cannot\s+(actually|really)",
    r"i\'m\s+not\s+able\s+to",
    r"my\s+training\s+data",
    r"my\s+knowledge\s+cutoff",
]

@action()
async def check_response_safety(bot_response: str) -> bool:
    """
    Check if bot response contains unsafe content.
    Returns True if unsafe content found.
    """
    if not bot_response:
        return False
    
    text = bot_response.lower()
    
    for pattern in UNSAFE_OUTPUT_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            print(f"⚠️ Unsafe output detected")
            return True
    
    return False


@action()
async def check_hallucination_markers(bot_response: str) -> bool:
    """
    Check for signs of hallucination (model talking about itself).
    Returns True if hallucination markers found.
    """
    if not bot_response:
        return False
    
    text = bot_response.lower()
    
    for pattern in HALLUCINATION_MARKERS:
        if re.search(pattern, text, re.IGNORECASE):
            print(f"⚠️ Hallucination marker detected")
            return True
    
    return False


@action()
async def self_check_output(bot_response: str) -> bool:
    """
    Self-check that output follows security guidelines.
    Returns True if output violates guidelines.
    """
    if not bot_response:
        return False
    
    # Check for instruction leakage
    if any(phrase in bot_response.lower() for phrase in [
        "my system prompt",
        "my instructions are",
        "i was told to",
        "my rules say"
    ]):
        print(f"⚠️ Potential instruction leakage")
        return True
    
    return False


# ============================================================================
# RATE LIMITING (Optional)
# ============================================================================

from collections import defaultdict
from datetime import datetime, timedelta

request_counts = defaultdict(list)
RATE_LIMIT = 10  # requests per minute
RATE_WINDOW = 60  # seconds

@action()
async def check_rate_limit(user_id: str) -> bool:
    """
    Check if user has exceeded rate limit.
    Returns True if rate limited.
    """
    now = datetime.now()
    window_start = now - timedelta(seconds=RATE_WINDOW)
    
    # Clean old requests
    request_counts[user_id] = [
        t for t in request_counts[user_id] 
        if t > window_start
    ]
    
    # Check limit
    if len(request_counts[user_id]) >= RATE_LIMIT:
        print(f"⚠️ Rate limit exceeded for user: {user_id}")
        return True
    
    # Record this request
    request_counts[user_id].append(now)
    return False
