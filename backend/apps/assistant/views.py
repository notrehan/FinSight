"""
API Views for FinSight AI Assistant.
Implements POST /api/v1/assistant/ask, health check, portfolio analysis, and mutual fund factsheets.
"""
import uuid
import csv
import io
import time
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, JSONParser, FormParser
from rest_framework.permissions import IsAuthenticated
from pydantic import ValidationError

from schemas.contracts import AskRequest, AskResponse, AgentState
from agent.workflow import FinSightWorkflow
from apps.tools.registry import ToolRegistry
from apps.observability.logger import StructuredLogger

class AskAssistantView(APIView):
    """
    POST /api/v1/assistant/ask
    Executes the FinSight stateful agent workflow.
    Validates request and response with Pydantic contracts.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        trace_id = request.headers.get('X-Correlation-ID', f"req_{uuid.uuid4().hex[:12]}")
        user_id = str(request.user.pk)

        try:
            req_data = request.data
            ask_req = AskRequest(**req_data)
        except (ValidationError, TypeError, ValueError) as e:
            return Response({
                "error": "Invalid request schema.",
                "details": e.errors() if isinstance(e, ValidationError) else str(e),
                "trace_id": trace_id
            }, status=status.HTTP_400_BAD_REQUEST)

        session_id = ask_req.session_id or f"sess_{uuid.uuid4().hex[:10]}"

        # Do not write into a session belonging to a different user. The
        # persistence layer will create a fresh session when this ID collides.
        from apps.sessions.models import ChatSession
        existing_session = ChatSession.objects.filter(id=session_id).first()
        if existing_session and existing_session.user_id != user_id:
            return Response({"error": "Session is unavailable.", "trace_id": trace_id}, status=status.HTTP_404_NOT_FOUND)

        # Initialize agent state
        state = AgentState(
            trace_id=trace_id,
            user_id=user_id,
            session_id=session_id,
            query=ask_req.question,
            company_id=ask_req.company_id,
            company_symbol=ask_req.symbol,
            language=ask_req.language,
            as_of_preference=ask_req.as_of_preference,
            fiscal_period=None
        )

        StructuredLogger.log_event(
            trace_id=trace_id,
            session_id=session_id,
            event_type="ask_request_received",
            node="api_gateway",
            status="started",
            metadata={"query_length": len(ask_req.question), "symbol": ask_req.symbol}
        )

        try:
            # Execute workflow
            response: AskResponse = FinSightWorkflow.run(state)
            
            StructuredLogger.log_event(
                trace_id=trace_id,
                session_id=session_id,
                event_type="ask_response_completed",
                node="api_gateway",
                status="success",
                metadata={"safety_label": response.safety_label, "citations_count": len(response.citations)}
            )

            # Return validated response schema
            return Response(response.model_dump(mode='json'), status=status.HTTP_200_OK)

        except ValidationError as e:
            StructuredLogger.log_event(
                trace_id=trace_id,
                session_id=session_id,
                event_type="ask_response_validation_failed",
                node="api_gateway",
                status="error",
                error_code="INVALID_AGENT_OUTPUT",
                metadata={"error_count": len(e.errors())}
            )
            return Response({
                "error": "A safe response could not be validated from the available evidence.",
                "trace_id": trace_id
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        except Exception as e:
            StructuredLogger.log_event(
                trace_id=trace_id,
                session_id=session_id,
                event_type="ask_execution_failed",
                node="api_gateway",
                status="error",
                error_code="INTERNAL_AGENT_ERROR",
                metadata={"error_type": type(e).__name__}
            )
            return Response({
                "error": "An error occurred while processing your request. Please check the trace ID.",
                "trace_id": trace_id
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class HealthCheckView(APIView):
    """
    GET /api/v1/health
    Liveness and readiness check. Exposes no secrets or internal stack traces.
    """
    def get(self, request):
        return Response({
            "status": "healthy",
            "service": "FinSight AI Monolith",
            "version": "1.2.0",
            "environment": "production-ready",
            "capabilities": [
                "bhavcopy_prices",
                "audited_fundamentals",
                "filing_rag",
                "deterministic_calculator",
                "bse_nse_announcements",
                "portfolio_exposure"
            ],
            "safety_enforced": True,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }, status=status.HTTP_200_OK)

class PortfolioAnalyzeView(APIView):
    """
    POST /api/v1/portfolio/analyze
    Accepts CSV upload or JSON payload containing user holdings.
    Runs deterministic sector exposure & concentration calculations.
    Strictly research & explanation only: no investment advice.
    """
    parser_classes = [MultiPartParser, JSONParser, FormParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        trace_id = request.headers.get('X-Correlation-ID', f"port_{uuid.uuid4().hex[:10]}")
        holdings_data = []

        # Check if CSV file was uploaded
        if 'file' in request.FILES:
            csv_file = request.FILES['file']
            if csv_file.size > 5 * 1024 * 1024:
                return Response({'error': 'Uploaded file exceeds 5MB size limit.'}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

            try:
                decoded_file = csv_file.read().decode('utf-8')
                io_string = io.StringIO(decoded_file)
                reader = csv.DictReader(io_string)
                for row in reader:
                    symbol = row.get('symbol') or row.get('Symbol') or row.get('Ticker') or row.get('Security')
                    shares = row.get('shares') or row.get('Shares') or row.get('Quantity') or row.get('Qty') or 0
                    price = row.get('avg_price') or row.get('Avg Price') or row.get('Buy Price') or row.get('Price') or 0
                    if symbol:
                        holdings_data.append({
                            "symbol": symbol.strip().upper(),
                            "shares": float(shares),
                            "avg_price": float(price)
                        })
            except Exception as e:
                return Response({'error': f'Malformed CSV file: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            holdings_data = request.data.get('holdings', [])

        if not holdings_data:
            return Response({'error': 'No holdings data provided. Supply a CSV file or JSON holdings list.'}, status=status.HTTP_400_BAD_REQUEST)

        # Run portfolio analyzer tool
        res = ToolRegistry.execute_tool("portfolio_analyzer", {"holdings": holdings_data}, trace_id=trace_id)
        if res.status == "error":
            return Response({
                'error': 'Portfolio data could not be analyzed. Check the numeric holdings and try again.',
                'trace_id': trace_id,
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "trace_id": trace_id,
            "analysis": res.data,
            "facts": [f.model_dump(mode='json') for f in res.facts],
            "attribution": res.source_attribution
        }, status=status.HTTP_200_OK)

class MutualFundsFactsheetView(APIView):
    """
    GET /api/v1/funds
    Exposes the factsheet route; remains empty until a verified AMFI feed is configured.
    """
    def get(self, request):
        return Response({
            "count": 0,
            "status": "unavailable",
            "source": "Association of Mutual Funds in India (AMFI)",
            "message": "No verified AMFI factsheet data is configured. No NAV, return, AUM, or expense-ratio values are being shown.",
            "disclaimer": "When verified data is available, comparisons will be factual only and will not rank or recommend funds.",
            "funds": []
        })
