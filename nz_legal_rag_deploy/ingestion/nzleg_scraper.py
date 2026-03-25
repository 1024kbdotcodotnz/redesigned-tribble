#!/usr/bin/env python3
"""
NZ Legislation Scraper
Downloads Acts and Regulations from legislation.govt.nz
"""

import requests
import json
import re
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
import xml.etree.ElementTree as ET

@dataclass
class ActMetadata:
    title: str
    act_id: str
    year: int
    version: str
    status: str  # "current", "repealed", "expired"
    date_as_at: str
    url: str

class NZLegislationScraper:
    """
    Scraper for New Zealand legislation from legislation.govt.nz
    Uses the public API and XML feeds
    """
    
    BASE_URL = "https://www.legislation.govt.nz"
    API_BASE = f"{BASE_URL}/api/query"
    
    # Priority Acts for criminal/defense work
    PRIORITY_ACTS = [
        "Crimes Act 1961",
        "Misuse of Drugs Act 1975", 
        "Evidence Act 2006",
        "Search and Surveillance Act 2012",
        "Criminal Procedure Act 2011",
        "Sentencing Act 2002",
        "Bail Act 2000",
        "Parole Act 2002",
        "Policing Act 2008",
        "New Zealand Bill of Rights Act 1990",
        "Human Rights Act 1993",
        "Privacy Act 2020",
        "Official Information Act 1982",
        "Criminal Proceeds (Recovery) Act 2009",
        "Mutual Assistance in Criminal Matters Act 1992"
    ]
    
    def __init__(self, output_dir: str = "./data/legislation"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "NZ-Legal-RAG-Scraper/1.0 (Legal Research Database)"
        })
    
    def fetch_act_list(self, type_: str = "act", status: str = "current") -> List[ActMetadata]:
        """
        Fetch list of Acts from legislation.govt.nz
        
        Args:
            type_: "act" or "regulation"
            status: "current", "repealed", "expired", "all"
        """
        url = f"{self.API_BASE}/act"
        params = {
            "status": status,
            "format": "json",
            "limit": 1000
        }
        
        acts = []
        offset = 0
        
        while True:
            params["offset"] = offset
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                for item in data.get("items", []):
                    act = ActMetadata(
                        title=item.get("title", ""),
                        act_id=item.get("id", ""),
                        year=item.get("year", 0),
                        version=item.get("version", ""),
                        status=item.get("status", ""),
                        date_as_at=item.get("dateAsAt", ""),
                        url=item.get("url", "")
                    )
                    acts.append(act)
                
                # Check if there are more results
                if len(data.get("items", [])) < params["limit"]:
                    break
                offset += params["limit"]
                time.sleep(0.5)  # Be respectful to the server
                
            except Exception as e:
                print(f"Error fetching act list: {e}")
                break
        
        return acts
    
    def fetch_act_content(self, act_id: str, format: str = "xml") -> Optional[str]:
        """
        Fetch full content of an Act
        
        Args:
            act_id: The legislation ID
            format: "xml", "json", or "html"
        """
        url = f"{self.BASE_URL}/{act_id}/{format}"
        
        try:
            response = self.session.get(url, timeout=60)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching act {act_id}: {e}")
            return None
    
    def parse_act_structure(self, xml_content: str) -> Dict:
        """
        Parse Act XML into structured format
        """
        try:
            root = ET.fromstring(xml_content)
            
            # Extract metadata
            title = root.findtext(".//title", "")
            act_id = root.findtext(".//id", "")
            
            # Extract sections
            sections = []
            for section in root.findall(".//section"):
                section_data = {
                    "number": section.get("id", ""),
                    "title": section.findtext(".//heading", ""),
                    "content": " ".join(section.itertext()),
                    "subsections": []
                }
                
                # Extract subsections
                for subsec in section.findall(".//subsection"):
                    section_data["subsections"].append({
                        "number": subsec.get("id", ""),
                        "content": " ".join(subsec.itertext())
                    })
                
                sections.append(section_data)
            
            return {
                "title": title,
                "act_id": act_id,
                "sections": sections,
                "parsed_date": datetime.now().isoformat()
            }
            
        except ET.ParseError as e:
            print(f"XML parse error: {e}")
            return {}
    
    def download_priority_acts(self) -> Dict[str, int]:
        """
        Download all priority Acts
        """
        results = {"downloaded": 0, "failed": 0}
        
        # Get list of all current Acts
        print("Fetching list of current Acts...")
        all_acts = self.fetch_act_list(status="current")
        print(f"Found {len(all_acts)} current Acts")
        
        # Filter to priority Acts
        priority_set = {act.lower() for act in self.PRIORITY_ACTS}
        priority_acts = [
            act for act in all_acts 
            if any(p in act.title.lower() for p in priority_set)
        ]
        
        print(f"\nFound {len(priority_acts)} priority Acts")
        
        for act in priority_acts:
            print(f"\nDownloading: {act.title}")
            
            # Fetch content
            content = self.fetch_act_content(act.act_id, format="xml")
            if not content:
                results["failed"] += 1
                continue
            
            # Parse structure
            parsed = self.parse_act_structure(content)
            
            # Save raw XML
            xml_path = self.output_dir / f"{act.act_id}.xml"
            with open(xml_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            # Save parsed JSON
            json_path = self.output_dir / f"{act.act_id}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(parsed, f, indent=2, ensure_ascii=False)
            
            # Save metadata
            meta_path = self.output_dir / f"{act.act_id}_meta.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump({
                    "title": act.title,
                    "act_id": act.act_id,
                    "year": act.year,
                    "version": act.version,
                    "status": act.status,
                    "date_as_at": act.date_as_at,
                    "download_date": datetime.now().isoformat()
                }, f, indent=2)
            
            print(f"  ✓ Saved: {xml_path.name}")
            results["downloaded"] += 1
            
            time.sleep(1)  # Be respectful
        
        return results
    
    def create_section_index(self) -> Dict:
        """
        Create searchable index of all sections from priority Acts
        """
        index = {
            "created": datetime.now().isoformat(),
            "sections": []
        }
        
        json_files = list(self.output_dir.glob("*.json"))
        json_files = [f for f in json_files if not f.name.endswith("_meta.json")]
        
        for json_file in json_files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                act_title = data.get("title", "")
                
                for section in data.get("sections", []):
                    index["sections"].append({
                        "act": act_title,
                        "act_file": json_file.stem,
                        "section_number": section.get("number", ""),
                        "section_title": section.get("title", ""),
                        "content_preview": section.get("content", "")[:500]
                    })
            except Exception as e:
                print(f"Error indexing {json_file}: {e}")
        
        # Save index
        index_path = self.output_dir / "section_index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Created index with {len(index['sections'])} sections")
        return index


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="NZ Legislation Scraper")
    parser.add_argument("--output", "-o", default="./data/legislation", 
                       help="Output directory")
    parser.add_argument("--index-only", action="store_true",
                       help="Only create index from existing downloads")
    
    args = parser.parse_args()
    
    scraper = NZLegislationScraper(output_dir=args.output)
    
    if args.index_only:
        scraper.create_section_index()
    else:
        results = scraper.download_priority_acts()
        print(f"\nDownload complete: {results['downloaded']} succeeded, {results['failed']} failed")
        
        # Create index
        scraper.create_section_index()


if __name__ == "__main__":
    main()
