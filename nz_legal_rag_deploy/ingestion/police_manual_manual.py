#!/usr/bin/env python3
"""
Manual Police Manual Import
Key chapters for legal defense work
"""

import json
from pathlib import Path
from datetime import datetime

POLICE_MANUAL_CHAPTERS = {
    "search_warrantless": {
        "title": "Police Manual - Search Powers (Warrantless)",
        "chapter": "Search",
        "section": "Warrantless Search Powers",
        "category": "Search and Seizure",
        "content": """
POLICE MANUAL - WARRANTLESS SEARCH POWERS

Section 10 Search and Surveillance Act 2012

Key Principles:
1. Reasonable grounds to suspect must exist BEFORE search
2. Cannot be retrospective justification
3. Must be objectively reasonable from perspective of officer at the time

Warrantless Search Powers Include:
- Section 10(1): Search vehicles if reasonable grounds to suspect evidence of offence
- Section 10(2): Search persons if reasonable grounds to suspect offensive weapon or drugs
- Section 11: Search persons in custody
- Section 12: Search at public place (disorder/drunkenness)
- Section 13: Search for weapons at serious violent incidents

Reasonable Grounds Requirement:
- Must be based on specific facts, not general suspicion
- Can include: informant information (must be corroborated), officer observations, circumstances
- Hunch or instinct is insufficient
- Race or ethnicity cannot form part of reasonable grounds

Documentation Requirements:
- Must record grounds for search
- Must inform person of authority for search
- Must provide receipt for anything seized

Related Legislation:
- Search and Surveillance Act 2012, ss 10-13
- NZ Bill of Rights Act 1990, s 21 (unreasonable search)
""",
        "key_procedures": [
            "Record reasonable grounds before conducting search",
            "Inform person of authority under which search conducted",
            "Provide receipt for seized items",
            "Document all observations forming basis for reasonable grounds"
        ]
    },
    
    "search_warrants": {
        "title": "Police Manual - Search Warrants",
        "chapter": "Search",
        "section": "Search Warrants",
        "category": "Search and Seizure",
        "content": """
POLICE MANUAL - SEARCH WARRANTS

Section 18 Search and Surveillance Act 2012

Requirements for Issuing Search Warrant:
1. Reasonable grounds to suspect offence committed
2. Reasonable grounds to believe evidence will be found
3. Specified place/person/thing to be searched
4. Must be issued by independent issuing officer (not police)

Application Requirements:
- Must be in writing
- Must specify offence suspected
- Must describe place/person with particularity
- Must specify items sought
- Cannot be "fishing expedition"

Execution Requirements:
- Must be executed within 14 days of issue
- Must be available for inspection
- Occupier must be informed of warrant and rights
- Search must be at reasonable hour (unless urgent)
- Must be conducted in reasonable manner

Particularity Requirement:
- Physical address must be specific
- Description must enable identification of place
- Cannot cover multiple premises on single warrant without justification

Occupier Rights:
- Right to see warrant
- Right to legal advice
- Right to observe search (unless would impede)
- Right to copy of warrant

Post-Search:
- List of items seized must be provided
- Copy of warrant left with occupier
- Return must be made to issuing officer

Related Cases:
- R v Williams [2007] - Warrant particularity
- R v McGowan [2014] - Staleness of information
- R v McGregor [2020] - Description requirements
""",
        "key_procedures": [
            "Obtain warrant from independent issuing officer",
            "Execute within 14 days",
            "Inform occupier of warrant and rights",
            "Provide list of seized items",
            "Leave copy of warrant with occupier"
        ]
    },
    
    "interview_adults": {
        "title": "Police Manual - Interviewing Adults",
        "chapter": "Interview",
        "section": "Interviewing Adults",
        "category": "Interview and Questioning",
        "content": """
POLICE MANUAL - INTERVIEWING ADULTS

Caution Requirements:
Before commencing interview, suspect must be cautioned:
"You are not obliged to say anything unless you wish to do so, but anything you do say may be given in evidence."

Rights Under NZBORA Section 23:
1. Right to be informed of reason for arrest/detention
2. Right to consult and instruct lawyer without delay
3. Right to be informed of right to lawyer

Before Interview:
- Must check Police computer for history
- Must consider if person needs support (language, disability)
- Must ensure person understands caution
- Must record time, place, persons present

During Interview:
- Regular breaks must be offered
- Food and water must be provided
- Adequate heating/lighting required
- No undue pressure or coercion
- Leading questions generally avoided in evidential phase

Recording Requirements:
- Electronic recording required where facility available
- Written notes must be contemporaneous
- Significant statements must be recorded verbatim
- Any changes to statement must be initialed

Voluntariness:
- Confession must be voluntary
- No threats, inducements, or oppressive conduct
- Consider suspect's age, mental state, circumstances
- Evidence obtained improperly may be excluded (Evidence Act s 30)

Access to Lawyer:
- Must be given reasonable opportunity to consult
- Interview must not proceed until lawyer consulted (unless waived)
- Waiver must be voluntary, informed, and unequivocal
- Youth suspects have additional protections

Related Legislation:
- NZ Bill of Rights Act 1990, s 23
- Evidence Act 2006, s 30
- Criminal Procedure Act 2011
""",
        "key_procedures": [
            "Administer caution before questioning",
            "Inform of right to lawyer",
            "Check Police database for relevant history",
            "Record interview electronically where possible",
            "Offer regular breaks"
        ]
    },
    
    "interview_youth": {
        "title": "Police Manual - Interviewing Young Persons",
        "chapter": "Interview",
        "section": "Young Persons",
        "category": "Young Persons",
        "content": """
POLICE MANUAL - INTERVIEWING YOUNG PERSONS

Definition: Young person means person aged 14-16 years
Child means person under 14 years

Additional Protections (Oranga Tamariki Act 1989):
- Parent/guardian must be present or consent obtained
- Person acting in interests of child/young person required
- Separate from adult suspects
- Special considerations for maturity and vulnerability

Notification Requirements:
- Oranga Tamariki must be notified if offence committed
- Parent/guardian must be notified as soon as practicable
- Welfare and interests of child/young person paramount

Interview Considerations:
- Appropriate adult must be present (usually parent/caregiver)
- Explanation of rights in age-appropriate language
- Shorter interview periods
- Additional breaks
- Consideration of maturity and understanding

Caution:
Same adult caution applies, but ensure understanding:
"You are not obliged to say anything unless you wish to do so, but anything you do say may be given in evidence. Do you understand?"

Legal Representation:
- Right to lawyer even more important
- Appropriate adult can assist with understanding
- Can request lawyer if not already present

Records:
- Higher standard of record-keeping
- Time in custody strictly monitored
- Welfare checks required

Related Legislation:
- Oranga Tamariki Act 1989
- Criminal Procedure Act 2011
- NZ Bill of Rights Act 1990
""",
        "key_procedures": [
            "Notify parent/guardian immediately",
            "Ensure appropriate adult present",
            "Notify Oranga Tamariki",
            "Explain rights in age-appropriate language",
            "Keep separate from adult suspects"
        ]
    },
    
    "disclosure": {
        "title": "Police Manual - Disclosure",
        "chapter": "Disclosure",
        "section": "Criminal Case Disclosure",
        "category": "Disclosure and Prosecution",
        "content": """
POLICE MANUAL - DISCLOSURE IN CRIMINAL CASES

Criminal Procedure Act 2011 Requirements:

Initial Disclosure (Section 34):
Must be made as soon as practicable after filing charging document:
- Copy of charging document
- Summary of facts
- Criminal record (if any)
- Any expert evidence to be relied on

Full Disclosure (Section 36):
Must be made no later than:
- Committal (if proceeding by committal)
- Case review (if proceeding directly to trial)

Material That Must Be Disclosed:
- Statements of all witnesses Police intend to call
- Any statement of defendant
- Any exhibit or document to be relied on
- Expert reports
- Any video/audio recording
- Photos, maps, diagrams
- Records of interview
- Any statement that is inconsistent with another statement
- Any material that may assist the defense (Brady material)

Brady Material (Material That May Assist Defense):
- Information undermining prosecution case
- Information supporting defense case
- Information affecting witness credibility
- Exculpatory evidence
- Any information that might reasonably be expected to assist defense

Timing of Disclosure:
- As soon as reasonably practicable
- Must not delay to gain tactical advantage
- Continuing duty to disclose as material becomes available
- Pre-charge disclosure may be appropriate in serious cases

Withholding Information:
- Can withhold on grounds of public interest immunity
- Must apply to court for non-disclosure order
- Privilege (legal professional privilege, informer privilege)
- Must balance against defendant's right to fair trial

Electronic Disclosure:
- Preferred method where possible
- Must be secure and accessible
- Metadata may need to be disclosed

Consequences of Non-Disclosure:
- Stay of proceedings
- Exclusion of evidence
- Costs against Police
- Reputational damage
- Disciplinary action

Related Legislation:
- Criminal Procedure Act 2011, ss 34-46
- Evidence Act 2006
- R v Ward [1993] (disclosure obligations)
""",
        "key_procedures": [
            "Provide initial disclosure within statutory timeframe",
            "Provide full disclosure before case review",
            "Disclose any inconsistent statements",
            "Disclose Brady material immediately",
            "Maintain audit trail of disclosure"
        ]
    },
    
    "use_of_force": {
        "title": "Police Manual - Use of Force",
        "chapter": "Force",
        "section": "Use of Force",
        "category": "Use of Force",
        "content": """
POLICE MANUAL - USE OF FORCE

Legal Framework:
- Crimes Act 1961, s 48 (self-defense)
- Criminal Procedure Act 2011
- Common law powers

General Principles:
1. Force must be necessary and proportionate
2. Minimum force necessary to achieve lawful objective
3. Force must be reasonable in circumstances
4. Must give warning if practicable

Levels of Force (from least to most intrusive):
1. Presence - officer's mere presence
2. Communication - verbal direction
3. Physical contact - guiding/restraining
4. Physical force - hands-on control
5. Intermediate weapons - baton, OC spray, taser
6. Lethal force - firearm

Factors for Determining Reasonable Force:
- Seriousness of offence
- Level of threat posed
- Suspect's age, size, gender
- Officer's training and experience
- Availability of other options
- Potential for de-escalation
- Presence of innocent bystanders

Reporting Requirements:
- All use of force must be reported
- Detailed account of circumstances
- Medical attention offered to subject
- Supervisor review required
- Critical incident investigation for serious uses

OC Spray (Pepper Spray):
- Must be justified by circumstances
- Warning required if practicable
- After-care required (water, monitoring)
- Not to be used on passive resisters

Taser:
- Higher threshold of justification
- Must be proportionate to threat
- Medical assessment required after use
- Not for passive resistance

Firearms:
- Highest level of justification
- Imminent threat of death or grievous bodily harm
- Command approval usually required
- Post-incident support mandatory

De-escalation:
- Always attempt where safe to do so
- Communication is primary tool
- Time and distance are tactical advantages
- Withdrawal may be appropriate option

Related Legislation:
- Crimes Act 1961, s 48
- Human Rights Act 1993
""",
        "key_procedures": [
            "Use minimum force necessary",
            "Give warning if practicable",
            "Provide medical attention after force used",
            "Report all uses of force",
            "Attempt de-escalation first"
        ]
    },
    
    "forensic_procedures": {
        "title": "Police Manual - Forensic Procedures",
        "chapter": "Forensic",
        "section": "Forensic Procedures",
        "category": "Evidence Collection",
        "content": """
POLICE MANUAL - FORENSIC PROCEDURES

Search and Surveillance Act 2012 - Part 5

Types of Forensic Procedures:
1. Intimate forensic procedures (require consent or court order):
   - Blood samples
   - Intimate searches
   - Buccal (mouth) swabs
   - DNA sampling

2. Non-intimate forensic procedures (may be authorized by senior officer):
   - Fingerprinting
   - Photography
   - External physical examination
   - Hair samples (non-intimate)

Consent Requirements:
- Must be informed consent
- Person must understand what is involved
- Consent can be withdrawn at any time
- Written record of consent required

High-Risk Forensic Procedures (Court Order Required):
- Intimate forensic procedures without consent
- Procedures on children/young persons without consent
- Procedures on person incapable of giving consent

Applying for Court Order:
- Must apply to District Court
- Must show reasonable grounds
- Must demonstrate necessity
- Proportionality test applies

DNA Sampling:
- Must be authorized
- Sample can be retained on database
- Consent for retention vs one-time comparison
- Destruction requirements for elimination samples

Fingerprints:
- Can be taken if person charged or suspected
- Can be taken if person convicted
- Must be destroyed if proceedings discontinued

Time Limits:
- Must be conducted within reasonable time
- Cannot delay unnecessarily
- Results must be provided to defense if exculpatory

Documentation:
- Detailed record of procedure
- Chain of custody
- Any refusal or resistance
- Medical attention if required

Related Legislation:
- Search and Surveillance Act 2012, ss 75-88
- Criminal Investigations (Bodily Samples) Act 1995
- Privacy Act 2020
""",
        "key_procedures": [
            "Obtain informed consent where possible",
            "Apply to court for intimate procedures without consent",
            "Maintain chain of custody",
            "Provide results to defense if exculpatory",
            "Destroy samples as required by law"
        ]
    },
    
    "complaints": {
        "title": "Police Manual - Complaints Against Police",
        "chapter": "Complaints",
        "section": "Complaints Management",
        "category": "Complaints and Conduct",
        "content": """
POLICE MANUAL - COMPLAINTS AGAINST POLICE

Independent Police Conduct Authority (IPCA):
- Independent Crown entity
- Oversees Police conduct
- Investigates complaints
- Makes recommendations

Types of Complaints:
1. Conduct complaints - behavior of officers
2. Policy/service complaints - procedures or decisions
3. Anonymous complaints - from unidentified sources
4. Third-party complaints - from witnesses

Receiving Complaints:
- Must be received professionally
- Cannot discourage person from complaining
- Must provide IPCA information
- Must record complaint promptly

Informal Resolution:
- Minor complaints may be resolved informally
- Complainant must agree
- Must still be recorded
- IPCA can review

Formal Investigation:
- Required for serious matters
- Must notify IPCA
- Must preserve evidence
- Must ensure independence

IPCA Referral:
- Death or serious injury in custody
- Serious criminal allegations against Police
- Pattern or practice issues
- Systemic issues

Police Obligations:
- Cooperate with IPCA
- Provide all relevant information
- Not obstruct investigation
- Implement recommendations (or explain why not)

Documentation:
- All complaints recorded
- Investigation documented
- Outcome recorded
- Appeals process explained

Related Legislation:
- Independent Police Conduct Authority Act 1988
- Privacy Act 2020
- Human Rights Act 1993
""",
        "key_procedures": [
            "Record all complaints promptly",
            "Provide IPCA contact information",
            "Notify IPCA of serious matters",
            "Cooperate with IPCA investigations",
            "Implement recommendations"
        ]
    },
    
    "covert_operations": {
        "title": "Police Manual - Controlled Operations",
        "chapter": "Covert",
        "section": "Controlled Operations",
        "category": "Surveillance and Covert Operations",
        "content": """
POLICE MANUAL - CONTROLLED OPERATIONS

Search and Surveillance Act 2012 - Part 6

Definition:
A controlled operation is an operation where:
- Law enforcement participates in criminal activity
- Undercover officers engage in illegal acts
- Participation is authorized and monitored

Authorization Required:
- Must obtain approval before operation
- Authorizing officer must be satisfied:
  * Serious offence involved
  * Necessary to obtain evidence
  * Other methods unlikely to succeed
  * Risks can be managed

Authorizing Officers:
- National Manager Criminal Investigations
- District Crime Manager
- Other designated senior officers

Documentation:
- Detailed application required
- Risk assessment mandatory
- Legal advice recommended
- Regular reviews required

Limitations:
- Cannot authorize serious violence
- Cannot authorize sexual acts
- Cannot authorize serious property damage
- Cannot encourage commission of offences

Undercover Officers:
- Must have proper training
- Identity protected
- Can participate in minor criminal acts if authorized
- Cannot exceed scope of authorization

Informants:
- Must be registered and managed
- Risk assessment required
- Cannot authorize informant to commit serious crimes
- Payment requires approval

Post-Operation:
- Full debrief required
- Evidence preservation
- Legal review of conduct
- Report to authorizing officer

Accountability:
- Strict record-keeping
- Regular audits
- IPCA oversight
- Judicial oversight through trial process

Related Legislation:
- Search and Surveillance Act 2012, ss 109-127
- Evidence Act 2006
""",
        "key_procedures": [
            "Obtain authorization before operation",
            "Conduct risk assessment",
            "Ensure officers properly trained",
            "Maintain strict documentation",
            "Conduct post-operation debrief"
        ]
    },
}

def create_police_manual_files():
    """Create JSON files for Police Manual chapters"""
    output_dir = Path("./data/police_manual_manual")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for chapter_id, chapter_data in POLICE_MANUAL_CHAPTERS.items():
        filepath = output_dir / f"{chapter_id}.json"
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                **chapter_data,
                "created": datetime.now().isoformat(),
                "source": "Police Manual (NZ Police)"
            }, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Created: {filepath.name}")
    
    print(f"\n✓ Total: {len(POLICE_MANUAL_CHAPTERS)} chapters created")
    return output_dir

def print_summary():
    """Print summary"""
    print("="*60)
    print("POLICE MANUAL - MANUAL IMPORT COMPLETE")
    print("="*60)
    print()
    print("The following chapters have been created:")
    print()
    
    for chapter_id, data in POLICE_MANUAL_CHAPTERS.items():
        print(f"  • {data['title']}")
        print(f"    Category: {data['category']}")
        print(f"    Procedures: {len(data.get('key_procedures', []))} key steps")
        print()
    
    print("="*60)
    print("These will be ingested into ChromaDB for searching")
    print("="*60)

if __name__ == "__main__":
    create_police_manual_files()
    print()
    print_summary()
