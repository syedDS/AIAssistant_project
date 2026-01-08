"""
Deep Research Module
Performs web search and synthesizes findings with document context
"""
import re
import json
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Try to import web search libraries
try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    print("⚠️ duckduckgo-search not installed. Install with: pip install duckduckgo-search")

try:
    import requests
    from bs4 import BeautifulSoup
    SCRAPING_AVAILABLE = True
except ImportError:
    SCRAPING_AVAILABLE = False
    print("⚠️ requests/beautifulsoup4 not installed for web scraping")


@dataclass
class SearchResult:
    """Single search result"""
    title: str
    url: str
    snippet: str
    source: str
    timestamp: Optional[str] = None


@dataclass  
class ResearchFindings:
    """Compiled research findings"""
    query: str
    web_results: List[SearchResult]
    document_context: str
    synthesis: str
    key_themes: List[str]
    gaps_identified: List[str]
    novel_ideas: List[str]
    sources: List[str]
    timestamp: str


class WebSearcher:
    """
    Web search using DuckDuckGo (no API key required)
    """
    
    def __init__(self):
        self.available = DDGS_AVAILABLE
        if not self.available:
            print("⚠️ Web search unavailable - install duckduckgo-search")
    
    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        Search the web using DuckDuckGo
        """
        if not self.available:
            return []
        
        results = []
        try:
            with DDGS() as ddgs:
                # Text search
                for r in ddgs.text(query, max_results=max_results):
                    results.append(SearchResult(
                        title=r.get('title', ''),
                        url=r.get('href', ''),
                        snippet=r.get('body', ''),
                        source='DuckDuckGo',
                        timestamp=datetime.now().isoformat()
                    ))
        except Exception as e:
            print(f"⚠️ Web search error: {e}")
        
        return results
    
    def search_news(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """
        Search news articles
        """
        if not self.available:
            return []
        
        results = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.news(query, max_results=max_results):
                    results.append(SearchResult(
                        title=r.get('title', ''),
                        url=r.get('url', ''),
                        snippet=r.get('body', ''),
                        source=r.get('source', 'News'),
                        timestamp=r.get('date', '')
                    ))
        except Exception as e:
            print(f"⚠️ News search error: {e}")
        
        return results
    
    def search_academic(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """
        Search for academic/research content
        """
        # Add academic qualifiers to query
        academic_query = f"{query} site:arxiv.org OR site:scholar.google.com OR site:researchgate.net OR site:ieee.org OR filetype:pdf"
        return self.search(academic_query, max_results)


class ContentFetcher:
    """
    Fetch and extract content from web pages
    """
    
    def __init__(self):
        self.available = SCRAPING_AVAILABLE
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def fetch_content(self, url: str, max_chars: int = 5000) -> str:
        """
        Fetch and extract main content from a URL
        """
        if not self.available:
            return ""
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                element.decompose()
            
            # Try to find main content
            main_content = soup.find('main') or soup.find('article') or soup.find('body')
            
            if main_content:
                text = main_content.get_text(separator=' ', strip=True)
                # Clean up whitespace
                text = re.sub(r'\s+', ' ', text)
                return text[:max_chars]
            
            return ""
        except Exception as e:
            print(f"⚠️ Failed to fetch {url}: {e}")
            return ""


class DeepResearcher:
    """
    Performs deep research combining web search and document analysis
    """
    
    def __init__(self, llm, vector_store=None, neo4j_graph=None):
        self.llm = llm
        self.vector_store = vector_store
        self.neo4j_graph = neo4j_graph
        self.web_searcher = WebSearcher()
        self.content_fetcher = ContentFetcher()
    
    def research(self, topic: str, include_web: bool = True, 
                 include_docs: bool = True, depth: str = "standard") -> ResearchFindings:
        """
        Perform deep research on a topic
        
        Args:
            topic: Research topic/question
            include_web: Include web search results
            include_docs: Include document context
            depth: "quick", "standard", or "deep"
        """
        print(f"\n🔬 Starting Deep Research: {topic}")
        print(f"   Mode: {'Web + Docs' if include_web and include_docs else 'Web' if include_web else 'Docs'}")
        print(f"   Depth: {depth}")
        
        # Determine search parameters based on depth
        search_params = {
            "quick": {"web_results": 5, "news_results": 3, "doc_chunks": 3, "fetch_pages": 2},
            "standard": {"web_results": 10, "news_results": 5, "doc_chunks": 5, "fetch_pages": 4},
            "deep": {"web_results": 20, "news_results": 10, "doc_chunks": 8, "fetch_pages": 8}
        }.get(depth, {"web_results": 10, "news_results": 5, "doc_chunks": 5, "fetch_pages": 4})
        
        web_results = []
        document_context = ""
        fetched_content = []
        
        # 1. Web Search
        if include_web and self.web_searcher.available:
            print("   🌐 Searching the web...")
            
            # General search
            web_results.extend(self.web_searcher.search(topic, search_params["web_results"]))
            print(f"      Found {len(web_results)} web results")
            
            # News search
            news_results = self.web_searcher.search_news(topic, search_params["news_results"])
            web_results.extend(news_results)
            print(f"      Found {len(news_results)} news results")
            
            # Academic search for deep mode
            if depth == "deep":
                academic_results = self.web_searcher.search_academic(topic, 5)
                web_results.extend(academic_results)
                print(f"      Found {len(academic_results)} academic results")
            
            # Fetch full content from top results
            print("   📄 Fetching page content...")
            for result in web_results[:search_params["fetch_pages"]]:
                content = self.content_fetcher.fetch_content(result.url, max_chars=3000)
                if content:
                    fetched_content.append({
                        "title": result.title,
                        "url": result.url,
                        "content": content
                    })
            print(f"      Fetched {len(fetched_content)} pages")
        
        # 2. Document Context
        if include_docs and self.vector_store:
            print("   📚 Searching documents...")
            try:
                doc_results = self.vector_store.similarity_search_with_relevance_scores(
                    topic, k=search_params["doc_chunks"]
                )
                
                doc_parts = []
                for doc, score in doc_results:
                    if score > 0.3:
                        source = doc.metadata.get('source', 'Unknown')
                        doc_parts.append(f"[{source}] (relevance: {score:.2f})\n{doc.page_content}")
                
                document_context = "\n\n".join(doc_parts)
                print(f"      Found {len(doc_parts)} relevant document chunks")
            except Exception as e:
                print(f"      ⚠️ Document search error: {e}")
        
        # 3. Synthesize findings with LLM
        print("   🧠 Synthesizing research...")
        
        synthesis_result = self._synthesize_findings(
            topic, web_results, fetched_content, document_context
        )
        
        # 4. Compile findings
        findings = ResearchFindings(
            query=topic,
            web_results=web_results,
            document_context=document_context,
            synthesis=synthesis_result.get("synthesis", ""),
            key_themes=synthesis_result.get("key_themes", []),
            gaps_identified=synthesis_result.get("gaps", []),
            novel_ideas=synthesis_result.get("ideas", []),
            sources=[r.url for r in web_results[:10]] + 
                    [f"Document: {s}" for s in set(
                        doc.metadata.get('source', '') 
                        for doc, _ in (doc_results if include_docs and self.vector_store else [])
                    )],
            timestamp=datetime.now().isoformat()
        )
        
        print("   ✅ Research complete!")
        return findings
    
    def _synthesize_findings(self, topic: str, web_results: List[SearchResult],
                            fetched_content: List[Dict], document_context: str) -> Dict:
        """
        Use LLM to synthesize research findings
        """
        # Build context for LLM
        context_parts = []
        
        # Add web search snippets
        if web_results:
            context_parts.append("=== WEB SEARCH RESULTS ===")
            for i, r in enumerate(web_results[:15], 1):
                context_parts.append(f"\n[{i}] {r.title}")
                context_parts.append(f"    Source: {r.source}")
                context_parts.append(f"    {r.snippet[:300]}...")
        
        # Add fetched page content
        if fetched_content:
            context_parts.append("\n\n=== DETAILED WEB CONTENT ===")
            for fc in fetched_content[:5]:
                context_parts.append(f"\n--- {fc['title']} ---")
                context_parts.append(fc['content'][:2000])
        
        # Add document context
        if document_context:
            context_parts.append("\n\n=== YOUR DOCUMENT CONTEXT ===")
            context_parts.append(document_context[:3000])
        
        full_context = "\n".join(context_parts)
        
        # Limit context size
        if len(full_context) > 12000:
            full_context = full_context[:12000] + "\n... [truncated]"
        
        # Rigorous Deep Research Synthesis Prompt
        synthesis_prompt = f"""You are an expert research analyst performing rigorous, end-to-end research.

RESEARCH TOPIC: {topic}

SOURCE MATERIAL:
{full_context}

YOUR TASK:
Perform rigorous, end-to-end research on the given topic. Systematically review the provided academic literature, technical papers, industry reports, and credible material. Extract key themes, recurring patterns, and underlying assumptions. Connect related ideas across adjacent and distant disciplines to build a coherent, high-level understanding of the domain.

Move beyond summarization. Synthesize findings into structured explanations that clarify complex concepts. Identify gaps, inconsistencies, and underexplored areas in existing research. From these gaps, propose original insights, hypotheses, or directions that could lead to meaningful new work, experiments, or applications.

The goal is to support deep understanding, spark high-quality ideas, and enable informed decision-making or further research—not just to restate what already exists.

Respond in the following JSON format:

{{
    "synthesis": "A comprehensive 4-6 paragraph synthesis that: (1) Establishes the core concepts and their relationships, (2) Identifies recurring patterns and underlying assumptions across sources, (3) Connects ideas across disciplines to build coherent understanding, (4) Clarifies complex concepts with structured explanations, (5) Highlights areas of consensus and debate.",
    
    "key_themes": [
        "Theme 1: [Name] - [2-3 sentence explanation of the theme, its significance, and how it connects to other themes]",
        "Theme 2: [Name] - [2-3 sentence explanation]",
        "Theme 3: [Name] - [2-3 sentence explanation]",
        "Theme 4: [Name] - [2-3 sentence explanation]"
    ],
    
    "gaps": [
        "Gap 1: [Specific area that lacks research] - Why this matters and what questions remain unanswered",
        "Gap 2: [Inconsistency or contradiction found] - How different sources conflict and what this implies",
        "Gap 3: [Underexplored intersection] - Adjacent field or approach that hasn't been applied",
        "Gap 4: [Missing perspective] - Stakeholder view or methodology not represented"
    ],
    
    "ideas": [
        "Idea 1: [Novel hypothesis] - Original insight derived from connecting disparate findings, with potential validation approach",
        "Idea 2: [Experiment/Application] - Concrete experiment or application that could address an identified gap",
        "Idea 3: [Cross-disciplinary connection] - How concepts from another field could advance this domain",
        "Idea 4: [Contrarian perspective] - Challenge to conventional wisdom supported by evidence from the research",
        "Idea 5: [Future direction] - Emerging trend or technology that could transform this space"
    ]
}}

CRITICAL REQUIREMENTS:
- DO NOT merely summarize - synthesize, connect, and generate novel insights
- Each theme must show connections across multiple sources
- Each gap must be specific and actionable, not generic
- Each idea must be ORIGINAL and derived from your analysis, not restated from sources
- Include specific examples, metrics, or evidence where available
- Be intellectually rigorous but accessible
- Respond ONLY with valid JSON, no preamble or explanation"""

        try:
            response = self.llm.invoke(synthesis_prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Try to parse JSON from response
            # Find JSON in response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                # Fallback: return raw synthesis
                return {
                    "synthesis": response_text,
                    "key_themes": [],
                    "gaps": [],
                    "ideas": []
                }
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parse error: {e}")
            return {
                "synthesis": response_text if 'response_text' in locals() else "Failed to synthesize",
                "key_themes": [],
                "gaps": [],
                "ideas": []
            }
        except Exception as e:
            print(f"⚠️ Synthesis error: {e}")
            return {
                "synthesis": f"Research synthesis failed: {str(e)}",
                "key_themes": [],
                "gaps": [],
                "ideas": []
            }
    
    def generate_ideas(self, topic: str, context: str = "", num_ideas: int = 5) -> List[Dict]:
        """
        Generate novel ideas based on research - going beyond what exists
        """
        idea_prompt = f"""You are an innovation researcher tasked with generating genuinely novel ideas.

RESEARCH TOPIC: "{topic}"

CONTEXT FROM RESEARCH:
{context[:4000] if context else "No additional context provided."}

YOUR TASK:
Generate {num_ideas} genuinely NOVEL ideas that go beyond restating what already exists. Each idea should:
- Connect disparate concepts in unexpected ways
- Address identified gaps or inconsistencies
- Propose testable hypotheses or actionable directions
- Challenge conventional assumptions where warranted
- Be specific enough to act upon

For each idea, provide a structured analysis:

Respond as a JSON array:
[
    {{
        "title": "Concise, descriptive title (5-10 words)",
        "description": "2-3 sentences explaining the core idea and its mechanism",
        "novelty": "What makes this genuinely new? What existing approaches does it differ from?",
        "evidence": "What patterns or findings from the research support this direction?",
        "challenges": "Key obstacles or risks in pursuing this idea",
        "next_steps": "Concrete first steps to validate or implement (be specific)",
        "impact_potential": "high/medium/low - with brief justification"
    }}
]

CRITICAL: 
- Ideas must be ORIGINAL insights derived from synthesis, not summaries of existing work
- Favor specific, actionable ideas over vague directions
- Include at least one contrarian or unexpected idea
- Consider cross-disciplinary applications

Respond ONLY with the JSON array, no preamble."""

        try:
            response = self.llm.invoke(idea_prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Parse JSON
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            if json_match:
                return json.loads(json_match.group())
            return []
        except Exception as e:
            print(f"⚠️ Idea generation error: {e}")
            return []


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def format_research_as_markdown(findings: ResearchFindings) -> str:
    """
    Format research findings as Markdown
    """
    md_parts = [
        f"# Deep Research: {findings.query}",
        f"*Generated: {findings.timestamp}*",
        "",
        "## 📊 Research Synthesis",
        "",
        findings.synthesis,
        "",
    ]
    
    if findings.key_themes:
        md_parts.extend([
            "## 🎯 Key Themes",
            ""
        ])
        for theme in findings.key_themes:
            md_parts.append(f"- {theme}")
        md_parts.append("")
    
    if findings.gaps_identified:
        md_parts.extend([
            "## 🔍 Research Gaps Identified",
            ""
        ])
        for gap in findings.gaps_identified:
            md_parts.append(f"- {gap}")
        md_parts.append("")
    
    if findings.novel_ideas:
        md_parts.extend([
            "## 💡 Novel Ideas & Directions",
            ""
        ])
        for idea in findings.novel_ideas:
            md_parts.append(f"- {idea}")
        md_parts.append("")
    
    if findings.sources:
        md_parts.extend([
            "## 📚 Sources",
            ""
        ])
        for i, source in enumerate(findings.sources[:15], 1):
            md_parts.append(f"{i}. {source}")
    
    return "\n".join(md_parts)


def format_research_as_html(findings: ResearchFindings) -> str:
    """
    Format research findings as HTML for display
    """
    html_parts = [
        f'<div class="research-report">',
        f'<h2>🔬 Deep Research: {findings.query}</h2>',
        f'<p class="timestamp"><em>Generated: {findings.timestamp}</em></p>',
        '',
        '<div class="synthesis">',
        '<h3>📊 Research Synthesis</h3>',
        f'<p>{findings.synthesis.replace(chr(10), "</p><p>")}</p>',
        '</div>',
    ]
    
    if findings.key_themes:
        html_parts.extend([
            '<div class="themes">',
            '<h3>🎯 Key Themes</h3>',
            '<ul>'
        ])
        for theme in findings.key_themes:
            html_parts.append(f'<li>{theme}</li>')
        html_parts.extend(['</ul>', '</div>'])
    
    if findings.gaps_identified:
        html_parts.extend([
            '<div class="gaps">',
            '<h3>🔍 Research Gaps</h3>',
            '<ul>'
        ])
        for gap in findings.gaps_identified:
            html_parts.append(f'<li>{gap}</li>')
        html_parts.extend(['</ul>', '</div>'])
    
    if findings.novel_ideas:
        html_parts.extend([
            '<div class="ideas">',
            '<h3>💡 Novel Ideas</h3>',
            '<ul>'
        ])
        for idea in findings.novel_ideas:
            html_parts.append(f'<li>{idea}</li>')
        html_parts.extend(['</ul>', '</div>'])
    
    if findings.sources:
        html_parts.extend([
            '<div class="sources">',
            '<h3>📚 Sources</h3>',
            '<ol>'
        ])
        for source in findings.sources[:10]:
            if source.startswith('http'):
                html_parts.append(f'<li><a href="{source}" target="_blank">{source[:60]}...</a></li>')
            else:
                html_parts.append(f'<li>{source}</li>')
        html_parts.extend(['</ol>', '</div>'])
    
    html_parts.append('</div>')
    
    return "\n".join(html_parts)
