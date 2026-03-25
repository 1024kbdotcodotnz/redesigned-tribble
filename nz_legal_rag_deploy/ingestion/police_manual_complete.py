#!/usr/bin/env python3
"""
Complete NZ Police Manual Import
All chapters A-Z plus sub-chapters
"""

import json
from pathlib import Path
from datetime import datetime

POLICE_MANUAL_COMPLETE = {
    # Already added chapters (will be skipped if exist)
    "search_warrantless": {
        "title": "Police Manual - Search Powers (Warrantless)",
        "chapter": "S",
        "section": "Warrantless Search Powers",
        "category": "Search and Surveillance",
        "priority": 1
    },
    "search_warrants": {
        "title": "Police Manual - Search Warrants",
        "chapter": "S",
        "section": "Search Warrants",
        "category": "Search and Surveillance",
        "priority": 1
    },
    "interview_adults": {
        "title": "Police Manual - Interviewing Adults",
        "chapter": "I",
        "section": "Interviewing Adults",
        "category": "Interview and Questioning",
        "priority": 1
    },
    "interview_youth": {
        "title": "Police Manual - Interviewing Young Persons",
        "chapter": "C",
        "section": "Young Persons",
        "category": "Children and Young Persons",
        "priority": 1
    },
    "disclosure": {
        "title": "Police Manual - Disclosure",
        "chapter": "D",
        "section": "Criminal Case Disclosure",
        "category": "Disclosure and Prosecution",
        "priority": 1
    },
    "use_of_force": {
        "title": "Police Manual - Use of Force",
        "chapter": "F",
        "section": "Use of Force",
        "category": "Use of Force",
        "priority": 1
    },
    "forensic_procedures": {
        "title": "Police Manual - Forensic Procedures",
        "chapter": "F",
        "section": "Forensic Procedures",
        "category": "Evidence Collection",
        "priority": 1
    },
    "complaints": {
        "title": "Police Manual - Complaints Against Police",
        "chapter": "Q",
        "section": "Complaints Management",
        "category": "Complaints and Conduct",
        "priority": 1
    },
    "covert_operations": {
        "title": "Police Manual - Controlled Operations",
        "chapter": "C",
        "section": "Controlled Operations",
        "category": "Surveillance and Covert Operations",
        "priority": 1
    },
    
    # NEW CHAPTERS - A to Z
    
    # A - Alcohol
    "alcohol": {
        "title": "Police Manual - Alcohol",
    "chapter": "A",
    "section": "Licensed Premises and Intoxication",
    "category": "Alcohol Enforcement",
        "content": """
POLICE MANUAL - ALCOHOL (LICENSED PREMISES AND INTOXICATION)

Sale and Supply of Alcohol Act 2012

Police Powers:
- Enter licensed premises without warrant to inspect
- Request production of licence
- Inspect records and documents
- Remove persons from licensed premises
- Seize alcohol from minors

Intoxication:
- Definition: State of intoxication means affected by alcohol to such a degree that the person is unable to care for themselves or is a risk to others
- Licensed premises must not serve intoxicated persons
- Police may remove intoxicated persons from licensed premises

Controlled Purchase Operations:
- Underage persons used to test compliance
- Must be authorized
- Must follow strict protocols
- Evidence must be recorded

Dry Areas:
- Local alcohol bans
- Can be temporary or permanent
- Police can seize alcohol in ban areas
- Offence to consume or possess in ban area

Enforcement Options:
- Verbal warning
- Written warning
- Prosecution
- Referral to licensing authority
- Application for licence suspension/cancellation

Working With Licensing Inspectors:
- District Licensing Committees
- Medical Officers of Health
- Territorial authorities
- Cooperation on compliance issues

Related Legislation:
- Sale and Supply of Alcohol Act 2012
- Local Government Act 2002
- Criminal Procedure Act 2011
""",
        "key_procedures": [
            "Identify yourself as Police officer",
            "Inspect licence and conditions",
            "Document any breaches observed",
            "Issue appropriate enforcement action",
            "Report to licensing authority if required"
        ],
        "priority": 2
    },
    
    # B - Bail
    "bail": {
        "title": "Police Manual - Bail",
        "chapter": "B",
        "section": "Police Bail",
        "category": "Bail and Custody",
        "content": """
POLICE MANUAL - BAIL

Bail Act 2000

Police Bail Powers:
- Can grant bail after arrest before first appearance
- Must consider grounds for remand in custody
- Must impose conditions if necessary
- Must record bail decision

Grounds for Remand in Custody (s 8 Bail Act):
(a) Defendant will fail to appear
(b) Defendant will interfere with witnesses or evidence
(c) Defendant will offend while on bail
(d) Detention necessary for protection of defendant or another

Standard Bail Conditions:
- Reside at specified address
- Not associate with specified persons
- Not enter specified areas
- Report to Police station
- Surrender passport
- Curfew

Additional Conditions:
- Electronic monitoring
- Non-association orders
- Area restrictions
- Drug/alcohol testing
- Treatment programs
- Sureties

Bail Review:
- Defendant can apply for bail variation
- Police can apply to add conditions
- Court ultimately decides bail matters
- Police can arrest if bail conditions breached

Breach of Bail:
- Arrest without warrant
- Bring before court
- May result in remand in custody
- Separate offence of breach of bail

Youth Bail:
- Additional considerations for young persons
- Oranga Tamariki may be involved
- Parent/guardian involvement required
- Youth bail residences available

Related Legislation:
- Bail Act 2000
- Criminal Procedure Act 2011
- Oranga Tamariki Act 1989
""",
        "key_procedures": [
            "Assess grounds for remand in custody",
            "Check defendant's history and circumstances",
            "Determine appropriate conditions",
            "Complete bail documentation",
            "Explain conditions to defendant"
        ],
        "priority": 2
    },
    
    # C - Children & Young Persons (beyond what we have)
    "child_protection": {
        "title": "Police Manual - Child Protection",
        "chapter": "C",
        "section": "Child Protection Investigations",
        "category": "Children and Young Persons",
        "content": """
POLICE MANUAL - CHILD PROTECTION INVESTIGATIONS

Oranga Tamariki Act 1989

Mandatory Reporting:
- Police must report suspected abuse/neglect to Oranga Tamariki
- Applies to all Police staff
- Can be verbal initially, written to follow
- Report must be made as soon as practicable

Types of Concern:
- Physical abuse
- Sexual abuse
- Emotional abuse
- Neglect
- Domestic violence exposure
- Parental substance abuse
- Care and protection concerns

Investigation Process:
1. Immediate safety assessment
2. Notification to Oranga Tamariki
3. Joint investigation with Oranga Tamariki
4. Video interview (if disclosure)
5. Medical examination if required
6. Safety planning
7. Referral to services

Video Interviews:
- Must use trained interviewers
- Joint interviews with Oranga Tamariki
- Evidential interviews where possible
- Specialist child interview suites

Child Sexual Abuse:
- Dedicated Child Protection Teams
- Medical examination coordinated
- Therapy referral
- Court support
- Specialist prosecutor liaison

Child Death Investigations:
- Serious incident response
- Oranga Tamariki notification
- Multi-agency response
- Family support
- Coroner liaison

Youth Offending:
- Youth Aid officer involvement
- Family group conferences
- Youth Court jurisdiction
- Alternative actions
- Rehabilitation focus

Related Legislation:
- Oranga Tamariki Act 1989
- Children, Young Persons, and Their Families Act 1989
- Crimes Act 1961
""",
        "key_procedures": [
            "Assess immediate safety",
            "Notify Oranga Tamariki immediately",
            "Document all observations",
            "Conduct joint investigation",
            "Arrange video interview if appropriate"
        ],
        "priority": 2
    },
    
    # D - Deaths
    "sudden_deaths": {
        "title": "Police Manual - Sudden Deaths",
        "chapter": "D",
        "section": "Sudden Death Investigation",
        "category": "Death Investigations",
        "content": """
POLICE MANUAL - SUDDEN DEATH INVESTIGATION

Coroners Act 2006

Police Role:
- Initial response to sudden deaths
- Preserve scene
- Identify deceased
- Notify next of kin
- Support Coroner
- Determine if death suspicious

Categories of Death:
- Natural causes (medical certificate)
- Unnatural (Coroner notification required)
- Suicide
- Homicide
- Accidental
- Undetermined

Coroner Notification Required For:
- Sudden and unexpected deaths
- Deaths without medical cause
- Deaths in custody
- Deaths during medical procedure
- Deaths related to employment
- Suspected suicides

Scene Preservation:
- Secure scene
- Prevent contamination
- Document scene
- Preserve evidence
- Note body position/state

Next of Kin Notification:
- Must be done in person where possible
- Empathetic approach
- Provide support information
- Obtain identification details
- Note reactions/observations

Cultural Considerations:
- Tikanga Māori protocols
- Religious considerations
- Family wishes
- Interpreter if required
- Support person present

Documentation:
- Body identification
- Scene photographs
- Witness statements
- Timeline of events
- Medical history
- Medication information

Post-Mortem:
- Police attend with pathologist
- Observe and document
- Collect evidence
- Photograph injuries
- Note pathologist observations

Related Legislation:
- Coroners Act 2006
- Crimes Act 1961
- Births, Deaths, Marriages, and Relationships Registration Act 1995
""",
        "key_procedures": [
            "Secure and preserve scene",
            "Verify death with medical practitioner",
            "Notify next of kin",
            "Notify Coroner",
            "Document scene comprehensively"
        ],
        "priority": 3
    },
    
    # E - Evidence
    "evidence_collection": {
        "title": "Police Manual - Evidence Collection",
        "chapter": "E",
    "section": "Evidence Collection and Preservation",
    "category": "Evidence Collection",
        "content": """
POLICE MANUAL - EVIDENCE COLLECTION AND PRESERVATION

Evidence Act 2006

Chain of Custody:
- Essential for all exhibits
- Must record every person who handles
- Must record date/time/reason
- Must maintain integrity
- Must be able to account for exhibit at all times

Exhibit Categories:
1. Physical (weapons, clothing, drugs)
2. Documentary (statements, records)
3. Digital (computers, phones, CCTV)
4. Biological (blood, DNA, fingerprints)
5. Photographic (scenes, injuries)

Scene Examination:
- Systematic approach
- Photograph before disturbing
- Grid search method
- Environmental evidence
- Contamination prevention
- DNA elimination samples from officers

Packaging:
- Appropriate containers
- Labelling requirements
- Sealing protocols
- Biological evidence (breathable packaging)
- Sharp objects (safety)
- Liquids (leak-proof)

Labelling:
- Unique exhibit number
- Brief description
- Date/time collected
- Location found
- Collector's details
- Signature

Transport:
- Secure transport
- Maintaining chain of custody
- Biological evidence (temperature considerations)
- Urgent items flagged
- Documentation of transport

Storage:
- Secure exhibit room
- Access control
- Climate control for biologicals
- Electronic tracking
- Regular audits
- Destruction procedures for unclaimed items

Digital Evidence:
- Faraday bags for phones
- Write-blocking for computers
- Cloud preservation
- Social media preservation
- CCTV seizure
- Data extraction logs

Related Legislation:
- Evidence Act 2006
- Search and Surveillance Act 2012
- Privacy Act 2020
""",
        "key_procedures": [
            "Photograph evidence in situ",
            "Collect using appropriate methods",
            "Package securely with proper labelling",
            "Complete chain of custody documentation",
            "Store in secure exhibit room"
        ],
        "priority": 2
    },
    
    # F - Family Violence
    "family_violence": {
        "title": "Police Manual - Family Violence",
        "chapter": "F",
        "section": "Family Violence Response",
        "category": "Family Violence",
        "content": """
POLICE MANUAL - FAMILY VIOLENCE RESPONSE

Family Violence Act 2018

Definition:
Family violence includes:
- Physical abuse
- Sexual abuse
- Psychological abuse
- Economic abuse
- Coercive control
- Threats and intimidation
- Damage to property
- Abuse of pets
- Control of daily activities

Police Response:
- Safety first - check for injuries
- Separate parties
- Identify primary aggressor
- Risk assessment
- Safety planning
- Referrals to services

Risk Assessment:
- High risk indicators:
  * Strangulation
  * Threats to kill
  * Access to weapons
  * Recent separation
  * Stalking
  * Pregnancy
  * Children present
  * Escalation pattern
  * Substance abuse
  * Mental health issues

Protection Orders:
- Temporary protection orders (Police can apply)
- Final protection orders (Court)
- Non-contact conditions
- Property orders
- Tenancy orders
- Occupation orders
- Weapons prohibitions

Police Safety Orders (PSO):
- Can issue on scene
- Remove perpetrator up to 5 days
- No arrest required
- Must assess risk
- Alternative to arrest in some cases
- Cannot appeal

Breaches:
- Arrest for breach of protection order
- Document all breaches
- Multiple breaches indicate escalation
- Safety planning review

Children:
- Child safety paramount
- Notification to Oranga Tamariki
- Risk to children assessed
- Impact of witnessing violence

Related Legislation:
- Family Violence Act 2018
- Oranga Tamariki Act 1989
- Crimes Act 1961
- Protection of Personal and Property Rights Act 1988
""",
        "key_procedures": [
            "Assess immediate safety and injuries",
            "Separate parties for interviewing",
            "Conduct risk assessment",
            "Identify primary aggressor",
            "Consider Protection Order or PSO",
            "Make appropriate referrals"
        ],
        "priority": 2
    },
    
    # G - General Policing (powers and duties)
    "general_policing": {
        "title": "Police Manual - General Policing Powers",
        "chapter": "G",
        "section": "Police Powers and Duties",
        "category": "General Policing",
        "content": """
POLICE MANUAL - GENERAL POLICING POWERS AND DUTIES

Policing Act 2008

Functions of Police (s 8):
- Keep the peace
- Maintain public safety
- Law enforcement
- Crime prevention
- Community support and reassurance
- National security support
- Emergency management participation
- Road safety

Powers:
- Common law powers preserved
- Statutory powers (various Acts)
- Power of arrest (Crimes Act)
- Power of entry (specific circumstances)
- Power to demand particulars
- Power to stop vehicles
- Power to search (various circumstances)
- Power to seize

Duties:
- Serve and protect community
- Respect human rights
- Act professionally
- Maintain confidentiality
- Use minimum force necessary
- Be accountable
- Maintain competence

Human Rights Compliance:
- NZ Bill of Rights Act 1990 must be considered
- Right to life
- Right not to be subjected to torture
- Right to be free from discrimination
- Right to freedom of movement
- Right to be secure against unreasonable search
- Rights of arrested persons

Code of Conduct:
- Integrity
- Professionalism
- Respect
- Commitment to Māori and Treaty
- Customer focus
- Valuing diversity

Disciplinary:
- Misconduct
- Neglect of duty
- Corruption
- Conflicts of interest
- Criminal charges
- Employment consequences

Use of Discretion:
- Not all offences require enforcement
- Consider public interest
- Consider alternatives
- Document reasons
- Consistent application

Related Legislation:
- Policing Act 2008
- NZ Bill of Rights Act 1990
- Privacy Act 2020
- Official Information Act 1982
""",
        "key_procedures": [
            "Identify yourself as Police",
            "State the power being exercised",
            "Act within legal authority",
            "Respect human rights",
            "Document actions taken"
        ],
        "priority": 2
    },
    
    # H - Health & Safety
    "health_safety": {
        "title": "Police Manual - Health and Safety",
        "chapter": "H",
        "section": "Health and Safety in Policing",
    "category": "Health and Safety",
        "content": """
POLICE MANUAL - HEALTH AND SAFETY IN POLICING

Health and Safety at Work Act 2015

Police Responsibilities:
- Provide safe workplace
- Identify and manage hazards
- Training and supervision
- Personal protective equipment
- Emergency procedures
- Incident reporting

Officer Responsibilities:
- Take reasonable care for own safety
- Take reasonable care not to harm others
- Comply with policies and procedures
- Report hazards and incidents
- Use provided safety equipment

Common Hazards:
- Physical violence
- Biological hazards (blood, bodily fluids)
- Chemical hazards (clandestine labs, chemicals)
- Psychological hazards (trauma exposure)
- Road risks (pursuits, roadside stops)
- Firearms
- Dogs
- Environmental hazards

Personal Protective Equipment (PPE):
- Body armor (mandatory for frontline)
- Gloves (for searches, evidence)
- Eye protection
- Hearing protection
- Hi-visibility vests
- Helmets (for certain operations)
- Respirators (for clandestine labs)

Clandestine Laboratories:
- Highly dangerous
- Specialist response required
- Decontamination procedures
- Never enter without proper training and equipment
- Coordinate with Customs, Environmental agencies

Mental Health:
- Trauma exposure
- Critical incident stress
- PTSD recognition
- Peer support
- Employee assistance programs
- Mandatory referrals after serious incidents

Fatigue Management:
- Shift work risks
- Minimum rest periods
- Fitness for duty
- Self-reporting
- Supervisor monitoring

Related Legislation:
- Health and Safety at Work Act 2015
- Employment Relations Act 2000
""",
        "key_procedures": [
            "Assess risks before action",
            "Use appropriate PPE",
            "Follow safe operating procedures",
            "Report incidents and near-misses",
            "Look after mental health"
        ],
        "priority": 3
    },
    
    # I - Information Management
    "information_management": {
    "title": "Police Manual - Information Management",
        "chapter": "I",
    "section": "Privacy and Official Information",
    "category": "Information Management",
        "content": """
POLICE MANUAL - INFORMATION MANAGEMENT

Privacy Act 2020
Official Information Act 1982

Privacy Principles:
1. Purpose - collect for lawful purpose
2. Source - collect from individual if possible
3. Collection - lawful and fair
4. Manner - not unreasonably intrusive
5. Storage and security - protect from loss/unauthorized access
6. Access - individuals can access their information
7. Correction - individuals can request correction
8. Accuracy - ensure accuracy before use
9. Retention - not keep longer than necessary
10. Use - generally use for collected purpose
11. Disclosure - generally not disclose to others
12. Unique identifiers - not assign unnecessarily

Police National Intelligence Application (NIA):
- Central database
- Records of convictions
- Wanted persons
- Protection orders
- Driver licence information
- Vehicle registration
- Firearms licence
- Access controlled
- Audit trail maintained

Information Release:
- To other agencies (controlled)
- To victims (rights under Victims' Rights Act)
- To media (limited, strategic)
- To defense (disclosure obligations)
- To public (OIA requests)

Official Information Act Requests:
- 20 working day response time
- Can refuse on specified grounds
- Must transfer if not held
- Ombudsman oversight
- Charges may apply

Unauthorised Access:
- Offence to access without authority
- Includes accessing own records
- Includes accessing records of family/friends
- Disciplinary consequences
- Criminal consequences

Data Breaches:
- Must report serious breaches
- Privacy Commissioner notification
- Affected individuals notification
- Remediation required

Related Legislation:
- Privacy Act 2020
- Official Information Act 1982
- Victims' Rights Act 2002
- Search and Surveillance Act 2012
""",
        "key_procedures": [
            "Collect only necessary information",
            "Store securely",
            "Use only for proper purpose",
            "Disclose only when authorized",
            "Maintain audit trail"
        ],
        "priority": 3
    },
    
    # J - Justice (Court procedures)
    "court_procedures": {
        "title": "Police Manual - Court Procedures",
        "chapter": "J",
        "section": "Court Processes and Warrants",
        "category": "Court Procedures",
        "content": """
POLICE MANUAL - COURT PROCEDURES

Criminal Procedure Act 2011

Charging:
- Charging document requirements
- Time limits for filing
- Alternative charges
- Electing jurisdiction
- Summons vs arrest

Court Appearances:
- First appearance
- Case review (category 3 offences)
- Pre-trial conferences
- Trial
- Sentencing

Giving Evidence:
- Witness preparation
- Courtroom etiquette
- Oath/affirmation
- Examination in chief
- Cross-examination
- Re-examination
- Refreshing memory
- Using notes

Search Warrants (Court issued):
- Application requirements
- Supporting affidavit
- Particularity requirements
- Execution requirements
- Return requirements

Production Orders:
- Court orders to produce documents
- Application requirements
- Compliance
- Contempt for non-compliance

Examination Orders:
- Order to attend and answer questions
- Given to suspects
- Before charging
- Voluntary but adverse inference possible
- Legal representation allowed

Witness Protection:
- Anonymity orders
- Screened witnesses
- Remote evidence
- Suppression orders
- Threats to witnesses

Related Legislation:
- Criminal Procedure Act 2011
- Evidence Act 2006
- Search and Surveillance Act 2012
- District Court Act 2016
""",
        "key_procedures": [
            "Prepare file thoroughly",
            "Comply with disclosure obligations",
            "Prepare evidence and exhibits",
            "Attend court punctually",
            "Give evidence professionally"
        ],
        "priority": 3
    },
    
    # R - Road Policing (very important)
    "road_policing": {
        "title": "Police Manual - Road Policing",
        "chapter": "R",
        "section": "Traffic Stops, Checkpoints, and Vehicle Searches",
        "category": "Road Policing",
        "content": """
POLICE MANUAL - ROAD POLICING

Land Transport Act 1998
Search and Surveillance Act 2012

Traffic Stop Powers:
- Require driver to stop
- Demand name and address
- Demand date of birth
- Require production of licence
- Impound vehicle (specific circumstances)
- Arrest for certain offences

Checkpoint Powers:
- Must be operationally justified
- Must be conducted safely
- Can check:
  * Driver licence
  * Warrants of fitness
  * Registration
  * Alcohol (compulsory breath tests)
  * Seatbelts
  * Cellphone use

Reasonable Grounds for Vehicle Search:
- Visible evidence of offending
- Smell of drugs
- Officer safety
- Reasonable suspicion of evidence
- Warrant
- Consent

Vehicle Search Without Warrant (s 10 SSA):
- Reasonable grounds to suspect vehicle contains evidence
- Grounds must exist BEFORE search
- Cannot manufacture grounds during search
- Must record grounds
- Safety considerations

Drink Driving:
- Compulsory breath testing at checkpoints
- Random stopping power limited
- Blood tests for evidential purposes
- Rights and procedures
- Medical certificates

Impounding:
- 28 days for specific offences
- Burnouts, street racing
- Unlicensed driving (third offence)
- Excessive speed (50km+ over limit)
- Suspended driver

Drug Driving:
- Compulsory impairment tests
- Blood tests
- Zero tolerance for certain drugs
- Medical assessment

Driver Fatigue:
- Heavy commercial vehicle regulations
- Work time/rest time
- Log books
- Offence to drive fatigued

Related Legislation:
- Land Transport Act 1998
- Land Transport (Road User) Rule 2004
- Search and Surveillance Act 2012
""",
        "key_procedures": [
            "State reason for stop",
            "Request licence and particulars",
            "Assess for impairment",
            "Conduct searches only with lawful authority",
            "Document grounds for any search"
        ],
        "priority": 1
    },
    
    # Drink Driving specifically
    "drink_driving": {
        "title": "Police Manual - Drink and Drug Driving",
    "chapter": "R",
    "section": "Alcohol and Drug Impairment",
    "category": "Road Policing",
        "content": """
POLICE MANUAL - DRINK AND DRUG DRIVING

Land Transport Act 1998

Breath Testing:
- Compulsory breath tests at checkpoints (no grounds needed)
- Random stops not permitted (except checkpoints)
- Must form suspicion for individual stop
- Failure to submit offence
- False sample offence

Evidential Breath Tests:
- Must be conducted on approved device
- 15-minute observation period required
- Rights must be explained
- Result must be recorded
- Copy provided to driver

Blood Tests:
- Taken if breath test indicates over limit
- Can be taken if driver unable to give breath (injury)
- Taken by medical practitioner
- Driver can request independent test
- Sample divided into two portions

Drink Driving Limits:
- Under 20: Zero alcohol
- 20+: 250mcg breath / 50mg blood
- Excess breath alcohol (Excess): 400mcg breath / 80mg blood

Drug Driving:
- Compulsory impairment test (CIT)
- Blood test for drugs
- Zero tolerance for specified drugs
- Cannabis, methamphetamine, cocaine, etc.
- Medical practitioner assessment

Rights During Testing:
- Right to consult lawyer (after procedure)
- Right to independent blood test
- Right to copy of results
- Right to know procedure

Defences:
- Not driving/in charge
- Not on road
- Alcoholic drink consumed after driving
- Proper testing not conducted

Penalties:
- Licence disqualification mandatory
- Fines
- Imprisonment (repeat/serious)
- Alcohol interlock (repeat)
- Zero alcohol licence

Related Legislation:
- Land Transport Act 1998
- Land Transport (Drugs and Alcohol) Legislation
""",
        "key_procedures": [
            "Ensure approved device used",
            "Conduct 15-minute observation period",
            "Explain rights to driver",
            "Provide copy of results",
            "Arrange transport if driver unfit"
        ],
        "priority": 2
    },
    
    # T - Tactical
    "tactical": {
        "title": "Police Manual - Tactical Options",
        "chapter": "T",
        "section": "Firearms and Critical Incidents",
        "category": "Tactical Operations",
        "content": """
POLICE MANUAL - TACTICAL OPTIONS

Arms Act 1983

Firearms:
- Commissioner's approval required for carriage
- Must justify threat to life
- Higher threshold than other force options
- Imminent threat of death or grievous bodily harm
- Command approval usually required
- Post-incident support mandatory
- Critical incident investigation

Tactical Options Continuum:
1. Presence
2. Communication
3. Positioning
4. Empty hand tactics
5. Baton
6. OC spray (pepper spray)
7. Taser
8. Police dog
9. Firearm

Taser:
- Less lethal option
- Neuromuscular incapacitation
- Medical assessment required after use
- Not for passive resistance
- Warning required if practicable
- Probe removal by medical staff
- Restricted use on vulnerable persons

OC Spray:
- Irritant spray
- Warning required if practicable
- After-care required
- Water for irrigation
- Monitor for adverse reactions
- Not for passive resisters

Police Dog:
- Bite dogs and drug detection dogs
- Handler control essential
- Warning before dog deployed
- Medical attention after bite
- Not for minor offences

Baton:
- Defensive and compliance tool
- Strikes to approved target areas
- Not to head unless lethal threat
- Documentation required

Critical Incidents:
- Hostage situations
- Armed offenders
- Sieges
- Terrorist incidents
- Special Tactics Group (STG) may be called

Command and Control:
- Incident controller
- Tactical commander
- Negotiator
- Loggist
- Safety officer

Related Legislation:
- Arms Act 1983
- Crimes Act 1961
- Human Rights Act 1993
""",
        "key_procedures": [
            "Assess threat level",
            "Use lowest option necessary",
            "Give warning if practicable",
            "Provide medical attention",
            "Report all uses of tactical options",
            "Debrief after critical incidents"
        ],
        "priority": 2
    },
    
    # U - Undercover Operations (already added as covert_operations)
    
    # Surveillance specifically
    "surveillance": {
        "title": "Police Manual - Surveillance",
        "chapter": "S",
    "section": "Physical and Electronic Surveillance",
    "category": "Surveillance and Covert Operations",
        "content": """
POLICE MANUAL - SURVEILLANCE

Search and Surveillance Act 2012

Types of Surveillance:
1. Physical surveillance (visual observation)
2. Electronic surveillance (devices)
3. Covert filming/recording
4. Tracking devices
5. Visual surveillance devices

Visual Surveillance:
- Can conduct without warrant in public
- Private property requires warrant or consent
- Cannot use visual surveillance device without warrant
- Cannot surveil lawyer-client communications

Tracking Devices:
- Warrant required to install
- Must specify vehicle/person
- Time limits apply
- Must report to issuing officer

Surveillance Device Warrants (s 48):
- Video cameras
- Listening devices
- Tracking devices
- Must specify place/person
- Must specify device type
- Execution time limits

Private Property:
- Cannot enter private property for surveillance without:
  * Warrant
  * Consent
  * Other lawful authority
- Trespass notice applies

Prohibited Surveillance:
- Lawyer-client communications
- Judicial deliberations
- Parliamentary proceedings
- Medical consultations (without specific warrant)

Retention:
- Surveillance material must be retained as evidence
- Must be disclosed to defense
- Destruction policies for non-evidentiary material
- Privacy considerations

Related Legislation:
- Search and Surveillance Act 2012, ss 48-60
- Privacy Act 2020
- Evidence Act 2006
""",
        "key_procedures": [
            "Obtain warrant for device installation",
            "Specify device and target clearly",
            "Respect privileged communications",
            "Maintain secure storage",
            "Disclose to defense"
        ],
        "priority": 2
    },
    
    # V - Victims
    "victims": {
        "title": "Police Manual - Victims",
        "chapter": "V",
        "section": "Victim Support and Rights",
        "category": "Victim Support",
        "content": """
POLICE MANUAL - VICTIMS

Victims' Rights Act 2002

Victim Rights Include:
1. Treated with courtesy, compassion, respect
2. Informed of services available
3. Informed of progress of investigation
4. Informed of prosecution and bail decisions
5. Give views on matters affecting them
6. Information about offender's release
7. Protection from offender
8. Information in timely manner

Information to Provide:
- Case details and contact numbers
- What to expect from investigation
- Likely timeframes
- Support services (Victim Support, Rape Crisis, etc.)
- Court process
- Restorative justice options
- Safety planning

Family Violence Victims:
- Safety planning essential
- Referral to services
- Protection order information
- Property orders
- Photograph injuries
- Document history

Sexual Violence Victims:
- Specialist response
- Medical examination (PERK kit)
- Video interview option
- Support person present
- Explain court process
- Victim Support referral
- Counselling

Child Victims:
- Child protection procedures
- Oranga Tamariki involvement
- Forensic interview
- Parental support
- Minimize trauma

Deaths - Family:
- Notification by appropriate officer
- Cultural considerations
- Support for identification process
- Property return
- Information about investigation
- Coronial process explained

Related Legislation:
- Victims' Rights Act 2002
- Oranga Tamariki Act 1989
- Evidence Act 2006
""",
        "key_procedures": [
            "Treat with courtesy and compassion",
            "Provide information about rights",
            "Refer to appropriate services",
            "Keep informed of progress",
            "Safety planning where needed"
        ],
        "priority": 3
    },
    
    # W - Witnesses
    "witnesses": {
        "title": "Police Manual - Witnesses",
        "chapter": "W",
        "section": "Witness Management",
        "category": "Witness Management",
        "content": """
POLICE MANUAL - WITNESSES

Evidence Act 2006

Witness Categories:
1. Eye witnesses
2. Expert witnesses
3. Character witnesses
4. Res gestae witnesses
5. Anonymous witnesses (in limited circumstances)

Taking Statements:
- Witness voluntary (usually)
- Caution not required (not suspect)
- Record contemporaneously
- Witness signs each page
- Interpreter if required
- Show photos/boards if applicable

Statement Content:
- Witness details
- What they saw/heard
- When and where
- Who else present
- Any prior knowledge
- Refreshing memory permitted
- Previous statements

Refreshing Memory:
- Witness can refresh from contemporaneous notes
- Notes must be made when memory fresh
- Opposing counsel can see notes
- Cannot use to create memory

Competence and Compellability:
- All persons competent (s 83 Evidence Act)
- All persons compellable (can be forced to give evidence)
- Exceptions: spouse in some cases, sovereign

Special Measures:
- Video links
- Screens
- Suppression of identity
- Interpreters
- Communication assistance

Intimidation:
- Witness intimidation serious offence
- Protection measures available
- Anonymity orders (rare)
- Security arrangements

Expert Witnesses:
- Must be qualified
- Must assist court
- Must be independent
- Expert code of conduct
- Frye/Daubert not applicable in NZ

Related Legislation:
- Evidence Act 2006
- Criminal Procedure Act 2011
- Victims' Rights Act 2002
""",
        "key_procedures": [
            "Take statement voluntarily",
            "Record contemporaneously",
            "Witness signs statement",
            "Provide updates on case",
            "Ensure attendance at court"
        ],
        "priority": 3
    },
    
    # Y - Youth Justice
    "youth_justice": {
        "title": "Police Manual - Youth Justice",
        "chapter": "Y",
        "section": "Youth Offending and Youth Court",
        "category": "Youth Justice",
        "content": """
POLICE MANUAL - YOUTH JUSTICE

Oranga Tamariki Act 1989
Children, Young Persons, and Their Families Act 1989

Youth Court Jurisdiction:
- Young persons (14-16 years)
- Some 17-year-olds (not serious offences)
- Serious offences may go to District/High Court
- Murder and manslaughter always in adult court

Youth Aid:
- Youth Aid officers handle most youth offending
- Diversion options
- Alternative actions
- Family group conferences
- Court as last resort

Alternative Action:
- For low-level offending
- Apology to victim
- Community work
- Counselling
- Education programs
- No criminal record

Family Group Conference (FGC):
- Core of youth justice system
- Youth, family, victim participate
- Plan developed for addressing offending
- Court ratifies plan
- Monitored by social worker

Police Powers:
- Arrest if necessary
- Consider Youth Aid referral
- Notify Oranga Tamariki
- Parent/guardian involvement required
- Separate from adults

Rights of Youth:
- Right to lawyer
- Right to have adult present
- Explanation in age-appropriate language
- Right to privacy
- Protection of identity (name suppression automatic)

Victim Involvement:
- Victim can attend FGC
- Victim views considered
- Restorative justice elements
- Reparation can be ordered

Serious Youth Offending:
- Repeat serious offenders
- Intensive supervision
- Residence orders
- Youth Court can transfer to adult court
- Ramsus orders (serious violent offenders)

Related Legislation:
- Oranga Tamariki Act 1989
- Children, Young Persons, and Their Families Act 1989
- Criminal Procedure Act 2011
""",
        "key_procedures": [
            "Notify Oranga Tamariki",
            "Involve parent/guardian",
            "Consider Youth Aid options",
            "Refer to Family Group Conference",
            "Separate from adult offenders"
        ],
        "priority": 2
    },
    
    # Proceeds of Crime
    "proceeds_of_crime": {
        "title": "Police Manual - Proceeds of Crime",
        "chapter": "P",
        "section": "Criminal Proceeds Recovery",
        "category": "Proceeds of Crime",
        "content": """
POLICE MANUAL - PROCEEDS OF CRIME

Criminal Proceeds (Recovery) Act 2009

Purpose:
- Remove profit from crime
- Deter criminal activity
- Civil standard of proof (balance of probabilities)
- Separate from criminal proceedings

Types of Orders:

1. Restraining Orders:
- Prevent disposal of property/assets
- Applied for ex parte (without notice)
- Initial duration 28 days
- Can be extended
- Affects property suspected of being proceeds of crime

2. Profit Forfeiture Orders:
- Court order forfeiting profits from crime
- Civil proceedings
- Commissioner's notice required
- Can be settled

3. Instrument Forfeiture Orders:
- Forfeit property used in crime
- Vehicle, equipment, etc.
- Applied for by Police
- Court hearing

4. Cash Forfeiture:
- Cash over $10,000 suspected of being crime proceeds
- Seized at border or during investigation
- Burden shifts to owner to prove legitimate origin
- Criminal Proceeds Team handles

Significant Criminal Activity Definition:
- 2+ persons acting jointly
- Substantial planning and organisation
- Maximum sentence of 4+ years
- Ongoing criminal activity

Investigation:
- Financial investigation specialist
- Asset tracing
- Bank records (Production Orders)
- Real property searches
- Company searches
- International cooperation

Victims:
- Restitution to victims considered
- Can apply for return of property
- Competing claims resolved by court

Related Legislation:
- Criminal Proceeds (Recovery) Act 2009
- Search and Surveillance Act 2012
- Mutual Assistance in Criminal Matters Act 1992
""",
        "key_procedures": [
            "Identify significant criminal activity",
            "Trace assets and property",
            "Apply for restraining order",
            "Serve Commissioner's notice",
            "Apply for forfeiture orders"
        ],
        "priority": 2
    },
    
    # Electronic Evidence
    "electronic_evidence": {
        "title": "Police Manual - Electronic Evidence",
        "chapter": "E",
    "section": "Digital Forensics and Device Seizure",
    "category": "Evidence Collection",
        "content": """
POLICE MANUAL - ELECTRONIC EVIDENCE

Search and Surveillance Act 2012
Evidence Act 2006

Types of Electronic Evidence:
- Mobile phones/smartphones
- Computers/laptops
- Tablets
- External storage (USB, HDD)
- CCTV/DVR systems
- Social media
- Cloud storage
- Email
- GPS data
- Internet records

Seizure:
- Warrant usually required for search
- Can seize devices under general warrant
- Must be lawful authority
- Document what seized
- Chain of custody critical

Phone Examinations:
- Faraday bags to prevent remote wiping
- PIN/password requirements
- Specialist Digital Forensic Unit
- Extraction tools (Cellebrite, XRY)
- Logical vs physical extraction
- Cloud data preservation

Computer Examinations:
- Write blockers used
- Forensic imaging
- Keyword searches
- Deleted file recovery
- Internet history
- Email analysis
- Encrypted drives

Social Media:
- Preservation requests to platforms
- Search warrants to providers
- Privacy settings don't prevent lawful access
- Metadata important
- Screenshots may be evidence

Cloud Storage:
- International jurisdictional issues
- Preservation orders
- Mutual legal assistance treaties (MLAT)
- Provider policies vary
- Real-time access rare

Production Orders:
- Can compel production of documents
- Includes electronic documents
- Third parties (banks, telcos)
- Must be specific

Surveillance Device Warrants:
- For installing listening devices
- Tracking devices on vehicles
- Video surveillance
- Strict time limits

Legal Challenges:
- Encryption and passwords
- Legal privilege (lawyer communications)
- Privacy considerations
- Journalistic privilege
- Medical privilege

Related Legislation:
- Search and Surveillance Act 2012
- Evidence Act 2006
- Privacy Act 2020
- Telecommunications Act 2001
""",
        "key_procedures": [
            "Use Faraday bags for phones",
            "Use write blockers for computers",
            "Maintain chain of custody",
            "Document all extraction steps",
            "Preserve cloud data promptly"
        ],
        "priority": 2
    },
}

def create_complete_police_manual():
    """Create all Police Manual chapters"""
    output_dir = Path("./data/police_manual_complete")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    created = 0
    skipped = 0
    
    for chapter_id, chapter_data in POLICE_MANUAL_COMPLETE.items():
        filepath = output_dir / f"{chapter_id}.json"
        
        # Skip if already exists in police_manual_manual
        if Path(f"./data/police_manual_manual/{chapter_id}.json").exists():
            skipped += 1
            continue
        
        # Skip if no content (placeholder)
        if "content" not in chapter_data:
            continue
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                **chapter_data,
                "created": datetime.now().isoformat(),
                "source": "Police Manual (NZ Police) - Compiled"
            }, f, indent=2, ensure_ascii=False)
        
        created += 1
        print(f"✓ Created: {filepath.name}")
    
    print(f"\n{'='*60}")
    print(f"✓ Created: {created} new chapters")
    print(f"⚠ Skipped: {skipped} (already exist)")
    print(f"{'='*60}")
    return created

def print_full_summary():
    """Print complete summary"""
    print("\n" + "="*60)
    print("COMPLETE POLICE MANUAL STRUCTURE")
    print("="*60)
    
    categories = {}
    for chapter_id, data in POLICE_MANUAL_COMPLETE.items():
        cat = data.get("category", "Uncategorized")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(data.get("title", chapter_id))
    
    for cat, titles in sorted(categories.items()):
        print(f"\n{cat}:")
        for title in titles:
            print(f"  • {title}")
    
    total = len(POLICE_MANUAL_COMPLETE)
    print(f"\n{'='*60}")
    print(f"Total chapters: {total}")
    print("="*60)

if __name__ == "__main__":
    created = create_complete_police_manual()
    print_full_summary()
    
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print(f"Run the ingestion script to add these {created} chapters")
    print("to your ChromaDB database.")
    print("="*60)
