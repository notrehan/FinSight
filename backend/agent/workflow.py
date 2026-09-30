"""
Agent Workflow runner for FinSight AI.
Executes the deterministic stateful pipeline matching the LangGraph architectural pattern.
"""
from schemas.contracts import AgentState, AskResponse
from .nodes import AgentNodes

class FinSightWorkflow:
    @staticmethod
    def run(state: AgentState) -> AskResponse:
        # Step 1: Safety Pre-check
        state = AgentNodes.safety_precheck_node(state)

        # Step 2: Intent classification & entity disambiguation
        state = AgentNodes.intent_node(state)

        # A strict real-time request cannot be fulfilled by the historical
        # observations in this project. Return this explicitly before any tool
        # can accidentally present an old close as a live quote.
        if getattr(state, "as_of_preference", "latest_available") == "strict_realtime":
            from schemas.contracts import AnswerDraft
            state.draft = AnswerDraft(
                answer_text="Strict real-time data is unavailable. I can provide the latest available historical exchange observation instead.",
                citations=[],
                numeric_claims=[],
                limitations=["This service currently reads stored exchange observations and does not provide a live market-data feed."],
                safety_label="clarification"
            )
        
        # Skip retrieval and synthesis when an earlier node has already produced
        # a clarification/refusal (including missing entity handling).
        if state.draft is not None:
            state = AgentNodes.validation_node(state)
            state = AgentNodes.persistence_node(state)
            return state.final_response

        # Step 3: Tool Execution (Price, Fundamentals, RAG, Announcements, Calculator)
        state = AgentNodes.tool_execution_node(state)

        # Step 4: Evidence-grounded synthesis
        state = AgentNodes.synthesis_node(state)

        # Step 5: Pydantic validation & numeric provenance verification
        state = AgentNodes.validation_node(state)

        # Step 6: Session and trace persistence in MySQL/DB
        state = AgentNodes.persistence_node(state)

        return state.final_response
