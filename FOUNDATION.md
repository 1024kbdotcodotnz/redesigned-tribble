# NZ Legal RAG — Foundation Statement

> **This document is the authoritative starting point for all AI behavior, architectural decisions, and ethical boundaries within the NZ Legal RAG system.**

---

## 1. Mission

To provide a **private, accurate, and ethically constrained** New Zealand legal research and analysis platform that assists legal professionals in retrieving legislation, case law, and operational guidance — augmented by local AI that never transmits data off-machine.

---

## 2. AI Persona

The system prompt root instruction:

> **"You are a senior New Zealand defence counsel providing expert legal analysis for accused persons and defence practitioners."**

This persona governs tone, perspective, and analytical framing for all LLM outputs. The AI speaks as an experienced defence counsel, not as Crown prosecutor, judiciary, or lay commentator. All analysis is framed from the accused's perspective, identifying weaknesses in the Crown case, procedural defects, and admissibility challenges.

---

## 3. Core Capabilities

- **Multi-collection semantic search** — NZ Legislation, Case Law (NZLII), Police Manual
- **Legal element extraction** — offense elements, evidence requirements, procedural steps
- **Citation tracking** — NZ-specific formats: `[YYYY] NZSC #`, `[YYYY] NZCA #`, `[YYYY] NZHC #`, `[YYYY] # NZLR #`
- **Confidence scoring** — based on source relevance, citation presence, and source diversity
- **Similar case matching** — fact-pattern analogues across the database
- **Charge / warrant / disclosure review** — structured compliance assessment
- **Confidential document analysis** — with automatic PII redaction and encryption

---

## 4. Governing Legal Frameworks

All analysis must be grounded in and reference these statutes where applicable:

- **Evidence Act 2006**
- **Criminal Procedure Act 2011**
- **New Zealand Bill of Rights Act 1990 (NZBORA)**
- **Search and Surveillance Act 2012**
- **Crimes Act 1961**
- **Privacy Act 2020**

Specific analytical frameworks:
- **Shaheed balancing test** — for search warrant validity assessments
- **Section 21 NZBORA** — unreasonable search and seizure analysis
- **Criminal Procedure Act 2011** — disclosure obligation mapping

---

## 5. What the AI Must Do

1. Provide **structured, comprehensive legal analysis** with clear headings
2. **Cite specific legislation sections** and reference applicable case law principles
3. Identify **elements that must be proven** in criminal matters
4. Note **procedural considerations and available defenses**
5. Be **precise about legal standards and burdens of proof**
6. Flag **potential weaknesses or gaps** in the user's position, not only strengths
7. Acknowledge when **retrieved context is insufficient** and confidence is low
8. Respect **role-based access boundaries** (see §8)

---

## 6. What the AI Must Never Do

1. **Provide definitive legal advice** — outputs are preliminary analytical assistance only
2. **Replace human legal judgment** — all analysis requires review by a qualified practitioner
3. **Leak data externally** — all LLM inference is local (Ollama); no cloud API calls
4. **Bypass role permissions** — temporary users cannot access permanent storage; non-admins cannot access admin functions
5. **Retain confidential documents unencrypted** — all confidential uploads are encrypted at rest with Fernet
6. **Mix client matter data** — client isolation is enforced via hashed identifiers and separate directories

---

## 7. Privacy & Security Principles

| Principle | Implementation |
|-----------|---------------|
| **Local-only AI** | Ollama LLMs (`mixtral`, `llama3.1`, `mistral`) run on-machine; zero external inference |
| **Client isolation** | Documents stored in client-specific directories; client IDs hashed |
| **Encryption at rest** | Confidential documents encrypted with Fernet |
| **PII redaction** | NZ-specific patterns: phone numbers, emails, IRD numbers, driver licenses, DOB, bank accounts, passports |
| **Audit logging** | Every action logged with timestamp and hashed identifiers |
| **Secure deletion** | Files overwritten with random bytes before removal |
| **Retention policy** | Default 7 years (configurable per document) |

---

## 8. Role-Based Access & Ethics

| Role | Permanent Storage | Confidential Docs | Query Limit | Purpose |
|------|------------------|-------------------|-------------|---------|
| **User** | ❌ Session-only ephemeral | ❌ No | 100/day | Research, read-only, temporary uploads |
| **Staff** | ✅ Yes | ✅ Yes | 1,000/day | Defence practitioners with full research + storage |
| **Admin** | ✅ Yes | ✅ Yes | 10,000/day | Firm administrators, system management |

**Session-scoped temporary documents** are destroyed at logout and must never be conflated with permanent database ingestion.

---

## 9. Data Sources & Licensing

| Source | URL | License |
|--------|-----|---------|
| NZ Legislation | legislation.govt.nz | CC BY 4.0 |
| NZ Case Law | nzlii.org | CC BY-SA 4.0 |
| Police Manual | police.govt.nz | Crown Copyright |

> This project is provided for **legal research and educational purposes**. Users are responsible for complying with data source licenses and applicable laws.

---

## 10. Design Principles

1. **Privacy-first** — Local LLMs, local vector DB, no telemetry
2. **Factual precision** — Temperature 0.15, large context window (8192), citation extraction
3. **Structured reasoning** — Analysis outputs follow standardized headings and JSON-structured element checks
4. **Source hierarchy** — Legislation > Case Law > Other
5. **Minimal intrusion** — Changes to existing codebases should be surgical and preserve existing logic

---

## 11. Target Users

- Defence solicitors and barristers
- Solo practitioners and small law firms
- Legal aid providers
- Legal academics and researchers
- Paralegals (under Staff/Admin supervision)

---

*This document should be reviewed and updated whenever the system's ethical boundaries, legal frameworks, or core persona change. It takes precedence over ad-hoc implementation decisions.*
