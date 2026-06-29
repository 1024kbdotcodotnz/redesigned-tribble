#!/usr/bin/env python3
"""
Test script for NZ Legal RAG multi-agent pipeline.
Can run standalone without the full API server.
"""

import sys
import json
import time

# Add project root to path
sys.path.insert(0, "/workspace/nz_legal_rag")
sys.path.insert(0, "C:/Users/megab/aegis")

# ─── Disclosure fixtures for regression testing ─────────────────────────────

GBL_DISCLOSURE = """POLICE v JAMES LIM

Charging Document

Name: LIM, James
Date of birth: 01 January 1990
Address: 23 Logan Road, Buckland

Offence Details
Offence description: Possession of Gamma-Butyrolactone (GBL), a Class B controlled drug
Legislative reference: Misuse of Drugs Act 1975 Section 7(1)(a) & (2)
Maximum penalty: 3 Months imprisonment, $500.00 fine
Date of offence: 15 November 2025
Offence location: 23 Logan Road, Buckland

Prosecutor details
File reference: 12345/25
Court: Auckland District Court
First appearance: 12 February 2026

Summary of Facts
On 15 November 2025 Police executed a search warrant at 23 Logan Road, Buckland. The warrant related to a stolen trailer.

At approximately 8:00am Sergeant Tod Lawrence KIRKER and Constable Taylor Ashby attended the address. Sergeant KIRKER observed a clear liquid in a plastic bottle on a bedside table in the defendant's bedroom. The bottle was next to the defendant's mobile phone and wallet. Plastic droppers were also located nearby.

Sergeant KIRKER invoked a warrantless search under s 18(2) of the Search and Surveillance Act 2012.

A white bottle containing approximately 40ml of liquid (45.2g) was seized as exhibit 11709BN. PHF Science forensic testing confirmed the liquid was Gamma-Butyrolactone (GBL), a Class B controlled drug.

The defendant was arrested at 9:15am and interviewed on DVD at 11:30am on 15 November 2025. He declined to comment.

On 6 January 2026 Constable Taylor Ashby advised the defendant of the forensic test results and offered him a formal warning in lieu of prosecution. The defendant said words to the effect that "the GBL substance was correct and that it was indeed GBL". The defendant then spoke to lawyer Mark EDGAR by telephone. After speaking to Mr Edgar, the defendant declined to sign the notebook entry recording the alleged admission.

On 10 January 2026 the defendant again declined to sign the notebook entry and was charged.
"""

BURGLARY_THEFT_DISCLOSURE = """POLICE v MICHAEL ROSS

Charging Document

Name: ROSS, Michael
Date of birth: 12 March 1988
Address: 14B View Road, Auckland

Offence Details
Offence description: Burglary
Legislative reference: Crimes Act 1961 s 231
Maximum penalty: 10 years imprisonment
Date of offence: 22 April 2026
Offence location: 88 Queen Street, Auckland

Summary of Facts
On 22 April 2026 at approximately 2:15am the defendant entered 88 Queen Street, Auckland, a commercial premises, by forcing the rear door. The defendant was captured on CCTV inside the premises for approximately six minutes.

The defendant removed a cash tin containing $420 from the office area and two bottles of spirits valued at $190 from behind the counter. The total value of property taken was $610.

Security guard Patricia Ng arrived at 2:30am and observed the defendant leaving through the rear door. She notified Police.

Constable Sarah Johnson attended at 2:47am and arrested the defendant nearby. He was found in possession of the cash tin and one of the bottles of spirits.

At Auckland Central Police Station the defendant was interviewed at 5:30am after consulting a duty solicitor for 15 minutes. He denied all allegations, claiming he found the items outside the premises.

The interview was video recorded. He was released on Police bail with conditions to reside at 14B View Road and not enter 88 Queen Street.
First appearance: 29 April 2026, Auckland District Court.
"""

def test_parser_only():
    """Test the parser agent without LLM calls."""
    from core.parser import DisclosureParser

    test_text = """POLICE v JOHN SMITH. On 15 March 2024 at 2:30pm, the defendant entered 
    Countdown supermarket, 123 Main St, Auckland. He selected two bottles of whiskey 
    valued at $190 and concealed them in a backpack. He exited without paying. 
    Security guard Michael Chen observed and notified PC Sarah Johnson who arrested 
    the defendant at 2:47pm. At Auckland Central Police Station, the defendant was 
    interviewed at 5:30pm after consulting a duty solicitor for 15 minutes. He denied 
    all allegations, claiming he intended to pay but forgot. The interview was video 
    recorded. He was charged with Theft, s234 Crimes Act 1961, and released on Police 
    bail with conditions to reside at 45A Beach Road and not enter any Countdown. 
    First appearance: 22 March 2024, Auckland District Court. Previous convictions 
    for similar offending in 2019 and 2021."""

    parser = DisclosureParser()
    parsed = parser.parse(test_text)
    result = parser.to_dict(parsed)

    print("=" * 60)
    print("PARSER TEST RESULTS")
    print("=" * 60)
    print(json.dumps(result, indent=2, default=str))
    print()

    # Assertions
    assert result["case_title"] == "POLICE v JOHN SMITH", f"Case title mismatch: {result['case_title']}"
    assert len(result["charges"]) > 0, "No charges extracted"
    assert result["charges"][0]["offense"] == "Theft", f"Offense mismatch: {result['charges'][0]['offense']}"
    assert result["procedural_history"]["interview_recorded"] == True, "Interview recording not detected"
    assert len(result["prior_convictions"]) > 0, "Prior convictions not detected"
    assert "brief_solicitor_consultation" in parsed.flags, "Flag not detected"

    print("OK: All parser assertions passed")
    return result


def test_gbl_parser():
    """Test parser extraction on a GBL possession disclosure."""
    from core.parser import DisclosureParser

    parser = DisclosureParser()
    parsed = parser.parse(GBL_DISCLOSURE)
    result = parser.to_dict(parsed)

    print("=" * 60)
    print("GBL PARSER TEST RESULTS")
    print("=" * 60)
    print(json.dumps(result, indent=2, default=str))
    print()

    pc = result.get("primary_charge") or {}
    assert pc.get("offense") == "Possession of GBL", f"Offense mismatch: {pc.get('offense')}"
    assert "Misuse of Drugs Act 1975" in (pc.get("statute") or ""), f"Statute mismatch: {pc.get('statute')}"
    assert pc.get("defendant_name") == "LIM, James", f"Defendant mismatch: {pc.get('defendant_name')}"
    assert result.get("court") == "Auckland District Court", f"Court mismatch: {result.get('court')}"

    print("OK: All GBL parser assertions passed")
    return result


def test_burglary_parser():
    """Test parser extraction on a burglary/theft disclosure."""
    from core.parser import DisclosureParser

    parser = DisclosureParser()
    parsed = parser.parse(BURGLARY_THEFT_DISCLOSURE)
    result = parser.to_dict(parsed)

    print("=" * 60)
    print("BURGLARY/THEFT PARSER TEST RESULTS")
    print("=" * 60)
    print(json.dumps(result, indent=2, default=str))
    print()

    pc = result.get("primary_charge") or {}
    assert pc.get("offense") == "Burglary", f"Offense mismatch: {pc.get('offense')}"
    assert "Crimes Act 1961" in (pc.get("statute") or ""), f"Statute mismatch: {pc.get('statute')}"
    assert pc.get("defendant_name") == "ROSS, Michael", f"Defendant mismatch: {pc.get('defendant_name')}"
    assert result.get("court") == "Auckland District Court", f"Court mismatch: {result.get('court')}"

    print("OK: All burglary/theft parser assertions passed")
    return result


def test_full_pipeline_stub():
    """Test full pipeline with stub LLM (no Ollama required)."""
    from core.agent_swarm import AgentSwarm, OllamaLLMClient

    class StubLLM(OllamaLLMClient):
        def generate(self, prompt, system="", temperature=0.2, max_tokens=4000):
            return "[Stub LLM output — real analysis requires Ollama running]"

        def generate_json(self, prompt, system="", temperature=0.1, max_tokens=4000):
            return ["theft elements New Zealand", "theft defence New Zealand"]

    test_text = "POLICE V JANE DOE. Charged with Theft s234 Crimes Act 1961."

    swarm = AgentSwarm(llm_client=StubLLM(), rag_engine=None)
    result = swarm.analyse_disclosure(test_text)

    print("=" * 60)
    print("FULL PIPELINE STUB TEST RESULTS")
    print("=" * 60)
    print(json.dumps(result, indent=2))
    print()

    # Assertions
    assert "executive_summary" in result, "Missing executive_summary"
    assert "disclaimer" in result, "Missing disclaimer"
    assert result["success"] is True, "Success flag not set"

    print("OK: All pipeline stub assertions passed")
    return result


def test_gbl_pipeline_stub():
    """Test full pipeline with GBL disclosure using a stub LLM."""
    from core.agent_swarm import AgentSwarm, OllamaLLMClient

    class StubLLM(OllamaLLMClient):
        def generate(self, prompt, system="", temperature=0.2, max_tokens=4000):
            return "[Stub LLM output — real analysis requires Ollama running]"

        def generate_json(self, prompt, system="", temperature=0.1, max_tokens=4000):
            return ["GBL possession elements New Zealand", "GBL defence New Zealand"]

    swarm = AgentSwarm(llm_client=StubLLM(), rag_engine=None)
    result = swarm.analyse_disclosure(GBL_DISCLOSURE)

    print("=" * 60)
    print("GBL FULL PIPELINE STUB RESULTS")
    print("=" * 60)
    print(json.dumps({k: v for k, v in result.items() if k not in ("raw_outputs",)}, indent=2))
    print()

    assert result.get("success") is True, "Success flag not set"
    assert result.get("executive_summary"), "Missing executive_summary"
    assert result.get("disclaimer"), "Missing disclaimer"
    title = result.get("title_block", "")
    assert "LIM" in title or "James" in title or "Possession of GBL" in title, f"Title block missing GBL case info: {title}"

    print("OK: All GBL pipeline stub assertions passed")
    return result


def test_burglary_pipeline_stub():
    """Test full pipeline with burglary disclosure using a stub LLM."""
    from core.agent_swarm import AgentSwarm, OllamaLLMClient

    class StubLLM(OllamaLLMClient):
        def generate(self, prompt, system="", temperature=0.2, max_tokens=4000):
            return "[Stub LLM output — real analysis requires Ollama running]"

        def generate_json(self, prompt, system="", temperature=0.1, max_tokens=4000):
            return ["burglary elements New Zealand", "burglary defence New Zealand"]

    swarm = AgentSwarm(llm_client=StubLLM(), rag_engine=None)
    result = swarm.analyse_disclosure(BURGLARY_THEFT_DISCLOSURE)

    print("=" * 60)
    print("BURGLARY/THEFT FULL PIPELINE STUB RESULTS")
    print("=" * 60)
    print(json.dumps({k: v for k, v in result.items() if k not in ("raw_outputs",)}, indent=2))
    print()

    assert result.get("success") is True, "Success flag not set"
    assert result.get("executive_summary"), "Missing executive_summary"
    assert result.get("disclaimer"), "Missing disclaimer"
    title = result.get("title_block", "")
    assert "ROSS" in title or "Michael" in title or "Burglary" in title, f"Title block missing burglary case info: {title}"

    print("OK: All burglary/theft pipeline stub assertions passed")
    return result


def test_full_pipeline_live():
    """Test full pipeline with live Ollama (requires Ollama running)."""
    from core.agent_swarm import AgentSwarm

    test_text = """POLICE v JOHN SMITH. On 15 March 2024 at 2:30pm, the defendant entered 
    Countdown supermarket, 123 Main St, Auckland. He selected two bottles of whiskey 
    valued at $190 and concealed them in a backpack. He exited without paying. 
    Security guard Michael Chen observed and notified PC Sarah Johnson who arrested 
    the defendant at 2:47pm. At Auckland Central Police Station, the defendant was 
    interviewed at 5:30pm after consulting a duty solicitor for 15 minutes. He denied 
    all allegations, claiming he intended to pay but forgot. The interview was video 
    recorded. He was charged with Theft, s234 Crimes Act 1961, and released on Police 
    bail with conditions to reside at 45A Beach Road and not enter any Countdown. 
    First appearance: 22 March 2024, Auckland District Court. Previous convictions 
    for similar offending in 2019 and 2021."""

    print("=" * 60)
    print("FULL PIPELINE LIVE TEST (requires Ollama)")
    print("=" * 60)
    print("This will take 2-5 minutes...")
    print()

    start = time.time()
    swarm = AgentSwarm(rag_engine=None)
    result = swarm.analyse_disclosure(test_text)
    elapsed = time.time() - start

    print(f"Completed in {elapsed:.1f}s")
    print()
    print("EXECUTIVE SUMMARY:")
    print(result.get("executive_summary", "[None]")[:500])
    print()
    print("CHARGE ANALYSIS:")
    print(result.get("charge_analysis", "[None]")[:500])
    print()
    print("DISCLAIMER:")
    print(result.get("disclaimer", "[None]"))
    print()

    print("OK: Live pipeline test completed")
    return result


if __name__ == "__main__":
    print("NZ Legal RAG — Pipeline Test Suite")
    print("=" * 60)
    print()

    # Test 1: Parser (always runs, no LLM needed)
    test_parser_only()
    print()

    # Test 2: GBL parser regression
    test_gbl_parser()
    print()

    # Test 3: Burglary parser regression
    test_burglary_parser()
    print()

    # Test 4: Full pipeline stub (no Ollama needed)
    test_full_pipeline_stub()
    print()

    # Test 5: GBL pipeline stub
    test_gbl_pipeline_stub()
    print()

    # Test 6: Burglary pipeline stub
    test_burglary_pipeline_stub()
    print()

    # Test 7: Full pipeline live (requires Ollama)
    print("Run live test? This requires Ollama with deepseek-r1:14b.")
    print("Type 'yes' to proceed, anything else to skip:")
    response = input().strip().lower()
    if response == "yes":
        test_full_pipeline_live()
    else:
        print("Skipped live test.")

    print()
    print("All tests completed.")
