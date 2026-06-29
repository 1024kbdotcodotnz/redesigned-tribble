# Structured Output Templates

## Table of Contents
- [Template 1: Charges Register](#template-1-charges-register)
- [Template 2: Evidence & Summary of Facts Assessment](#template-2-evidence--summary-of-facts-assessment)
- [Template 3: Procedural Breaches & LEA Conduct Audit](#template-3-procedural-breaches--lea-conduct-audit)
- [Template 4: Further Disclosure Request](#template-4-further-disclosure-request)
- [Template 5: Accused Options & Next Steps](#template-5-accused-options--next-steps)
- [Integration Format](#integration-format)

---

## Template 1: Charges Register

For each charge, provide:

```
# CHARGES REGISTER

## Charge [N]: [Offence Name]
- **Statutory basis**: [Act] [Section]
- **Date of alleged offence**: [date]
- **Location**: [location]
- **Complainant/victim**: [identifier or "not specified"]

### Elements Required (Crown must prove each beyond reasonable doubt)
| # | Element | Statutory Source | Evidence Relied Upon | Status |
|---|---------|-----------------|---------------------|--------|
| 1 | [e.g., Applied force directly/indirectly] | s196(1)(a) Crimes Act 1961 | Summary of facts para [X]; Witness statement [name] | Supported / Partial / Unsupported / Disputed |
| 2 | [e.g., Without consent] | s196(1)(a) Crimes Act 1961 | [evidence reference] | Supported / Partial / Unsupported / Disputed |
| 3 | [e.g., Intentionally or recklessly] | s196(1)(a); s24 Crimes Act 1961 | [evidence reference] | Supported / Partial / Unsupported / Disputed |

### Maximum Penalty
- [Penalty from statute]
- **Charge type**: [Category 1 / 2 / 3 / 4 per CPA 2011 s6]
- **Electable**: [Yes/No — if Category 2 or 3, note defendant election rights]

### Available Defences
| Defence | Basis | Evidence Required | Assessment |
|---------|-------|-------------------|------------|
| [e.g., Self-defence] | s48 Crimes Act 1961 | Evidence of reasonable belief of imminent force | [Viable / Partially viable / Not viable — with reasons] |
| [e.g., Consent] | s59 Crimes Act 1961 | Evidence of informed consent | [Assessment] |

### Preliminary Assessment
- **Evidential sufficiency**: [Sufficient / Insufficient / Borderline — reasons]
- **Credibility issues**: [Any witness reliability concerns]
- **Identified weakness**: [Strongest defence point]
- **Perspective divergence**: [If perspectives disagree on charge strength]
```

---

## Template 2: Evidence & Summary of Facts Assessment

```
# EVIDENCE AND SUMMARY OF FACTS ASSESSMENT

## A. Summary of Facts Analysis

| Para # | SoF Assertion | Corroborating Evidence | Gaps / Inconsistencies | Assessment |
|--------|---------------|----------------------|------------------------|------------|
| [1] | [Quote or summarise] | [Exhibit/statement reference] | [Any missing corroboration] | Accepted / Contested / Unverified |

### Overall SoF Assessment
- **Completeness**: [Complete / Incomplete — missing elements identified]
- **Accuracy**: [Consistent with evidence / Contains inaccuracies at paras: X, Y]
- **Omissions**: [Material facts favourable to accused not included]
- **Prosecution narrative strength**: [Strong / Moderate / Weak]

## B. Witness Evidence Assessment

| Witness | Role | Statement Date | Key Claims | Credibility Factors | Reliability Concerns | Cross-Exam Issues |
|---------|------|---------------|------------|--------------------|----------------------|-------------------|
| [Name/ID] | Complainant/Police/Eye witness/Expert | [Date] | [Summary] | [Consistent/inconsistent with other evidence] | [Memory, sightline, intoxication, motive] | [Suggested lines] |

### Witness Reliability Flags
- **s122 Evidence Act direction required**: [Yes/No — visually identification issues]
- **s123 Evidence Act direction required**: [Yes/No — prison informer]
- **s125 Evidence Act direction required**: [Yes/No — witness with motive to lie]
- **s126 Evidence Act direction required**: [Yes/No — paid witness]

## C. Physical / Forensic Evidence

| Exhibit | Type | Forensic Analysis | Chain of Custody | Alternative Explanation | Challenge Available? |
|---------|------|------------------|------------------|------------------------|---------------------|
| [e.g., EXH-001] | DNA | ESR report dated [X] | [Complete/Gap at [stage]] | [Contamination, transfer, innocent explanation] | [Yes — basis / No] |

## D. Digital Evidence

| Device/Source | Data Extracted | Authority for Extraction | Search Method | Legal Challenge |
|---------------|---------------|--------------------------|---------------|-----------------|
| [e.g., iPhone SE] | [Messages, location data, photos] | [Warrant # / Consent / s21 S&S Act] | [Cellebrite/manual] | [s21/s56/s68 S&S Act grounds] |

## E. Audio/Video Evidence

| Recording | Source | Quality | Provenance | Enhancement | Admissibility Issue |
|-----------|--------|---------|------------|-------------|---------------------|
| [e.g., CCTV Main St] | [Business/Private/Police bodycam] | [Clear/Partial/Obstructed] | [Continuous/edited] | [Enhanced/original] | [Authentication, editing, completeness] |

## F. Interview Evidence

| Interview | Date | Location | Duration | Caution Given? | Lawyer Present? | Vulnerabilities | s56 Challenge? |
|-----------|------|----------|----------|---------------|-----------------|-----------------|---------------|
| [Accused #1] | [Date] | [Police station/street] | [X mins] | [Yes/No/Partial] | [Yes/No/Delayed] | [Intoxication, youth, language, mental health] | [Grounds for challenge] |

### Custody Timeline Check
- **Arrest time**: [time]
- **Arrest location**: [location]
- **Arresting officer**: [name/number]
- **Station arrival**: [time]
- **Caution given**: [time]
- **Lawyer contact attempted**: [time]
- **Lawyer arrived**: [time]
- **Interview commenced**: [time]
- **Interview concluded**: [time]
- **Total custody duration**: [duration]
- **s23 NZBORA compliance**: [Compliant / Issues at: [specify]]

## G. Identification Evidence

| ID Method | Circumstances | Procedure Compliance | s122 Direction Required? | Reliability Assessment |
|-----------|--------------|---------------------|-------------------------|----------------------|
| [Photo array / Show-up / Dock ID / CCTV] | [Where, when, conditions] | [Per Casey guidelines / Departures] | [Yes/No] | [High/Medium/Low confidence] |
```

---

## Template 3: Procedural Breaches & LEA Conduct Audit

```
# PROCEDURAL BREACHES AND LAW ENFORCEMENT CONDUCT AUDIT

## Summary of Findings
- **Total potential breaches identified**: [N]
- **High severity**: [N] (may warrant exclusion or stay)
- **Medium severity**: [N] (may affect weight or require judicial direction)
- **Low severity**: [N] (documented, may assist in negotiation)

---

### Category 1: Search and Seizure Breaches (s21 NZBORA / Search and Surveillance Act 2012)

| # | Item/Evidence Affected | Alleged Breach | Statutory Basis | Severity | Remedy Sought | Likely Outcome |
|---|----------------------|---------------|-----------------|----------|---------------|---------------|
| 1 | [e.g., Phone EXH-003] | Warrant lacked particularity — authorised "any electronic device" without specifying offence nexus | s48 S&S Act 2012 (particularity requirement); s21 NZBORA | High | s56 Evidence Act exclusion | [Perspective assessment] |
| 2 | [e.g., Home search] | Warrantless search — no statutory power, no consent, no exigency | s14 S&S Act 2012; s21 NZBORA | High | Exclusion + s130 S&S Act remedy | [Assessment] |
| 3 | [e.g., Plain view seizure] | Seizure exceeded warrant scope | s55 S&S Act 2012; s21 NZBORA | Medium | Exclusion of item | [Assessment] |
| 4 | [e.g., Delay in providing inventory] | Post-search notification not provided within required timeframe | s59 S&S Act 2012 | Low | Documented for trial | N/A |

### Category 2: Arrest and Detention Breaches (s22-23 NZBORA)

| # | Alleged Breach | Statutory Basis | Severity | Remedy Sought | Likely Outcome |
|---|---------------|-----------------|----------|---------------|---------------|
| 1 | [Arrest without reasonable grounds] | s22 NZBORA | High | Stay of proceedings / exclusion | [Assessment] |
| 2 | [Failure to inform of right to lawyer promptly] | s23(1)(b), s23(2) NZBORA | High | Exclusion of statement | [Assessment] |
| 3 | [Interview commenced before lawyer consultation] | s23(1)(c) NZBORA | High | Exclusion of statement | [Assessment] |
| 4 | [Failure to inform of right to silence] | s23(2) NZBORA | High | Exclusion of statement | [Assessment] |
| 5 | [Excessive detention before charge] | s23(3) NZBORA | Medium | Bail application / sentence credit | [Assessment] |

### Category 3: Interview and Statement Breaches (s61 Evidence Act / s23 NZBORA)

| # | Statement/Interview Affected | Alleged Breach | Statutory Basis | Severity | Remedy Sought | Likely Outcome |
|---|------------------------------|---------------|-----------------|----------|---------------|---------------|
| 1 | [Accused interview] | Oppression — officer used threats/inducements | s61 Evidence Act 2006 | High | Exclusion | [Assessment] |
| 2 | [Accused interview] | Statement involuntary — accused intoxicated, comprehension impaired | s61 Evidence Act 2006; s24 NZBORA (fair trial) | High | Exclusion | [Assessment] |
| 3 | [Accused interview] | False representation by officer | s56 Evidence Act 2006 | High | Exclusion | [Assessment] |
| 4 | [Accused interview] | No ERISP/recorded caution in te reo when accused requested | s23(2) NZBORA; s77 Evidence Act (interpreter) | Medium | Exclusion / adverse inference direction | [Assessment] |

### Category 4: Disclosure Breaches (CPA 2011)

| # | Alleged Breach | Statutory Basis | Severity | Remedy Sought | Likely Outcome |
|---|---------------|-----------------|----------|---------------|---------------|
| 1 | [Late disclosure of witness statement] | s62 CPA 2011 (continuing obligation) | Medium | Adjournment / costs / adverse inference | [Assessment] |
| 2 | [Withheld material — no s63 reasons given] | s63 CPA 2011 | Medium | Court review of withholding | [Assessment] |
| 3 | [Incomplete initial disclosure] | s60 CPA 2011 | Low-Medium | Formal request / court direction | [Assessment] |

### Category 5: Privacy and Data Breaches (Privacy Act 2020)

| # | Alleged Breach | Statutory Basis | Severity | Remedy Sought |
|---|---------------|-----------------|----------|---------------|
| 1 | [Unlawful collection of personal information] | Privacy Act 2020 IPP 1 | Medium | Privacy Commissioner complaint |
| 2 | [Unreasonable intrusion] | Privacy Act 2020 IPP 4 | Medium | Documented for trial / civil claim |

### Category 6: Other Procedural Irregularities

| # | Issue | Relevant Provision | Impact | Recommended Action |
|---|-------|-------------------|--------|-------------------|
| 1 | [e.g., Charging document defect] | s14-17 CPA 2011 | [Substantial/Technical] | [Amendment request / challenge] |
| 2 | [e.g., Incorrect offence category] | s6 CPA 2011 | [Affects election rights] | [Seek reclassification] |
```

---

## Template 4: Further Disclosure Request

```
# FURTHER DISCLOSURE REQUEST

## Basis
Under s61 and s62 Criminal Procedure Act 2011, the Crown must disclose all relevant material it has or controls. The following material has not been provided and is requested.

---

### A. Evidential Disclosure (s68-72 CPA 2011)

| # | Item Requested | Legal Basis | Relevance | Urgency |
|---|---------------|-------------|-----------|---------|
| 1 | [e.g., Full CCTV footage from [location] including 30 mins before and after incident, not just edited extract] | s68 CPA 2011 (video recordings) | Context, alternative narrative, completeness | High |
| 2 | [e.g., Original ESR report and all working notes, not just summary] | s68 CPA 2011 (expert reports) | Cross-examination material, methodology challenge | High |
| 3 | [e.g., Complete witness statement of [name], not just excerpt in summary] | s60(1)(f), s61 CPA 2011 | Full context, potential inconsistencies | High |
| 4 | [e.g., Police notebook entries of [officer] for [date]] | s61 CPA 2011 | Contemporaneous record, potential inconsistencies with SoF | Medium |
| 5 | [e.g., Body-worn camera footage of all officers at scene] | s68 CPA 2011 | Scene integrity, officer conduct, contemporaneous observations | Medium |

### B. Witness Disclosure (s74-78 CPA 2011)

| # | Item Requested | Legal Basis | Relevance | Urgency |
|---|---------------|-------------|-----------|---------|
| 1 | [e.g., Complete criminal history of complainant [name]] | s74 CPA 2011 (witness criminal records) | Credibility, motive, pattern of complaints | High |
| 2 | [e.g., Previous complaints made by complainant (similar fact — s43 Evidence Act)] | s61 CPA 2011 (material assisting defence) | Credibility, alternative explanation | Medium |
| 3 | [e.g., Witness contact details for independent witnesses [names]] | s74 CPA 2011 | Defence investigation, potential alibi/confirmation | Medium |

### C. Forensic and Technical Disclosure

| # | Item Requested | Legal Basis | Relevance | Urgency |
|---|---------------|-------------|-----------|---------|
| 1 | [e.g., Complete digital forensic extraction report including extraction logs, hash values, tools used] | s68 CPA 2011 | Chain of custody, integrity of extraction, challenge methodology | High |
| 2 | [e.g., Cell tower/location data underlying map exhibits] | s68 CPA 2011 | Accuracy of location evidence, alternative explanation for presence | Medium |
| 3 | [e.g., All photographs taken at scene (not just selected exhibits)] | s61 CPA 2011 | Context, exculpatory details not in selected photos | Medium |

### D. Investigative Material

| # | Item Requested | Legal Basis | Relevance | Urgency |
|---|---------------|-------------|-----------|---------|
| 1 | [e.g., 111/emergency call recording and transcript] | s61 CPA 2011 | Original complaint context, timing, urgency assessment | High |
| 2 | [e.g., Police communication logs for [date/time] — dispatch, radio] | s61 CPA 2011 | Response time, officer observations, scene management | Medium |
| 3 | [e.g., Informant material — if relied upon, disclosure required per s61; if withheld, s63 reasons] | s61, s63 CPA 2011 | Source of information, reliability of investigation | Medium |
| 4 | [e.g., Any photo arrays, line-ups, or identification procedures conducted] | s61 CPA 2011 | Identification reliability, procedure compliance (Casey guidelines) | High |

### E. Withheld Material (s63 CPA 2011)

| # | Matter | Action Required |
|---|--------|----------------|
| 1 | [e.g., Material withheld on public interest grounds — request s63 reasons and court review] | Crown to provide s63 notice; defence reserves right to seek court review |

### F. Third-Party Material

| # | Item Requested | Held By | Legal Basis | Action |
|---|---------------|---------|-------------|--------|
| 1 | [e.g., Medical records of complainant] | [DHB/Practice name] | s61 CPA 2011 (relevant material); s74(2) (medical reports) | Defence to obtain consent/release; Crown to facilitate if held |
| 2 | [e.g., CYFS/Oranga Tamariki records] | Oranga Tamariki | s61 CPA 2011 | Third-party disclosure application if Crown does not hold |
| 3 | [e.g., ACC records] | ACC | Privacy Act 2020 + relevance | Consent-based request or third-party production order |

---

## Draft Request Letter

[To: [Prosecutor name and court]
From: [Defence counsel]
Date: [Date]
Re: [Defendant name] — [Court file number] — Further Disclosure Request

Dear [Prosecutor],

I act for [defendant] who is charged with [charges].

Pursuant to sections 60, 61, and 62 of the Criminal Procedure Act 2011, I request disclosure of the following material which appears to be relevant to these proceedings and which I understand the Crown has or controls.

[Insert numbered requests from above]

To the extent that any of this material is withheld under section 63, please provide written reasons as required by that section.

This request is made without prejudice to any application for further or more specific disclosure as the defence case develops.

Yours faithfully,
[Counsel]]
```

---

## Template 5: Accused Options & Next Steps

```
# OPTIONS AVAILABLE TO THE ACCUSED

## Overview
This section outlines the strategic options available to [accused name] at this stage of proceedings, following disclosure review. Each option is assessed against the three analytical perspectives.

---

## Option 1: Plead Not Guilty — Proceed to Trial

### Requirements
- Enter not guilty plea at case review or first appearance
- Elect jury trial if Category 3; automatic if Category 4

### Assessment by Perspective
| Perspective | Assessment | Confidence |
|-------------|-----------|------------|
| Defence | [Assessment of trial prospects, strengths, risks] | |
| Crown | [Assessment of how Crown will run case, perceived strengths] | |
| Judicial | [Assessment of likely bail position, trial length, conviction likelihood] | |

### Pros
- [e.g., Crown case has identifiable weaknesses]
- [e.g., Strong defence evidence available]
- [e.g., Significant exclusion applications likely to succeed]

### Cons
- [e.g., If convicted, may face more serious sentence than early plea]
- [e.g., Trial stress and cost]
- [e.g., Crown case may strengthen with further disclosure]

### Key Tactical Considerations
- [Exclusion applications to file]
- [Witnesses to secure]
- [Evidence to preserve]

---

## Option 2: Plead Guilty (Early) — Seek Sentence Discount

### Requirements
- Plead guilty at first reasonable opportunity
- Maximum 25% sentence discount available (per s9C(2)(a) Sentencing Act 2002 as amended)

### Assessment by Perspective
| Perspective | Assessment | Confidence |
|-------------|-----------|------------|
| Defence | [Likely sentencing range, mitigating factors] | |
| Crown | [Crown sentencing submission likely range] | |
| Judicial | [Expected sentencing outcome, relevant guidelines] | |

### Pros
- [Maximum sentence discount: 25% at earliest stage]
- [Avoids trial stress and uncertainty]
- [Demonstrates remorse (mitigating factor)]

### Cons
- [Criminal conviction recorded]
- [May still receive custodial sentence]
- [Forecloses possibility of acquittal]

### Expected Sentencing Range (if applicable)
- **Starting point**: [Range based on offence and authority]
- **Aggravating factors**: [List]
- **Mitigating factors**: [List]
- **Likely outcome**: [Estimated range after discount]

---

## Option 3: Case Review — Seek Withdrawal or Downgrade

### Requirements
- Participate in case review conference (CPA 2011 Part 3)
- Present evidential or legal submissions on charge adequacy

### Grounds for Application
| Ground | Basis | Likelihood | Evidence Required |
|--------|-------|------------|-------------------|
| Evidential insufficiency | Crown cannot prove element [X] | [Assessment] | [What defence must show] |
| Mischarge | Wrong section charged; should be lesser/different offence | [Assessment] | [Legal argument + facts] |
| Duplicity | One charge covers multiple separate acts | [Assessment] | [Factual analysis] |
| Alternative charge more appropriate | Charge should be downgraded | [Assessment] | [Sentencing authority comparison] |

### Outcome if Successful
- Charges withdrawn entirely
- Charges downgraded to less serious offence
- Charges amended (e.g., s196 assault instead of s189 wounding)

---

## Option 4: Pre-Trial Applications

### A. Stay of Proceedings (Permanent)
| Ground | Basis | Likelihood | Evidence Required |
|--------|-------|------------|-------------------|
| Abuse of process | Prosecution conduct so unfair trial would be affront to justice | [Assessment] | [Documented breaches] |
| Unreasonable delay | s24(c) NZBORA — breach of right to trial without undue delay | [Assessment] | [Timeline analysis from arrest] |
| Lost/destroyed evidence | Evidence favourable to defence no longer available | [Assessment] | [Proof of existence, proof of loss, proof of prejudice] |

### B. Exclusion of Evidence Applications
| Evidence | Ground | Statutory Basis | Likelihood | Key Authority |
|----------|--------|----------------|------------|---------------|
| [e.g., Accused interview] | Unfairly obtained — s23 NZBORA breach | s56 Evidence Act 2006 | [Assessment] | R v Shaheed; R v Te Kira |
| [e.g., Phone data] | Warrant invalid — lack of particularity | s56 Evidence Act 2006; s48 S&S Act | [Assessment] | R v Fraser |
| [e.g., Identification] | Unreliable identification | s8, s10 Evidence Act 2006 | [Assessment] | R v Casey; R v Harichandra |

### C. Severance Application
| Ground | Basis | Likelihood |
|--------|-------|------------|
| Prejudicial joinder | Multiple charges should be tried separately | [Assessment] |
| Inadmissible evidence in joint trial | Evidence admissible on one charge but not another | [Assessment] |

### D. Bail Variation/Applications
- Current bail status: [Remanded in custody / Bail with conditions / Electronically monitored]
- Variation sought: [If applicable]
- Likelihood: [Assessment based on flight risk, interference risk, offence seriousness]

---

## Option 5: Negotiated Resolution

### Charge Bargaining
| Discussion Point | Defence Position | Crown Position Likely | Outcome |
|-----------------|-----------------|----------------------|---------|
| [e.g., Withdraw most serious charge] | [Position] | [Likely response] | [Potential outcome] |
| [e.g., Substitute lesser offence] | [Position] | [Likely response] | [Potential outcome] |
| [e.g., Agreed facts] | [Position] | [Likely response] | [Potential outcome] |

### Sentence Indication
- Application for sentence indication under s62 CPA 2011
- If indication given and accepted: 25% discount + certainty
- If indication refused or not accepted: no prejudice, proceed to trial

### Restorative Justice
- Eligibility for restorative justice referral (s24M-24Q CPA 2011)
- May result in reduced sentence or discharge without conviction
- Requires victim willingness

---

## Option 6: Appeals and Reviews

### Appeal Rights (if convicted)
| Route | Time Limit | Grounds | Likely Outcome |
|-------|-----------|---------|---------------|
| Appeal against conviction (District Court → High Court) | 20 working days | Error of law, unreasonable verdict, procedural unfairness | [Assessment] |
| Appeal against sentence | 20 working days | Manifestly excessive, wrong starting point, error of principle | [Assessment] |
| Second appeal (leave required) | - | Fresh evidence, miscarriage of justice | [Assessment] |

### Other Review Mechanisms
| Mechanism | Purpose | Likelihood of Success |
|-----------|---------|----------------------|
| Police Complaint (IPC/Authority) | Officer misconduct | [Assessment] |
| Privacy Commissioner | Privacy Act breach | [Assessment] |
| Judicial Review | Decision-making unlawfulness | [Assessment] |
| Compensation (s130 S&S Act) | Damages for unlawful search | [Assessment] |

---

## RECOMMENDED IMMEDIATE ACTIONS

| Priority | Action | Responsible | Deadline | Purpose |
|----------|--------|-------------|----------|---------|
| 1 | [e.g., File further disclosure request] | Defence counsel | [Date] | Obtain complete disclosure before decision |
| 2 | [e.g., Obtain client instructions on [issue]] | Defence counsel | [Date] | Informed decision-making |
| 3 | [e.g., Instruct private investigator re: [witness]] | Defence counsel | [Date] | Preserve evidence, secure defence witnesses |
| 4 | [e.g., File bail variation application] | Defence counsel | [Date] | Remove restrictive conditions |
| 5 | [e.g, Commence exclusion application drafting] | Defence counsel | [Date] | Pre-trial applications |
| 6 | [e.g, Request restorative justice assessment] | Defence counsel/Court | [Date] | Explore resolution options |

---

## DECISION MATRIX

| Factor | Not Guilty + Trial | Early Guilty | Case Review Challenge | Negotiated Resolution |
|--------|-------------------|--------------|----------------------|----------------------|
| Risk of custody | [High/Low] | [Reduced] | [N/A at this stage] | [Reduced] |
| Criminal conviction | [Avoidable] | [Certain] | [May downgrade] | [Certain] |
| Cost | [Higher] | [Lower] | [Moderate] | [Lower] |
| Stress | [Higher] | [Lower] | [Moderate] | [Lower] |
| Sentence range | [Nil if acquitted] | [25% discount] | [Depends on outcome] | [Variable] |
| Timeline | [Months/years] | [Weeks] | [Months] | [Months] |
| Control over outcome | [Low — jury decides] | [Moderate] | [Moderate] | [Higher] |

### Final Recommendation
[Integrated recommendation based on all three perspectives, with conditions and caveats]
```

---

## Integration Format

### Final Deliverable Structure

Present all five templates as a single integrated report with this structure:

```
# CRIMINAL DISCLOSURE ANALYSIS REPORT
## [Defendant Name] — [Court File Number] — [Date]

### CONFIDENTIALITY NOTICE
This report is prepared for the purposes of legal proceedings. It is subject to legal professional privilege. It does not constitute definitive legal advice. All analysis must be reviewed by qualified legal practitioners before any decisions are made.

---

## EXECUTIVE SUMMARY
[One-page summary of key findings, most significant issues, and recommended priority actions]

## 1. CHARGES REGISTER
[Template 1 content]

## 2. EVIDENCE AND SUMMARY OF FACTS ASSESSMENT
[Template 2 content]

## 3. PROCEDURAL BREACHES AND LAW ENFORCEMENT CONDUCT AUDIT
[Template 3 content]

## 4. FURTHER DISCLOSURE REQUEST
[Template 4 content]

## 5. OPTIONS AVAILABLE TO THE ACCUSED
[Template 5 content]

## APPENDICES
- A: Document index (all disclosure documents referenced)
- B: Timeline of events
- C: Witness contact matrix
- D: Legislation and case law authorities cited
- E: Glossary of terms

---

### SYSTEM CONFIDENCE ASSESSMENT
| Section | Confidence | Reason |
|---------|-----------|--------|
| Charges Register | [High/Medium/Low] | [Reason] |
| Evidence Assessment | [High/Medium/Low] | [Based on completeness of disclosure] |
| Procedural Breaches | [High/Medium/Low] | [Based on documents available] |
| Further Disclosure | [High/Medium/Low] | [Known gaps] |
| Options Assessment | [High/Medium/Low] | [Perspectives agreement/disagreement] |

**Overall**: This analysis is based on disclosure provided to [date]. Findings may change if further disclosure reveals additional material. All findings must be verified by qualified practitioners.
```
