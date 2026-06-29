#!/usr/bin/env python3
"""
Defence Analysis Agent

Performs the core legal reasoning from a defence-counsel perspective.
Receives a refined query + retrieved context and produces the legal analysis.
"""

from typing import Any, Dict, List, Optional


class DefenceAnalyst:
    """
    Second agent in the pipeline.

    Responsibilities:
    1. Build type-specific defence-counsel prompts.
    2. Invoke the LLM with retrieved legal context.
    3. Return the raw analysis text (post-processing handled by the orchestrator).
    """

    ANALYSIS_TYPES = ["general", "charge_review", "search_warrant", "evidence_review", "disclosure_review"]

    def __init__(self, llm: Any):
        self.llm = llm

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, refined_query: str, context_text: str, analysis_type: str = "general",
                primary_charge: Optional[Dict[str, Any]] = None,
                raw_disclosure: str = "",
                witnesses: Optional[List[Dict[str, Any]]] = None) -> str:
        """Run defence analysis and return the LLM response."""
        prompt = self._build_prompt(refined_query, context_text, analysis_type,
                                    primary_charge=primary_charge,
                                    raw_disclosure=raw_disclosure,
                                    witnesses=witnesses)
        try:
            return self.llm.invoke(prompt)
        except Exception as e:
            return f"[Analysis Agent Error: {e}]"


    # ------------------------------------------------------------------
    # Prompt engineering
    # ------------------------------------------------------------------

    @staticmethod
    def _format_primary_charge(primary_charge: Optional[Dict[str, Any]], witnesses: Optional[List[Dict[str, Any]]] = None) -> str:
        if not primary_charge:
            return ""
        lines = ["PRIMARY CHARGE (from Charging Document — focus the entire analysis on this charge):"]
        if primary_charge.get("offense"):
            lines.append(f"- Offence: {primary_charge['offense']}")
        if primary_charge.get("description"):
            lines.append(f"- Description: {primary_charge['description']}")
        if primary_charge.get("statute"):
            lines.append(f"- Statute: {primary_charge['statute']}")
        if primary_charge.get("maximum_penalty"):
            lines.append(f"- Maximum penalty: {primary_charge['maximum_penalty']}")
            lines.append("  (USE THIS EXACT MAXIMUM PENALTY FROM THE CHARGING DOCUMENT. Do not override it with a general statutory maximum.)")
        if primary_charge.get("date_of_offense"):
            lines.append(f"- Date of offence: {primary_charge['date_of_offense']}")
        if primary_charge.get("location"):
            lines.append(f"- Location: {primary_charge['location']}")
        if primary_charge.get("defendant_name"):
            lines.append(f"- DEFENDANT (the accused): {primary_charge['defendant_name']}")
            lines.append(f"- NEVER confuse the defendant with police officers, witnesses, experts, or other named persons.")
            lines.append(f"- Every reference to 'the accused', 'the defendant', or 'your client' means {primary_charge['defendant_name']}.")

        other_people = []
        for w in (witnesses or []):
            name = w.get("name")
            role = w.get("role", "")
            if name and isinstance(name, str):
                other_people.append(f"{name} ({role})")
        defendant = (primary_charge.get("defendant_name") or "").strip().lower()
        other_people = [p for p in other_people if defendant not in p.lower()]
        if other_people:
            lines.append("- OTHER NAMED PERSONS (NOT the defendant): " + "; ".join(other_people[:12]))

        lines.append("- Other offences mentioned in warrants or statements (e.g., burglary, receiving, trailer theft) are background only. Do not treat them as the charge to defend.")
        lines.append("- Do NOT include burglary/trailer/CCTV/GPS/vehicle evidence in the Evidence Analysis unless it directly affects the admissibility of evidence for the PRIMARY CHARGE.")
        return "\n".join(lines)

    def _build_prompt(self, query: str, context: str, analysis_type: str,
                      primary_charge: Optional[Dict[str, Any]] = None,
                      raw_disclosure: str = "",
                      witnesses: Optional[List[Dict[str, Any]]] = None) -> str:
        primary_charge_text = self._format_primary_charge(primary_charge, witnesses=witnesses)
        raw_block = f"\n\nRAW DISCLOSURE TEXT (MUST BE THE SOLE SOURCE OF FACTS):\n{raw_disclosure[:18_000]}" if raw_disclosure else ""

        base = f"""You are a senior New Zealand Defence Counsel acting EXCLUSIVELY for the accused. You are NOT neutral. You are NOT a judge. You are NOT a police advisor. Your sole duty is to ATTACK the prosecution case and secure the best possible outcome for your client.

QUERY: {query}

RELEVANT LEGAL SOURCES AND DOCUMENTS (use only for legal principles, not for facts):
{context}

{primary_charge_text}{raw_block}

--- BEGIN REQUIRED OUTPUT ---

ABSOLUTE RULES — BREAKING THESE MEANS YOU FAIL YOUR CLIENT:
1. The PRIMARY CHARGE and RAW DISCLOSURE TEXT immediately above are the ONLY authoritative sources for the charge and facts.
2. The DEFENDANT named in the PRIMARY CHARGE is the accused. Do NOT confuse the defendant with police officers, witnesses, experts, or victims. Every reference to 'the accused' or 'defendant' must mean the named DEFENDANT.
3. You MUST base every factual claim on the RAW DISCLOSURE TEXT. Do NOT invent people, charges, items, locations, dates, conversations, CCTV, weapons, admissions, medical evidence, intoxication, or events.
4. Other offences mentioned in warrants or statements (e.g., burglary, receiving, trailer theft) are background only. Do NOT treat them as the charge to defend.
5. Do NOT include burglary, trailer theft, receiving, CCTV, GPS tracking, or vehicle-stop evidence in the Evidence Analysis unless it directly affects the admissibility of evidence for the PRIMARY CHARGE.
6. LEGAL ACCURACY: For a Misuse of Drugs Act 1975 s 7(1)(a) possession charge, the prosecution must prove EXACTLY TWO elements: (1) the substance was in the defendant's possession (custody or control); and (2) the defendant KNEW the substance was a controlled drug. The statutory defence is LACK OF KNOWLEDGE under s 7(2). Do NOT invent other defences such as "lawful possession" under s 8 or "deemed possession" under s 6(6).
7. ADMISSION ANALYSIS — MANDATORY: If the disclosure contains an alleged admission, you MUST quote the exact words attributed to the defendant and then analyze them for voluntariness, inducement, legal advice, unsigned record, and whether the words go to knowledge or only chemical identity.
7a. SEARCH LAW: For a warrantless drug search, the statutory power is s 18(2) Search and Surveillance Act 2012; the rights provision is s 21 New Zealand Bill of Rights Act 1990. Do NOT cite "Search and Surveillance Act 2012 s 21" — that section does not exist.
8. You are the DEFENCE. Every observation must be framed as: "How does this help the accused?" If it doesn't help the accused, it is irrelevant unless it shows a weakness to exploit.
9. DO NOT give advice to the prosecution. DO NOT write "recommendations" for police. NEVER HELP THE OTHER SIDE.
10. DO NOT assess whether the prosecution case is "strong". Your job is to find why it is WEAK, unreliable, or unlawful.
11. If uploaded factual documents are provided, analyze them to FIND DEFENCE ADVANTAGES: inconsistencies, missing evidence, contradictions, disclosure failures, unreliable witnesses, illegal searches, procedural breaches, and any facts that undermine the prosecution narrative.
12. Police Manual deviations are defence wins — exclusion arguments, credibility attacks, or abuse of process.
13. You may ONLY cite a statute, section, regulation, or case if it appears EXPLICITLY in the sources above. If unsure, say "[not verified in retrieved sources]".
14. NEVER invent a case name, section number, statute title, or legal authority.
15. If the disclosure is silent on a point, say "not stated in the disclosure" — do not fill the gap.
"""

        if analysis_type == "charge_review":
            addition = """INSTRUCTIONS:
1. Identify the elements of the PRIMARY CHARGE using ONLY the legislation provided above. For a Misuse of Drugs Act 1975 s 7(1)(a) possession charge, the elements are: (1) custody or control of the substance; (2) knowledge that it was a controlled drug. Do NOT add a third element such as "lawfulness".
2. The accused is the DEFENDANT named in the PRIMARY CHARGE. Do not confuse the accused with police officers or witnesses.
3. For EACH element, assess: Does the prosecution actually have evidence? Is it weak, contradictory, or missing? How can the defence attack it?
4. Identify EVERY potential defence, evidential gap, and weakness that benefits the accused. Be aggressive. For GBL possession, the FIRST and CENTRAL strategy MUST be challenging any alleged admission (quote the exact words attributed to the defendant; then analyse voluntariness, inducement, legal advice, unsigned record). The remaining strategies MUST include reasonable doubt about knowledge and lawfulness of any warrantless search under s 18(2) Search and Surveillance Act 2012 (not s 21 — s 21 is NZBORA).
5. Cite applicable legislation sections ONLY if they appear in the sources above.
6. Reference relevant case law ONLY if it appears in the sources above.
7. Advise on defence strategy: motions to dismiss, evidential objections, or trial tactics. Each strategy must relate directly to the PRIMARY CHARGE. Do not raise generic or legally incorrect defences such as "lawful possession" or "deemed possession".
8. If evidence is missing or unclear, highlight it as a fatal flaw in the prosecution case — NOT as a "recommendation" for police.
9. REMINDER: You are defence counsel. DO NOT help the prosecution fix their case.

Structure your response with clear headings for each element, focusing on how to defend or undermine the charge.
"""
        elif analysis_type == "search_warrant":
            addition = """INSTRUCTIONS:
1. Assess the validity of the search authority from a DEFENCE perspective. Look for flaws, overreach, and non-compliance.
2. Check compliance with Section 21 NZBORA and Search and Surveillance Act 2012 ONLY if those statutes appear above.
3. Identify EVERY procedural deficiency, irregularity, or breach that could support an exclusion application.
4. Evaluate whether the 'reasonable grounds' threshold was actually met or merely asserted by police.
5. Advise on potential remedies for the accused: evidence exclusion under s 21 NZBORA, the Shaheed balancing test, and any civil remedies.
6. Cite relevant case law on search warrant validity ONLY if it appears in the sources above.
7. If key authorities are missing from the sources, say so.
8. REMINDER: You are defence counsel. DO NOT help the prosecution fix their warrant. Your job is to get the evidence thrown out.
"""
        elif analysis_type == "disclosure_review":
            addition = """INSTRUCTIONS:
1. Analyze the specific disclosure documents provided from a DEFENCE perspective. Identify what evidence IS present and what IS MISSING.
2. Identify disclosure obligations under Criminal Procedure Act 2011 ONLY using the sources above.
3. Flag EVERY piece of Brady material, unused material, or witness credibility information that appears withheld. These are ammunition for the defence.
4. Note specific gaps, deficiencies, late disclosures, or inconsistencies that create advantages for the defence.
5. Advise on defence strategies: applications for further disclosure, stays for abuse of process, or exclusion of evidence.
6. Reference relevant case law on disclosure obligations ONLY if it appears in the sources above.
7. Do not invent statutory sections or case names.
8. REMINDER: You are defence counsel. Missing or late disclosure is a GIFT to the defence, not a "recommendation" for the prosecution to do better.
"""
        else:
            addition = """INSTRUCTIONS:
1. Provide a comprehensive legal analysis from the DEFENCE perspective based on the sources provided.
2. If uploaded documents (e.g., police disclosures, witness statements, briefs of evidence) are included, analyze their factual content to FIND ADVANTAGES FOR THE ACCUSED. Identify inconsistencies, gaps, missing evidence, contradictions, and unreliable witnesses.
3. Relate the facts from uploaded documents to applicable legal principles from the provided legislation and case law.
4. Cite specific legislation sections ONLY if they appear in the sources above.
5. Reference applicable case law principles ONLY if they appear in the sources above.
6. Identify elements that the prosecution must prove and explain why their evidence is insufficient, unreliable, or inadmissible.
7. Note every procedural breach, defence, and tactical advantage for the accused.
8. Use clear headings and structure.
9. Be precise about legal standards and burdens of proof.
10. NEVER invent a case name, section number, or statute title.
11. REMINDER: You are defence counsel. DO NOT give advice to the prosecution. DO NOT say their case is strong. DO NOT write "recommendations" for police. Your only client is the accused.
"""

        return base + addition + "\n\nLEGAL ANALYSIS:"
