#!/usr/bin/env python3
"""
Manual NZ Legislation Import
For when API scraping is blocked
"""

import json
from pathlib import Path
from datetime import datetime

# Priority Acts content (manually curated)
PRIORITY_ACTS = {
    "bail_act_2000": {
        "title": "Bail Act 2000",
        "sections": [
            {"number": "s 3", "title": "Purpose", "content": "The purpose of this Act is to provide a framework for deciding whether persons charged with offences should be remanded in custody or released on bail, with or without conditions."},
            {"number": "s 7", "title": "General rule about bail", "content": "An arrested person has a right to be released on bail pending trial unless the court is satisfied that one or more of the grounds for remand in custody in section 8 are made out."},
            {"number": "s 8", "title": "Grounds for remand in custody", "content": "The grounds for remand in custody are: (a) the defendant will fail to appear; (b) the defendant will interfere with witnesses or evidence; (c) the defendant will offend while on bail; (d) detention is necessary for protection of the defendant or another person."},
            {"number": "s 30", "title": "Conditions of bail", "content": "The court may impose conditions on bail that are necessary to address any of the grounds for remand in custody."},
        ]
    },
    "parole_act_2002": {
        "title": "Parole Act 2002",
        "sections": [
            {"number": "s 3", "title": "Purpose", "content": "The purpose of this Act is to make provision for the release of long-term and short-term prisoners on parole or compassionate release."},
            {"number": "s 18", "title": "Parole eligibility date", "content": "A long-term prisoner's parole eligibility date is one-third of the way through the sentence or 12 years, whichever is less."},
            {"number": "s 21", "title": "Test for release on parole", "content": "The Parole Board must not order release on parole unless satisfied that the prisoner does not pose an undue risk to the safety of the community."},
        ]
    },
    "sentencing_act_2002": {
        "title": "Sentencing Act 2002",
        "sections": [
            {"number": "s 7", "title": "Purposes of sentencing", "content": "The purposes of sentencing are: to hold the offender accountable, to denounce the conduct, to deter the offender or others, to protect the community, to assist rehabilitation."},
            {"number": "s 8", "title": "Principles of sentencing", "content": "The court must take into account: the gravity of the offence, the degree of culpability, the personal circumstances of the offender, and the extent of harm caused."},
            {"number": "s 9", "title": "Aggravating factors", "content": "Aggravating factors include: vulnerability of victim, breach of trust, premeditation, group offending, hate motivation."},
            {"number": "s 10", "title": "Mitigating factors", "content": "Mitigating factors include: remorse, guilty plea, youth, previous good character, cooperation with authorities."},
        ]
    },
    "policing_act_2008": {
        "title": "Policing Act 2008",
        "sections": [
            {"number": "s 8", "title": "Functions of Police", "content": "The functions of Police include: keeping the peace, maintaining public safety, law enforcement, crime prevention, and emergency management."},
            {"number": "s 9", "title": "Principles of policing", "content": "Police must act professionally, ethically, and with respect for human rights. Police must be accountable and maintain public confidence."},
            {"number": "s 40", "title": "Constables' powers", "content": "A constable has all the powers, protections, duties, and responsibilities of a constable at common law and under any enactment."},
        ]
    },
    "privacy_act_2020": {
        "title": "Privacy Act 2020",
        "sections": [
            {"number": "s 22", "title": "Information privacy principles", "content": "Agencies must not collect personal information unless it is necessary and collected in a lawful manner."},
            {"number": "s 66", "title": "Disclosure of personal information", "content": "An agency must not disclose personal information to any other agency or person, unless an exception applies."},
        ]
    },
    "human_rights_act_1993": {
        "title": "Human Rights Act 1993",
        "sections": [
            {"number": "s 21", "title": "Prohibited grounds of discrimination", "content": "Discrimination is prohibited on grounds including: sex, race, disability, age, sexual orientation, religious belief."},
            {"number": "s 29", "title": "Unlawful discrimination in public life", "content": "It is unlawful to discriminate in the provision of access to public places, facilities, and services."},
        ]
    },
    "official_information_act_1982": {
        "title": "Official Information Act 1982",
        "sections": [
            {"number": "s 5", "title": "Good reasons for withholding", "content": "Information may be withheld if necessary to protect personal privacy, commercial interests, or to maintain the effective conduct of public affairs."},
            {"number": "s 9", "title": "Requests for official information", "content": "Any person may request official information. Agencies must respond within 20 working days."},
        ]
    },
}

def create_legislation_files():
    """Create JSON files for priority Acts"""
    output_dir = Path("./data/legislation")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for act_id, act_data in PRIORITY_ACTS.items():
        # Create structured file
        act_file = {
            "title": act_data["title"],
            "act_id": act_id,
            "sections": act_data["sections"],
            "parsed_date": datetime.now().isoformat(),
            "source": "Manual compilation"
        }
        
        filepath = output_dir / f"{act_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(act_file, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Created: {filepath.name} ({len(act_data['sections'])} sections)")
    
    print(f"\n✓ Total: {len(PRIORITY_ACTS)} Acts created")
    return output_dir

def print_summary():
    """Print summary of created files"""
    print("="*60)
    print("NZ LEGISLATION - MANUAL IMPORT COMPLETE")
    print("="*60)
    print()
    print("The following Acts have been created:")
    print()
    
    for act_id, act_data in PRIORITY_ACTS.items():
        print(f"  • {act_data['title']}")
        for section in act_data['sections']:
            print(f"    - {section['number']}: {section['title']}")
        print()
    
    print("="*60)
    print("To ingest into ChromaDB, run:")
    print("  python -m core.rag_engine --ingest data/legislation")
    print("="*60)

if __name__ == "__main__":
    create_legislation_files()
    print()
    print_summary()
