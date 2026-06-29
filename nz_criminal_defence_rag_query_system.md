# NZ Criminal Defence RAG: Query Expansion, Reformulation & Metadata Filtering System

## Technical Document — Production-Grade Legal Retrieval Engineering

**Version:** 1.0  
**Jurisdiction:** New Zealand  
**Domain:** Criminal Defence  
**Knowledge Bases:** NZ Legislation | NZ Case Law | NZ Police Manual  
**Pipeline Stage:** Retrieval Optimisation (Post-Query Generation, Pre-Vector Search)

---

## Table of Contents

1. [Part 1: Query Expansion Prompt](#part-1-query-expansion-prompt)
   - A. Synonym Expansion
   - B. Hyponym/Hypernym Expansion
   - C. Legal Citation Expansion
   - D. Defence-Based Expansion
   - E. Procedural Rights Expansion
2. [Part 2: Query Reformulation Prompts](#part-2-query-reformulation-prompts)
   - A. Dense Vector Queries (Semantic)
   - B. Sparse Keyword Queries (BM25)
   - C. Hybrid Queries
   - D. Sub-query Decomposition
3. [Part 3: Metadata Filter Generation Prompt](#part-3-metadata-filter-generation-prompt)
   - Legislation KB Filters
   - Case Law KB Filters
   - Police Manual KB Filters
4. [Part 4: Query Prioritisation and Ranking](#part-4-query-prioritisation-and-ranking)
5. [Part 5: Complete Pipeline Architecture](#part-5-complete-pipeline-architecture)
6. [Appendices](#appendices)

---

## Part 1: Query Expansion Prompt

### Overview

The Query Expansion module takes initial queries generated from the disclosure parsing stage and enriches them using five expansion strategies. Each strategy is applied via a structured prompt to an LLM with legal-domain knowledge. The output is a set of expanded query terms organised by strategy, ready for reformulation.

**System Prompt — Query Expansion Engine**

```
You are the Query Expansion Engine for a New Zealand criminal defence legal RAG system.
Your role is to expand initial search queries using multiple linguistic and legal strategies
to maximise retrieval coverage across NZ legislation, case law, and police procedure.

EXPANSION PRINCIPLES:
1. NZ-SPECIFIC: All expansions must use New Zealand legal terminology, statute names, and citations.
2. DEFENCE-ORIENTED: Prioritise terms that help identify defence arguments, procedural errors, and rights violations.
3. CITATION-AWARE: Include proper NZ legal citations (Act name, section number, year where relevant).
4. COMPREHENSIVE: Cover synonyms, hierarchical relationships, related offences, defences, and procedural rights.
5. STRUCTURED: Output must follow the exact JSON schema specified.

STATUTE REFERENCE QUICK GUIDE:
- Crimes Act 1961: Main criminal offences (ss1-411)
- Summary Offences Act 1981: Minor offences
- New Zealand Bill of Rights Act 1990 (NZBORA): Fundamental rights (ss2-29)
- Search and Surveillance Act 2012 (SSAct): Search powers, warrants, surveillance
- Evidence Act 2006: Evidence rules, admissibility, exclusion (ss1-203)
- Bail Act 2000: Bail applications, conditions, variations
- Criminal Procedure Act 2011: Court procedure, case management, sentencing
- Sentencing Act 2002: Sentencing principles, purposes
- Misuse of Drugs Act 1975: Drug offences, classifications
- Land Transport Act 1998: Driving offences
- Arms Act 1983: Firearms offences
- Proceeds of Crime Act 1991: Asset forfeiture

DEFENCE CATEGORIES:
- General: Insanity (s23 Crimes Act), automatism, intoxication (s25 Crimes Act), claim of right, mistake of fact
- Assault/Violence: Self-defence (s48 Crimes Act), defence of property (s55 Crimes Act), provocation (historical), consent
- Drugs: Lack of knowledge, personal use, medical cannabis (Medicinal Cannabis Scheme), lawful authority
- Dishonesty: Claim of right (s2(1)(a) Crimes Act), consent, mistake, no intent to deprive
- Driving: Necessity, emergency, reasonable excuse, automatism
- Sexual: Consent (ss128A-129 Crimes Act), honest belief in consent, mental incapacity
- Procedural: Unlawful search (NZBORA s21), unlawful arrest (NZBORA s22), right to lawyer (NZBORA s23),
  right to silence, exclusion of evidence (Evidence Act s30), unreasonable delay

OUTPUT FORMAT: Strict JSON only. No explanatory text outside the JSON structure.
```

---

### A. Synonym Expansion Strategy

**Prompt Template — Synonym Expansion**

```
TASK: Expand the following query using NZ-specific legal synonyms.

INITIAL QUERY: {{initial_query}}

Expand each legal term using the following synonym categories:

1. SUBSTANTIVE OFFENCE SYNONYMS (NZ-specific):
   - Use alternative names for the same or closely related offences
   - Include both formal (statute) and informal (practitioner) terminology
   - Include Maori terms where commonly used in legal contexts

2. PROCEDURAL TERM SYNONYMS:
   - Alternative procedural descriptions
   - Police terminology vs court terminology vs statutory terminology

3. RIGHTS TERMINOLOGY SYNONYMS:
   - NZBORA section references
   - Common law rights descriptions
   - Police Manual terminology

SYNONYM EXPANSION RULES:
- Use "OR" to separate alternatives (for Boolean search compatibility)
- Include the original term always
- Include at least 3-5 synonyms per significant legal term
- Prioritise terms most commonly used in NZ courts

EXAMPLE:
Input: "aggravated robbery"
Output:
{
  "original_term": "aggravated robbery",
  "expansions": [
    "aggravated robbery OR armed robbery OR robbery with weapon OR robbery with firearm OR robbery with offensive weapon OR s234 Crimes Act 1961 OR violent robbery OR aggravated theft",
    "robbery + weapon OR robbery + arms OR robbery + firearm OR robbery + offensive weapon OR robbery + violence",
    "s234(1)(a) OR s234(1)(b) OR s234(1)(c) OR s234(1)(d)"  // subsections
  ],
  "source_act": "Crimes Act 1961",
  "section": "s234"
}

Now expand the following query:

INITIAL QUERY: {{initial_query}}
CHARGE CONTEXT (if known): {{charge_context}}
PROCEEDINGS STAGE: {{proceedings_stage}}  // e.g., "pre-trial", "trial", "sentencing", "appeal"

OUTPUT FORMAT: Return a JSON array of expansion objects, one per significant legal term in the query.
```

**Example Input/Output:**

| Input | Output |
|-------|--------|
| `"search warrant execution"` | `[{"term": "search warrant", "expansion": "search warrant OR search authority OR executing search warrant OR warrant to search OR search and surveillance warrant OR SSAct s98 OR s110 Search and Surveillance Act", ...}]` |
| `"right to lawyer"` | `[{"term": "right to lawyer", "expansion": "right to consult lawyer OR right to legal advice OR s23 NZBORA OR right to solicitor OR right to counsel OR access to lawyer OR duty lawyer", ...}]` |
| `"methamphetamine supply"` | `[{"term": "methamphetamine", "expansion": "methamphetamine OR meth OR P OR class A drug OR controlled drug OR illicit drug OR Schedule 1 Misuse of Drugs Act", ...}, {"term": "supply", "expansion": "supply OR supply for sale OR distribute OR deal OR trafficking OR conspiracy to supply OR offer to supply", ...}]` |

---

### B. Hyponym/Hypernym Expansion Strategy

**Prompt Template — Hierarchical Expansion**

```
TASK: Expand the following query using hyponym/hypernym relationships in NZ criminal law.
Move UP the offence hierarchy (generalise) AND move DOWN (specify with related/similar offences).

INITIAL QUERY: {{initial_query}}

HIERARCHY EXPANSION RULES:

1. MOVE UP (HYPERNYMS — broader categories):
   - Identify the parent offence category
   - Include the broader statutory part/chapter
   - Include related offence categories that might apply

2. MOVE DOWN (HYPONYMS — more specific):
   - Identify specific sub-types of the offence
   - Include related but distinct offences that share elements
   - Include attempt/complicity variants (s72 attempt, s66 party to offence)

3. SECTION CLUSTERING:
   - Identify the statutory section for the primary offence
   - Include adjacent sections in the same statutory grouping
   - Include related sections that create alternative charges

EXAMPLE — Moving UP:
Input: "common assault" (s196 Crimes Act)
UP expansion: "common assault OR assault OR offences against the person OR violent offence OR crimes against person OR Part 8 Crimes Act 1961"

EXAMPLE — Moving DOWN:
Input: "theft" (s219 Crimes Act)
DOWN expansion: "theft OR stealing OR theft by person in special relationship (s220) OR theft of valuable security (s222) OR theft by servant (s222) OR dishonest taking (s217) OR conversion OR burglary (s231) OR robbery (s234)"

EXAMPLE — SECTION CLUSTERING:
Input: "s234 aggravated robbery"
CLUSTER expansion: "s234 aggravated robbery OR s235 robbery OR s231 burglary OR s232 entering with intent OR s236 assault with intent to rob OR s229 possession of offensive weapon"

Now process:

INITIAL QUERY: {{initial_query}}
PRIMARY OFFENCE (if identified): {{primary_offence}}
KNOWLEDGE BASE TARGET: {{kb_target}}  // "legislation", "case_law", "police_manual", or "all"

OUTPUT FORMAT: JSON with "up_expansions", "down_expansions", and "section_cluster" arrays.
```

**NZ Offence Hierarchy Reference (for prompt grounding):**

| Category | Hypernym | Common Hyponyms | Key Sections |
|----------|----------|-----------------|--------------|
| Assault | Offences against the person | Common assault (s196), Assault with weapon (s199), Wounding (s198), Aggravated assault (s192) | Part 8 Crimes Act |
| Robbery | Dishonesty + Violence | Robbery (s235), Aggravated robbery (s234), Assault with intent to rob (s236) | ss234-236 |
| Burglary | Dishonesty + Property | Burglary (s231), Entering with intent (s232), Being on property (s229) | ss229-232 |
| Theft | Dishonesty | Theft (s219), Theft special relationship (s220), Theft by servant (s222), Dishonest taking (s217), Receiving (s246) | ss217-246 |
| Fraud | Dishonesty | Obtaining by deception (s240), Using document for pecuniary advantage (s228), Tax fraud, Benefit fraud | ss228,240 |
| Drugs | Regulatory offence | Possession (s6 Misuse of Drugs Act), Supply (s6(1)(c)), Manufacture, Importation, Conspiracy | Misuse of Drugs Act 1975 |
| Driving | Regulatory offence | Dangerous driving, Careless driving (s22), Drink driving (s56), Drug driving, Failing to stop, Disqualified driving | Land Transport Act 1998 |
| Sexual | Offences against the person | Sexual violation (s128), Unlawful sexual connection, Indecent assault (s135), Sexual conduct with child | ss128-144 |

---

### C. Legal Citation Expansion Strategy

**Prompt Template — Citation Expansion**

```
TASK: When a legal citation (case or statute) is detected in the query, expand it to
maximise retrieval of relevant authority.

INITIAL QUERY: {{initial_query}}

CITATION EXPANSION RULES:

1. CASE CITATION EXPANSION:
   Given a case name or citation, expand to include:
   a) Full case name and common abbreviations
   b) All NZLR/official citation formats (year, volume, page)
   c) Key ratio/ratio decidendi (the governing legal principle)
   d) Leading judgment author (if significant, e.g., Elias CJ, William Young J)
   e) Cases that follow/apply/criticise this authority (if known)
   f) Related cases cited in the judgment

2. STATUTE SECTION EXPANSION:
   Given a section reference, expand to include:
   a) Section number and section name (short title)
   b) The broader Part/Division containing the section
   c) Related sections that create companion offences or procedures
   d) Cross-referenced sections in other Acts
   e) Amendment history if relevant to defence (e.g., provocation repealed by Crimes (Provocation Repeal) Amendment Act 2009)

3. CROSS-REFERENCE MAPPING:
   Map related provisions across Acts:
   - NZBORA rights → related Evidence Act provisions → related Police Manual chapters
   - Offence sections → related defence sections → related sentencing provisions

NZ CASE CITATION FORMATS:
- [Year] NZLR page (New Zealand Law Reports)
- [Year] NZCA number (Court of Appeal)
- [Year] NZHC number (High Court)
- [Year] NZDC number (District Court)
- [Year] NZSC number (Supreme Court)
- CRNZ (Criminal Reports of New Zealand)
- Unreported: [Date] [Court] [Registry number]

EXAMPLE — Case Expansion:
Input: "R v Wang"
Output:
{
  "case_expansions": [
    {
      "case_name": "R v Wang",
      "citations": ["[1989] 2 NZLR 213 (CA)", "[1989] NZCA 112"],
      "full_name": "R v Wang",
      "key_ratio": "Aggravated robbery - requirement that offender have weapon at time of robbery",
      "related_cases": ["R v Nathan [2011] NZCA 607", "R v Terewi [1993] 2 NZLR 571"],
      "legal_principle": "elements of aggravated robbery, weapon requirement, constructive presence",
      "court": "Court of Appeal"
    }
  ]
}

EXAMPLE — Statute Cross-Reference:
Input: "s24 NZBORA right to lawyer"
Output:
{
  "statute_expansions": [
    {
      "primary": "s23 NZBORA - Right to consult lawyer",
      "related_sections": [
        "s24 NZBORA - Rights of persons arrested or detained",
        "s25 NZBORA - Rights of persons charged",
        "Evidence Act 2006 s28 - defendant's statements",
        "Evidence Act 2006 s30 - improperly obtained evidence",
        "Evidence Act 2006 s31 - warnings in criminal proceedings",
        "Search and Surveillance Act 2012 s37 - rights of detained persons"
      ],
      "police_manual_refs": ["Chapter 7: Custody and Interviews", "IIF - Initial Investigation Framework"],
      "case_law_themes": ["R v Ormsby [2013] NZCA 526", "R v Shaheed [2002] 2 NZLR 377", "Police v Smith"]
    }
  ]
}

Now process:

INITIAL QUERY: {{initial_query}}
DETECTED CITATIONS (if any): {{detected_citations}}
CASE NAME DRAFTNET (if any): {{case_name}}

OUTPUT FORMAT: JSON with "case_expansions" and "statute_expansions" arrays.
```

**Key NZ Cross-Reference Mappings (built into system):**

| Primary Provision | Related Legislation | Related Case Law Themes | Police Manual Chapter |
|-------------------|---------------------|------------------------|----------------------|
| NZBORA s21 (Search) | SSAct ss98-110, Evidence Act s30 | Shaheed exclusion, R v Jefferies | Ch 4: Search and Surveillance |
| NZBORA s22 (Arrest) | Crimes Act s315, Bail Act 2000 | R v Pamflett, R v Faletoi | Ch 3: Arrest and Detention |
| NZBORA s23 (Lawyer) | Evidence Act s28, SSAct s37 | R v Ormsby, R v Matenga | Ch 7: Custody and Interviews |
| NZBORA s24 (Arrested persons) | Criminal Procedure Act ss14-16, Bail Act | Police v Smith | Ch 7: Custody and Interviews |
| NZBORA s25 (Charged persons) | Criminal Procedure Act, Evidence Act | R v Barlow | Ch 14: Charging |
| Evidence Act s30 (Improperly obtained) | NZBORA s21-s26, SSAct | R v Shaheed, R v Williams [2007] NZCA 52 | Ch 5: Evidence |
| Crimes Act s48 (Self-defence) | s55 (Defence of property), s59 (discipline) | R v Wang, R v Keogh [1964] NZLR 737 | Ch 10: Assault Offences |
| Crimes Act s234 (Aggravated robbery) | ss235-236, s231 (Burglary) | R v Nathan, R v Wang | Ch 11: Dishonesty and Property |

---

### D. Defence-Based Expansion Strategy

**Prompt Template — Defence Expansion**

```
TASK: For each charge identified in the query, generate comprehensive defence-oriented
query expansions. Identify all available defences under NZ law and create targeted
retrieval queries for each.

CHARGE: {{charge}}
FACTUAL CONTEXT: {{factual_context}}
EVIDENCE AVAILABLE: {{evidence_summary}}  // brief summary of defence evidence
PROCEEDINGS STAGE: {{proceedings_stage}}

DEFENCE EXPANSION FRAMEWORK:

For each charge, expand queries to cover ALL of the following defence categories:

1. SUBSTANTIVE DEFENCES (complete defence → acquittal):
   a) Self-defence / defence of others
   b) Defence of property
   c) Consent (where legally available)
   d) Claim of right
   e) Alibi / mistaken identity
   f) Insanity / mental impairment
   g) Automatism
   h) Intoxication (limited availability)
   i) Duress
   j) Necessity
   k) Coercion (s60 Crimes Act - married women)

2. PROCEDURAL DEFENCES (may result in exclusion or stay):
   a) Unlawful search → exclusion of evidence (Evidence Act s30)
   b) Unlawful arrest → jurisdiction issues, Bail Act remedies
   c) Denial of right to lawyer → exclusion of statements (Evidence Act s28, s30)
   d) Breach of NZBORA rights → s30 exclusion, s31 warnings
   e) Unreasonable delay → stay of proceedings
   f) Abuse of process
   g) Non-disclosure → Crown disclosure obligations (Criminal Procedure Act ss122-124)

3. ELEMENT-ATTACKING DEFENCES (negate an element):
   a) Lack of intent (mens rea failure)
   b) Mistake of fact
   c) Lack of knowledge (especially drug cases)
   d) No causation
   e) Consent negating absence of consent element

4. MITIGATION/ALTERNATIVE CHARGE DEFENCES:
   a) Reduced charge negotiation
   b) Diversion eligibility
   c) Mental health pathways (s45 Mental Health Act)
   d) Restorative justice

CHARGE-DEFENCE MAPPING — NZ LAW:

ASSAULT / VIOLENT OFFENCES:
- Self-defence: s48 Crimes Act 1961
- Defence of property: s55 Crimes Act 1961
- Defence of another: s48 Crimes Act 1961
- Consent: s196(2) - implied consent to ordinary contact, s2 common law
- Provocation: REPEALED 2009 (historical cases only)
- Accident: absence of intent (mens rea)
- Intoxication: s25 Crimes Act (limited to specific intent)
- Insanity: s23 Crimes Act
- Automatism: common law (sleeplessness, concussion)

DRUG OFFENCES (Misuse of Drugs Act 1975):
- Lack of knowledge (possession - don't know it's there, don't know what it is)
- Personal use vs supply (social supply argument, s6(6) supply definition)
- Lawful authority (Medical Cannabis Scheme, prescriber authorisation)
- Temporal possession (momentary handling)
- No control (unable to exercise dominion)
- Entrapment (abuse of process argument)

DISHONESTY OFFENCES:
- Claim of right: s2(1)(a) Crimes Act 1961 (honest belief in legal right to property)
- Consent of owner
- Mistake of fact (honest belief facts were such that no dishonesty)
- No intention to deprive (temporary borrowing)
- No dishonesty (s217(3) - claim of right defence to theft)

DRIVING OFFENCES (Land Transport Act 1998):
- Necessity / emergency
- Reasonable excuse (failing to stop, disqualified driving)
- Automatism (medical episode, sneezing fit)
- Duress (forced to drive under threat)
- Factual dispute (was driver? was vehicle? was road?)
- Evidential threshold (careless vs dangerous standard)
- Breath/blood test procedural challenges

SEXUAL OFFENCES:
- Consent: ss128A-128C Crimes Act (steps to ascertain, reasonable belief)
- Honest belief in consent (s128A(4))
- Mistake of age (ss134(5), 135(4))
- Marriage/relationship exception (historical)
- Fabrication/alibi

FIREARMS OFFENCES (Arms Act 1983):
- Lawful purpose (target shooting, hunting, collection)
- Licence holder / permitted activity
- Temporary possession (safekeeping)
- No knowledge of presence
- Invalid search leading to exclusion

OUTPUT FORMAT: JSON array of defence objects, each containing:
{
  "defence_name": "string",
  "defence_type": "substantive|procedural|element-attacking|mitigation",
  "statutory_basis": "section reference",
  "case_law_authority": "leading NZ case",
  "expansion_queries": ["query 1", "query 2", ...],
  "applicability_score": "1-5"  // 5 = highly applicable given context
}
```

**Example Input/Output:**

| Charge | Defence Expansions Generated |
|--------|------------------------------|
| Aggravated robbery (s234) | Self-defence (s48), Claim of right (s2), Intoxication (s25), Identification challenge, Unlawful search exclusion (s30 Evidence Act), Element attack: no weapon present, Element attack: no theft/dishonesty intent |
| Supply of methamphetamine (s6 Misuse of Drugs Act) | Lack of knowledge, Personal use argument, Social supply (s6(6)), Unlawful search, Medical Cannabis Scheme relevance, Element attack: no supply (possession only) |
| Careless driving causing injury (s22 Land Transport Act) | Necessity/emergency, Automatism, Factual dispute (not careless), Reasonable driving standard challenge |

---

### E. Procedural Rights Expansion Strategy

**Prompt Template — Procedural Rights Expansion**

```
TASK: For each procedural stage relevant to the query, generate comprehensive
rights-based query expansions. Each procedural step in a NZ criminal investigation
has parallel statutory frameworks, rights provisions, and compliance requirements.

PROCEDURAL CONTEXT: {{procedural_context}}
ALLEGED RIGHTS BREACHES: {{alleged_breaches}}
EVIDENCE SOUGHT TO EXCLUDE: {{evidence_to_exclude}}

PROCEDURAL RIGHTS FRAMEWORK — PARALLEL QUERIES:

For each procedural step, generate queries across FOUR parallel dimensions:
1. STATUTORY AUTHORITY (the power)
2. RIGHTS PROTECTION (the limitation)
3. POLICE COMPLIANCE (the procedure)
4. REMEDY/CONSEQUENCE (for breach)

=== PROCEDURAL STAGE TEMPLATES ===

STAGE 1: SEARCH
---
Dimension 1 — Statutory Authority:
- "Search and Surveillance Act 2012 search powers"
- "s18 SSAct search without warrant"
- "s98 SSAct search warrant requirements"
- "s110 SSAct surveillance device warrant"
- "s20 SSAct search of person"
- "s21 SSAct vehicle search powers"
- "s48 SSAct examination order"
- "s50 SSAct production order"

Dimension 2 — Rights Protection (NZBORA):
- "s21 NZBORA unreasonable search and seizure"
- "s21 NZBORA search reasonable grounds"
- "s21 NZBORA privacy expectation"
- "s14 NZBORA freedom from arbitrary detention" (if detained during search)

Dimension 3 — Police Compliance:
- "Police Manual Chapter 4 search and surveillance"
- "Police Manual executing search warrants"
- "Police Manual search without warrant procedures"
- "Police Manual s18 search authority requirements"
- "Police Manual s48 examination order execution"
- "Police Manual dealing with exhibits search"

Dimension 4 — Remedy/Consequence:
- "Evidence Act 2006 s30 improperly obtained evidence"
- "Evidence Act 2006 s30 exclusion search breach"
- "R v Shaheed exclusion test"
- "s30 Evidence Act balancing factors"
- "fruit of poisonous tree doctrine NZ"
- "R v Williams [2007] NZCA 52 exclusion threshold"

STAGE 2: ARREST
---
Dimension 1 — Statutory Authority:
- "Crimes Act 1961 s315 arrest without warrant"
- "s315 Crimes Act arrest powers grounds"
- "Summary Offences Act 1981 arrest powers"
- "Bail Act 2000 arrest for breach"
- "Immigration Act 2009 arrest (if relevant)"

Dimension 2 — Rights Protection:
- "s22 NZBORA liberty of person"
- "s22 NZBORA arbitrary arrest detention"
- "s23 NZBORA right to consult lawyer"
- "s24 NZBORA rights arrested persons"
- "s25 NZBORA rights charged persons"

Dimension 3 — Police Compliance:
- "Police Manual Chapter 3 arrest and detention"
- "Police Manual arrest procedures"
- "Police Manual grounds for arrest s315"
- "Police Manual caution rights"
- "Police Manual use of force arrest"
- "Police Manual dealing with minors arrest"
- "IIF initial investigation framework arrest"

Dimension 4 — Remedy/Consequence:
- "unlawful arrest jurisdiction challenge"
- "unlawful arrest evidence exclusion"
- "Bail Act 2000 arrest without warrant"
- "R v Faletoi unlawful arrest"
- "R v Pamflett arrest powers"

STAGE 3: INTERVIEW / QUESTIONING
---
Dimension 1 — Statutory Authority:
- "Evidence Act 2006 s28 defendant's statements admissibility"
- "Evidence Act 2006 s29 statements by suspects in criminal proceedings"
- "Search and Surveillance Act 2012 s37 rights detained persons"
- "Evidence Act 2006 admissibility confessions"

Dimension 2 — Rights Protection:
- "s23 NZBORA right to consult lawyer"
- "s24 NZBORA rights persons arrested detained"
- "s25 NZBORA minimum rights charged persons"
- "s27 NZBORA right to justice"
- "Evidence Act 2006 s30 improperly obtained evidence"

Dimension 3 — Police Compliance:
- "Police Manual Chapter 7 custody and interviews"
- "Police Manual interviewing suspects"
- "Police Manual vulnerable suspect interview"
- "Police Manual youth justice interview"
- "Police Manual taping recording requirements"
- "Police Manual lawyer access interview"
- "Police Manual IIF interview framework"
- "Police Manual caution requirements NZ"
- "Police Manual right to silence advice"

Dimension 4 — Remedy/Consequence:
- "Evidence Act 2006 s28 exclusion involuntary statements"
- "Evidence Act 2006 s30 exclusion improperly obtained confession"
- "R v Ormsby [2013] NZCA 526 lawyer access"
- "R v Matenga [2013] NZCA 38 police questioning"
- "s31 Evidence Act warnings criminal proceedings"
- "R v Barlow NZCA breach rights interview"

STAGE 4: IDENTIFICATION PROCEDURES
---
Dimension 1 — Statutory Authority:
- "Evidence Act 2006 s4 identification evidence defined"
- "Evidence Act 2006 s5 admissibility identification evidence"
- "Evidence Act 2006 s6 reliability of identification evidence"
- "Evidence Act 2006 s7 direction to jury on identification"

Dimension 2 — Rights Protection:
- "s25 NZBORA minimum rights charged persons"
- "s27 NZBORA right to natural justice"
- "right to lawyer during identification"

Dimension 3 — Police Compliance:
- "Police Manual identification procedures"
- "Police Manual formal identification procedure"
- "Police Manual photo montage procedure"
- "Police Manual video identification"
- "Police Manual dock identification"
- "Police Manual witness viewing cautions"

Dimension 4 — Remedy/Consequence:
- "R v Tawhai [1985] 2 NZLR 237 identification evidence unreliable"
- "R v Harmer [2000] 2 NZLR 659 identification warning"
- "s6 Evidence Act identification reliability"
- "s7 Evidence Act jury direction identification"
- "dock identification NZ law admissibility"

STAGE 5: BAIL
---
Dimension 1 — Statutory Authority:
- "Bail Act 2000 s7 presumption bail"
- "Bail Act 2000 s8 bail application procedure"
- "Bail Act 2000 s12 bail conditions"
- "Bail Act 2000 s13 electronic monitoring bail"
- "Bail Act 2000 s28 bail review"
- "Bail Act 2000 s30 bail variation"
- "Bail Act 2000 s38 bail appeals"

Dimension 2 — Rights Protection:
- "s24 NZBORA rights arrested detained persons bail"
- "s25 NZBORA reasonable time to trial bail"
- "s20 NZBORA equality before law bail"

Dimension 3 — Police Compliance:
- "Police Manual bail procedures"
- "Police Manual custody officer bail decisions"
- "Police Manual bail conditions"
- "Police Manual remand court bail"

Dimension 4 — Remedy/Consequence:
- "Bail Act 2000 s28 bail review High Court"
- "Bail Act 2000 s38 bail appeal District Court"
- "unreasonable bail conditions challenge"
- "R v Hall bail principles NZ"

OUTPUT FORMAT: JSON object with a key for each procedural stage ("search", "arrest", "interview", "identification", "bail"). Each stage contains an array of the four dimensions, each with an array of expansion queries.
```

---

## Part 2: Query Reformulation Prompts

### A. Dense Vector Queries (Semantic Reformulation)

**Prompt Template — Semantic Query Reformulation**

```
TASK: Reformulate the following expanded queries as natural language questions
and statements optimised for dense vector (semantic) retrieval.

Dense vector retrieval embeds queries and documents into high-dimensional vectors
and retrieves based on semantic similarity (cosine/dot product). The reformulated
query should read like a natural question or statement that captures the full legal intent.

INPUT QUERIES: {{expanded_queries}}
CHARGE CONTEXT: {{charge_context}}
DEFENCE STRATEGY: {{defence_strategy}}

SEMANTIC REFORMULATION RULES:
1. Use natural, complete sentences — not keyword lists
2. Frame as questions that a lawyer would ask when researching
3. Include the full legal context (statutes, rights, procedures)
4. Use precise legal terminology but in grammatical sentences
5. Vary between: direct questions, indirect questions, declarative statements
6. Length: 15-50 words per query (long enough for semantic richness)

REFORMULATION PATTERNS:
- "What are the elements of [OFFENCE] under New Zealand law?"
- "How does [STATUTE SECTION] apply to [FACTUAL SCENARIO]?"
- "What are the requirements for [PROCEDURE] under [ACT]?"
- "When is [EVIDENCE TYPE] admissible in a NZ criminal trial?"
- "What constitutes [LEGAL STANDARD] in the context of [OFFENCE]?"
- "How is [DEFENCE] established under [STATUTE]?"
- "What remedies are available for [RIGHTS BREACH] under NZ law?"
- "What is the test for [LEGAL PRINCIPLE] in New Zealand?"

NZ-SPECIFIC CONTEXT TO EMBED:
- Reference to "New Zealand" or "NZ" explicitly
- Reference to the specific statute by full name
- Reference to standard of proof (beyond reasonable doubt)
- Reference to relevant NZ cases by name

EXAMPLES:
Input (keyword): "aggravated robbery s234 weapon Crimes Act elements"
Output (semantic): "What are the legal elements of aggravated robbery under section 234 of the Crimes Act 1961 in New Zealand, and what constitutes a weapon for the purposes of this offence?"

Input (keyword): "s24 NZBORA right lawyer police interview custody"
Output (semantic): "What rights does a detained person have to consult a lawyer under section 24 of the New Zealand Bill of Rights Act 1990 during a police interview in custody?"

Input (keyword): "search warrant unlawful exclusion evidence s30"
Output (semantic): "Under what circumstances will evidence obtained from an unlawful search be excluded from a criminal trial under section 30 of the Evidence Act 2006 in New Zealand?"

Now reformulate:

EXPANDED QUERIES: {{expanded_queries}}
KNOWLEDGE BASE: {{kb_target}}  // affects tone and depth

OUTPUT FORMAT: JSON array of reformulated semantic queries.
```

**Example Semantic Queries by Knowledge Base:**

| KB | Keyword Input | Semantic Output |
|----|--------------|-----------------|
| Legislation | `"theft s219 Crimes Act elements"` | `"What are the essential elements of the offence of theft under section 219 of the Crimes Act 1961, and how is the mens rea of dishonesty defined in New Zealand law?"` |
| Case Law | `"aggravated robbery self-defence NZCA"` | `"In what circumstances has the New Zealand Court of Appeal accepted self-defence as a defence to a charge of aggravated robbery under section 234 of the Crimes Act 1961?"` |
| Police Manual | `"police interview youth suspect requirements"` | `"What special procedures must New Zealand Police follow when interviewing a young person or youth offender in custody, and what safeguards are required under the Police Manual and NZBORA?"` |

---

### B. Sparse Keyword Queries (BM25 Reformulation)

**Prompt Template — Keyword Query Reformulation**

```
TASK: Reformulate the following expanded queries as keyword-heavy Boolean-style
queries optimised for BM25 sparse retrieval.

BM25 is a lexical matching algorithm that scores documents based on term frequency,
inverse document frequency, and field length. These queries should be keyword-dense,
use legal jargon and abbreviations, and follow Boolean search syntax.

INPUT QUERIES: {{expanded_queries}}
TARGET KB: {{kb_target}}

BM25 REFORMULATION RULES:
1. Use keyword-heavy format — remove stop words where possible
2. Include exact section numbers (e.g., "s234", "s48", "s21")
3. Include statute abbreviations ("Crimes Act", "NZBORA", "SSAct", "Evidence Act")
4. Use Boolean operators: AND (+), OR, NOT (-) where supported
5. Include NZ-specific abbreviations: "NZ", "CA", "HC", "DC", "SC"
6. Prioritise rare, discriminative terms over common words
7. Group related concepts with parentheses for boolean logic
8. Length: 5-20 significant keywords per query

BOOLEAN SYNTAX GUIDE:
- "term1 term2" = term1 AND term2 (implicit AND in most systems)
- "term1 OR term2" = either term
- "+term1 +term2" = required terms (explicit AND)
- "-term" = exclude term
- "\"exact phrase\"" = phrase match
- "(term1 OR term2) AND term3" = grouped boolean

NZ LEGAL ABBREVIATIONS FOR KEYWORDS:
- Acts: "Crimes Act", "NZBORA", "SSAct", "Evidence Act", "Bail Act", "CPA", "Sentencing Act"
- Courts: "NZCA", "NZHC", "NZDC", "NZSC", "NZLR", "CRNZ"
- Sections: "s" (single), "ss" (plural), "s(1)", "s(1)(a)"
- General: "NZ", "defence", "offence", "mens rea", "actus reus"

EXAMPLES:
Input (semantic): "What are the elements of aggravated robbery under New Zealand law?"
Output (BM25): "aggravated robbery s234 Crimes Act 1961 elements weapon violence dishonesty theft +NZ"

Input (semantic): "Police interview procedures for vulnerable suspects in New Zealand"
Output (BM25): "police interview vulnerable suspect NZBORA s23 s24 custody Police Manual Chapter 7 IIF recording"

Input (semantic): "When is evidence excluded for an unlawful search?"
Output (BM25): "exclusion evidence unlawful search s30 Evidence Act 2006 NZBORA s21 improperly obtained Shaheed"

EXAMPLES BY QUERY TYPE:

Offence Elements Query:
Input: theft
Output: "theft s219 Crimes Act 1961 elements dishonest intention appropriation property belonging another +NZ"

Defence Query:
Input: self-defence
Output: "self-defence s48 Crimes Act 1961 defence violence reasonable force necessity +NZ +case"

Procedural Rights Query:
Input: right to lawyer
Output: "s23 NZBORA right consult lawyer detained custody police interview Evidence Act s28 s30"

Now reformulate:

EXPANDED QUERIES: {{expanded_queries}}
BOOLEAN SYNTAX PREFERENCE: {{boolean_style}}  // "explicit" (+/-), "implicit" (space=AND), "full"

OUTPUT FORMAT: JSON array of BM25 keyword queries.
```

---

### C. Hybrid Queries

**Prompt Template — Hybrid Query Generation**

```
TASK: For each input query, generate BOTH a semantic (dense vector) version AND a
keyword (BM25) version to be executed in parallel as a hybrid search.

Hybrid search combines semantic similarity (capturing meaning) with lexical matching
(capturing exact terms). By generating both query types, we maximise the chance of
retrieving relevant documents regardless of which retrieval channel they score best on.

INPUT QUERIES: {{expanded_queries}}

HYBRID QUERY GENERATION RULES:
1. Generate semantic and keyword versions that are SEMANTICALLY EQUIVALENT
2. The semantic version should be a natural language question/statement
3. The keyword version should extract the key legal terms from the semantic version
4. Both must target the same legal information need
5. Include a weight recommendation based on query type

WEIGHTING RECOMMENDATIONS:
- Statute-heavy queries (section numbers clear): weight BM25 higher (0.6 keyword, 0.4 semantic)
- Principle-heavy queries (tests, standards): weight semantic higher (0.3 keyword, 0.7 semantic)
- Mixed queries: equal weight (0.5/0.5)
- Case name queries: weight BM25 higher for exact name matching (0.7 keyword, 0.3 semantic)

HYBRID FUSION:
Use Reciprocal Rank Fusion (RRF) to combine results:
RRF_score(d) = sum_over_queries(1 / (k + rank_q(d)))
where k = 60 (constant)

EXAMPLE:
Input concept: "aggravated robbery self-defence"
Output:
{
  "hybrid_query": {
    "semantic": "Under what circumstances can a defendant raise self-defence to a charge of aggravated robbery under section 234 of the New Zealand Crimes Act 1961?",
    "keyword": "self-defence s48 Crimes Act aggravated robbery s234 NZ +defence +violence",
    "semantic_weight": 0.4,
    "keyword_weight": 0.6,
    "fusion_method": "RRF",
    "rrf_k": 60,
    "rationale": "Section-specific query benefits from exact keyword matching"
  }
}

Now generate hybrid queries:

EXPANDED QUERIES: {{expanded_queries}}

OUTPUT FORMAT: JSON array of hybrid query objects, each with "semantic", "keyword", weights, and fusion parameters.
```

---

### D. Sub-query Decomposition

**Prompt Template — Sub-query Decomposition**

```
TASK: Break complex legal questions into atomic sub-queries that can be independently
retrieved and then combined for comprehensive coverage.

Complex legal questions typically involve multiple legal issues, each requiring
separate research. Decompose them into simpler, retrievable questions.

COMPLEX QUERY: {{complex_query}}
CASE CONTEXT: {{case_context}}

SUB-QUERY DECOMPOSITION RULES:
1. Each sub-query should address ONE legal issue only
2. Sub-queries should be independently answerable
3. Sub-queries should cover ALL aspects of the complex query
4. Order sub-queries by logical dependency (prerequisite first)
5. Include sub-queries for both prosecution requirements AND defence arguments
6. Include a sub-query for procedural/compliance issues
7. Each sub-query should specify its target knowledge base

DECOMPOSITION PATTERNS:

Pattern: "Was [PROCEDURE] lawful?"
→ 1. "What are the requirements for [PROCEDURE]?"
→ 2. "What powers authorise [PROCEDURE] without [REQUIREMENT]?"
→ 3. "What rights protect against unlawful [PROCEDURE]?"
→ 4. "What remedies for breach of [PROCEDURE] requirements?"

Pattern: "Can [DEFENCE] apply to [CHARGE]?"
→ 1. "What are the elements of [CHARGE]?"
→ 2. "What is the legal test for [DEFENCE]?"
→ 3. "Has [DEFENCE] succeeded for [CHARGE] in NZ cases?"
→ 4. "What evidence is needed to establish [DEFENCE]?"

Pattern: "Is [EVIDENCE] admissible?"
→ 1. "What is the definition of [EVIDENCE] under Evidence Act 2006?"
→ 2. "What are the admissibility requirements for [EVIDENCE]?"
→ 3. "Was [EVIDENCE] properly obtained?"
→ 4. "Should [EVIDENCE] be excluded under s30?"

EXAMPLE — Complex Query Decomposition:
Input: "Was the search of my client's vehicle lawful and can the drugs found be excluded?"

Output:
{
  "complex_query": "Was the vehicle search lawful and is the evidence excluded?",
  "sub_queries": [
    {
      "id": 1,
      "sub_query": "What are the legal requirements for police to search a vehicle in New Zealand?",
      "target_kb": ["legislation", "police_manual"],
      "legal_issue": "statutory authority for vehicle search",
      "key_statutes": ["Search and Surveillance Act 2012 s21", "s18", "s20"],
      "priority": 1
    },
    {
      "id": 2,
      "sub_query": "What rights does the New Zealand Bill of Rights Act 1990 provide against unreasonable search of vehicles?",
      "target_kb": ["legislation"],
      "legal_issue": "NZBORA s21 protection against unreasonable search",
      "key_statutes": ["NZBORA s21"],
      "priority": 2
    },
    {
      "id": 3,
      "sub_query": "What Police Manual procedures apply to vehicle searches under the Search and Surveillance Act 2012?",
      "target_kb": ["police_manual"],
      "legal_issue": "police compliance with search procedures",
      "key_references": ["Police Manual Chapter 4"],
      "priority": 3
    },
    {
      "id": 4,
      "sub_query": "When will evidence obtained from an unlawful vehicle search be excluded under section 30 of the Evidence Act 2006?",
      "target_kb": ["legislation", "case_law"],
      "legal_issue": "exclusion of improperly obtained evidence",
      "key_statutes": ["Evidence Act 2006 s30"],
      "key_cases": ["R v Shaheed", "R v Williams [2007] NZCA 52"],
      "priority": 4
    },
    {
      "id": 5,
      "sub_query": "What case law exists on vehicle searches and exclusion of evidence in New Zealand?",
      "target_kb": ["case_law"],
      "legal_issue": "NZ case law on vehicle search exclusion",
      "key_cases": ["R v Jefferies", "R v Shaheed"],
      "priority": 5
    }
  ],
  "execution_order": "parallel",  // "sequential" or "parallel"
  "aggregation_strategy": "union"  // "union" or "intersection"
}

Now decompose:

COMPLEX QUERY: {{complex_query}}
DEFENCE STRATEGY: {{defence_strategy}}
ALLEGED BREACHES: {{alleged_breaches}}

OUTPUT FORMAT: JSON with sub_queries array, execution order, and aggregation strategy.
```

**Example Decompositions:**

| Complex Query | Sub-Queries (5-7 per complex query) |
|---------------|-------------------------------------|
| "Can we exclude the confession and get a stay?" | (1) Admissibility under Evidence Act s28, (2) s30 improperly obtained evidence exclusion, (3) NZBORA s23 breach, (4) s24 rights of detained persons, (5) Abuse of process doctrine NZ, (6) Stay of proceedings for unfairness, (7) R v Ormsby lawyer right |
| "Is this aggravated robbery or just theft?" | (1) Elements of aggravated robbery s234, (2) Elements of theft s219, (3) Weapon requirement for aggravated robbery, (4) Dishonesty element in both, (5) Case law on charge reduction robbery to theft, (6) Jury directions on aggravated robbery |
| "Was the identification procedure fair?" | (1) Evidence Act s4 definition of ID evidence, (2) Evidence Act s5 admissibility requirements, (3) Evidence Act s6 reliability test, (4) Evidence Act s7 jury direction, (5) Police Manual ID procedures, (6) Case law on unreliable ID (R v Tawhai), (7) Dock identification admissibility |

---

## Part 3: Metadata Filter Generation Prompt

### Overview

Metadata filters narrow the search space before vector/BM25 retrieval, dramatically improving precision. The metadata filter generator analyses the expanded queries and generates structured filter conditions for each knowledge base.

**System Prompt — Metadata Filter Generator**

```
You are the Metadata Filter Generator for a NZ criminal defence RAG system.
Your task is to generate precise metadata filters for each knowledge base to
narrow retrieval to the most relevant documents.

FILTER GENERATION PRINCIPLES:
1. SPECIFICITY: Filters should be as specific as possible while not excluding relevant results
2. MULTI-FIELD: Use multiple metadata fields in combination
3. NZ-SPECIFIC: Use NZ court names, Act names, and legal conventions
4. DEFENCE-ORIENTED: Prioritise filters that surface defence-helpful content
5. TEMPORAL AWARENESS: Use date ranges appropriate for the legal issue
6. CONDITIONAL LOGIC: Use $and, $or, $not operators where the retrieval system supports them
```

---

### A. Legislation KB Filters

**Prompt Template — Legislation Metadata Filters**

```
TASK: Generate structured metadata filters for the NZ Legislation knowledge base.

QUERY: {{query}}
LEGAL ISSUE: {{legal_issue}}
CHARGE: {{charge}}

LEGISLATION KB SCHEMA:
{
  "id": "string (legislation document ID)",
  "title": "string (Act name)",
  "type": "primary_legislation | regulations | secondary_legislation | amendment_act",
  "jurisdiction": "new_zealand",
  "act_name": "string (full Act name)",
  "act_year": "integer (year of enactment)",
  "section_number": "string (e.g., 's234', 'ss230-240')",
  "section_name": "string (short title of section)",
  "part": "string (Part number/name)",
  "division": "string (Division name)",
  "amendment_status": "current | repealed | amended | historical",
  "effective_date": "date (when current version took effect)",
  "keywords": ["array of relevant terms"],
  "related_sections": ["array of related section references"],
  "subject_matter": "string (category)"
}

FILTER GENERATION RULES:
1. Always set jurisdiction = "new_zealand"
2. Identify the primary Act(s) relevant to the query
3. Identify section ranges relevant to the charge/issue
4. Set amendment_status based on proceedings stage:
   - Active proceedings: "current"
   - Historical analysis: "current" OR "historical"
   - Appeals on old law: "historical" for the relevant period
5. Include related Acts that provide procedural context
6. For defence queries, include Acts providing defence frameworks

ACT MAPPING — CHARGE TO RELEVANT ACTS:

| Charge Category | Primary Act | Related Acts |
|-----------------|-------------|--------------|
| Assault/Violence | Crimes Act 1961 | NZBORA 1990, Summary Offences Act 1981, Sentencing Act 2002 |
| Robbery/Burglary | Crimes Act 1961 | NZBORA 1990, Evidence Act 2006, Sentencing Act 2002 |
| Theft/Dishonesty | Crimes Act 1961 | Evidence Act 2006, Sentencing Act 2002, Criminal Procedure Act 2011 |
| Drugs | Misuse of Drugs Act 1975 | Crimes Act 1961 (complicity, attempt), Medicinal Cannabis Scheme, Customs Act 2018 |
| Driving | Land Transport Act 1998 | Land Transport (Road User) Rule 2004, Criminal Procedure Act 2011 |
| Sexual | Crimes Act 1961 | Evidence Act 2006 (ss34-44, sexual evidence), Victims' Rights Act 2002 |
| Firearms | Arms Act 1983 | Crimes Act 1961, Search and Surveillance Act 2012 |
| Fraud/Financial | Crimes Act 1961 | Secret Commissions Act 1910, Tax Administration Act 1994 |
| Procedural Rights | NZBORA 1990 | Evidence Act 2006, Search and Surveillance Act 2012, Bail Act 2000 |
| Sentencing | Sentencing Act 2002 | Criminal Procedure Act 2011, Victims' Rights Act 2002 |

EXAMPLE — Legislation Filters:
Input: "aggravated robbery s234 Crimes Act"
Output:
{
  "kb": "legislation",
  "filter": {
    "$and": [
      {"jurisdiction": {"$eq": "new_zealand"}},
      {"type": {"$eq": "primary_legislation"}},
      {"amendment_status": {"$eq": "current"}},
      {"$or": [
        {"act_name": {"$eq": "Crimes Act 1961"}},
        {"act_name": {"$eq": "New Zealand Bill of Rights Act 1990"}},
        {"act_name": {"$eq": "Evidence Act 2006"}},
        {"act_name": {"$eq": "Sentencing Act 2002"}}
      ]},
      {"$or": [
        {"section_number": {"$regex": "s23[0-9]"}},
        {"section_number": {"$regex": "s4[0-9]"}},
        {"keywords": {"$in": ["robbery", "theft", "weapon", "violence", "dishonesty"]}},
        {"subject_matter": {"$eq": "offences against property"}}
      ]}
    ]
  },
  "section_ranges": ["ss229-240", "ss46-60"],
  "rationale": "Crimes Act covers offence elements, NZBORA covers rights, Evidence Act covers admissibility, Sentencing Act covers sentencing"
}

EXAMPLE — Defence Filters:
Input: "self-defence assault"
Output:
{
  "kb": "legislation",
  "filter": {
    "$and": [
      {"jurisdiction": {"$eq": "new_zealand"}},
      {"amendment_status": {"$eq": "current"}},
      {"$or": [
        {"act_name": {"$eq": "Crimes Act 1961"}},
        {"act_name": {"$eq": "New Zealand Bill of Rights Act 1990"}},
        {"act_name": {"$eq": "Summary Offences Act 1981"}}
      ]},
      {"$or": [
        {"section_number": {"$regex": "s4[0-9]"}},  // s48 self-defence, s55 defence of property
        {"section_number": {"$regex": "s1[89][0-9]"}},  // assault sections
        {"section_number": {"$regex": "s2[0-9]"}},  // general defences
        {"keywords": {"$in": ["self-defence", "defence", "assault", "violence", "consent", "provocation"]}}
      ]}
    ]
  },
  "section_ranges": ["ss46-60", "ss190-200"],
  "rationale": "s48 self-defence and related defence provisions, assault elements for context"
}

Now generate filters for:

QUERY: {{query}}
LEGAL ISSUE: {{legal_issue}}
CHARGE: {{charge}}
DEFENCE STRATEGY: {{defence_strategy}}
PROCEEDINGS STAGE: {{proceedings_stage}}

OUTPUT FORMAT: JSON filter object with MongoDB-style query operators.
```

---

### B. Case Law KB Filters

**Prompt Template — Case Law Metadata Filters**

```
TASK: Generate structured metadata filters for the NZ Case Law knowledge base.

QUERY: {{query}}
LEGAL ISSUE: {{legal_issue}}
CHARGE: {{charge}}

CASE LAW KB SCHEMA:
{
  "id": "string (case ID)",
  "case_name": "string",
  "citation": "string (e.g., '[2020] NZSC 45')",
  "court": "Supreme Court | Court of Appeal | High Court | District Court | Privy Council | Court of Appeal (Historical)",
  "year": "integer",
  "judges": ["array of judge names"],
  "charge_categories": ["violent", "dishonesty", "drug", "driving", "sexual", "regulatory", "procedural"],
  "offences": ["array of offence names/statutes"],
  "legal_principles": ["array of principles"],
  "statutes_discussed": ["array of statute references"],
  "defences_raised": ["array of defences"],
  "reported_status": "NZLR | NZCA | NZHC | NZDC | NZSC | CRNZ | unreported",
  "keywords": ["array of terms"],
  "appellate_history": "string",
  "distinguishable": "boolean",
  "overruled": "boolean"
}

FILTER GENERATION RULES:
1. Court hierarchy preference:
   - Binding authority: Supreme Court > Court of Appeal > High Court > District Court
   - For well-settled law: any court level acceptable
   - For novel arguments: higher courts preferred
   - For procedural specifics: lower courts may have more detailed reasoning
2. Year range:
   - General principles: no year filter (or 1900-2025)
   - Modern procedure: 2006-2025 (Evidence Act 2006, CPA 2011)
   - NZBORA rights: 1990-2025 (post-NZBORA)
   - Search and surveillance: 2012-2025 (post-SSAct)
   - Sentencing: 2002-2025 (post-Sentencing Act)
3. Charge category: filter to relevant offence type
4. Defences: filter to cases where relevant defence was raised
5. Reported status: prefer reported decisions (NZLR, NZCA, NZHC) but include unreported

COURT HIERARCHY AND WEIGHTS:
- Supreme Court: binding on all lower courts (weight: 1.0)
- Court of Appeal: binding on HC and DC (weight: 0.9)
- High Court: persuasive, binding on DC (weight: 0.7)
- District Court: persuasive only (weight: 0.5)
- Privy Council: historical, pre-2004 (weight: 0.6)

YEAR RANGE RECOMMENDATIONS:

| Legal Issue | Recommended Range | Rationale |
|-------------|-------------------|-----------|
| General criminal law | 1980-2025 | Modern approach sufficient |
| NZBORA rights | 1990-2025 | Post-enactment only |
| Evidence admissibility | 2007-2025 | Post-Evidence Act 2006 |
| Search and surveillance | 2012-2025 | Post-SSAct 2012 |
| Bail | 2001-2025 | Post-Bail Act 2000 |
| Sentencing | 2002-2025 | Post-Sentencing Act 2002 |
| Self-defence | 1961-2025 | Post-Crimes Act 1961 |
| Provocation | 1961-2009 | Repealed in 2009 |
| Landmark authority | 1900-2025 | May need historical authority |

EXAMPLE — Case Law Filters:
Input: "aggravated robbery self-defence"
Output:
{
  "kb": "case_law",
  "filter": {
    "$and": [
      {"charge_categories": {"$in": ["violent", "dishonesty"]}},
      {"$or": [
        {"offences": {"$in": ["aggravated robbery", "robbery", "s234 Crimes Act"]}},
        {"statutes_discussed": {"$in": ["s234 Crimes Act 1961", "s48 Crimes Act 1961"]}},
        {"legal_principles": {"$in": ["self-defence", "aggravated robbery elements"]}}
      ]},
      {"$or": [
        {"defences_raised": {"$in": ["self-defence", "s48 Crimes Act"]}},
        {"keywords": {"$in": ["self-defence", "defence", "aggravated robbery", "weapon", "s48"]}}
      ]}
    ],
    "$or": [
      {"court": {"$in": ["Supreme Court", "Court of Appeal", "High Court"]}},
      {"reported_status": {"$in": ["NZLR", "NZCA", "NZHC", "NZSC", "CRNZ"]}}
    ]
  },
  "year_range": {"$gte": 1961, "$lte": 2025},
  "court_weights": {"Supreme Court": 1.0, "Court of Appeal": 0.9, "High Court": 0.7, "District Court": 0.5},
  "rationale": "Robbery cases where self-defence raised; all court levels acceptable but higher courts preferred for binding authority"
}

EXAMPLE — Exclusion of Evidence Filters:
Input: "unlawful search evidence exclusion"
Output:
{
  "kb": "case_law",
  "filter": {
    "$and": [
      {"$or": [
        {"legal_principles": {"$in": ["improperly obtained evidence", "exclusion", "s30 Evidence Act", "s21 NZBORA", "unlawful search"]}},
        {"statutes_discussed": {"$in": ["Evidence Act 2006 s30", "NZBORA 1990 s21", "Search and Surveillance Act 2012"]}},
        {"keywords": {"$in": ["Shaheed", "exclusion", "improperly obtained", "search", "warrant", "s30"]}}
      ]}
    ],
    "$or": [
      {"court": {"$in": ["Supreme Court", "Court of Appeal", "High Court"]}},
      {"case_name": {"$in": ["R v Shaheed", "R v Williams", "R v Jefferies", "R v Ormsby", "R v Wichman"]}}
    ]
  },
  "year_range": {"$gte": 1990, "$lte": 2025},
  "court_weights": {"Supreme Court": 1.0, "Court of Appeal": 0.9, "High Court": 0.7},
  "rationale": "Exclusion cases from NZBORA era; Shaheed and Williams are leading authorities"
}

Now generate case law filters for:

QUERY: {{query}}
LEGAL ISSUE: {{legal_issue}}
CHARGE: {{charge}}
DEFENCE: {{defence}}
PROCEEDINGS STAGE: {{proceedings_stage}}
TARGET: {{target}}  // "landmark_only", "recent", "comprehensive"

OUTPUT FORMAT: JSON filter object with court weights, year range, and rationale.
```

---

### C. Police Manual KB Filters

**Prompt Template — Police Manual Metadata Filters**

```
TASK: Generate structured metadata filters for the NZ Police Manual knowledge base.

QUERY: {{query}}
LEGAL ISSUE: {{legal_issue}}
PROCEDURAL STAGE: {{procedural_stage}}

POLICE MANUAL KB SCHEMA:
{
  "id": "string (document ID)",
  "chapter": "string (chapter name/number)",
  "chapter_number": "string",
  "topic": "string",
  "sub_topic": "string",
  "title": "string (document title)",
  "effective_date": "date",
  "version": "string",
  "status": "current | superseded | draft",
  "authority_basis": "string (statute authorising this procedure)",
  "applies_to": ["adult", "youth", "vulnerable", "all"],
  "offence_types": ["array of relevant offence categories"],
  "keywords": ["array of terms"],
  "cross_references": ["array of Police Manual chapter refs"],
  "related_legislation": ["array of statute refs"],
  "document_type": "procedure | policy | guideline | form | checklist",
  "content_type": "instructional | reference | template"
}

POLICE MANUAL CHAPTER REFERENCE:
- Chapter 1: Introduction and General Principles
- Chapter 2: Crime Reporting and Initial Investigation
- Chapter 3: Arrest and Detention
- Chapter 4: Search and Surveillance
- Chapter 5: Evidence
- Chapter 6: Charging and Bail
- Chapter 7: Custody and Interviews
- Chapter 8: Prosecutions and Court
- Chapter 9: Family Violence
- Chapter 10: Assault Offences
- Chapter 11: Dishonesty and Property Offences
- Chapter 12: Drug Offences
- Chapter 13: Sexual Offences
- Chapter 14: Traffic and Vehicle Offences
- Chapter 15: Firearms and Weapons
- Chapter 16: Youth Justice
- Chapter 17: Mental Health
- Chapter 18: Transgender and Gender Diverse
- Chapter 19: Death Investigation
- Chapter 20: Family Court and Protection Orders
- IIF: Initial Investigation Framework

FILTER GENERATION RULES:
1. Always prefer status = "current"
2. Map legal issues to specific chapters
3. Filter by offence type relevance
4. For rights-based queries, filter to chapters dealing with suspect rights
5. For vulnerable suspect queries, filter to youth/vulnerable procedures
6. Effective date: prefer versions current at time of alleged incident

CHAPTER MAPPING — LEGAL ISSUE TO POLICE MANUAL:

| Legal Issue | Primary Chapter(s) | Secondary Chapter(s) |
|-------------|-------------------|----------------------|
| Search | Ch 4: Search and Surveillance | Ch 5: Evidence |
| Arrest | Ch 3: Arrest and Detention | Ch 6: Charging and Bail |
| Interview | Ch 7: Custody and Interviews | IIF, Ch 16 (Youth) |
| Identification | Ch 5: Evidence | Ch 7: Custody and Interviews |
| Bail | Ch 6: Charging and Bail | Ch 3: Arrest and Detention |
| Assault | Ch 10: Assault Offences | Ch 9: Family Violence |
| Dishonesty | Ch 11: Dishonesty and Property | Ch 2: Initial Investigation |
| Drugs | Ch 12: Drug Offences | Ch 4: Search and Surveillance |
| Sexual | Ch 13: Sexual Offences | Ch 9: Family Violence |
| Driving | Ch 14: Traffic and Vehicle | Ch 4: Search (vehicle) |
| Firearms | Ch 15: Firearms and Weapons | Ch 4: Search |
| Youth | Ch 16: Youth Justice | Ch 7: Custody and Interviews |
| Mental Health | Ch 17: Mental Health | Ch 3: Arrest, Ch 7: Interviews |
| Family Violence | Ch 9: Family Violence | Ch 10-13 (relevant offence) |

EXAMPLE — Police Manual Filters:
Input: "police interview right to lawyer"
Output:
{
  "kb": "police_manual",
  "filter": {
    "$and": [
      {"status": {"$eq": "current"}},
      {"$or": [
        {"chapter": {"$in": ["Chapter 7: Custody and Interviews", "IIF"]}},
        {"topic": {"$in": ["interview", "custody", "lawyer", "right to consult", "detained person"]}},
        {"keywords": {"$in": ["interview", "lawyer", "s23", "NZBORA", "custody", "detention", "right to silence", "caution"]}}
      ]},
      {"$or": [
        {"applies_to": {"$in": ["adult", "all"]}},
        {"document_type": {"$in": ["procedure", "policy", "checklist"]}}
      ]}
    ]
  },
  "effective_date_range": {"$lte": "{{incident_date}}"},  // version current at time of incident
  "chapter_priority": ["Chapter 7", "IIF"],
  "rationale": "Police interview procedures are primarily in Chapter 7; IIF provides initial investigation context"
}

EXAMPLE — Youth Suspect Filters:
Input: "police interview 16 year old suspect"
Output:
{
  "kb": "police_manual",
  "filter": {
    "$and": [
      {"status": {"$eq": "current"}},
      {"$or": [
        {"chapter": {"$in": ["Chapter 7: Custody and Interviews", "Chapter 16: Youth Justice"]}},
        {"topic": {"$in": ["youth interview", "young person", "age of suspect", "appropriate adult"]}},
        {"applies_to": {"$in": ["youth"]}},
        {"keywords": {"$in": ["youth", "young person", "child", "minor", "age", " guardian", "appropriate adult", "Oranga Tamariki"]}}
      ]},
      {"document_type": {"$in": ["procedure", "policy", "guideline"]}}
    ]
  },
  "effective_date_range": {"$lte": "{{incident_date}}"},
  "chapter_priority": ["Chapter 16", "Chapter 7"],
  "rationale": "Youth-specific procedures in Ch 16; general interview procedures in Ch 7 also apply to youth with modifications"
}

Now generate Police Manual filters for:

QUERY: {{query}}
LEGAL ISSUE: {{legal_issue}}
PROCEDURAL STAGE: {{procedural_stage}}
SUSPECT TYPE: {{suspect_type}}  // "adult", "youth", "vulnerable", "unknown"
INCIDENT DATE: {{incident_date}}

OUTPUT FORMAT: JSON filter object with chapter priority and effective date range.
```

---

## Part 4: Query Prioritisation and Ranking

### Algorithm: Multi-Factor Query Scoring and Selection

After expansion and reformulation, we typically have 50-200 candidate queries. The prioritisation module selects the top-K queries per knowledge base (default K=10) using a multi-factor scoring algorithm.

**Prompt Template — Query Prioritisation**

```
TASK: Score and rank all generated queries to select the top-K most effective
queries for retrieval.

CANDIDATE QUERIES: {{candidate_queries_json}}
CASE CONTEXT: {{case_context}}
DISCLOSURE SUMMARY: {{disclosure_summary}}
DEFENCE STRATEGY: {{defence_strategy}}
CRITICAL ISSUES: {{critical_issues}}  // list of make-or-break legal issues

SCORING FRAMEWORK:

Each query is scored on the following dimensions (each 1-5):

1. RELEVANCE TO DEFENCE (weight: 0.30)
   Score 5: Directly addresses a critical defence issue
   Score 4: Addresses an important defence element
   Score 3: Provides useful context for defence
   Score 2: Marginally relevant to defence
   Score 1: Not directly relevant but worth checking

2. LEGAL IMPORTANCE (weight: 0.25)
   Score 5: Tests fundamental legal principle / constitutional right
   Score 4: Tests significant statutory interpretation
   Score 3: Standard legal issue with established precedent
   Score 2: Minor procedural point
   Score 1: Background/context only

3. COVERAGE OF CRITICAL ISSUES (weight: 0.25)
   Score 5: Addresses a critical issue that could determine the case outcome
   Score 4: Addresses an issue that significantly impacts trial strategy
   Score 3: Addresses a material issue for evidence or procedure
   Score 2: Addresses a peripheral issue
   Score 1: No clear connection to critical issues

4. NOVELTY / DISTINCTIVENESS (weight: 0.10)
   Score 5: Explores a unique or underutilised legal angle
   Score 4: Covers an angle not addressed by other queries
   Score 3: Moderate overlap with other queries
   Score 2: Significant overlap with other queries
   Score 1: Nearly identical to another query

5. RETRIEVAL CONFIDENCE (weight: 0.10)
   Score 5: High confidence that relevant documents exist for this query
   Score 4: Good likelihood of relevant results
   Score 3: Moderate likelihood
   Score 2: Low likelihood but worth trying
   Score 1: Speculative query

COMPOSITE SCORE:
score = (relevance * 0.30) + (importance * 0.25) + (critical * 0.25) + (novelty * 0.10) + (confidence * 0.10)

DIVERSITY ENFORCEMENT:
After scoring, enforce diversity by:
1. Selecting top-scoring query from each category (offence elements, defence, procedure, evidence, sentencing)
2. Removing queries with >80% term overlap with already-selected queries
3. Ensuring at least one query per knowledge base
4. Ensuring coverage of all critical issues identified

EXAMPLE SCORING:
Query: "What are the elements of aggravated robbery under s234 Crimes Act 1961?"
Scores: relevance=4, importance=5, critical=4, novelty=2, confidence=5
Composite: (4*0.30) + (5*0.25) + (4*0.25) + (2*0.10) + (5*0.10) = 4.15

Query: "Can evidence from an unlawful vehicle search be excluded under s30 Evidence Act 2006?"
Scores: relevance=5, importance=5, critical=5, novelty=3, confidence=5
Composite: (5*0.30) + (5*0.25) + (5*0.25) + (3*0.10) + (5*0.10) = 4.80

SELECTION CONFIGURATION:
- Top-K per KB: {{top_k}}  // default: 10
- Minimum score threshold: {{min_score}}  // default: 2.5
- Maximum overlap allowed: {{max_overlap}}  // default: 0.80 (80% Jaccard similarity)
- Required categories: {{required_categories}}  // default: ["offence", "defence", "procedure", "evidence"]

Now score and rank:

CANDIDATE QUERIES: {{candidate_queries_json}}

OUTPUT FORMAT: JSON array of ranked queries with scores and selection status.
```

### Diversity Algorithm (Post-Scoring)

```python
# Pseudocode for diversity enforcement

def enforce_diversity(scored_queries, top_k=10, max_overlap=0.80):
    """
    Select top-K diverse queries ensuring coverage of different legal angles.
    """
    selected = []
    categories_covered = set()

    # Phase 1: Select best query from each required category
    required_categories = ["offence_elements", "defence", "procedure", "evidence", "rights"]
    for category in required_categories:
        category_queries = [q for q in scored_queries if q["category"] == category]
        if category_queries:
            best = max(category_queries, key=lambda q: q["composite_score"])
            if best not in selected:
                selected.append(best)
                categories_covered.add(category)

    # Phase 2: Fill remaining slots with highest-scoring non-overlapping queries
    remaining = sorted(scored_queries, key=lambda q: q["composite_score"], reverse=True)

    for query in remaining:
        if len(selected) >= top_k:
            break
        if query in selected:
            continue

        # Check overlap with already selected
        is_diverse = True
        for sel in selected:
            overlap = jaccard_similarity(
                set(query["terms"]),
                set(sel["terms"])
            )
            if overlap > max_overlap:
                is_diverse = False
                break

        if is_diverse:
            selected.append(query)

    return selected

def jaccard_similarity(set_a, set_b):
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0
```

### Priority Weights for Re-ranking

After retrieval, documents are re-ranked using the following priority signals:

| Signal | Weight | Description |
|--------|--------|-------------|
| Query match score (vector/BM25) | 0.25 | Base retrieval score |
| Court authority level | 0.20 | Supreme Court > CA > HC > DC |
| Recency | 0.15 | More recent decisions preferred |
| Defence relevance | 0.20 | Document addresses defence argument |
| Statute currency | 0.10 | References current law vs repealed |
| Citation count (case law) | 0.05 | More cited = more authoritative |
| Knowledge base priority | 0.05 | Legislation > Case Law > Police Manual (for authority) |

---

## Part 5: Complete Pipeline Architecture

### Pipeline Diagram

```
DISCLOSURE UPLOAD
       |
       v
  +-------------------------+
  | 1. PARSE / EXTRACT      |  <- Extract: charges, facts, dates, evidence items,
  |    (Document Parser)    |     witnesses, procedural timeline, exhibits
  +-------------------------+
       |
       v
  +-------------------------+
  | 2. GENERATE INITIAL     |  <- LLM generates 5-15 initial queries from
  |    QUERIES              |     disclosure content
  |    (Query Generator)    |
  +-------------------------+
       |
       v
  +-------------------------+
  | 3. EXPAND QUERIES       |  <- Apply 5 expansion strategies (Part 1)
  |    (Expansion Engine)   |     Synonym, Hyponym, Citation, Defence, Procedural
  +-------------------------+
       |
       v
  +-------------------------+
  | 4. REFORMULATE QUERIES  |  <- Generate: semantic, keyword, hybrid (Part 2)
  |    (Reformulation Eng.) |     + Sub-query decomposition
  +-------------------------+
       |
       v
  +-------------------------+
  | 5. GENERATE METADATA    |  <- Create filters for each KB (Part 3)
  |    FILTERS              |
  |    (Filter Generator)   |
  +-------------------------+
       |
       v
  +-------------------------+
  | 6. PRIORITISE & RANK    |  <- Score, enforce diversity, select top-K (Part 4)
  |    (Query Selector)     |
  +-------------------------+
       |
       +----------+----------+----------+
       |          |          |          |
       v          v          v          v
  +--------+ +--------+ +--------+ +--------+
  |KB:     | |KB:     | |KB:     | |KB:     |
  |NZ      | |NZ      | |NZ      | |Cross-  |
  |Legis-  | |Case    | |Police  | |KB      |
  |lation  | |Law     | |Manual  | |Fusion  |
  +--------+ +--------+ +--------+ +--------+
       |          |          |          |
       v          v          v          v
  +--------+ +--------+ +--------+ +--------+
  |Hybrid  | |Hybrid  | |Hybrid  | |Unified |
  |Search  | |Search  | |Search  | |Ranking |
  |(Vector+| |(Vector+| |(Vector+| |(RRF/   |
  | BM25)  | | BM25)  | | BM25)  | |Weighted|
  +--------+ +--------+ +--------+ +--------+
       |          |          |          |
       +----------+----------+----------+
                  |
                  v
         +------------------+
         | 7. RE-RANK       |  <- Apply priority weights, authority scoring
         |    (Re-ranker)   |
         +------------------+
                  |
                  v
         +------------------+
         | 8. DEDUPLICATE   |  <- Remove duplicate/similar documents
         |    (Deduplicator)|     across KB results
         +------------------+
                  |
                  v
         +------------------+
         | 9. FORMAT FOR    |  <- Chunk, context window, citation formatting
         |    KC PERSONAS   |
         +------------------+
                  |
                  v
         +------------------+
         | 10. FEED TO      |  <- Knowledge-Customised Personas consume
         |     KC PERSONAS  |     the retrieved context
         +------------------+
```

---

### Step-by-Step Specification

#### Step 1: Parse / Extract

| Attribute | Value |
|-----------|-------|
| **Component** | Document Parser |
| **Input** | Police disclosure PDF (.pdf), charge sheet, CCTV list, exhibit list, witness statements |
| **Output** | Structured JSON: `{charges: [...], facts: [...], timeline: [...], evidence: [...], witnesses: [...], procedural_events: [...]}` |
| **LLM Prompt** | Extraction prompt (separate system) |
| **Model** | GPT-4o or Claude 3.5 Sonnet (strong structured output) |
| **Temperature** | 0.1 (deterministic extraction) |
| **Max Tokens** | 4000 |
| **Hardware** | Standard cloud inference |
| **Constraints** | Must handle redacted documents, poor-quality scans, handwritten notes |

#### Step 2: Generate Initial Queries

| Attribute | Value |
|-----------|-------|
| **Component** | Query Generator |
| **Input** | Structured disclosure JSON from Step 1 |
| **Output** | 5-15 initial search queries (natural language questions) |
| **LLM Prompt** | "Given the following charges and facts, generate search queries for NZ criminal law research..." |
| **Model** | GPT-4o or Claude 3.5 Sonnet |
| **Temperature** | 0.3 (some creativity for query variation) |
| **Max Tokens** | 2000 |
| **Hardware** | Standard cloud inference |
| **Constraints** | Queries must be NZ-specific, defence-oriented, and cite known statutes |

#### Step 3: Expand Queries (EXPANSION ENGINE)

| Attribute | Value |
|-----------|-------|
| **Component** | Expansion Engine (Part 1 of this document) |
| **Input** | Initial queries from Step 2 |
| **Output** | Expanded queries: ~20-50 per initial query across 5 strategies |
| **LLM Prompt** | Query Expansion Prompts (Sections A-E above) |
| **Model** | GPT-4o (best legal reasoning) or fine-tuned legal LLM |
| **Temperature** | 0.4 (creative expansion but grounded) |
| **Max Tokens** | 4000 per expansion batch |
| **Hardware** | Standard cloud inference; batch parallel calls |
| **Constraints** | Must validate all section references against NZ statute database |

**Execution Pattern:**
```
For each initial query:
  - Call Synonym Expansion (parallel)
  - Call Hyponym Expansion (parallel)
  - Call Citation Expansion (parallel, if citations detected)
  - Call Defence Expansion (parallel, if charges identified)
  - Call Procedural Expansion (parallel, if procedural issues detected)
  - Merge all expansions into unified expansion set
```

#### Step 4: Reformulate Queries (REFORMULATION ENGINE)

| Attribute | Value |
|-----------|-------|
| **Component** | Reformulation Engine (Part 2 of this document) |
| **Input** | Expanded queries from Step 3 |
| **Output** | For each query: semantic version + keyword version + hybrid config |
| **LLM Prompt** | Query Reformulation Prompts (Sections A-D above) |
| **Model** | GPT-4o or Claude 3.5 Sonnet |
| **Temperature** | 0.2 (consistent reformulation) |
| **Max Tokens** | 3000 per batch |
| **Hardware** | Standard cloud inference |
| **Constraints** | Semantic queries must be grammatical; keyword queries must be index-friendly |

**Execution Pattern:**
```
For each expanded query:
  - Generate semantic version (dense vector query)
  - Generate keyword version (BM25 query)
  - Generate hybrid config (weights, fusion method)
  - If complex legal question: decompose into sub-queries
  - Package as HybridQuery object
```

#### Step 5: Generate Metadata Filters (FILTER GENERATOR)

| Attribute | Value |
|-----------|-------|
| **Component** | Filter Generator (Part 3 of this document) |
| **Input** | Reformulated queries + charge context |
| **Output** | Structured metadata filters per KB (JSON with operators) |
| **LLM Prompt** | Metadata Filter Prompts (Sections A-C above) |
| **Model** | GPT-4o or Claude 3.5 Sonnet |
| **Temperature** | 0.1 (deterministic filter generation) |
| **Max Tokens** | 2000 |
| **Hardware** | Standard cloud inference |
| **Constraints** | Filters must be valid against KB schema; section ranges must be validated |

**Execution Pattern:**
```
For each charge:
  - Generate Legislation KB filters (act names, section ranges, amendment status)
  - Generate Case Law KB filters (courts, year ranges, charge categories)
  - Generate Police Manual KB filters (chapters, topics, effective dates)
  - Attach filters to corresponding queries
```

#### Step 6: Prioritise & Rank (QUERY SELECTOR)

| Attribute | Value |
|-----------|-------|
| **Component** | Query Selector (Part 4 of this document) |
| **Input** | All reformulated queries + metadata filters + case context |
| **Output** | Top-K queries per KB (default K=10) with scores |
| **LLM Prompt** | Query Prioritisation Prompt (above) |
| **Algorithm** | Multi-factor scoring + diversity enforcement |
| **Model** | GPT-4o for scoring; deterministic algorithm for diversity |
| **Temperature** | 0.2 |
| **Max Tokens** | 4000 |
| **Hardware** | Standard cloud inference |
| **Constraints** | Must ensure coverage of all critical issues; no KB left without queries |

**Configuration:**
```yaml
top_k_per_kb: 10
total_queries_max: 30  # across all KBs
min_score_threshold: 2.5
max_jaccard_overlap: 0.80
required_categories:
  - offence_elements
  - defence
  - procedure
  - evidence
  - rights
diversity_algorithm: "category_first_then_score"
```

#### Step 7: Execute Hybrid Search

| Attribute | Value |
|-----------|-------|
| **Component** | Hybrid Search Executor |
| **Input** | Top-K queries + metadata filters per KB |
| **Output** | Retrieved document chunks with scores |
| **Method** | Dense (vector) + Sparse (BM25) with RRF fusion |
| **Vector DB** | Weaviate / Pinecone / Milvus with HNSW indexing |
| **BM25 Engine** | Elasticsearch / OpenSearch / built-in hybrid |
| **Fusion** | RRF (Reciprocal Rank Fusion, k=60) or weighted score fusion |
| **Hardware** | GPU for embedding inference; vector DB cluster |
| **Constraints** | Query latency <2s per KB; support for metadata pre-filtering |

**Hybrid Search Configuration:**
```yaml
vector_search:
  embedding_model: "intfloat/multilingual-e5-large"  # or NZ-legal fine-tuned
  dimension: 1024
  similarity_metric: "cosine"
  ef: 256  # HNSW exploration factor
  max_candidates: 100

bm25_search:
  k1: 1.2  # term saturation
  b: 0.75   # length normalisation
  max_candidates: 100

fusion:
  method: "RRF"
  rrf_k: 60
  # OR: weighted
  # vector_weight: 0.5
  # bm25_weight: 0.5

retrieval_per_query: 20  # top-N chunks per query
```

#### Step 8: Re-rank

| Attribute | Value |
|-----------|-------|
| **Component** | Re-ranker |
| **Input** | Fused retrieval results from all queries |
| **Output** | Re-ranked document list with composite scores |
| **Method** | Cross-encoder re-ranker + legal-specific signals |
| **Model** | MonoT5 or BGE-Reranker (fine-tuned on legal data) |
| **Signals** | Court authority, recency, defence relevance, statute currency |
| **Hardware** | GPU for cross-encoder inference |
| **Constraints** | Must process up to 500 documents within 1s |

**Re-ranking Formula:**
```python
final_score = (
    0.25 * retrieval_score +
    0.20 * court_authority_weight +
    0.15 * recency_score +
    0.20 * defence_relevance_score +
    0.10 * statute_currency_score +
    0.05 * citation_count_score +
    0.05 * kb_priority_score
)
```

#### Step 9: Deduplicate

| Attribute | Value |
|-----------|-------|
| **Component** | Deduplicator |
| **Input** | Re-ranked document list |
| **Output** | Deduplicated document set |
| **Method** | Semantic similarity + exact citation matching |
| **Threshold** | >90% semantic similarity = duplicate |
| **Priority** | Keep highest-scoring version; merge citations if different |
| **Hardware** | CPU only |

#### Step 10: Feed to KC Personas

| Attribute | Value |
|-----------|-------|
| **Component** | Context Formatter |
| **Input** | Final deduplicated document set |
| **Output** | Formatted context chunks for KC Personas |
| **Format** | XML-structured context with citation metadata |
| **Max Context** | 128K tokens total across all KBs |
| **Chunking** | 512-token chunks with 128-token overlap |
| **Citations** | Full NZ citation format embedded in each chunk |

**Context Format:**
```xml
<context source="nz_legislation" citation="Crimes Act 1961, s234" type="primary_legislation" currency="current">
Section 234 — Aggravated robbery
(1) Robbery is aggravated if committed—
    (a) By 2 or more people; or
    (b) By a person armed with a weapon; or
    (c) By a person armed with a pistol, revolver, or other firearm; or
    (d) By a person armed with any explosive substance or device.
</context>

<context source="nz_case_law" citation="[2011] NZCA 607" court="Court of Appeal" year="2011">
R v Nathan — The Court of Appeal held that for aggravated robbery under s234(1)(b), 
the Crown must prove that the defendant had a weapon at the time of the robbery...
</context>
```

---

### Configuration Summary

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Embedding Model** | `intfloat/multilingual-e5-large` or NZ-legal fine-tuned | Best for legal domain; supports long documents |
| **Cross-encoder** | `BAAI/bge-reranker-large` fine-tuned on NZ case law | Relevance scoring optimised for NZ legal text |
| **Vector Dimension** | 1024 | Standard for e5-large |
| **Chunk Size** | 512 tokens | Balance between specificity and context |
| **Chunk Overlap** | 128 tokens | Preserve cross-chunk context |
| **Max Queries per KB** | 10 | Manage latency while maintaining coverage |
| **Retrieval per Query** | 20 chunks | 200 total per KB before re-ranking |
| **Final Context Size** | ~50 chunks / ~25K tokens | Fits within LLM context window |
| **RRF Constant (k)** | 60 | Standard RRF value; robust across query types |
| **Temperature (Expansion)** | 0.4 | Creative but controlled expansion |
| **Temperature (Reformulation)** | 0.2 | Consistent output |
| **Temperature (Filters)** | 0.1 | Deterministic |
| **Temperature (Prioritisation)** | 0.2 | Structured scoring |
| **LLM for All Stages** | GPT-4o or Claude 3.5 Sonnet | Strong legal reasoning, structured output |

---

## Appendices

### Appendix A: NZ Statute Quick Reference

| Act | Year | Key Sections (Criminal Defence) |
|-----|------|--------------------------------|
| Crimes Act 1961 | 1961 | ss2 (definitions), ss23-25 (defences), s48 (self-defence), s55 (defence of property), s128-144 (sexual), ss190-200 (assault), ss217-246 (dishonesty), ss229-240 (robbery/burglary) |
| New Zealand Bill of Rights Act 1990 | 1990 | ss2-29 (all rights), s21 (search), s22 (arrest), s23 (lawyer), s24 (arrested persons), s25 (charged persons) |
| Evidence Act 2006 | 2006 | ss4-7 (identification), s28 (defendant's statements), s29 (suspect statements), s30 (improperly obtained evidence), s31 (warnings), ss34-44 (sexual evidence) |
| Search and Surveillance Act 2012 | 2012 | ss18-21 (search powers), s37 (detained persons' rights), ss48-50 (examination/production orders), ss98-110 (warrants) |
| Bail Act 2000 | 2000 | ss7-8 (bail application), ss12-13 (conditions), ss28-30 (review/variation), ss38-39 (appeals) |
| Criminal Procedure Act 2011 | 2011 | ss122-124 (disclosure), ss14-16 (procedure after arrest), s366 (sentencing procedure) |
| Sentencing Act 2002 | 2002 | ss7-10 (purposes/principles), ss27-29 (aggravating/mitigating factors) |
| Misuse of Drugs Act 1975 | 1975 | s6 (drug offences), Schedules 1-5 (classification) |
| Land Transport Act 1998 | 1998 | s22 (careless driving), s36 (reckless driving), s56 (drink driving) |
| Arms Act 1983 | 1983 | ss3-5 (licensing), ss16-20 (offences) |

### Appendix B: Leading NZ Case Law by Topic

| Topic | Leading Case | Citation |
|-------|-------------|----------|
| Self-defence | R v Keogh | [1964] NZLR 737 (CA) |
| Aggravated robbery — weapon | R v Wang | [1989] 2 NZLR 213 (CA) |
| Aggravated robbery — elements | R v Nathan | [2011] NZCA 607 |
| Exclusion of evidence | R v Shaheed | [2002] 2 NZLR 377 (CA) |
| Exclusion — threshold | R v Williams | [2007] NZCA 52 |
| Right to lawyer | R v Ormsby | [2013] NZCA 526 |
| Police questioning | R v Matenga | [2013] NZCA 38 |
| Identification evidence | R v Tawhai | [1985] 2 NZLR 237 (CA) |
| Identification — warning | R v Harmer | [2000] 2 NZLR 659 (CA) |
| Unlawful arrest | R v Faletoi | [1996] 2 NZLR 433 (HC) |
| Search — reasonable grounds | R v Jefferies | [1990] 1 NZLR 515 (HC) |
| Provocation repeal | Crimes (Provocation Repeal) Amendment Act 2009 | N/A |
| Claim of right | R v Fatu | [2002] NZCA 152 |
| Theft — dishonesty | R v Morley | [1992] 2 NZLR 305 (CA) |
| Bail principles | R v Hall | [1990] 2 NZLR 675 (CA) |

### Appendix C: System Prompt Template (Complete)

```
You are the advanced retrieval optimisation system for a New Zealand criminal 
defence legal RAG platform. Your purpose is to maximise the retrieval of 
legally relevant, defence-helpful documents from three knowledge bases:
1. NZ Legislation (Acts, Regulations)
2. NZ Case Law (reported and unreported decisions)
3. NZ Police Manual (operational procedures and policies)

OPERATING PRINCIPLES:
1. DEFENCE-ORIENTED: Every query and filter should prioritise finding 
   information that helps the defendant's case.
2. NZ-SPECIFIC: All legal references must use New Zealand law only.
3. CITATION-PRECISE: Use exact section numbers, case citations, and legal 
   terminology recognised in NZ courts.
4. COMPREHENSIVE: Cover all angles — offence elements, defences, procedural 
   rights, evidence rules, and sentencing.
5. CURRENT LAW: Prefer current legislation unless the proceedings relate to 
   historical events governed by repealed law.
6. PROCEDURAL RIGOUR: For every investigative step, check whether police 
   complied with their statutory obligations and internal procedures.

OUTPUT FORMAT: Always return valid JSON. No explanatory text outside JSON.
```

### Appendix D: Query Category Taxonomy

```
query_categories:
  offence_elements:
    description: "Queries about the legal elements of the charged offence"
    priority: high
    kb_preference: ["legislation", "case_law"]
  
  defence_substantive:
    description: "Queries about complete defences (self-defence, claim of right, etc.)"
    priority: high
    kb_preference: ["legislation", "case_law"]
  
  defence_procedural:
    description: "Queries about procedural defences (exclusion, abuse of process, stay)"
    priority: high
    kb_preference: ["legislation", "case_law", "police_manual"]
  
  evidence_admissibility:
    description: "Queries about whether evidence can be admitted"
    priority: high
    kb_preference: ["legislation", "case_law"]
  
  procedural_rights:
    description: "Queries about NZBORA and statutory rights"
    priority: high
    kb_preference: ["legislation", "case_law", "police_manual"]
  
  police_compliance:
    description: "Queries about whether police followed correct procedures"
    priority: medium
    kb_preference: ["police_manual", "case_law"]
  
  sentencing:
    description: "Queries about sentencing principles and ranges"
    priority: medium
    kb_preference: ["legislation", "case_law"]
  
  case_authority:
    description: "Queries about leading cases and their application"
    priority: medium
    kb_preference: ["case_law"]
  
  statutory_interpretation:
    description: "Queries about how courts have interpreted legislation"
    priority: medium
    kb_preference: ["case_law", "legislation"]
  
  practice_procedure:
    description: "Queries about court rules and practice"
    priority: low
    kb_preference: ["legislation", "police_manual"]
```

---

## Document End

**This document is the complete technical specification for the NZ Criminal Defence RAG Query Expansion, Reformulation, and Metadata Filtering System.**

**All prompt templates are production-ready and designed for use with GPT-4o or Claude 3.5 Sonnet-class LLMs.**

---
*Generated for NZ Criminal Defence RAG Implementation*
