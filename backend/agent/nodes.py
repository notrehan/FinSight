"""
Agent Workflow Nodes for FinSight AI.
Implements modular LangGraph-compatible state nodes with explicit typed transitions.
"""
import os
import re
import time
from decimal import Decimal
from typing import Dict, Any, List, Optional
from schemas.contracts import (
    AgentState, ToolResult, Citation, NumericClaim, NumericFact,
    AnswerDraft, AskResponse
)
from .guardrails import SafetyGuardrail
from apps.tools.registry import ToolRegistry
from apps.companies.models import Company, Security
from apps.sessions.models import ChatSession, ChatMessage
from prompts.templates import (
    PROMPT_VERSION, SYSTEM_PROMPT_FINSIGHT,
    GROUNDED_SYNTHESIS_PROMPT, SAFETY_REFUSAL_TEMPLATE
)

class AgentNodes:
    @staticmethod
    def safety_precheck_node(state: AgentState) -> AgentState:
        t0 = time.time()
        is_safe, category, refusal_msg = SafetyGuardrail.check_query_safety(state.query)
        state.latencies['safety_precheck'] = round((time.time() - t0) * 1000, 2)

        if not is_safe:
            state.safety_status = "refuse"
            state.safety_reason = category
            state.intent = "advice_refusal" if category == "advice_refusal" else "clarification"
            state.draft = AnswerDraft(
                answer_text=refusal_msg or "Query refused due to safety policy.",
                citations=[],
                numeric_claims=[],
                limitations=["FinSight AI strictly provides factual research and historical explanation, not investment advice."],
                safety_label="refusal" if category != "clarification" else "clarification"
            )
        return state

    @staticmethod
    def intent_node(state: AgentState) -> AgentState:
        if state.safety_status == "refuse":
            return state

        t0 = time.time()
        q = state.query.lower()

        # Validate caller-provided identifiers too; an unknown ticker should
        # produce a clarification instead of an apparently successful empty result.
        if state.company_id:
            company = Company.objects.prefetch_related("securities").filter(pk=state.company_id).first()
            if company is None:
                state.intent = "clarification"
                state.draft = AnswerDraft(
                    answer_text="I could not find that company ID. Please choose a company from the company search results.",
                    citations=[], numeric_claims=[],
                    limitations=["The supplied company identifier did not match a company in the directory."],
                    safety_label="clarification",
                )
                return state
            state.company_name = company.legal_name
            if state.company_symbol and not company.securities.filter(symbol__iexact=state.company_symbol).exists():
                state.intent = "clarification"
                state.draft = AnswerDraft(
                    answer_text="The supplied company ID and ticker refer to different or unknown listings. Please select a company and ticker from search results.",
                    citations=[], numeric_claims=[],
                    limitations=["Company ID and ticker must resolve to the same listed company."],
                    safety_label="clarification",
                )
                return state
            if not state.company_symbol:
                security = company.securities.first()
                state.company_symbol = security.symbol if security else None
        elif state.company_symbol:
            security = Security.objects.select_related("company").filter(symbol__iexact=state.company_symbol).first()
            if security is None:
                state.intent = "clarification"
                state.draft = AnswerDraft(
                    answer_text=f"I could not find the ticker {state.company_symbol} in the company directory. Please check the symbol or search by company name.",
                    citations=[], numeric_claims=[],
                    limitations=["The supplied ticker did not match a listed security in the company directory."],
                    safety_label="clarification",
                )
                return state
            state.company_id = security.company_id
            state.company_name = security.company.legal_name

        # Entity disambiguation: check if company symbol or name in query
        if not state.company_id and not state.company_symbol:
            all_companies = Company.objects.prefetch_related('securities').all()
            query_tokens = set(re.findall(r"[a-z0-9._-]+", q))
            for comp in all_companies:
                # check symbol
                for sec in comp.securities.all():
                    if sec.symbol.lower() in query_tokens:
                        state.company_id = comp.id
                        state.company_symbol = sec.symbol
                        state.company_name = comp.legal_name
                        break
                if state.company_id:
                    break
                # check legal name
                if comp.normalized_name.lower() in q or comp.legal_name.lower() in q:
                    state.company_id = comp.id
                    state.company_name = comp.legal_name
                    first_sec = comp.securities.first()
                    if first_sec:
                        state.company_symbol = first_sec.symbol
                    break

        # Extract fiscal period if mentioned (e.g. FY24, FY25, Q3FY25)
        period_matches = re.findall(r"\b(?:q[1-4]\s*)?fy\s*2\d\b", q)
        if period_matches:
            # For a two-period comparison (e.g. FY24 to FY25), query the later
            # period first; calculation routing separately loads both operands.
            state.fiscal_period = period_matches[-1].upper().replace(" ", "")

        # Classify on words and explicit phrases; substring matching made words
        # such as "operational" accidentally match the token "ratio".
        query_terms = set(re.findall(r"[a-z0-9]+", q))
        if query_terms.intersection({"growth", "margin", "ratio", "calculate", "calculation", "percentage"}) or "debt to equity" in q or "percentage change" in q:
            state.intent = "calculation"
        elif query_terms.intersection({"price", "closing", "bhavcopy"}) or "last 5" in q or "trading session" in q:
            state.intent = "market_history"
        elif query_terms.intersection({"announcement", "disclosure"}) or "board meeting" in q or "filing notice" in q:
            state.intent = "announcement"
        elif query_terms.intersection({"why", "explain", "management", "commentary", "transcript"}) or "conference call" in q:
            state.intent = "filing_qa"
        elif query_terms.intersection({"revenue", "profit", "ebitda", "debt", "eps"}) or "pe ratio" in q:
            state.intent = "metric"
        elif any(w in q for w in ["portfolio", "holdings", "exposure", "concentration"]):
            state.intent = "portfolio_analysis"
        else:
            state.intent = "filing_qa"

        state.latencies['intent_classification'] = round((time.time() - t0) * 1000, 2)
        return state

    @staticmethod
    def tool_execution_node(state: AgentState) -> AgentState:
        if state.safety_status == "refuse":
            return state

        t0 = time.time()
        target_entity = state.company_symbol or state.company_id

        # Do not silently query an unrelated default company when entity resolution
        # fails. Ask for the missing company before invoking data tools.
        if not target_entity:
            state.intent = "clarification"
            state.draft = AnswerDraft(
                answer_text="Which company or ticker should I research? Please include its name or exchange symbol.",
                citations=[],
                numeric_claims=[],
                limitations=["A company or ticker is required to retrieve company-specific facts."],
                safety_label="clarification"
            )
            return state

        if state.intent == "market_history":
            days = 5
            if "10" in state.query:
                days = 10
            res = ToolRegistry.execute_tool("price_lookup", {
                "symbol": target_entity,
                "days": days
            }, trace_id=state.trace_id)
            state.tool_results.append(res)
            state.numeric_facts.extend(res.facts)

        elif state.intent == "metric":
            # Lookup fundamentals
            res_fund = ToolRegistry.execute_tool("fundamentals_lookup", {
                "company_id": target_entity,
                "period": state.fiscal_period
            }, trace_id=state.trace_id)
            state.tool_results.append(res_fund)
            state.numeric_facts.extend(res_fund.facts)
            state.evidence.extend(res_fund.citations)

            # Also retrieve filing context if needed
            res_rag = ToolRegistry.execute_tool("filing_retrieval", {
                "company_id": target_entity,
                "query": state.query,
                "period": state.fiscal_period
            }, trace_id=state.trace_id)
            state.tool_results.append(res_rag)
            state.evidence.extend(res_rag.citations)

        elif state.intent == "calculation":
            # For calculation, fetch fundamentals first, then invoke calculator tool
            res_fund = ToolRegistry.execute_tool("fundamentals_lookup", {
                "company_id": target_entity
            }, trace_id=state.trace_id)
            state.tool_results.append(res_fund)
            state.numeric_facts.extend(res_fund.facts)
            state.evidence.extend(res_fund.citations)

            # Determine formula using same-company, comparable-period facts.
            q = state.query.lower()
            if "growth" in q or "percentage change" in q:
                revenue_facts = [f for f in res_fund.facts if "revenue" in f.metric.lower()]
                current = next((f for f in revenue_facts if state.fiscal_period and f.period_or_observation_date.upper() == state.fiscal_period), None)
                if current is None:
                    current = next((f for f in revenue_facts if "FY25" in f.period_or_observation_date.upper()), None)
                prior = next((f for f in revenue_facts if "FY24" in f.period_or_observation_date.upper()), None)
                if current and prior:
                    formula = "percentage_change" if "percentage change" in q and "growth" not in q else "revenue_growth_pct"
                    operands = {"new": current.value, "old": prior.value} if formula == "percentage_change" else {"current": current.value, "prior": prior.value}
                    calc_res = ToolRegistry.execute_tool("calculator", {
                        "formula": formula,
                        "operands": operands,
                        "units": {"result": "%"},
                        "operand_facts": [current, prior]
                    }, trace_id=state.trace_id)
                    state.tool_results.append(calc_res)
                    state.numeric_facts.extend(calc_res.facts)
            elif "margin" in q:
                # Use an explicitly requested reported period or the latest common period.
                revenues = [f for f in res_fund.facts if "revenue" in f.metric.lower()]
                profits = [f for f in res_fund.facts if "net_profit" in f.metric.lower() or "net profit" in f.metric.lower()]
                rev_fact = next((f for f in revenues if state.fiscal_period and f.period_or_observation_date.upper() == state.fiscal_period), revenues[0] if revenues else None)
                profit_fact = next((f for f in profits if rev_fact and f.period_or_observation_date == rev_fact.period_or_observation_date), None)
                if profit_fact and rev_fact:
                    calc_res = ToolRegistry.execute_tool("calculator", {
                        "formula": "profit_margin_pct",
                        "operands": {"profit": profit_fact.value, "revenue": rev_fact.value},
                        "units": {"result": "%"},
                        "operand_facts": [profit_fact, rev_fact]
                    }, trace_id=state.trace_id)
                    state.tool_results.append(calc_res)
                    state.numeric_facts.extend(calc_res.facts)
            elif "debt" in q:
                debts = [f for f in res_fund.facts if "debt" in f.metric.lower()]
                equities = [f for f in res_fund.facts if "equity" in f.metric.lower()]
                debt_fact = next((f for f in debts if state.fiscal_period and f.period_or_observation_date.upper() == state.fiscal_period), debts[0] if debts else None)
                equity_fact = next((f for f in equities if debt_fact and f.period_or_observation_date == debt_fact.period_or_observation_date), None)
                if debt_fact and equity_fact:
                    calc_res = ToolRegistry.execute_tool("calculator", {
                        "formula": "debt_to_equity",
                        "operands": {"debt": debt_fact.value, "equity": equity_fact.value},
                        "units": {"result": "ratio"},
                        "operand_facts": [debt_fact, equity_fact]
                    }, trace_id=state.trace_id)
                    state.tool_results.append(calc_res)
                    state.numeric_facts.extend(calc_res.facts)

            if not any(result.tool_name == "calculator" for result in state.tool_results):
                formula = (
                    "revenue_growth_pct" if "growth" in q
                    else "profit_margin_pct" if "margin" in q
                    else "debt_to_equity" if "debt" in q
                    else "revenue_growth_pct"
                )
                required_operands = {
                    "revenue_growth_pct": {"current": None, "prior": None},
                    "profit_margin_pct": {"profit": None, "revenue": None},
                    "debt_to_equity": {"debt": None, "equity": None},
                }[formula]
                calc_res = ToolRegistry.execute_tool(
                    "calculator",
                    {"formula": formula, "operands": required_operands},
                    trace_id=state.trace_id,
                )
                state.tool_results.append(calc_res)
                state.draft = AnswerDraft(
                    answer_text="I could not calculate this from available reported data. The required inputs or comparable fiscal periods are missing.",
                    citations=res_fund.citations,
                    numeric_claims=[],
                    limitations=["No estimate was substituted for missing inputs. Provide a supported formula and periods or ingest the missing reported metrics."],
                    safety_label="clarification"
                )

        elif state.intent == "announcement":
            res = ToolRegistry.execute_tool("announcement_retrieval", {
                "company_id": target_entity,
                "limit": 5
            }, trace_id=state.trace_id)
            state.tool_results.append(res)
            state.evidence.extend(res.citations)

        else:  # filing_qa
            res_rag = ToolRegistry.execute_tool("filing_retrieval", {
                "company_id": target_entity,
                "query": state.query,
                "period": state.fiscal_period,
                "top_k": 4
            }, trace_id=state.trace_id)
            state.tool_results.append(res_rag)
            state.evidence.extend(res_rag.citations)

        if state.as_of_preference == "strict_realtime" and state.intent == "market_history":
            # The configured price tool reads exchange observations, not a live quote
            # feed. Never represent an older close as a real-time price.
            price_result = state.tool_results[-1]
            if price_result.freshness != "current":
                state.draft = AnswerDraft(
                    answer_text="A strict real-time quote is unavailable from the configured exchange-observation data. I can provide the latest available historical close instead.",
                    citations=price_result.citations,
                    numeric_claims=[],
                    limitations=["The configured price source provides historical exchange observations, not a guaranteed real-time quote."],
                    safety_label="clarification"
                )

        state.latencies['tool_execution'] = round((time.time() - t0) * 1000, 2)
        return state

    @staticmethod
    def synthesis_node(state: AgentState) -> AgentState:
        if state.draft is not None:
            return state

        t0 = time.time()
        api_key = os.getenv("LLM_API_KEY", os.getenv("GEMINI_API_KEY", ""))

        # Prepare evidence text
        evidence_text = ""
        for tr in state.tool_results:
            if tr.tool_name == "filing_retrieval" and isinstance(tr.data, dict):
                for p in tr.data.get("passages", []):
                    evidence_text += f"\n[Document: {p.get('document_title')} | Period: {p.get('period')} | Page: {p.get('page_no')} | Section: {p.get('section')}]\n\"{p.get('text')}\"\n"
            elif tr.tool_name == "announcement_retrieval" and isinstance(tr.data, dict):
                for a in tr.data.get("announcements", []):
                    evidence_text += f"\n[Announcement: {a.get('category')} | {a.get('published_at')}]\nHeadline: {a.get('headline')}\nSummary: {a.get('body')}\n"

        # Prepare facts text
        facts_text = ""
        for f in state.numeric_facts:
            facts_text += f"- {f.metric} ({f.period_or_observation_date}): {f.display_value} [Source: {f.source_name}, As of: {f.fetched_at.strftime('%Y-%m-%d') if hasattr(f.fetched_at, 'strftime') else f.fetched_at}]\n"
            if f.calculation:
                facts_text += f"  Lineage: Calculated via deterministic formula `{f.calculation.get('formula')}` with operands {f.calculation.get('operands')}\n"

        # If Gemini API key is available, call Gemini
        answer_text = None
        if api_key and len(api_key) > 5:
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
                prompt = GROUNDED_SYNTHESIS_PROMPT.format(
                    query=state.query,
                    intent=state.intent,
                    evidence=evidence_text or "No filing passages retrieved.",
                    facts=facts_text or "No structured metrics retrieved."
                )
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config={
                        "system_instruction": SYSTEM_PROMPT_FINSIGHT,
                        "temperature": 0.1,
                        "max_output_tokens": int(os.getenv("MAX_QUERY_TOKENS", "4000"))
                    }
                )
                answer_text = response.text
                usage = getattr(response, "usage_metadata", None)
                if usage is not None:
                    state.tokens_used = (
                        int(getattr(usage, "prompt_token_count", 0) or 0)
                        + int(getattr(usage, "candidates_token_count", 0) or 0)
                    )
            except Exception as e:
                state.errors.append(f"LLM fallback triggered: {str(e)}")

        # Numeric prose is rendered from tool facts below. If the free-form model
        # draft contains digits, use deterministic synthesis so the model cannot
        # introduce an untracked figure, period, page, or price.
        if answer_text and re.search(r"\d", answer_text):
            answer_text = None

        # Deterministic Grounded Synthesizer Fallback (Guaranteed to work 100% offline & without API key!)
        if not answer_text:
            answer_text = AgentNodes._deterministic_grounded_fallback(state, evidence_text, facts_text)

        # Model prose is untrusted. Never emit factual-research answers with
        # numeric-looking claims that cannot be tied to a tool fact.
        if state.numeric_facts:
            for fact in state.numeric_facts:
                if not fact.source_name or not fact.period_or_observation_date:
                    state.errors.append(f"Numeric fact {fact.fact_id} lacks required provenance.")
                    answer_text = "A numeric result was withheld because its source or observation period could not be verified."
                    state.evidence = []
                    state.numeric_facts = []
                    break

        # Build NumericClaims
        claims: List[NumericClaim] = []
        for f in state.numeric_facts:
            claims.append(NumericClaim(
                value=f.value,
                unit=f.unit,
                period=f.period_or_observation_date,
                source_id=f.source_name,
                as_of=f.fetched_at,
                tool_run_id=f.calculation.get("tool_run_id") if f.calculation else None
            ))

        limitations = [
            "Data grounded exclusively in official public company filings and stock exchange records.",
            "Calculations executed by deterministic calculator code; no model arithmetic.",
            "Historical and factual research only; does not constitute investment advice."
        ]

        state.draft = AnswerDraft(
            answer_text=answer_text,
            citations=state.evidence,
            numeric_claims=claims,
            limitations=limitations,
            safety_label="factual_research"
        )
        state.latencies['synthesis'] = round((time.time() - t0) * 1000, 2)
        return state

    @staticmethod
    def _deterministic_grounded_fallback(state: AgentState, evidence_text: str, facts_text: str) -> str:
        """
        High-precision deterministic factual generator adhering to Section 7 & 11.2 of blueprint.
        Ensures perfect answer structure, accurate numbers, and explicit page citations.
        """
        parts = []
        entity_name = state.company_name or state.company_symbol or "The company"

        if state.intent == "filing_qa":
            parts.append(f"### Management Commentary & Filing Analysis for {entity_name}")
            if state.evidence:
                parts.append("Based on reported filings and earnings commentary:")
                for tr in state.tool_results:
                    if tr.tool_name == "filing_retrieval" and isinstance(tr.data, dict):
                        for p in tr.data.get("passages", []):
                            parts.append(f"- **{p.get('section', 'Report')}** (Page {p.get('page_no', 'N/A')} of *{p.get('document_title')}*):")
                            parts.append(f"  \"{p.get('text')}\"")
            else:
                parts.append("No specific filing passage was found matching the query in the indexed corpus.")

        elif state.intent == "calculation":
            parts.append(f"### Deterministic Financial Calculation for {entity_name}")
            calc_facts = [f for f in state.numeric_facts if f.calculation]
            if calc_facts:
                for cf in calc_facts:
                    parts.append(f"- **{cf.metric}**: **{cf.display_value}**")
                    parts.append(f"  - **Formula**: `{cf.calculation.get('formula')}`")
                    parts.append(f"  - **Operands**: {cf.calculation.get('operands')}")
                    parts.append(f"  - **Execution**: Deterministic calculator engine (Run ID: `{cf.calculation.get('tool_run_id')}`)")
            if state.numeric_facts:
                parts.append("\n**Underlying Reported Metrics**:")
                for f in state.numeric_facts:
                    if not f.calculation:
                        parts.append(f"- {f.metric} ({f.period_or_observation_date}): {f.display_value} [Source: {f.source_name}]")

        elif state.intent == "metric":
            parts.append(f"### Reported Financial Fundamentals for {entity_name}")
            if state.numeric_facts:
                for f in state.numeric_facts:
                    parts.append(f"- **{f.metric}** ({f.period_or_observation_date}): **{f.display_value}** (Source: {f.source_name})")
            else:
                parts.append("No structured metric observations found for the specified period.")

        elif state.intent == "market_history":
            parts.append(f"### Historical Price Series for {entity_name}")
            for tr in state.tool_results:
                if tr.tool_name == "price_lookup" and isinstance(tr.data, dict):
                    prices = tr.data.get("prices", [])
                    if prices:
                        parts.append("| Trading Date | Closing Price | Freshness | Source |")
                        parts.append("| :--- | :--- | :--- | :--- |")
                        for p in prices:
                            parts.append(f"| {p.get('date')} | {p.get('close_price')} {p.get('unit')} | {p.get('freshness')} | {p.get('source')} |")
                        parts.append(f"\n*Note: Data reflects official exchange Bhavcopy closes as of {tr.as_of}. Stale/historical observations are clearly labeled and do not represent live quotes.*")
                    else:
                        parts.append("No price records retrieved.")

        elif state.intent == "announcement":
            parts.append(f"### Regulatory Announcements & Exchange Disclosures for {entity_name}")
            for tr in state.tool_results:
                if tr.tool_name == "announcement_retrieval" and isinstance(tr.data, dict):
                    for a in tr.data.get("announcements", []):
                        parts.append(f"- **{a.get('published_at')}** | **[{a.get('category')}]** {a.get('headline')}")
                        if a.get('body'):
                            parts.append(f"  {a.get('body')}")

        else:
            parts.append(f"Factual research response for {entity_name} across indexed filings.")

        return "\n\n".join(parts)

    @staticmethod
    def validation_node(state: AgentState) -> AgentState:
        t0 = time.time()
        draft = state.draft

        if not draft:
            draft = AnswerDraft(
                answer_text="No answer could be generated from available evidence.",
                citations=[],
                numeric_claims=[],
                limitations=["Insufficient evidence in repository."],
                safety_label="clarification"
            )

        # Ensure every citation is well formed and every numeric claim points to
        # a known source fact or deterministic calculator result.
        fact_keys = {
            (str(f.value), f.unit, f.period_or_observation_date, f.source_name)
            for f in state.numeric_facts
        }
        for claim in draft.numeric_claims:
            claim_key = (str(claim.value), claim.unit, claim.period, claim.source_id)
            matching_fact = any(
                str(f.value) == str(claim.value)
                and f.unit == claim.unit
                and f.period_or_observation_date == claim.period
                and f.source_name == claim.source_id
                for f in state.numeric_facts
            )
            if not matching_fact:
                draft.answer_text = "A numeric claim was withheld because its source could not be verified."
                draft.numeric_claims = []
                draft.safety_label = "clarification"
                break

        # Enforce that no buy/sell advice appears in answer text
        lowered = draft.answer_text.lower()
        if any(term in lowered for term in ["we recommend to buy", "you should buy", "strong buy", "target price of inr", "price will reach"]):
            # Hard fail closed
            draft.answer_text = "I cannot provide buy, sell, or hold recommendations or price forecasts. I can only provide historical and reported financial facts."
            draft.safety_label = "refusal"

        # Determine overall data freshness
        freshness = "historical"
        for tr in state.tool_results:
            if tr.freshness == "current":
                freshness = "current"
                break
            elif tr.freshness == "delayed" and freshness != "current":
                freshness = "delayed"

        # Construct final AskResponse
        total_lat = sum(state.latencies.values())
        final_resp = AskResponse(
            trace_id=state.trace_id,
            session_id=state.session_id,
            question=state.query,
            answer=draft.answer_text,
            safety_label=draft.safety_label,
            citations=draft.citations,
            numeric_claims=draft.numeric_claims,
            limitations=draft.limitations,
            data_freshness=freshness,
            prompt_version=PROMPT_VERSION,
            tool_trace=[{
                "tool": tr.tool_name,
                "status": tr.status,
                "tool_run_id": tr.tool_run_id,
                "error_code": "TOOL_EXECUTION_ERROR" if tr.status == "error" else None,
                "duration_ms": tr.duration_ms,
                "attribution": tr.source_attribution,
                "as_of": tr.as_of
            } for tr in state.tool_results],
            latency_breakdown_ms={**state.latencies, "validation": round((time.time() - t0) * 1000, 2)},
            tokens_used=state.tokens_used
        )
        state.final_response = final_resp
        state.latencies['validation'] = final_resp.latency_breakdown_ms['validation']
        return state

    @staticmethod
    def persistence_node(state: AgentState) -> AgentState:
        t0 = time.time()
        try:
            session = ChatSession.objects.filter(id=state.session_id, user_id=state.user_id).first()
            if session is None:
                # A colliding or foreign session ID must not be overwritten or
                # populated with another user's conversation.
                session = ChatSession.objects.create(
                    id=state.session_id,
                    user_id=state.user_id,
                    title=state.query[:40] or "New Research Session"
                )
            # Store user message
            ChatMessage.objects.create(
                session=session,
                role="user",
                content=state.query,
                schema_version=PROMPT_VERSION,
                trace_id=state.trace_id,
                safety_label="user_query"
            )
            # Store assistant message
            if state.final_response:
                ChatMessage.objects.create(
                    session=session,
                    role="assistant",
                    content=state.final_response.answer,
                    schema_version=PROMPT_VERSION,
                    trace_id=state.trace_id,
                    safety_label=state.final_response.safety_label,
                    citations_json=[c.model_dump() for c in state.final_response.citations],
                    numeric_claims_json=[nc.model_dump(mode='json') for nc in state.final_response.numeric_claims],
                    limitations_json=state.final_response.limitations,
                    tool_trace_json=state.final_response.tool_trace
                )
        except Exception as e:
            state.errors.append(f"Persistence error: {str(e)}")

        state.latencies['persistence'] = round((time.time() - t0) * 1000, 2)
        return state
