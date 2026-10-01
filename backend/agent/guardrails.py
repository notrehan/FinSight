"""
Fintech safety guardrails for FinSight AI.
Enforces hard boundaries:
- 100% refusal on buy/sell/hold, price forecasts, or suitability queries.
- Injection defense (untrusted instructions).
- Ambiguous inquiry handling.
"""
import re
from typing import Tuple, Optional

ADVICE_PATTERNS = [
    r"\bshould\s+i\s+(buy|sell|hold|invest|trade)\b",
    r"\bshould\s+we\s+(buy|sell|hold|invest)\b",
    r"\b(buy|sell|hold)\s+recommendation\b",
    r"\btarget\s+price\b",
    r"\bwhere\s+will\s+.*(be\s+next\s+week|tomorrow|reach|hit)\b",
    r"\bprice\s+(target|prediction|forecast|forecasts)\b",
    r"\bwill\s+it\s+(go\s+up|fall|rise|crash|rally|explode|skyrocket)\b",
    r"\b(is\s+it\s+a\s+good\s+time\s+to\s+buy|is\s+it\s+worth\s+buying)\b",
    r"\b(best\s+stock\s+to\s+buy|multibagger|stock\s+tips?)\b",
    r"\bwhich\s+stock\s+should\s+i\s+buy\b",
    r"\bwhich\s+stocks?\s+to\s+buy\b",
    r"\btell\s+me\s+which\s+stocks?\s+to\s+buy\b",
    r"\bwhere\s+will\s+nifty\s+be\b",
    r"\bportfolio\s+recommendation\b",
    r"\bgive\s+me\s+investment\s+advice\b",
]

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(prior|previous)\s+instructions?",
    r"disregard\s+(all\s+)?(guidelines|rules|instructions)",
    r"you\s+are\s+now\s+an?\s+(unfiltered|financial\s+advisor|oracle)",
    r"system\s*:\s*override",
    r"developer\s+mode\s+enabled",
    r"bypass\s+safety",
]

class SafetyGuardrail:
    @staticmethod
    def check_query_safety(query: str) -> Tuple[bool, str, Optional[str]]:
        """
        Returns (is_safe, category, refusal_message)
        """
        query_clean = query.strip().lower()

        # 1. Prompt Injection check
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, query_clean, re.IGNORECASE):
                refusal = (
                    "Security Notice: System policies and evidence boundaries cannot be overridden. "
                    "FinSight AI strictly operates as a factual research assistant analyzing official historical filings and reported data."
                )
                return False, "injection", refusal

        # 2. Advice / Prediction check
        for pattern in ADVICE_PATTERNS:
            if re.search(pattern, query_clean, re.IGNORECASE):
                refusal = (
                    "I cannot provide buy, sell, or hold recommendations, target prices, or price forecasts. "
                    "FinSight AI is a factual research and explanation workspace designed to analyze historical filings and reported financial statements.\n\n"
                    "I can, however, provide:\n"
                    "- Historical price series and Bhavcopy observations with observation dates\n"
                    "- Reported revenue, net profit, and debt ratios from audited disclosures\n"
                    "- Explanations of management commentary and earnings calls with exact page citations\n"
                    "- Exchange announcements and regulatory disclosures."
                )
                return False, "advice_refusal", refusal

        # 3. Vague subjective verdicts: "Is the company good?" / "Is it good?"
        if query_clean in ["is the company good?", "is it good?", "is this good?", "should i?"]:
            clarification = (
                "FinSight AI does not provide qualitative verdicts or subjective ratings. "
                "Which factual dimension would you like to examine? For example:\n"
                "- Revenue and profit growth trend over recent fiscal years\n"
                "- Operating and net profit margin progression\n"
                "- Total debt and debt-to-equity ratio\n"
                "- Recent corporate disclosures and exchange filings."
            )
            return False, "clarification", clarification

        return True, "pass", None
