# Criminal Disclosure Ingestion & Analysis Workflow

## Table of Contents
- [Document Ingestion](#document-ingestion)
- [Multi-Perspective Analysis Protocol](#multi-perspective-analysis-protocol)
- [Evidence Chain Mapping](#evidence-chain-mapping)
- [Cross-Reference Procedure](#cross-reference-procedure)

---

## Document Ingestion

### Step 1: Document Classification
Classify each document in the disclosure bundle:

| Category | Document Types | Priority |
|----------|---------------|----------|
| **Charging** | Charging document, information, court notices | Critical |
| **Facts** | Summary of facts, police narrative, timeline | Critical |
| **Evidence** | Witness statements, affidavits, CCTV footage, photos, audio/video recordings, physical exhibit list | Critical |
| **Forensic** | Expert reports (DNA, fingerprint, digital, medical, ESR), certificates of analysis | High |
| **Warrants** | Search warrants, surveillance device warrants, production orders, interception warrants | High |
| **Interview** | Recorded interviews, written statements, ERISP transcripts, cautions | High |
| **Procedural** | Bail documents, remand sheets, court minutes, case review notes, transfer documents | Medium |
| **Background** | Criminal history, CPIC/NIA records, previous court orders | Medium |
| **Communication** | 111 transcripts, police radio logs, emails, text messages, social media | Medium |
| **Intelligence** | Police intelligence reports, informant material, risk assessments | Low (s63 likely) |

### Step 2: Metadata Extraction
For each document extract:
- Document date (created, received, executed)
- Author/creator (officer number, agency, expert credentials)
- File reference numbers
- Chain of custody references
- Cross-references to other documents
- Redactions present (noted but not bypassed)

### Step 3: Content Chunking for RAG
- Chunk by logical sections (not arbitrary sizes)
- Preserve context: each chunk must be self-sufficient with surrounding context
- Tag chunks by: document type, date, author, offence relevance
- Maintain original numbering (paragraph numbers, page numbers, exhibit numbers)

### Step 4: Priority Ingestion Order
1. Charging document + summary of facts (establish scope)
2. All warrants and judicial authorisations (procedural compliance)
3. Interview recordings/transcripts (potential s56/s23 issues)
4. Witness statements (evidential sufficiency)
5. Forensic/expert reports (reliability assessment)
6. CCTV/audio/video (corroboration assessment)
7. Procedural documents (timelines, bail compliance)

---

## Multi-Perspective Analysis Protocol

After ingestion, generate analysis from three independent perspectives simultaneously:

### Perspective A: Defence Counsel (Senior, 25+ years NZ criminal practice)
Focus: Protect accused rights, identify Crown weaknesses, procedural defects, admissibility challenges
- Assumes accused is innocent until proven guilty
- Applies highest scrutiny to Crown evidence
- Identifies all available defences and evidential gaps
- Flags any conduct that may breach NZBORA, Evidence Act, or CPA
- Seeks exclusion of improperly obtained evidence
- Advises on tactical advantages and disadvantages

### Perspective B: Crown Prosecutor (Experienced, previously Senior Sergeant)
Focus: Assess strength of Crown case, anticipate prosecution strategy, identify vulnerabilities in Crown presentation
- Assumes Crown obligation to prove each element beyond reasonable doubt
- Evaluates witness credibility and reliability
- Assesses evidential chain completeness
- Identifies where Crown case is strong and where it is thin
- Notes tactical decisions prosecutor likely to make
- Flags any disclosure deficiencies from Crown perspective

### Perspective C: Judicial Officer (Retired District Court Judge, NZ)
Focus: Trial fairness, admissibility rulings likely outcomes, procedural compliance, sentencing considerations
- Applies judicial neutrality and case management perspective
- Assesses likelihood of evidence being admitted
- Evaluates whether evidential threshold met (prima facie case)
- Considers trial management issues (length, complexity, severance)
- Assesses likely bail position and sentencing range if convicted
- Identifies procedural irregularities that may require remedy

### Integration Protocol
After generating three independent perspectives:
1. Identify points of **agreement** — these are the strongest findings
2. Identify points of **disagreement** — flag for practitioner attention
3. Where perspectives diverge, note the **conditions** under which each view would prevail
4. Present integrated findings with confidence levels:
   - **High confidence**: All three perspectives agree
   - **Medium confidence**: Two perspectives agree, one neutral
   - **Requires review**: Perspectives actively disagree

---

## Evidence Chain Mapping

### For each exhibit or piece of evidence:
1. **Origin**: Where did this evidence come from? (seizure location, person, device)
2. **Authority**: What legal authority supported its obtaining? (warrant reference, consent, statutory power)
3. **Chain of custody**: Who handled it? When? Where stored?
4. **Analysis**: What forensic or expert analysis was performed? By whom? With what qualifications?
5. **Conclusions**: What does the Crown claim it proves?
6. **Alternative interpretations**: What other explanations exist?
7. **Gaps**: What is missing from the chain?

### Exhibit Matrix Template

| Exhibit # | Description | Seized From | Seized By | Date | Warrant/Authority | Chain Complete? | Analysis Done | Conclusions Challenged? |
|-----------|-------------|-------------|-----------|------|-------------------|-----------------|---------------|------------------------|
| | | | | | | | | |

---

## Cross-Reference Procedure

### Legislation Cross-Reference
For each charge identified:
1. Identify governing statute and section
2. Retrieve full text of offence provision
3. Deconstruct into elements (actus reus, mens rea, circumstances)
4. Cross-check against Crimes Act general provisions (s20, s24, Part 1)
5. Identify applicable maximum penalties
6. Retrieve related statutory defences

### Case Law Cross-Reference
For each charge and issue:
1. Search NZLII for leading authority on the offence
2. Retrieve interpretation cases for ambiguous statutory terms
3. Search for cases with similar fact patterns
4. Retrieve sentencing guideline cases
5. Note any appellate authority that has modified the offence scope

### Procedural Cross-Reference
For every procedural step:
1. Map against CPA 2011 requirements
2. Check timing compliance (service, filing, disclosure deadlines)
3. Verify authorisation validity (warrant issuing officers, delegation)
4. Check NZBORA compliance at each stage
5. Verify Evidence Act admissibility requirements
