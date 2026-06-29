"""Quick diagnostic for element 1 correction."""
from core.agent_swarm import AgentSwarm
import re

swarm = AgentSwarm.__new__(AgentSwarm)

text = """1. The defendant had custody or control of the substance.

CCTV footage shows an individual entering TechHub Electronics.
"""

offense_lower = "burglary"
expected = swarm._expected_element_1(offense_lower)
first_line = next((l for l in text.splitlines() if l.strip()), "")
print("first_line:", repr(first_line))
print("expected:", expected)
print("matches:", swarm._element_heading_matches_offense(first_line, offense_lower))

if first_line and not swarm._element_heading_matches_offense(first_line, offense_lower):
    text = re.sub(
        r"^\s*\d+\.\s+.*$",
        f"1. {expected}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
print("RESULT:")
print(text)
