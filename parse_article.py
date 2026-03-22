"""
Parse an HTML article into structured segments for video production.

Each segment represents a narration unit (heading or paragraph) with
associated metadata: text, links, section context.
"""
import os
import re
import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from bs4 import BeautifulSoup
import requests


@dataclass
class Citation:
    """A hyperlink within a text segment."""
    text: str       # anchor text
    url: str        # href target
    position: int   # character offset in the segment text


@dataclass
class Segment:
    """A narration unit — one heading or one paragraph."""
    segment_type: str           # "title", "heading", "paragraph", "blockquote"
    text: str                   # plain text for narration
    section_title: str = ""     # which section this belongs to
    section_index: int = 0      # section number (0-based)
    citations: List[Citation] = field(default_factory=list)

    @property
    def has_citations(self) -> bool:
        return len(self.citations) > 0

    @property
    def unique_citation_urls(self) -> List[str]:
        seen = set()
        urls = []
        for c in self.citations:
            if c.url not in seen:
                seen.add(c.url)
                urls.append(c.url)
        return urls


def fetch_html(url_or_path: str) -> str:
    """Fetch raw HTML from a URL or read from a local file."""
    if os.path.isfile(url_or_path):
        with open(url_or_path, "r", encoding="utf-8") as f:
            return f.read()
    resp = requests.get(url_or_path, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_article(html: str) -> List[Segment]:
    """
    Parse HTML into a list of Segments.

    Looks for <article> content first, falls back to <main>, then <body>.
    Extracts headings (h1-h3) and paragraphs with their inline links.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Find the main content container
    container = soup.find("article") or soup.find("main") or soup.find("body")
    if not container:
        raise ValueError("Could not find article content in HTML")

    segments: List[Segment] = []
    current_section = ""
    section_index = -1

    # Get the page title
    title_tag = soup.find("title")
    if title_tag:
        segments.append(Segment(
            segment_type="title",
            text=title_tag.get_text(strip=True),
            section_title="",
            section_index=0,
        ))

    for element in container.find_all(["h1", "h2", "h3", "p", "blockquote"]):
        tag_name = element.name

        if tag_name in ("h1", "h2", "h3"):
            section_index += 1
            current_section = element.get_text(strip=True)
            segments.append(Segment(
                segment_type="heading",
                text=current_section,
                section_title=current_section,
                section_index=section_index,
            ))

        elif tag_name == "p":
            text = element.get_text()
            # Normalize whitespace but preserve intentional structure
            text = re.sub(r'\s+', ' ', text).strip()
            if not text:
                continue

            # Extract citations
            citations = []
            for link in element.find_all("a", href=True):
                link_text = link.get_text(strip=True)
                link_url = link["href"]
                # Find position of link text in the plain text
                pos = text.find(link_text)
                citations.append(Citation(
                    text=link_text,
                    url=link_url,
                    position=max(pos, 0),
                ))

            segments.append(Segment(
                segment_type="paragraph",
                text=text,
                section_title=current_section,
                section_index=max(section_index, 0),
                citations=citations,
            ))

        elif tag_name == "blockquote":
            text = element.get_text()
            text = re.sub(r'\s+', ' ', text).strip()
            if text:
                segments.append(Segment(
                    segment_type="blockquote",
                    text=text,
                    section_title=current_section,
                    section_index=max(section_index, 0),
                ))

    return segments


def segments_to_json(segments: List[Segment]) -> str:
    """Serialize segments to JSON."""
    data = []
    for s in segments:
        data.append({
            "type": s.segment_type,
            "text": s.text,
            "section": s.section_title,
            "sectionIndex": s.section_index,
            "citations": [{"text": c.text, "url": c.url, "position": c.position}
                          for c in s.citations],
        })
    return json.dumps(data, indent=2)


def segments_from_json(json_path: str) -> List[Segment]:
    """Load segments from a JSON file (e.g. extracted via browser JS)."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    segments = []
    for item in data:
        citations = [
            Citation(text=c["text"], url=c["url"], position=c.get("position", 0))
            for c in item.get("citations", [])
        ]
        segments.append(Segment(
            segment_type=item["type"],
            text=item["text"],
            section_title=item.get("section", ""),
            section_index=item.get("sectionIndex", 0),
            citations=citations,
        ))
    return segments


def get_all_citation_urls(segments: List[Segment]) -> List[str]:
    """Get deduplicated list of all citation URLs in order of appearance."""
    seen = set()
    urls = []
    for seg in segments:
        for c in seg.citations:
            if c.url not in seen:
                seen.add(c.url)
                urls.append(c.url)
    return urls


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://curtcox.github.io/SFWA/why-ai-still-makes-things-up.html"
    html = fetch_html(url)
    segments = parse_article(html)
    print(f"Parsed {len(segments)} segments across {segments[-1].section_index + 1} sections")
    all_urls = get_all_citation_urls(segments)
    print(f"Found {len(all_urls)} unique citation URLs")
    for i, seg in enumerate(segments):
        cites = f" [{len(seg.citations)} citations]" if seg.citations else ""
        print(f"  [{seg.segment_type:>10}] {seg.text[:80]}...{cites}" if len(seg.text) > 80
              else f"  [{seg.segment_type:>10}] {seg.text}{cites}")
