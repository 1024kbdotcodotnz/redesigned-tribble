#!/usr/bin/env python3
"""
Remaining Police Manual Chapters (High + Medium Priority)
Adds ~48 more chapters for 75% coverage
"""

import json
from pathlib import Path
from datetime import datetime

REMAINING_CHAPTERS = {
    # HIGH PRIORITY
    
    "arrest_procedures": {
        "title": "Police Manual - Arrest Procedures",
        "chapter": "A",
        "section": "Arrest and Detention",
        "category": "Arrest and Detention",
        "content": """
POLICE MANUAL - ARREST PROCEDURES

Crimes Act 1961, s 315
Policing Act 2008
NZ Bill of Rights Act 1990, s 22-23

ARREST POWERS:

When Arrest is Necessary:
- To ensure appearance in court
- To prevent continuation of offence
- To prevent destruction of evidence
- To prevent interference with witnesses
- To protect victim or community
- To determine identity
- To preserve safety and security

Arrest Without Warrant (Crimes Act s 315):
- For any offence punishable by imprisonment
- For breach of the peace
- If person escaping from custody
- If person interfering with officer's duty
- On reasonable grounds to suspect offence

Information Required at Arrest:
- Must inform person they are under arrest
- Must inform reason for arrest (s 23 NZBORA)
- Must inform of right to consult lawyer (s 23 NZBORA)
- Must inform of right to remain silent
- Caution: "You are not obliged to say anything..."

Use of Force During Arrest:
- Only reasonable force permitted
- Must be proportionate to resistance
- Must cease when person submits
- Report any injury caused

After Arrest:
- Take to Police station (unless bail granted on scene)
- Search person (common law power)
- Secure property
- Note time of arrest
- Transport safely
- No unnecessary delay in processing

Time Limits for Processing:
- Must charge or release within reasonable time
- Generally within 24 hours (can be extended for complex matters)
- Regular reviews of necessity of continued detention
- Bail consideration

Identification:
- Must determine identity
- May photograph, fingerprint if charged
- Must provide opportunity to have lawyer present

Notification:
- Right to have friend/relative notified
- Right to have lawyer notified
- For youth, parent/guardian must be notified
- For foreign nationals, consulate notification

Special Circumstances:
- Medical attention if required
- Interpreter if language barrier
- Mental health assessment if concerns
- Dietary/medical requirements

Related Legislation:
- Crimes Act 1961, s 315
- Policing Act 2008
- NZ Bill of Rights Act 1990, s 22-23
- Bail Act 2000
""",
        "key_procedures": [
            "Inform person they are under arrest",
            "State reason for arrest",
            "Caution and inform of rights",
            "Use only reasonable force",
            "Transport to station promptly",
            "Allow notification of lawyer/family"
        ]
    },
    
    "informant_management": {
        "title": "Police Manual - Informant Management",
        "chapter": "I",
        "section": "Informants and Human Sources",
        "category": "Intelligence and Covert Operations",
        "content": """
POLICE MANUAL - INFORMANT MANAGEMENT

Definition:
Informant (human source) - Person who provides information to Police 
in confidence about criminal activity, often in exchange for benefit.

Registration:
- Must be registered with National Intelligence Application (NIA)
- Unique registration number assigned
- Handler allocated
- Risk assessment required
- Regular reviews mandatory

Categories of Informants:
1. Community sources (general public)
2. Registered informants (criminal background)
3. Covert human intelligence sources (CHIS)
4. Agents (directed and tasked)

Benefits Provided:
- Financial payments (require approval)
- Sentence reduction consideration
- Bail consideration
- Charge reduction
- Protection/relocation
- Other consideration (must be documented)

Obligations:
- Must not authorize commission of serious offences
- Must not entrap (cannot induce offence)
- Must protect identity
- Must verify information
- Must not guarantee outcomes (e.g., "charges will be dropped")

Management:
- Dedicated handler
- Regular contact
- Debriefing sessions
- Information evaluation (corroboration required)
- Welfare monitoring
- Exit strategy

Reliability Assessment:
- Corroboration required
- History of accurate information
- Motivation assessment
- Credibility factors
- Ongoing evaluation

Disclosure to Defense:
- Identity generally protected (public interest immunity)
- Existence of informant may need to be disclosed
- Material provided must be disclosed
- Handler notes may be discoverable
- Independent evidence required

Controlled Operations:
- Informants may participate in controlled operations
- Must be authorized
- Must not encourage serious offending
- Safety paramount

Protection:
- Identity strictly confidential
- Codes used in documentation
- Restricted access to files
- No disclosure to other criminals
- Relocation available if risk

Related Legislation:
- Search and Surveillance Act 2012
- Criminal Procedure Act 2011
- Privacy Act 2020
- Evidence Act 2006
""",
        "key_procedures": [
            "Register informant in NIA",
            "Conduct risk assessment",
            "Allocate dedicated handler",
            "Corroborate information",
            "Protect identity strictly",
            "Document all benefits provided"
        ]
    },
    
    "interpreters": {
        "title": "Police Manual - Interpreters",
        "chapter": "I",
        "section": "Language Assistance and Interpreters",
        "category": "Interview and Questioning",
        "content": """
POLICE MANUAL - INTERPRETERS

NZ Bill of Rights Act 1990, s 24(f)
Evidence Act 2006

Right to Interpreter:
- Every person has right to interpreter if cannot understand proceedings
- Must be provided free of charge
- Must be competent
- Must be impartial

When Required:
- Suspect/defendant has limited English
- Deaf or hearing impaired (sign interpreter)
- Complex legal concepts involved
- Important to ensure understanding of rights
- Statement being taken for evidence

Booking Interpreters:
- Use approved interpreter services
- NZ Society of Translators and Interpreters
- Cultural advisors for Māori
- Pacific language services
- Sign language (NZSL)

Competency Requirements:
- Certified/qualified interpreter preferred
- Understanding of legal terminology
- Ability to interpret accurately
- Impartiality (no personal connection)
- Confidentiality obligations

Procedure During Interview:
- Interpreter interprets everything said
- Everything interpreted into English for recording
- Suspect speaks in own language
- Officer speaks in English
- Interpreter must not add, omit, or change meaning
- Record interpreter's details

Cautions and Rights:
- Caution must be interpreted fully
- Rights must be explained in language understood
- Waivers must be informed
- Understanding must be confirmed
- Document confirmation

Cultural Considerations:
- Cultural concepts may not translate directly
- Different cultural understanding of legal concepts
- Family dynamics may differ
- Gender considerations for interpreters
- Religious/cultural practices

Sign Language:
- NZSL interpreter for deaf persons
- Video relay services available
- Notetaker may be alternative in some cases
- Visual access to interpreter essential

Telephone Interpreting:
- Available for less common languages
- Immediate access
- May not be suitable for complex interviews
- Document service used

Challenging Interpreter Evidence:
- Competency of interpreter
- Accuracy of interpretation
- Certification/qualifications
- Impartiality
- Understanding of legal terminology

Related Legislation:
- NZ Bill of Rights Act 1990, s 24(f)
- Evidence Act 2006
- NZ Sign Language Act 2006
""",
        "key_procedures": [
            "Assess language needs immediately",
            "Book qualified interpreter",
            "Ensure caution and rights fully interpreted",
            "Confirm understanding",
            "Record interpreter details",
            "Everything interpreted into English for record"
        ]
    },
    
    "prisoner_management": {
        "title": "Police Manual - Prisoner Management",
        "chapter": "P",
        "section": "Custody and Detention",
        "category": "Arrest and Detention",
        "content": """
POLICE MANUAL - PRISONER MANAGEMENT

NZ Bill of Rights Act 1990
Policing Act 2008

Custody Suite Requirements:
- Secure cells
- CCTV monitoring
- Access to toilet facilities
- Adequate heating/lighting
- Bedding if overnight
- Regular checks
- Medical equipment available

Receiving Prisoners:
- Search person (safety and evidence)
- Inventory property
- Record personal details
- Check for injuries (document pre-existing)
- Medical assessment if required
- Risk assessment (suicide, violence, escape)
- Notify rights again

Segregation:
- Separate males and females
- Separate adults and youth
- Separate co-accused
- Vulnerable prisoners isolated for protection
- High-risk prisoners managed appropriately
- Cultural considerations (Māori, Pacific)

Checks:
- Regular physical checks (frequency based on risk)
- CCTV monitoring
- Welfare checks
- Medical observations
- Must be logged

Time in Custody:
- Regular reviews of necessity
- Cannot hold indefinitely without charge
- Bail consideration at appropriate intervals
- Charge or release within reasonable time
- 24-hour rule (can extend for serious matters)

Rights in Custody:
- Right to lawyer (ongoing)
- Right to food and water
- Right to toilet facilities
- Right to medical attention
- Right to religious observance
- Right to have family informed
- Right to remain silent

Property:
- Inventory all property
- Secure storage
- Valuables receipt
- Clothing may be taken for forensic examination
- Return on release

Medical Care:
- Medical attention if required
- Prescription medication (verify and administer)
- Mental health concerns addressed
- Detoxification support
- Injury treatment
- Regular welfare checks

Food and Drink:
- Regular meals
- Special dietary requirements (religious, medical)
- Water available
- No deprivation as punishment

Release:
- Return property
- Provide copy of charging document if charged
- Explain bail conditions if applicable
- Explain next court date
- Provide contact information
- Safe transport if necessary

Deaths or Serious Incidents in Custody:
- Immediate medical attention
- Preserve scene
- Notify IPCA
- Notify Coroner if death
- Investigation launched
- Family notification

Related Legislation:
- Policing Act 2008
- NZ Bill of Rights Act 1990
- Corrections Act 2004 (if transferred to prison)
""",
        "key_procedures": [
            "Conduct thorough search and inventory",
            "Assess medical needs and risks",
            "Complete custody record",
            "Conduct regular checks",
            "Review necessity of continued detention",
            "Ensure all rights respected"
        ]
    },
    
    "public_order": {
        "title": "Police Manual - Public Order",
        "chapter": "P",
        "section": "Protests, Rallies, and Disorder",
        "category": "Public Order",
        "content": """
POLICE MANUAL - PUBLIC ORDER

Policing Act 2008
Bill of Rights Act 1990 (freedom of assembly, expression)

Rights vs Responsibilities:
- Freedom of peaceful assembly (s 16 NZBORA)
- Freedom of expression (s 14 NZBORA)
- Must be balanced against:
  * Public safety
  * Rights of others
  * Prevention of crime
  * Protection of property

Trespass Act 1980:
- Person trespassing if on property without permission
- Warning can be verbal or written
- After warning, person commits offence if remains
- Police can arrest for trespass
- No specific notice period required

Breach of the Peace:
- Common law power
- Arrest to prevent breach of the peace
- Actual violence not required
- Imminent threat of violence sufficient
- Prevention principle

Dispersal Orders:
- Can require person to move on
- Must have lawful authority
- Cannot be arbitrary
- Must be necessary

Protest Management:
- Liaison with organizers preferred
- Negotiation over enforcement
- Minimum intervention necessary
- Graduated response
- Containment (kettling) - extreme measure, time-limited
- Documentation essential

Road Blocking:
- Offence to obstruct road
- Arrest power available
- Safety paramount
- Graduated approach
- Negotiation preferred

Rallies and Demonstrations:
- No permit required for public spaces (generally)
- Local bylaws may apply
- Health and Safety requirements
- Traffic management
- Counter-demonstrations

Use of Force in Public Order:
- Minimum force necessary
- Proportionate to threat
- De-escalation preferred
- Communication first
- Tactical withdrawal if appropriate
- Public perception considered

Kettling/Containment:
- Containment of crowd
- Only in extreme circumstances
- Must be necessary and proportionate
- Time-limited
- Must be safe
- Legal advice recommended
- Must facilitate dispersal when safe

Media:
- Media have right to report
- Police cannot delete footage without warrant
- Media accreditation helpful
- Safety of journalists

After Event:
- Review
- Complaints management
- Lessons learned
- Accountability

Related Legislation:
- Policing Act 2008
- Trespass Act 1980
- Bill of Rights Act 1990
- Summary Offences Act 1981
""",
        "key_procedures": [
            "Assess balance of rights vs safety",
            "Negotiate where possible",
            "Use minimum force necessary",
            "Document decisions",
            "Ensure lawful authority for any arrests",
            "Facilitate lawful protest"
        ]
    },
    
    "pursuit_driving": {
        "title": "Police Manual - Pursuit Driving",
        "chapter": "R",
        "section": "Emergency Driving and Pursuits",
        "category": "Road Policing",
        "content": """
POLICE MANUAL - PURSUIT DRIVING

Land Transport (Road User) Rule 2004

General Rule:
- Police not exempt from traffic laws except when:
  * Using warning devices (sirens and lights)
  * Driving urgently in certain circumstances
  * Even then, must drive with due care

Pursuit Policy (Risk Assessment):
- Pursuit only initiated/continued if justified
- Risk to public must not outweigh risk of not pursuing
- Factors to consider:
  * Seriousness of offence
  * Risk to public of pursuit
  * Risk if offender escapes
  * Weather conditions
  * Traffic conditions
  * Driver skill
  * Vehicle capability

Abandonment:
- Pursuit MUST be abandoned if:
  * Risk to public too high
  * Unnecessary danger
  * Continuation unjustified
- Abandonment is tactical option, not failure

Warning Devices:
- Sirens and lights must be used
- Visual and audible warning
- Must give other road users time to react

Speed Limits:
- Even with sirens/lights, speed must be safe
- Excessive speed may be dangerous driving
- Accountability for crashes

Interventions:
- Tactical contact (ramming) - highly restricted
- Road spikes - must be authorized, safety measures
- Boxing in - coordinated, trained officers
- Road blocks - significant authorization required

Communication:
- Control room must be informed
- Continuous updates
- Authority to pursue
- Clearance for interventions
- Real-time risk assessment

Post-Pursuit:
- Review mandatory
- Account for driving
- Investigation if crash
- IPCA notification if injury/death
- Learn lessons

Alternative Actions:
- Discontinue and apprehend later
- Air support (Helicopter)
- ANPR (Automatic Number Plate Recognition)
- Follow at safe distance
- Intelligence-led apprehension later

Liability:
- Police liable for crashes caused by negligent driving
- Criminal liability for dangerous driving
- No immunity from prosecution
- Must justify actions

Related Legislation:
- Land Transport (Road User) Rule 2004
- Land Transport Act 1998
- Health and Safety at Work Act 2015
""",
        "key_procedures": [
            "Assess risk vs benefit continuously",
            "Use warning devices",
            "Maintain communication with control",
            "Abandon if risk too high",
            "Report all pursuits",
            "Review all pursuit incidents"
        ]
    },
    
    "search_dogs": {
        "title": "Police Manual - Search Dogs",
        "chapter": "S",
        "section": "Police Dog Operations",
        "category": "Search and Surveillance",
        "content": """
POLICE MANUAL - SEARCH DOGS

Types of Police Dogs:
1. General Purpose (Patrol) Dogs - tracking, searching, protection
2. Narcotic Detection Dogs - drug detection
3. Explosive Detection Dogs - bomb/explosive detection

General Purpose Dogs:
- Trained to track persons
- Search buildings/areas
- Apprehend offenders (bite and hold)
- Handler protection

Narcotic Detection Dogs:
- Trained to detect:
  * Cannabis
  * Methamphetamine
  * Cocaine
  * Heroin
  * MDMA
- Passive indication (sit)
- Can be used in various environments

Use of Dogs for Searching:
- Can search vehicles (with lawful authority)
- Can search buildings (with warrant or consent)
- Can search open areas
- Can be used at checkpoints (drug dogs)
- Airport screening

Reliability:
- Dogs must be trained and certified
- Regular training required
- Handler competency maintained
- False positives possible
- Cannot be sole basis for search (must corroborate)

Indications:
- Dog's behavior change indicates detection
- Handler interprets indication
- Probable cause for further search
- Must document what dog indicated

Apprehension (Bite):
- Dog may apprehend fleeing suspect
- Warning should be given if practicable
- Dog will bite and hold
- Handler must be in control
- Medical attention required after bite
- Report all bites

Limitations:
- Cannot search person internally
- Cannot differentiate user vs supplier
- Weather affects tracking
- Environment affects detection
- Handler interpretation critical

Documentation:
- Dog's certification
- Training records
- Deployment details
- Indications recorded
- Search results

Challenging Dog Evidence:
- Reliability of dog
- Handler training
- Certification current
- False positive rate
- Corroboration
- Environmental factors

Related Legislation:
- Search and Surveillance Act 2012
- Animal Welfare Act 1999
""",
        "key_procedures": [
            "Ensure dog certified and current training",
            "Document deployment details",
            "Record dog's indication",
            "Corroborate indication with search",
            "Provide medical attention if bite occurs",
            "Maintain training records"
        ]
    },
    
    "stolen_vehicles": {
        "title": "Police Manual - Stolen Vehicles",
        "chapter": "S",
        "section": "Vehicle Theft and Recovery",
        "category": "Road Policing",
        "content": """
POLICE MANUAL - STOLEN VEHICLES

Reporting:
- Stolen vehicle reports taken seriously
- Check if actually stolen (owner confirmation)
- Check if repossessed
- Enter in Police database immediately
- Contact registered owner

ANPR (Automatic Number Plate Recognition):
- Cameras read number plates
- Check against stolen vehicle database
- Real-time alerts
- Can track vehicle movements
- Data retention policies apply

Stopping Stolen Vehicles:
- Reasonable grounds required to stop
- ANPR hit provides grounds
- Must consider safety
- Risk assessment for fleeing driver
- Pursuit policy applies

Searching Recovered Vehicles:
- Search for evidence of theft
- Search for offender property
- Fingerprint opportunities
- DNA opportunities
- Dashcam/CCTV footage

Forensic Examination:
- Fingerprints
- DNA
- Tool marks
- Damage analysis
- Ignition examination
- GPS data extraction

Recovery:
- Owner notification
- Release procedures
- Damage documentation
- Property return
- Insurance information

Chop Shops:
- Organised theft for parts
- Surveillance required
- Search warrants usually required
- Coordinated operations
- Large-scale investigations

Prevention:
- Immobilizers
- Alarms
- Tracking devices
- Secure parking advice
- Public education

Related Legislation:
- Land Transport Act 1998
- Crimes Act 1961 (theft, receiving)
- Search and Surveillance Act 2012
""",
        "key_procedures": [
            "Verify vehicle actually stolen",
            "Enter in database immediately",
            "Use ANPR for detection",
            "Forensic examination if recovered",
            "Coordinate with owner",
            "Gather evidence for prosecution"
        ]
    },
    
    "homicide_investigation": {
        "title": "Police Manual - Homicide Investigation",
        "chapter": "H",
        "section": "Homicide and Serious Death Investigations",
        "category": "Death Investigations",
        "content": """
POLICE MANUAL - HOMICIDE INVESTIGATION

Initial Response:
- Preserve life (medical priority)
- Secure scene
- Identify witnesses
- Preserve evidence
- Establish cordons
- Log all persons entering scene

Scene Examination:
- Scene of Crime Officer (SOCO) attendance
- Pathologist attendance
- Photograph everything before moving
- Note body position
- Collect physical evidence
- Fingerprint/DNA opportunities

Post-Mortem Examination:
- Police attend with pathologist
- Observe and document
- Cause of death determination
- Time of death estimation
- Injury documentation
- Toxicology samples

Family Liaison:
- Dedicated family liaison officer
- Support family
- Information sharing
- Cultural considerations
- Victim Support referral

Investigation Team:
- Homicide investigation structure
- Senior Investigating Officer (SIO)
- Investigative team
- Scene team
- Intelligence cell
- Family liaison

Suspect Interviews:
- Legal representation essential
- No short-cuts with procedure
- Full disclosure obligations
- Video recorded
- Defenses anticipated

Media:
- Strategic media releases
- Appeals for information
- Victim identification (privacy)
- Suspect identification (suppression)
- Managing public interest

Coronial Process:
- Coroner notified
- Inquest may be held
- Police provide brief
- Determination of cause
- Recommendations

Cold Cases:
- Historical homicide reviews
- New evidence
- DNA advances
- Family persistence
- Media campaigns
- Rewards

Related Legislation:
- Coroners Act 2006
- Crimes Act 1961
- Criminal Procedure Act 2011
""",
        "key_procedures": [
            "Secure scene immediately",
            "Preserve all evidence",
            "Log all scene visitors",
            "Attend post-mortem",
            "Establish family liaison",
            "Coordinate investigation team"
        ]
    },
    
    "cybercrime": {
        "title": "Police Manual - Cybercrime Investigation",
        "chapter": "C",
        "section": "Digital Crime and Online Offending",
        "category": "Cybercrime",
        "content": """
POLICE MANUAL - CYBERCRIME INVESTIGATION

Types of Cybercrime:
- Hacking/unauthorized access
- Malware distribution
- Online fraud
- Identity theft
- Online child exploitation
- Cyberstalking/harassment
- Denial of service attacks
- Ransomware
- Cryptocurrency crimes

Jurisdiction:
- International element common
- Mutual Legal Assistance Treaties (MLAT)
- International Police cooperation (INTERPOL)
- Time zone challenges
- Evidence preservation across borders

Reporting:
- NetSafe for minor complaints
- Police for criminal matters
- CERT NZ for cybersecurity incidents
- Financial crimes to Financial Crime Unit

Digital Evidence Preservation:
- Volatile data (RAM)
- Servers (cloud and physical)
- Internet records (ISPs)
- Social media (platforms)
- Email providers
- Gaming platforms

Search Powers:
- Search warrants for devices
- Production orders for records
- Surveillance Device Warrants (if applicable)
- International cooperation

Forensic Examination:
- Digital Forensic Unit
- Write-blocking
- Imaging drives
- Deleted file recovery
- Metadata analysis
- Network traffic analysis
- Cryptocurrency tracing

Victim Evidence:
- Screenshot preservation
- URL preservation
- Email headers
- Banking records
- Timeline documentation

Challenges:
- Encryption
- Dark web
- Cryptocurrency anonymity
- Jurisdiction
- Technical complexity
- Rapidly evolving technology

Offender Identification:
- IP addresses
- Email tracing
- Device fingerprinting
- Behavioral analysis
- Financial trails
- Undercover online operations

Related Legislation:
- Crimes Act 1961 (computer crimes)
- Search and Surveillance Act 2012
- Harmful Digital Communications Act 2015
- Films, Videos, and Publications Classification Act 1993
""",
        "key_procedures": [
            "Preserve digital evidence immediately",
            "Engage Digital Forensic Unit",
            "Identify jurisdiction issues",
            "Obtain necessary warrants",
            "Document victim evidence",
            "Coordinate international cooperation"
        ]
    },
    
    "methamphetamine_investigation": {
        "title": "Police Manual - Methamphetamine Investigation",
        "chapter": "M",
        "section": "Clandestine Laboratories and Drug Investigation",
        "category": "Drug Investigation",
        "content": """
POLICE MANUAL - METHAMPHETAMINE INVESTIGATION

Misuse of Drugs Act 1975

Clandestine Laboratories (Clan Labs):
- Extremely dangerous
- Toxic chemicals
- Explosion risk
- Fire risk
- Chemical burns
- Respiratory hazards

DO NOT ENTER without:
- Specialist training
- Specialist equipment
- Decontamination facilities
- Hazmat team
- Fire service on standby

Signs of Clan Lab:
- Strong chemical smells
- Ventilation equipment
- Chemical containers
- Laboratory glassware
- Discarded pseudoephedrine packaging
- Coffee grinder residue
- Distilled water containers
- Excessive security

Investigation Approaches:
- Intelligence-led
- Chemical precursor monitoring
- Power consumption analysis
- Waste dumping monitoring
- Communication analysis
- Controlled deliveries
- Surveillance

Search Warrants:
- Essential for entry
- Must specify chemical hazards
- Specialist teams required
- Safety equipment mandatory
- Decontamination required after

Precursors:
- Pseudoephedrine (cold medicine)
- Ephedrine
- Phenyl-2-propanone (P2P)
- Iodine
- Red phosphorus
- Hypophosphorous acid

Offences:
- Manufacture (s 6 Misuse of Drugs Act)
- Importation
- Supply
- Possession for supply
- Possession of precursor with intent
- Conspiracy

Safety:
- Never enter without clearance
- Full PPE required
- Respiratory protection
- Decontamination mandatory
- Medical monitoring

Offender Characteristics:
- Organised crime involvement
- Chemical knowledge
- Security conscious
- Often rental properties
- Environmental contamination

Property Contamination:
- Testing required post-lab
- Remediation may be needed
- Landlord notification
- Insurance issues
- Health risks for future occupants

Related Legislation:
- Misuse of Drugs Act 1975
- Search and Surveillance Act 2012
- Resource Management Act 1991 (environmental)
- Health and Safety at Work Act 2015
""",
        "key_procedures": [
            "Do not enter without specialist clearance",
            "Obtain search warrant",
            "Hazmat team attendance",
            "Full PPE and decontamination",
            "Chemical analysis of substances",
            "Environmental safety assessment"
        ]
    },
    
    "fraud_investigation": {
        "title": "Police Manual - Fraud Investigation",
        "chapter": "F",
        "section": "Financial Crime and Fraud",
        "category": "Financial Crime",
        "content": """
POLICE MANUAL - FRAUD INVESTIGATION

Crimes Act 1961 (obtaining by deception)
Secret Commissions Act 1910

Types of Fraud:
- Banking/credit card fraud
- Identity fraud
- Investment fraud
- Insurance fraud
- Benefit fraud
- Cyber fraud
- Corporate fraud
- Securities fraud

Initial Report:
- Take detailed statement
- Document timeline
- Preserve evidence
- Financial losses quantified
- Suspects identified
- Witnesses listed

Financial Investigation:
- Bank records (Production Orders)
- Transaction analysis
- Asset tracing
- Company searches
- Property searches
- International transfers
- Cryptocurrency tracing

Documentary Evidence:
- Contracts
- Emails
- Bank statements
- Invoices
- Accounting records
- Company records
- Digital records

Digital Forensics:
- Computer examination
- Email analysis
- Metadata examination
- Deleted file recovery
- Cloud storage

Search Warrants:
- Business premises
- Residential premises
- Document seizure
- Computer/device seizure
- Financial records

Production Orders:
- Bank records
- Company records
- Tax records
- Telecommunications
- Third party records

Victim Impact:
- Financial loss quantification
- Restitution orders
- Sentencing considerations
- Support for victims

Prevention:
- Education
- Due diligence advice
- Verification procedures
- Security measures

Related Legislation:
- Crimes Act 1961
- Secret Commissions Act 1910
- Companies Act 1993
- Financial Markets Conduct Act 2013
- Anti-Money Laundering and Countering Financing of Terrorism Act 2009
""",
        "key_procedures": [
            "Take detailed victim statement",
            "Preserve all evidence",
            "Obtain financial records",
            "Trace assets",
            "Execute search warrants if necessary",
            "Prepare comprehensive brief"
        ]
    },
    
    "wiretapping": {
        "title": "Police Manual - Interception Warrants (Wiretapping)",
        "chapter": "W",
        "section": "Telecommunications and Surveillance Interception",
        "category": "Surveillance and Covert Operations",
        "content": """
POLICE MANUAL - INTERCEPTION WARRANTS

Search and Surveillance Act 2012, Part 4

What Can Be Intercepted:
- Telephone calls (landline and mobile)
- Text messages (SMS)
- Internet communications
- Email
- VoIP calls
- Any telecommunications

Authorization Required:
- Interception warrant from High Court Judge
- Must be serious offence (4+ years imprisonment)
- Must be necessary and proportionate
- Must be no other reasonable means
- Must specify target and method

Application Requirements:
- Affidavit setting out grounds
- Details of investigation
- Why interception necessary
- What evidence sought
- Time period requested
- Minimization procedures

Time Limits:
- Maximum 60 days initial
- Extensions possible
- Must report to Judge
- Continuous necessity review

Privileged Communications:
- Lawyer-client communications protected
- Journalist sources protected (limited)
- Parliamentary proceedings protected
- Medical consultations protected
- Must be minimized (not recorded/monitored)

Minimization:
- Must minimize collection of irrelevant communications
- Must stop monitoring privileged communications
- Regular review of necessity
- Destruction of irrelevant material

Execution:
- Telecommunications provider assistance
- Technical implementation
- Monitoring facility
- Real-time or recorded
- Secure storage

Disclosure:
- Intercepted material must be disclosed to defense
- May apply for non-disclosure (rare)
- Summaries may be provided
- Full transcripts available

Challenging Evidence:
- Authorization validity
- Necessity
- Privilege breaches
- Minimization failures
- Proportionality

Privacy Considerations:
- Significant privacy intrusion
- High threshold
- Judicial oversight
- Accountability
- Reporting requirements

Related Legislation:
- Search and Surveillance Act 2012, Part 4
- Telecommunications Act 2001
- Privacy Act 2020
""",
        "key_procedures": [
            "High Court application required",
            "Establish serious offence and necessity",
            "Specify minimization procedures",
            "Secure storage of intercepts",
            "Disclose to defense",
            "Regular necessity reviews"
        ]
    },
    
    "terrorism_investigation": {
        "title": "Police Manual - Terrorism Investigation",
        "chapter": "T",
        "section": "Counter-Terrorism and National Security",
        "category": "National Security",
        "content": """
POLICE MANUAL - TERRORISM INVESTIGATION

Terrorism Suppression Act 2002
Search and Surveillance Act 2012

Terrorism Defined:
- Ideologically motivated violence
- Designed to intimidate population or coerce government
- Serious harm to people or property
- International and domestic terrorism

Investigation Powers:
- Standard criminal powers apply
- Special surveillance powers
- Financial tracking (designated entities)
- Border alerts
- Passport cancellation
- Intelligence sharing (domestic and international)

Terrorism Finance:
- Designated terrorist entities
- Freezing assets
- Financial tracking
- Money laundering investigations
- International cooperation

Threat Assessment:
- Joint Intelligence Group (JIG)
- Threat level assessment
- Critical infrastructure protection
- Event security
- VIP protection

Surveillance:
- Intensive surveillance authorized
- Interception warrants commonly used
- Physical surveillance
- Financial surveillance
- Travel monitoring

Arrest and Detention:
- Can arrest for terrorism offences
- Can arrest for preparatory acts
- Prolonged detention provisions
- Special interview provisions

Prosecution:
- Attorney-General consent required
- Closed court for sensitive evidence
- Suppression of sensitive details
- Witness protection
- Jury security

Prevention:
- Community engagement
- De-radicalization support
- Early intervention
- Partnership with communities
- Intelligence-led

International:
- INTERPOL cooperation
- Five Eyes intelligence sharing
- Mutual legal assistance
- Extradition
- Border security

Victims:
- Mass casualty planning
- Victim identification
- Family support
- Media management
- Psychological support

Related Legislation:
- Terrorism Suppression Act 2002
- Search and Surveillance Act 2012
- Anti-Money Laundering and Countering Financing of Terrorism Act 2009
- Passports Act 1992
""",
        "key_procedures": [
            "Threat assessment",
            "Intelligence gathering and sharing",
            "Financial tracking",
            "Obtain necessary warrants",
            "Attorney-General consent for prosecution",
            "Community engagement and prevention"
        ]
    },
    
    "trafficking_exploitation": {
        "title": "Police Manual - Trafficking and Exploitation",
        "chapter": "T",
        "section": "Human Trafficking and Modern Slavery",
        "category": "Organised Crime",
        "content": """
POLICE MANUAL - TRAFFICKING AND EXPLOITATION

Crimes Act 1961 (slavery, trafficking)
Immigration Act 2009 (people smuggling)
Prostitution Reform Act 2003

Types of Trafficking:
- Sex trafficking
- Labour trafficking
- Domestic servitude
- Forced marriage
- Child trafficking
- Organ trafficking
- People smuggling (different but related)

Vulnerability Factors:
- Immigration status
- Language barriers
- Poverty
- Lack of education
- Isolation
- Mental health issues
- Drug dependency
- Previous abuse

Victim Identification:
- Physical signs (injuries, malnutrition)
- Psychological signs (fear, trauma)
- Behavioral signs (controlled movements)
- Documentation (confiscated passport)
- Work conditions (excessive hours, no pay)
- Living conditions (overcrowded, locked in)

Victim Approach:
- Safety first
- Trauma-informed
- Interpreter if needed
- Cultural sensitivity
- Victim Support referral
- Protection planning
- Not criminalize victim

Investigation:
- Financial investigation
- Surveillance
- Victim interviews (specialist trained)
- Suspect interviews
- Document seizure
- International cooperation

Offences:
- Slavery (Crimes Act)
- Human trafficking (Crimes Act)
- Dealing in slaves
- Debt bondage
- Forced labour
- Child exploitation
- People smuggling

Victim Protection:
- Immediate safety
- Medical attention
- Secure accommodation
- Legal advice
- Visa assistance
- Family reunification
- Long-term support
- Protection from reprisal

Challenges:
- Victim fear/reticence
- Language barriers
- Cultural differences
- Transnational crime
- Organised crime involvement
- Victim traumatization

Related Legislation:
- Crimes Act 1961
- Immigration Act 2009
- Prostitution Reform Act 2003
- Oranga Tamariki Act 1989 (for children)
""",
        "key_procedures": [
            "Identify victim vulnerabilities",
            "Ensure immediate safety",
            "Use trauma-informed approach",
            "Financial investigation",
            "Victim protection planning",
            "International cooperation"
        ]
    },
    
    "cannabis_eradication": {
        "title": "Police Manual - Cannabis Eradication",
        "chapter": "C",
        "section": "Cannabis and Drug Cultivation",
        "category": "Drug Investigation",
        "content": """
POLICE MANUAL - CANNABIS ERADICATION

Misuse of Drugs Act 1975

Offences:
- Cultivation of cannabis (s 9)
- Supply
- Possession for supply
- Possession (personal use - infringement notice)
- Possession of utensils

Indoor Growing Operations:
- Hydroponic setups
- Heat lamps
- Ventilation systems
- Odour control
- Power consumption

Outdoor Growing:
- Forest/plantation grows
- Residential grows
- Riverbeds
- Remote locations

Detection Methods:
- Power consumption analysis
- Aerial surveillance
- Thermal imaging
- Odour complaints
- Informant information
- Search warrants

Search Powers:
- Search warrants for premises
- Search of vehicles (s 10 SSA)
- Person search (with grounds)

Aerial Operations:
- Helicopter surveillance
- Fixed-wing aircraft
- Thermal imaging
- GPS marking
- Ground crew follow-up

Indoor Grow Dangers:
- Fire risk (electrical)
- Chemical exposure (nutrients)
- Structural damage (moisture)
- Electrical theft

Safety:
- Electrical hazards
- Structural hazards
- Chemical exposure
- Booby traps
- Armed offenders

Destruction of Plants:
- Count and document
- Photograph
- Seize for evidence if prosecution
- Destroy remainder
- Environmental considerations

Cultivation Quantity:
- Number of plants
- Mature vs immature
- Weight (if harvested)
- Estimated yield

Related Offences:
- Electricity theft
- Benefit fraud
- Property damage
- Receiving

Related Legislation:
- Misuse of Drugs Act 1975
- Search and Surveillance Act 2012
- Electricity Act 1992
""",
        "key_procedures": [
            "Obtain search warrant",
            "Assess electrical and structural hazards",
            "Count and document plants",
            "Photograph evidence",
            "Seize samples for prosecution if required",
            "Destroy remainder safely"
        ]
    },
    
    "protected_persons": {
        "title": "Police Manual - Protected Persons",
        "chapter": "P",
        "section": "Witness Protection and Anonymous Evidence",
        "category": "Witness Protection",
        "content": """
POLICE MANUAL - PROTECTED PERSONS

Evidence Act 2006
Criminal Procedure Act 2011

Witness Protection:
- Relocation
- Identity change
- Ongoing security
- Psychological support
- For high-risk witnesses

Anonymous Evidence:
- Witness anonymity orders
- Screened witnesses
- Voice distortion
- Pseudonyms
- Limited disclosure to defense

Testimony by Video Link:
- From remote location
- Identity protected
- Voice modified
- Defense can see witness (unless exceptional circumstances)

Relocation:
- New identity
- New location
- Financial support
- Employment assistance
- Long-term commitment
- Cannot contact previous life

Risk Assessment:
- Threat level
- Suspect connections
- Gang involvement
- Organised crime
- Likelihood of reprisal

Security Measures:
- Secure housing
- Surveillance
- Security alarms
- Patrols
- Emergency response

Challenges:
- Cost
- Long-term commitment
- Psychological impact on witness
- Family impact
- Reintegration difficulties

Legal Basis:
- Court orders for anonymity
- Suppression orders
- Closed court
- Special measures
- Defense rights balanced

Corroboration:
- Protected witness testimony may need corroboration
- Independent evidence preferred
- Jury warnings
- Credibility assessment

Related Legislation:
- Evidence Act 2006
- Criminal Procedure Act 2011
- Witness Protection Act 2017
""",
        "key_procedures": [
            "Assess threat level",
            "Apply for anonymity orders if needed",
            "Implement security measures",
            "Consider relocation for high-risk",
            "Provide ongoing support",
            "Balance with defense rights"
        ]
    },
    
    "missing_persons": {
        "title": "Police Manual - Missing Persons",
        "chapter": "M",
        "section": "Missing Person Investigations",
        "category": "Investigations",
        "content": """
POLICE MANUAL - MISSING PERSONS

Definition:
- Anyone whose whereabouts are unknown
- Concern for safety/welfare
- Not necessarily crime-related
- Can be voluntary or involuntary

Risk Assessment:
- Vulnerability factors (age, mental health, medical needs)
- Circumstances of disappearance
- Suicide risk
- Foul play indicators
- Weather/environmental factors
- Time elapsed

Categories:
- High risk (vulnerable, suspicious circumstances)
- Medium risk (some concerns)
- Low risk (likely voluntary, adult with capacity)
- Historical (missing for extended period)

Initial Response:
- Take report seriously
- Gather detailed description
- Photograph
- Circumstances of disappearance
- Last known location
- Associates
- Medical needs
- Mental state

Investigation:
- Cell phone data
- Bank transactions
- CCTV footage
- Social media activity
- Vehicle tracking
- Associates interviewed
- Media appeals
- Public appeals

Search Powers:
- Limited without warrant
- Can enter premises with consent
- Urgent welfare checks (limited entry)
- Search warrants if foul play suspected
- Phone records (Production Orders)

Vulnerable Missing:
- Children (immediate response)
- Elderly (dementia, medical)
- Mental health issues
- Medical conditions
- High suicide risk

Voluntary Missing Adults:
- Adults have right to go missing
- Privacy considerations
- Cannot force return
- Welfare check only
- Inform family if located

Media:
- Photograph release
- Public appeals
- Social media campaigns
- Privacy considerations
- Family liaison

Recovery:
- Safe and well check
- Medical attention if needed
- Mental health support
- Family notification
- Interview if suspicious circumstances

Related Legislation:
- Privacy Act 2020
- Oranga Tamariki Act 1989 (for children)
- Search and Surveillance Act 2012
""",
        "key_procedures": [
            "Conduct risk assessment immediately",
            "Gather detailed description and circumstances",
            "Check electronic footprint",
            "Conduct welfare checks",
            "Media appeals if appropriate",
            "Safe and well check on location"
        ]
    },
    
    "money_laundering": {
        "title": "Police Manual - Money Laundering Investigation",
        "chapter": "M",
        "section": "Financial Crime and Asset Tracing",
        "category": "Financial Crime",
        "content": """
POLICE MANUAL - MONEY LAUNDERING INVESTIGATION

Anti-Money Laundering and Countering Financing of Terrorism Act 2009 (AML/CFT)
Criminal Proceeds (Recovery) Act 2009

Money Laundering Process:
1. Placement - Introducing cash into financial system
2. Layering - Complex transactions to obscure source
3. Integration - Legitimate-looking investments

Indicators:
- Large cash transactions
- Structured deposits (under reporting threshold)
- Unusual transaction patterns
- Business with no apparent purpose
- Complex offshore structures
- Use of nominees
- Cryptocurrency transactions

Reporting Entities (must report suspicious transactions):
- Banks
- Casinos
- Real estate agents
- Lawyers
- Accountants
- Dealers in high-value goods
- Non-bank lenders

Police Powers:
- Financial analysis
- Asset tracing
- Production Orders (bank records)
- Search warrants
- Surveillance
- International cooperation
- Suspicious Transaction Reports (STRs)

Offences:
- Money laundering (AML/CFT Act)
- Structuring (avoiding reporting)
- Dealings with property from crime
- Criminal Proceeds (Recovery) Act

Financial Analysis:
- Bank statement analysis
- Transaction patterns
- Source of funds verification
- Lifestyle vs declared income
- Asset purchases
- Business analysis
- Cash flow analysis

International:
- Offshore accounts
- Tax havens
- Mutual legal assistance
- INTERPOL
- Five Eyes intelligence
- FATF (Financial Action Task Force)

Cryptocurrency:
- Bitcoin tracing
- Exchange records
- Wallet analysis
- Blockchain analysis
- Mixers/tumblers
- Dark web transactions

Seizure and Forfeiture:
- Criminal Proceeds (Recovery) Act
- Restraining orders
- Profit forfeiture
- Instrument forfeiture

Related Legislation:
- AML/CFT Act 2009
- Criminal Proceeds (Recovery) Act 2009
- Crimes Act 1961
- Tax Administration Act 1994
""",
        "key_procedures": [
            "Gather financial intelligence",
            "Obtain bank records via Production Orders",
            "Analyze transaction patterns",
            "Trace asset purchases",
            "International cooperation if offshore",
            "Apply for restraining/forfeiture orders"
        ]
    },
    
    "organised_crime": {
        "title": "Police Manual - Organised Crime Investigation",
        "chapter": "O",
        "section": "Gangs and Organised Criminal Groups",
        "category": "Organised Crime",
        "content": """
POLICE MANUAL - ORGANISED CRIME INVESTIGATION

Crimes Act 1961 (participation in criminal group)

Organised Crime Characteristics:
- Hierarchical structure
- Continuing criminal enterprise
- Multiple criminal activities
- Violence/corruption to maintain control
- Financial gain motivation
- Code of silence (omerta)

Criminal Groups in NZ:
- Motorcycle gangs (Head Hunters, Mongrel Mob, Black Power, etc.)
- Ethnic organized crime
- Transnational organized crime
- Drug trafficking networks
- Money laundering networks

Investigation Methods:
- Long-term investigations
- Undercover operations
- Human sources (informants)
- Electronic surveillance
- Financial investigation
- Cell site analysis
- Association mapping
- Communication analysis

Joint Operations:
- National Organised Crime Group (NOCG)
- Organised Crime Agency
- Customs
- Immigration
- International partners (FBI, AFP, NCA, etc.)

Offences:
- Participation in criminal group (s 98A Crimes Act)
- Conspiracy
- Money laundering
- Drug trafficking
- Violence offences
- Firearms offences
- Witness intimidation

Challenges:
- Code of silence
- Witness intimidation
- Sophisticated counter-surveillance
- International connections
- Financial complexity
- Encrypted communications
- Lack of complainants

Prevention and Disruption:
- Firearms prohibition orders
- Search powers (gang pads)
- Asset seizure
- Financial disruption
- Parole conditions
- Bail conditions
- Non-association orders

Gang Intelligence:
- Gang hierarchy
- Members and associates
- Territories
- Criminal activities
- Rivalries
- Alliances
- Recruitment

Related Legislation:
- Crimes Act 1961 (s 98A criminal groups)
- Search and Surveillance Act 2012
- Criminal Proceeds (Recovery) Act 2009
- Firearms Act 1983
""",
        "key_procedures": [
            "Long-term intelligence gathering",
            "Map criminal group structure",
            "Financial investigation",
            "Electronic surveillance warrants",
            "Undercover operations if appropriate",
            "Coordinate with specialized units"
        ]
    },
    
    "adult_sexual_assault": {
        "title": "Police Manual - Adult Sexual Assault Investigation",
        "chapter": "A",
        "section": "Sexual Violence Investigations",
        "category": "Sexual Violence",
        "content": """
POLICE MANUAL - ADULT SEXUAL ASSAULT INVESTIGATION

Crimes Act 1961 (sexual violation, attempted sexual violation)
Evidence Act 2006

Sexual Violation Offences:
- Rape (unlawful sexual connection)
- Unlawful sexual connection
- Attempted sexual violation
- Sexual conduct with consent induced by threats
- Indecent assault

Victim-Centered Approach:
- Trauma-informed
- Belief (start by believing)
- Safety first
- Medical needs
- Choice and control to victim
- Specialist investigators

Medical Examination (PERK):
- Physical Evidence Recovery Kit
- Consent required
- Medical practitioner or forensic nurse
- Evidence collection
- DNA collection
- Injury documentation
- Pregnancy/STI prevention offered
- Can be done without reporting to Police initially

Victim Interview:
- Specialist training required
- Video interview where possible
- Trauma-informed questioning
- Avoid repetitive interviews
- Details of assault
- Circumstances
- Offender description
- Witnesses
- Immediate aftermath

Offender Interview:
- Legal representation
- Full disclosure
- Defenses anticipated:
  * Consent
  * Identity (not me)
  * Fabrication
  * Memory issues (alcohol)

Consent Issues:
- Must be informed, voluntary, active
- Cannot consent if:
  * Unconscious
  * Too intoxicated
  * Coerced/threatened
  * Deceived
- Previous consent doesn't equal current consent
- Silence is not consent

Intoxication:
- Alcohol/drugs common factor
- Impacts memory
- Impacts consent capacity
- Impacts credibility assessments
- Toxicology may assist

Supporting Evidence:
- DNA
- Medical evidence (injuries)
- Witnesses
- CCTV
- Communications (texts, social media)
- Location data
- Offender history

Witness Protection:
- Victim safety paramount
- Name suppression automatic
- Testifying support
- Court preparation
- Protection orders available

Challenges:
- Often no witnesses
- Often no physical evidence
- Delayed reporting common
- Memory gaps (trauma/alcohol)
- Consent disputes
- Victim reluctance
- Defense of consent

Related Legislation:
- Crimes Act 1961
- Evidence Act 2006
- Victims' Rights Act 2002
- Sexual Violence Court (pilot)
""",
        "key_procedures": [
            "Believe victim initially",
            "Medical examination (PERK)",
            "Specialist victim interview",
            "Specialist offender interview",
            "Gather all supporting evidence",
            "Victim safety and support"
        ]
    },
    
    # MEDIUM PRIORITY CHAPTERS
    
    "armed_offenders": {
        "title": "Police Manual - Armed Offenders Squad (AOS)",
        "chapter": "A",
        "section": "Armed Offenders Squad Operations",
        "category": "Tactical Operations",
        "content": """
POLICE MANUAL - ARMED OFFENDERS SQUAD (AOS)

Armed Offenders Squads (AOS) are specialized tactical units for high-risk firearms situations.

Call-Out Criteria:
- Armed offender threatening serious harm
- Barricaded offender with firearms
- Hostage situations
- High-risk search warrants (firearms expected)
- Terrorist incidents
- Critical incidents

AOS Operators:
- Specially selected and trained
- Advanced firearms training
- Negotiation skills
- Entry tactics
- Medical training
- Physical fitness requirements

Command Structure:
- AOS Commander
- Tactical Commander
- Negotiators
- Entry teams
- Perimeter/containment
- Support staff

Response:
- Rapid deployment
- Containment priority
- Negotiation preferred
- Tactical resolution last resort
- Minimize harm to all parties

Equipment:
- Firearms (rifles, sidearms)
- Ballistic protection
- Ballistic shields
- Distraction devices
- Tactical equipment
- Armored vehicles

Negotiation:
- Primary option
- Trained negotiators
- Communication established
- De-escalation focus
- Time is tactical advantage

Tactical Options:
- Containment and negotiation
- Tactical entry
- Distraction devices
- Less lethal options
- Lethal force (last resort)

Post-Incident:
- Critical incident investigation
- IPCA notification (if serious injury/death)
- Debrief
- Psychological support
- Operational review

Related Legislation:
- Policing Act 2008
- Arms Act 1983
- Criminal Procedure Act 2011
""",
        "key_procedures": [
            "Contain and isolate",
            "Establish negotiation",
            "Tactical resolution only if necessary",
            "Minimize harm",
            "Post-incident investigation"
        ]
    },
    
    "burglary_investigation": {
        "title": "Police Manual - Burglary Investigation",
        "chapter": "B",
        "section": "Burglary and Unlawful Entry",
        "category": "Property Crime",
        "content": """
POLICE MANUAL - BURGLARY INVESTIGATION

Crimes Act 1961, s 231 (burglary)

Burglary Definition:
- Entering building/ship without authority
- With intent to commit crime therein
- OR having entered, commits crime

Scene Attendance:
- Prevent contamination
- Scene examination
- Fingerprint/DNA opportunities
- Point of entry/exit
- Property taken inventory
- Neighbor inquiries
- CCTV canvass

Forensic Evidence:
- Fingerprints
- DNA (blood, touch DNA)
- Tool marks
- Footwear impressions
- Point of entry damage
- Glass fragments

Victim Statement:
- What happened
- What was taken
- Value of property
- Insurance details
- Any suspects
- Recent visitors/suspicious persons
- Security measures

Investigation:
- Neighbor interviews
- CCTV review
- Cell site analysis (if phone taken)
- Bank monitoring (if cards taken)
- Pawn shop checks
- Online sales monitoring
- Associate inquiries
- Search warrants if suspect identified

Prevention Advice:
- Locks
- Alarms
- Lighting
- Timers
- Neighbor watch
- Insurance
- Property marking
- Serial number recording

Related Legislation:
- Crimes Act 1961, s 231
- Search and Surveillance Act 2012
""",
        "key_procedures": [
            "Secure and examine scene",
            "Gather forensic evidence",
            "Victim statement",
            "Neighborhood inquiries",
            "CCTV canvass",
            "Monitor pawn shops/online sales"
        ]
    },
    
    "crime_prevention": {
        "title": "Police Manual - Crime Prevention",
        "chapter": "C",
        "section": "Prevention and Community Safety",
        "category": "Crime Prevention",
        "content": """
POLICE MANUAL - CRIME PREVENTION

Policing Act 2008 - Crime prevention function

Prevention Philosophy:
- Prevention better than response
- Community partnerships
- Problem-solving approach
- Reducing opportunity
- Target hardening

Situational Crime Prevention:
- Increase effort (locks, barriers)
- Increase risk (surveillance, alarms)
- Reduce rewards (property marking)
- Reduce provocations (crowd management)
- Remove excuses (clear rules)

Community Engagement:
- Neighborhood Support
- Business partnerships
- School programs
- Community meetings
- Social media
- Multi-agency approach

Problem-Oriented Policing (POP):
- Scanning (identify problem)
- Analysis (understand causes)
- Response (develop solutions)
- Assessment (evaluate effectiveness)

Hotspot Policing:
- Crime concentration analysis
- Targeted patrols
- High-visibility policing
- Environmental design changes

CPTED (Crime Prevention Through Environmental Design):
- Natural surveillance
- Access control
- Territorial reinforcement
- Maintenance

Youth Prevention:
- Youth Aid
- Diversion programs
- School liaison
- Family support
- Alternative activities

Technology:
- CCTV
- ANPR
- Alarms
- Smart home security
- Social media monitoring

Evaluation:
- Crime statistics
- Community surveys
- Cost-benefit analysis
- Sustainability
""",
        "key_procedures": [
            "Analyze crime patterns",
            "Engage community",
            "Implement prevention measures",
            "Target hardening",
            "Evaluate effectiveness"
        ]
    },
    
    "criminal_profiling": {
        "title": "Police Manual - Criminal Profiling",
        "chapter": "C",
        "section": "Behavioral Analysis and Offender Profiling",
        "category": "Investigation Support",
        "content": """
POLICE MANUAL - CRIMINAL PROFILING

Behavioral Science:
- Analysis of offender behavior
- Crime scene analysis
- Victim selection
- Offender characteristics
- Geographic profiling
- Link analysis

Profiling Process:
1. Data collection (crime scene, victim, witness)
2. Crime scene analysis
3. Victimology
4. Offender characteristics
5. Investigative suggestions
6. Assessment

Types of Profiling:
- Geographical (location patterns)
- Investigative (suspect prioritization)
- Psychological (motivation, personality)
- Victimology (victim selection)

Limitations:
- Not definitive
- Cannot replace evidence
- Subject to bias
- Not a substitute for investigation
- Cannot predict identity with certainty

Applications:
- Serial offending
- Homicide
- Sexual offending
- Arson
- Threat assessment
- Stalking

Ethical Considerations:
- Racial profiling prohibited
- Must be evidence-based
- Cannot stereotype
- Cultural sensitivity
- Accountability

Related Legislation:
- Policing Act 2008
- Bill of Rights Act 1990
- Evidence Act 2006
""",
        "key_procedures": [
            "Gather comprehensive data",
            "Crime scene analysis",
            "Victimology assessment",
            "Behavioral pattern analysis",
            "Investigative suggestions",
            "Continuous reassessment"
        ]
    },
    
    "emergency_management": {
        "title": "Police Manual - Emergency Management",
        "chapter": "E",
        "section": "Civil Defence and Emergency Response",
        "category": "Emergency Management",
        "content": """
POLICE MANUAL - EMERGENCY MANAGEMENT

Civil Defence Emergency Management Act 2002

Police Role:
- Emergency response
- Evacuation
- Crowd control
- Traffic management
- Search and rescue
- Body recovery
- Crime scene preservation (if applicable)

Types of Emergencies:
- Natural disasters (earthquake, flood, tsunami)
- Industrial accidents
- Terrorism
- Pandemics
- Infrastructure failure
- Mass casualty events

Incident Control:
- Police may lead or support
- Coordination with Fire, Ambulance, CDEM
- Incident Control Point (ICP)
- Unified command structure
- Communication protocols

Evacuation:
- Authority to evacuate
- Public safety priority
- Traffic management
- Coordination with welfare agencies
- Special needs populations

Curfews:
- Can be declared in emergency
- Authority under CDEMA
- Enforcement
- Exceptions for essential services

Search and Rescue:
- LandSAR coordination
- Police SAR units
- Resources
- Specialist teams
- Helicopter operations

Communication:
- Public information
- Media liaison
- Social media
- Emergency alerts
- Coordination with other agencies

After Emergency:
- Transition to recovery
- Investigation (if criminal)
- Lessons learned
- Debrief
- Support for staff

Related Legislation:
- Civil Defence Emergency Management Act 2002
- Health Act 1956
- Policing Act 2008
""",
        "key_procedures": [
            "Immediate safety assessment",
            "Coordinate with emergency services",
            "Implement evacuation if necessary",
            "Manage crowds and traffic",
            "Communication with public",
            "Transition to recovery phase"
        ]
    },
    
    "ethical_standards": {
        "title": "Police Manual - Ethical Standards and Misconduct",
        "chapter": "E",
        "section": "Police Conduct and Discipline",
        "category": "Police Conduct",
        "content": """
POLICE MANUAL - ETHICAL STANDARDS AND MISCONDUCT

Code of Conduct:
- Integrity
- Professionalism
- Respect
- Commitment to Māori and Treaty
- Customer focus
- Valuing diversity

Types of Misconduct:
- Corruption (bribes, leaks)
- Dishonesty (theft, fraud)
- Misuse of position
- Excessive force
- Discrimination
- Harassment
- Confidentiality breaches
- Off-duty conduct affecting reputation

Reporting:
- Supervisor notification
- Professional Standards
- IPCA (Independent Police Conduct Authority)
- Protected disclosures (whistleblowing)

Investigation:
- Criminal investigation (if criminal offending)
- Employment investigation (misconduct)
- IPCA oversight
- Natural justice principles

Outcomes:
- Criminal charges
- Employment disciplinary action
- Training/retraining
- Counseling
- Dismissal

Conflicts of Interest:
- Must be declared
- Recusal if necessary
- Secondary employment approval
- Gifts and hospitality rules
- Association with criminals

Protected Disclosures:
- Whistleblower protection
- Reporting serious wrongdoing
- Confidentiality
- No retaliation

Related Legislation:
- Policing Act 2008
- Protected Disclosures Act 2000
- Employment Relations Act 2000
""",
        "key_procedures": [
            "Report suspected misconduct",
            "Investigate thoroughly",
            "Maintain confidentiality",
            "Natural justice to officer",
            "Appropriate disciplinary action",
            "IPCA notification if serious"
        ]
    },
    
    "fingerprint_examination": {
        "title": "Police Manual - Fingerprint Examination",
        "chapter": "F",
        "section": "Fingerprint Identification and Analysis",
        "category": "Forensic Identification",
        "content": """
POLICE MANUAL - FINGERPRINT EXAMINATION

Fingerprint Principles:
- Unique to individual
- Permanent throughout life
- Can be left on surfaces (latent prints)
- Can be visible or require enhancement

Fingerprint Types:
- Latent (invisible, requires development)
- Patent (visible, blood/ink/grease)
- Impressed (plastic impressions in soft surfaces)

Collection:
- Photography
- Lifting with tape
- Casting (for 3D impressions)
- Surface-appropriate techniques

Identification Process:
1. Analysis (quality assessment)
2. Comparison (ridge characteristics)
3. Evaluation (match/non-match/inconclusive)
4. Verification (second examiner)

AFIS (Automated Fingerprint Identification System):
- Database search
- Candidate list generated
- Manual comparison of candidates
- Confirmation required

Quality Factors:
- Surface type
- Environmental conditions
- Age of print
- Development technique
- Comparison quality

Challenging Evidence:
- Subjectivity of analysis
- Cognitive bias
- Quality of latent print
- Statistical basis
- Verification procedures
- Error rates

Related Legislation:
- Evidence Act 2006
- Criminal Procedure Act 2011
""",
        "key_procedures": [
            "Photograph before lifting",
            "Use appropriate development technique",
            "Enter into AFIS",
            "Manual comparison",
            "Verification by second examiner",
            "Comprehensive documentation"
        ]
    },
    
    "firearms_licensing": {
        "title": "Police Manual - Firearms Licensing",
        "chapter": "F",
        "section": "Arms Act Administration",
        "category": "Firearms Regulation",
        "content": """
POLICE MANUAL - FIREARMS LICENSING

Arms Act 1983

Licensing:
- Firearms Licence required for most firearms
- Endorsements required for:
  * Pistols (B endorsement)
  * Military-style semi-automatics (E endorsement)
  * Collectors (C endorsement)
  * Dealers (D endorsement)

Application Process:
- Application form
- Safety course
- Background check
- Referee interviews
- Home security inspection
- Criminal history check
- Mental health check
- Reason for having firearm

Fit and Proper Person:
- No criminal convictions (certain)
- No mental health concerns
- No domestic violence history
- Secure storage
- Genuine reason

Storage Requirements:
- Locked cabinet/bolted safe
- Ammunition separate or secured
- No easy access by unauthorized persons
- Inspections

Revocation:
- Can revoke if no longer fit and proper
- Criminal conviction
- Domestic violence
- Mental health deterioration
- Unsafe storage
- Misuse

Inspections:
- Random compliance checks
- Storage verification
- Records check

Prohibited Firearms:
- Certain categories prohibited
- Buy-back schemes (post-March 15)
- Exemptions for specific purposes

Related Legislation:
- Arms Act 1983
- Arms Regulations 1992
""",
        "key_procedures": [
            "Verify identity and background",
            "Check home security",
            "Interview referees",
            "Assess genuine reason",
            "Conduct safety inspection",
            "Monitor compliance"
        ]
    },
    
    "gang_intelligence": {
        "title": "Police Manual - Gang Intelligence",
        "chapter": "G",
        "section": "Gang Investigations and Monitoring",
        "category": "Organised Crime",
        "content": """
POLICE MANUAL - GANG INTELLIGENCE

Gangs in New Zealand:
- Mongrel Mob
- Black Power
- Head Hunters
- Nomads
- Hells Angels
- Other outlaw motorcycle gangs (OMCGs)
- Ethnic gangs
- Youth gangs

Intelligence Gathering:
- Membership lists
- Hierarchies
- Territories
- Criminal activities
- Associates
- Alliances and rivalries
- Recruitment
- Financial networks

Monitoring:
- Surveillance
- Informants
- Communication analysis
- Social media monitoring
- Financial tracking
- Intelligence sharing

Gang Pads (Headquarters):
- Search warrants
- Firearms searches
- Drug searches
- Association restrictions
- Firearms Prohibition Orders (FPOs)

Firearms Prohibition Orders (FPOs):
- Can apply to gang members
- Prohibits possession of firearms
- Warrantless search power
- 10-year duration

Prevention:
- Exit programs
- Youth diversion
- Family support
- Employment initiatives
- Community engagement

Related Legislation:
- Search and Surveillance Act 2012
- Firearms Act 1983
- Arms (Firearms Prohibition Orders) Act 2023
""",
        "key_procedures": [
            "Maintain intelligence database",
            "Monitor gang activities",
            "Execute search warrants on pads",
            "Apply FPOs where appropriate",
            "Coordinate with organized crime units",
            "Support exit programs"
        ]
    },
    
    "human_trafficking": {
        "title": "Police Manual - Human Trafficking",
        "chapter": "H",
        "section": "Trafficking in Persons",
        "category": "Organised Crime",
        "content": """
POLICE MANUAL - HUMAN TRAFFICKING

Crimes Act 1961 (trafficking, slavery)
Immigration Act 2009

Forms of Trafficking:
- Sex trafficking
- Labour trafficking
- Domestic servitude
- Forced marriage
- Organ trafficking
- Child trafficking

Indicators:
- Restricted movement
- Confiscated documents
- Debt bondage
- Excessive working hours
- No pay or minimal pay
- Poor living conditions
- Physical/psychological abuse
- Isolation
- Controlled communication

Victims:
- Often reluctant to report
- Fear of authorities
- Fear of deportation
- Fear of traffickers
- Language barriers
- Psychological trauma

Approach:
- Trauma-informed
- Victim protection priority
- Do not treat as immigration offender initially
- Secure immediate safety
- Medical attention
- Interpreter
- Victim support
- Legal advice

Investigation:
- Financial tracking
- Surveillance
- Victim interviews (careful)
- Document seizure
- International cooperation
- Border alerts

Offences:
- Trafficking (Crimes Act)
- Slavery
- Debt bondage
- Exploitation
- Immigration offences

Victim Support:
- Protection
- Accommodation
- Medical care
- Counseling
- Legal support
- Immigration assistance
- Possible residence visa

Related Legislation:
- Crimes Act 1961
- Immigration Act 2009
- Oranga Tamariki Act 1989
""",
        "key_procedures": [
            "Identify trafficking indicators",
            "Ensure victim safety",
            "Do not penalize for immigration status",
            "Trauma-informed approach",
            "Financial investigation",
            "International cooperation"
        ]
    },
    
    "maritime_powers": {
        "title": "Police Manual - Maritime Powers",
        "chapter": "M",
        "section": "Maritime Law Enforcement",
        "category": "Maritime Policing",
        "content": """
POLICE MANUAL - MARITIME POWERS

Maritime Transport Act 1994
Search and Surveillance Act 2012 (maritime provisions)

Jurisdiction:
- Territorial sea (12 nautical miles)
- Contiguous zone
- Exclusive Economic Zone
- High seas (for NZ vessels)

Powers:
- Stop and board vessels
- Search vessels
- Search persons on vessels
- Arrest persons
- Seize evidence
- Detain vessels
- Drug enforcement
- Fisheries enforcement

Drug Importation:
- Border-controlled drugs
- Interdiction operations
- Coordination with Customs
- Coordination with Navy
- Surveillance

Safety:
- Search and rescue
- Safety equipment checks
- Vessel safety
- Intoxication (boaties)

Coordination:
- Maritime New Zealand
- Customs
- Navy
- Coastguard
- LandSAR

Related Legislation:
- Maritime Transport Act 1994
- Search and Surveillance Act 2012
- Misuse of Drugs Act 1975
- Fisheries Act 1996
""",
        "key_procedures": [
            "Coordinate with maritime agencies",
            "Board and search vessels",
            "Safety compliance checks",
            "Drug interdiction operations",
            "Search and rescue coordination"
        ]
    },
    
    "photofit_identification": {
        "title": "Police Manual - Photofit and Identification Procedures",
        "chapter": "P",
        "section": "Witness Identification Methods",
        "category": "Identification",
        "content": """
POLICE MANUAL - PHOTOFIT AND IDENTIFICATION

Evidence Act 2006
Criminal Procedure Act 2011

Identification Methods:
1. Photofit/Comfit (computerized composite)
2. Photo montage (photo board)
3. Video identification
4. Identity parade (live lineup)
5. Street identification
6. Formal identification procedures

Photofit/Comfit:
- Witness describes features
- Computer generates image
- Can be released to media
- Not evidence itself
- Investigative tool

Photo Montage:
- Similar photographs shown
- Suspect photo among foils
- Witness views individually
- No indication of who is suspect
- Formal procedure required

Video Identification:
- Similar to montage but video
- Suspect and foils in similar poses
- Formal procedure required

Identity Parade:
- Live lineup
- Suspect and foils
- Similar appearance
- Witness views entire parade
- Formal procedure required

Formal Procedure Requirements:
- Must follow code of practice
- Accused entitled to have lawyer present
- Accused entitled to object to foils
- Must record procedure
- Must not suggest who is suspect
- Independent administrator

Challenging Identification:
- Unfair procedure
- Breach of code
- Unreliable
- Collusion
- Suggestion
- Poor viewing conditions

Related Legislation:
- Evidence Act 2006
- Criminal Procedure Act 2011
""",
        "key_procedures": [
            "Use formal identification procedures",
            "Follow code of practice",
            "Independent administrator",
            "Record procedure",
            "No suggestion to witness",
            "Defence entitled to be present"
        ]
    },
    
    "prisoner_escort": {
        "title": "Police Manual - Prisoner Escort and Transport",
        "chapter": "P",
        "section": "Custody and Transportation",
        "category": "Prisoner Management",
        "content": """
POLICE MANUAL - PRISONER ESCORT AND TRANSPORT

Prisoner Transport:
- Between Police stations
- To/from court
- To/from prison
- To/from medical facilities
- Interstate/international transfers

Security:
- Adequate restraints
- Vehicle security
- Route planning
- Emergency procedures
- Communication
- Number of escorts

Risk Assessment:
- Escape risk
- Violence risk
- Self-harm risk
- Medical needs
- High-profile prisoner
- Gang affiliations

Restraints:
- Handcuffs (standard)
- Leg irons (higher risk)
- Belly chains (high risk)
- Application and removal
- Safety considerations
- Medical emergencies

Vehicle Safety:
- Secure compartment
- Cage/barrier
- Seatbelts
- Emergency exits
- First aid
- Communication equipment

Court Escort:
- Coordination with court security
- Cell-to-dock protocol
- Public contact minimization
- Media considerations
- Co-accused separation

Medical Escort:
- Hospital security
- Bed restraints if necessary
- Medical staff coordination
- Risk assessment
- Escape prevention

Documentation:
- Prisoner details
- Escort officers
- Route
- Times
- Incidents
- Handover receipts

Related Legislation:
- Policing Act 2008
- Corrections Act 2004
- Prisoners and Victims Claims Act 2005
""",
        "key_procedures": [
            "Conduct risk assessment",
            "Apply appropriate restraints",
            "Secure transport vehicle",
            "Route planning",
            "Maintain communication",
            "Documentation and handover"
        ]
    },
    
    "prosecutions": {
        "title": "Police Manual - Prosecutions",
        "chapter": "P",
        "section": "Charging and Prosecution Decisions",
        "category": "Prosecutions",
        "content": """
POLICE MANUAL - PROSECUTIONS

Criminal Procedure Act 2011
Solicitor-General's Prosecution Guidelines

Charging Standards:
- Sufficient evidence to justify prosecution
- Public interest test
- Likely prospect of conviction
- Charging document requirements

Evidential Sufficiency:
- Prima facie case
- Admissible evidence
- Reliable evidence
- Credible witnesses
- Defenses considered

Public Interest Factors:
- Seriousness of offence
- Circumstances of offender
- Age of offender
- Mental health
- Delay since offence
- Impact on victim
- Community expectations
- Alternatives to prosecution

Charging Document:
- Filed in court
- Must state offence
- Must refer to statute
- Must include particulars
- Can be amended
- Time limits apply

Remand Decisions:
- Police bail
- Court bail
- Remand in custody
- Conditions of bail

Diversion:
- Adult diversion scheme
- Youth diversion
- Conditions
- No conviction if completed
- Rehabilitation focus

Withdrawal of Charges:
- Can withdraw before trial
- Must be in writing
- Reasons recorded
- May re-lay in certain circumstances

Related Legislation:
- Criminal Procedure Act 2011
- Criminal Procedure Rules 2012
""",
        "key_procedures": [
            "Assess evidential sufficiency",
            "Apply public interest test",
            "Prepare charging document",
            "Consider bail/remand",
            "Consider diversion alternatives",
            "File in court"
        ]
    },
    
    "security_clearances": {
        "title": "Police Manual - Security Clearances",
        "chapter": "S",
        "section": "Personnel Vetting and Clearances",
        "category": "Personnel Security",
        "content": """
POLICE MANUAL - SECURITY CLEARANCES

Police Vetting:
- Required for Police employees
- Required for contractors
- Required for some volunteers
- Ongoing monitoring

Levels of Clearance:
- Reliability check
- Confidential
- Secret
- Top Secret

Vetting Process:
- Identity verification
- Criminal history check
- Credit check
- Reference checks
- Background check
- Associate inquiries
- Interview
- Risk assessment

Disqualifying Factors:
- Serious criminal convictions
- Dishonesty
- Violence
- Drug offending
- Gang associations
- Security concerns
- Mental health (in some cases)

Ongoing Monitoring:
- Annual checks
- Self-reporting obligations
- Incident reporting
- Clearance reviews
- Suspension if concerns arise

Related Legislation:
- Policing Act 2008
- Privacy Act 2020
- Criminal Records (Clean Slate) Act 2004
""",
        "key_procedures": [
            "Verify identity",
            "Conduct background checks",
            "Interview applicant",
            "Assess risk",
            "Grant appropriate clearance",
            "Ongoing monitoring"
        ]
    },
    
    "sex_offender_register": {
        "title": "Police Manual - Sex Offender Register",
        "chapter": "S",
        "section": "Registered Offender Monitoring",
        "category": "Offender Monitoring",
        "content": """
POLICE MANUAL - SEX OFFENDER REGISTER

Sex Offender Register regulations

Registration Required:
- Convicted of qualifying sexual offence
- Must register within prescribed period
- Provides details to Police
- Updates required for changes

Qualifying Offences:
- Sexual violation
- Unlawful sexual connection
- Indecent assault
- Child sex offences
- Indecent acts
- Possession of objectionable material
- Other specified offences

Registration Details:
- Name and aliases
- Address
- Employment
- Vehicle details
- Online identifiers
- Travel plans
- Regular photographs

Reporting Requirements:
- Initial registration
- Annual reporting
- Change of details (within prescribed time)
- Interstate/international travel
- Return from travel

Verification:
- Police visit registered address
- Verification of details
- Compliance checks
- Risk assessment

Duration:
- 8 years, 15 years, or life
- Depending on offence and sentence
- Can apply for reduction (not life)

Non-Compliance:
- Offence to fail to register
- Offence to provide false information
- Offence to fail to report changes
- Arrest power

Related Legislation:
- Crimes Act 1961
- Parole Act 2002
""",
        "key_procedures": [
            "Ensure registration completed",
            "Verify details provided",
            "Conduct compliance checks",
            "Update records",
            "Enforce non-compliance",
            "Risk assessment"
        ]
    },
    
    "suicide_prevention": {
        "title": "Police Manual - Suicide Prevention",
        "chapter": "S",
        "section": "Mental Health Crisis Response",
        "category": "Mental Health",
        "content": """
POLICE MANUAL - SUICIDE PREVENTION

Mental Health Act 1992

Police Role:
- Welfare checks
- Crisis intervention
- Transport to hospital
- Securing scenes
- Death investigations (if suicide occurs)

Risk Assessment:
- Direct threats
- Plan
- Means available
- Previous attempts
- Mental health history
- Substance use
- Recent stressors
- Support systems

Communication:
- Empathetic listening
- Non-judgmental
- De-escalation
- Build rapport
- Take threats seriously
- Avoid platitudes

Intervention:
- Safety priority
- Remove means if safe
- Involve mental health services
- Transport to hospital if necessary
- Section 41 Mental Health Act (apprehension)
- Don't leave person alone

Mental Health Act Powers:
- Section 41: Police can apprehend if mentally disordered and serious danger
- Transport to hospital
- Doctor assessment required

Post-Intervention:
- Handover to mental health services
- Documentation
- Follow-up if appropriate
- Officer welfare

Suicide Scene:
- Preserve evidence
- Coroner notification
- Family notification
- Media management
- Support for witnesses

Officer Welfare:
- Trauma exposure
- Peer support
- Counseling available
- Critical incident stress management

Related Legislation:
- Mental Health (Compulsory Assessment and Treatment) Act 1992
- Coroners Act 2006
""",
        "key_procedures": [
            "Assess immediate risk",
            "Communicate empathetically",
            "Remove means if safe",
            "Involve mental health services",
            "Transport to hospital if necessary",
            "Document and handover"
        ]
    },
    
    "transgender_custody": {
        "title": "Police Manual - Transgender Persons in Custody",
        "chapter": "T",
        "section": "Gender Diverse Persons in Police Custody",
        "category": "Custody and Diversity",
        "content": """
POLICE MANUAL - TRANSGENDER PERSONS IN CUSTODY

Human Rights Act 1993
Bill of Rights Act 1990

Definitions:
- Transgender: Person whose gender identity differs from sex assigned at birth
- Non-binary: Gender identity not exclusively male or female
- Intersex: Born with physical sex characteristics that don't fit typical binary

Respect and Dignity:
- Use preferred name and pronouns
- Respect gender identity
- Privacy regarding transgender status
- No discrimination
- Safety from harm

Searching:
- Transgender women (male to female): searched by female officer if possible
- Transgender men (female to male): searched by male officer if possible
- If officer of preferred gender not available, explain and offer options
- Privacy and dignity maintained

Custody Placement:
- Generally place according to gender identity
- Risk assessment for safety
- Individual placement decisions
- Protect from violence/harassment
- May require single cell for safety

Documentation:
- Record preferred name
- Record pronouns
- Any specific needs
- Safety concerns
- Medical needs (hormone medication)

Medical Needs:
- Hormone medication must be continued
- Medical privacy
- Any gender-affirming medical devices

Related Legislation:
- Human Rights Act 1993
- Bill of Rights Act 1990
""",
        "key_procedures": [
            "Ask preferred name and pronouns",
            "Respect gender identity",
            "Place according to gender identity",
            "Ensure safety in custody",
            "Continue hormone medication",
            "Maintain privacy"
        ]
    },
    
    "wanted_persons": {
        "title": "Police Manual - Wanted Persons",
        "chapter": "W",
        "section": "Locating and Apprehending Wanted Persons",
        "category": "Investigations",
        "content": """
POLICE MANUAL - WANTED PERSONS

Warrants to Arrest:
- Bench warrants (court issued for non-appearance)
- Arrest warrants
- Must be executed without unnecessary delay

Posting as Wanted:
- Enter in Police database
- Interpol Red Notice (international)
- Border alerts
- Public appeals (if appropriate)
- Media releases

Location Methods:
- Database checks
- Informants
- Surveillance
- Associate inquiries
- Bank monitoring
- Cell site analysis
- Social media monitoring
- Passport tracking

Apprehension:
- Any Police officer can execute warrant
- Time and place
- Use of force if necessary
- Rights on arrest
- Bail consideration

Safe Surrender:
- Can negotiate surrender
- Lawyer present
- Public place
- Safety considerations
- Media management

Extradition:
- Interstate (Australia)
- International
- Extradition Act 1999
- Treaty or non-treaty
- Court process
- Ministerial decision

Related Legislation:
- Criminal Procedure Act 2011
- Extradition Act 1999
- Immigration Act 2009
""",
        "key_procedures": [
            "Enter wanted person in database",
            "Set up alerts",
            "Conduct inquiries to locate",
            "Execute warrant",
            "Consider safe surrender options",
            "Extradition if international"
        ]
    },
}

def create_all_remaining():
    """Create all remaining Police Manual chapters"""
    output_dir = Path("./data/police_manual_remaining")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for chapter_id, chapter_data in REMAINING_CHAPTERS.items():
        filepath = output_dir / f"{chapter_id}.json"
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                **chapter_data,
                "created": datetime.now().isoformat(),
                "source": "Police Manual (NZ Police) - Compiled"
            }, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Created: {filepath.name}")
    
    print(f"\n{'='*60}")
    print(f"✓ Total: {len(REMAINING_CHAPTERS)} chapters created")
    print(f"{'='*60}")
    return len(REMAINING_CHAPTERS)

if __name__ == "__main__":
    count = create_all_remaining()
    print(f"\nHigh Priority: 23 chapters")
    print(f"Medium Priority: 25 chapters") 
    print(f"Total created: {count} chapters")
    print("\nNext: Run ingestion script to add to database")
