#!/usr/bin/env python3
"""
NZ Police Manual Scraper
Downloads chapters from police.govt.nz
"""

import requests
import json
import re
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from bs4 import BeautifulSoup

@dataclass
class ManualChapter:
    title: str
    url: str
    category: str
    last_updated: Optional[str]

class PoliceManualScraper:
    """
    Scraper for NZ Police Manual chapters
    Source: https://www.police.govt.nz/about-us/publications/corporate/police-manual-chapters
    """
    
    BASE_URL = "https://www.police.govt.nz"
    MANUAL_URL = f"{BASE_URL}/about-us/publications/corporate/police-manual-chapters"
    
    # Critical chapters for defense work
    PRIORITY_CHAPTERS = [
        "search",
        "surveillance",
        "arrest",
        "interview",
        "evidence",
        "disclosure",
        "prosecution",
        "force",
        "detention",
        "complaints",
        "covert",
        "forensic"
    ]
    
    def __init__(self, output_dir: str = "./data/police_manual"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "NZ-Legal-RAG-Scraper/1.0 (Legal Research Database)"
        })
    
    def get_chapter_list(self) -> List[ManualChapter]:
        """
        Get list of all Police Manual chapters
        """
        try:
            response = self.session.get(self.MANUAL_URL, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            chapters = []
            
            # Find all chapter links
            for link in soup.find_all('a', href=True):
                href = link['href']
                # Pattern: /about-us/publications/corporate/police-manual-chapters/[chapter-name]
                if '/police-manual-chapters/' in href and href != '/about-us/publications/corporate/police-manual-chapters':
                    title = link.get_text(strip=True)
                    if title:
                        # Determine category
                        category = self._categorize_chapter(title.lower())
                        
                        chapters.append(ManualChapter(
                            title=title,
                            url=f"{self.BASE_URL}{href}" if href.startswith('/') else href,
                            category=category,
                            last_updated=None
                        ))
            
            return chapters
            
        except Exception as e:
            print(f"Error fetching chapter list: {e}")
            return []
    
    def _categorize_chapter(self, title: str) -> str:
        """Categorize chapter by content type"""
        categories = {
            "search": "Search and Seizure",
            "warrant": "Search and Seizure",
            "surveillance": "Surveillance and Covert Operations",
            "covert": "Surveillance and Covert Operations",
            "arrest": "Arrest and Detention",
            "detention": "Arrest and Detention",
            "custody": "Arrest and Detention",
            "interview": "Interview and Questioning",
            "question": "Interview and Questioning",
            "evidence": "Evidence Collection and Preservation",
            "forensic": "Evidence Collection and Preservation",
            "disclosure": "Disclosure and Prosecution",
            "prosecution": "Disclosure and Prosecution",
            "charging": "Disclosure and Prosecution",
            "force": "Use of Force",
            "firearm": "Use of Force",
            "complaint": "Complaints and Conduct",
            "conduct": "Complaints and Conduct",
            "rights": "Rights and Treatment",
            "treatment": "Rights and Treatment",
            "victim": "Victim Rights",
            "witness": "Witness Management",
            "young": "Young Persons",
            "youth": "Young Persons",
            "mental": "Mental Health",
            "health": "Health and Safety"
        }
        
        for keyword, category in categories.items():
            if keyword in title:
                return category
        
        return "General Procedures"
    
    def fetch_chapter(self, chapter: ManualChapter) -> Optional[Dict]:
        """
        Fetch and parse a single chapter
        """
        try:
            response = self.session.get(chapter.url, timeout=60)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract main content
            content = self._extract_content(soup)
            
            # Extract last updated date
            last_updated = self._extract_date(soup)
            
            # Extract TOC/structure
            structure = self._extract_structure(soup)
            
            # Extract key procedures
            procedures = self._extract_procedures(content)
            
            return {
                "title": chapter.title,
                "url": chapter.url,
                "category": chapter.category,
                "last_updated": last_updated,
                "content": content,
                "structure": structure,
                "key_procedures": procedures,
                "downloaded_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error fetching chapter {chapter.title}: {e}")
            return None
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main content of the chapter"""
        # Remove navigation, headers, footers
        for element in soup.find_all(['nav', 'header', 'footer', 'script', 'style']):
            element.decompose()
        
        # Try to find main content area
        main = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main'))
        
        if main:
            return main.get_text(separator='\n', strip=True)
        
        return soup.get_text(separator='\n', strip=True)
    
    def _extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract last updated date"""
        text = soup.get_text()
        
        # Look for date patterns
        patterns = [
            r'(?:Last updated|Updated|Version)[:\s]+(\d{1,2}[\s/]\w+[\s/]\d{4})',
            r'(?:Last updated|Updated|Version)[:\s]+(\w+\s+\d{4})',
            r'(?:Date)[:\s]+(\d{1,2}[\s/]\d{1,2}[\s/]\d{4})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_structure(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract document structure/TOC"""
        structure = []
        
        # Find headings
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4']):
            text = heading.get_text(strip=True)
            if text:
                structure.append({
                    "level": int(heading.name[1]),
                    "title": text
                })
        
        return structure
    
    def _extract_procedures(self, content: str) -> List[Dict]:
        """Extract key procedures and requirements"""
        procedures = []
        
        # Look for numbered procedures or steps
        procedure_patterns = [
            r'(?:Step|Procedure|Requirement)\s+\d+[.:]\s*([^\n]+)',
            r'\d+\.\s+(?:Police|Officers?|Members?)\s+(?:must|shall|should|will|may)\s+([^\n]+)',
            r'(?:Before|When|If)\s+[^,]+,\s+(?:police|officers?)\s+(?:must|shall)',
        ]
        
        for pattern in procedure_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                if len(match) > 20:  # Filter out short fragments
                    procedures.append({
                        "type": "requirement",
                        "text": match.strip()[:500]  # Limit length
                    })
        
        return procedures[:20]  # Limit to top 20
    
    def download_all_chapters(self) -> Dict[str, int]:
        """
        Download all Police Manual chapters
        """
        results = {"downloaded": 0, "failed": 0, "skipped": 0}
        
        print("Fetching Police Manual chapter list...")
        chapters = self.get_chapter_list()
        print(f"Found {len(chapters)} chapters")
        
        for chapter in chapters:
            # Create safe filename
            safe_title = re.sub(r'[^\w\-]', '_', chapter.title)[:80]
            filename = f"{safe_title}.json"
            filepath = self.output_dir / filename
            
            # Skip if already downloaded
            if filepath.exists():
                print(f"  Skipping (exists): {chapter.title[:50]}...")
                results["skipped"] += 1
                continue
            
            print(f"  Downloading: {chapter.title[:50]}...")
            
            chapter_data = self.fetch_chapter(chapter)
            if chapter_data:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(chapter_data, f, indent=2, ensure_ascii=False)
                results["downloaded"] += 1
            else:
                results["failed"] += 1
            
            time.sleep(1)  # Rate limiting
        
        return results
    
    def download_priority_chapters(self) -> Dict[str, int]:
        """
        Download priority chapters for defense work
        """
        results = {"downloaded": 0, "failed": 0}
        
        chapters = self.get_chapter_list()
        
        # Filter to priority chapters
        priority_chapters = [
            c for c in chapters
            if any(p in c.title.lower() for p in self.PRIORITY_CHAPTERS)
        ]
        
        print(f"Found {len(priority_chapters)} priority chapters")
        
        for chapter in priority_chapters:
            safe_title = re.sub(r'[^\w\-]', '_', chapter.title)[:80]
            filename = f"PRIORITY_{safe_title}.json"
            filepath = self.output_dir / filename
            
            print(f"  Downloading: {chapter.title[:50]}...")
            
            chapter_data = self.fetch_chapter(chapter)
            if chapter_data:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(chapter_data, f, indent=2, ensure_ascii=False)
                results["downloaded"] += 1
            else:
                results["failed"] += 1
            
            time.sleep(1)
        
        return results
    
    def create_chapter_index(self) -> Dict:
        """
        Create searchable index of all chapters
        """
        index = {
            "created": datetime.now().isoformat(),
            "total_chapters": 0,
            "by_category": {},
            "chapters": []
        }
        
        for json_file in self.output_dir.glob("*.json"):
            if json_file.name == "chapter_index.json":
                continue
            
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    chapter = json.load(f)
                
                chapter_entry = {
                    "title": chapter.get("title", ""),
                    "category": chapter.get("category", ""),
                    "url": chapter.get("url", ""),
                    "last_updated": chapter.get("last_updated"),
                    "file": json_file.name,
                    "has_procedures": len(chapter.get("key_procedures", [])) > 0
                }
                
                index["chapters"].append(chapter_entry)
                index["total_chapters"] += 1
                
                category = chapter_entry["category"]
                index["by_category"][category] = index["by_category"].get(category, 0) + 1
                
            except Exception as e:
                print(f"Error indexing {json_file}: {e}")
        
        # Save index
        index_path = self.output_dir / "chapter_index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Created index with {index['total_chapters']} chapters")
        return index


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Police Manual Scraper")
    parser.add_argument("--output", "-o", default="./data/police_manual",
                       help="Output directory")
    parser.add_argument("--priority-only", action="store_true",
                       help="Only download priority chapters")
    parser.add_argument("--index-only", action="store_true",
                       help="Only create index")
    
    args = parser.parse_args()
    
    scraper = PoliceManualScraper(output_dir=args.output)
    
    if args.index_only:
        scraper.create_chapter_index()
    elif args.priority_only:
        results = scraper.download_priority_chapters()
        print(f"\nDownloaded {results['downloaded']} priority chapters")
    else:
        results = scraper.download_all_chapters()
        print(f"\nDownload complete: {results['downloaded']} new, {results['skipped']} skipped, {results['failed']} failed")
        
        # Create index
        scraper.create_chapter_index()


if __name__ == "__main__":
    main()
