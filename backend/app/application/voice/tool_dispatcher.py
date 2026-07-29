"""Tool dispatcher — routes LLM function calls to application use cases.

This is the bridge between the LLM's decision ("call the create_booking tool")
and the actual use case that executes it. The LLM never calls infrastructure
directly — it goes through use cases in the application layer.

Architecture:
    LLM (infrastructure/llm) → returns tool_call {name, arguments}
    ToolDispatcher (this file) → maps tool name → use case
    Use case (application/<domain>) → orchestrates domain entities + infra
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    """A function call requested by the LLM."""
    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    """Result returned to the LLM after tool execution."""
    tool_call_id: str
    name: str
    success: bool
    result: Any = None
    error: str | None = None


class ToolDispatcher:
    """Maps LLM tool calls to application use cases and executes them.

    Each 'tool' is a use case class from the application layer.
    The dispatcher holds a registry: tool_name → use_case_callable.

    Tools available to the LLM (see TOOL_SCHEMAS below):
        - search_faq          → answer caller questions from KB
        - check_availability   → query Google Calendar for open slots
        - create_booking       → book an appointment
        - cancel_booking       → cancel an existing booking
        - add_to_waitlist      → put caller on waitlist for a full slot
        - transfer_to_human    → escalate to a human agent
        - end_conversation     → hang up gracefully
    """

    def __init__(self):
        self._tools: dict[str, Any] = {}

    def register(self, name: str, handler):
        """Register a tool handler (usually a use case callable)."""
        self._tools[name] = handler

    def get_schemas(self) -> list[dict]:
        """Return OpenAPI/function-calling schemas for all registered tools.

        These are injected into the LLM system prompt so the model
        knows what functions it can call.
        """
        return TOOL_SCHEMAS

    async def dispatch(self, tool_call: ToolCall, session: Any, domain_profile: Any) -> ToolResult:
        """Execute a single tool call and return the result.

        Args:
            tool_call: The function call from the LLM (name + arguments).
            session: The active CallSession with accumulated state.
            domain_profile: The resolved DomainProfile for context.

        Returns:
            ToolResult with success/error and structured result data.
        """
        handler = self._tools.get(tool_call.name)
        if handler is None:
            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                success=False,
                error=f"Unknown tool: {tool_call.name}",
            )

        try:
            result = await handler(tool_call.arguments, session, domain_profile)
            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                success=True,
                result=result,
            )
        except Exception as exc:
            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                success=False,
                error=str(exc),
            )

    async def execute_tool_phase(
        self,
        tool_calls: list[ToolCall],
        session: Any,
        domain_profile: Any,
    ) -> list[ToolResult]:
        """Execute multiple tool calls in parallel and return all results.

        Used when the LLM requests 2+ tools in one turn (e.g.,
        check_availability + search_faq simultaneously).
        """
        results = []
        for tc in tool_calls:
            result = await self.dispatch(tc, session, domain_profile)
            results.append(result)
        return results


# ── Tool Schemas (provided to the LLM via prompts/system message) ───────────

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_faq",
            "description": "Search the knowledge base for FAQ answers. Use when the caller asks about hours, policies, directions, pricing, or general information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The caller's question, phrased as a search query.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check available time slots for a given resource (doctor, room, stylist, etc.) on a specific date and time window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "resource_name": {
                        "type": "string",
                        "description": "The resource to check (e.g., 'Dr. Smith', 'Suite 301'). Use the resource the caller mentioned or infer from context.",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format.",
                    },
                    "time_start": {
                        "type": "string",
                        "description": "Start of time window in HH:MM format (e.g., '09:00').",
                    },
                    "time_end": {
                        "type": "string",
                        "description": "End of time window in HH:MM format (e.g., '17:00').",
                    },
                },
                "required": ["resource_name", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_booking",
            "description": "Create a new booking/appointment. Call ONLY after check_availability confirmed the slot is free and the caller confirmed they want to book.",
            "parameters": {
                "type": "object",
                "properties": {
                    "resource_name": {
                        "type": "string",
                        "description": "The resource to book.",
                    },
                    "date": {"type": "string", "description": "Date in YYYY-MM-DD."},
                    "time": {"type": "string", "description": "Time in HH:MM format."},
                    "caller_name": {"type": "string", "description": "Caller's full name."},
                    "caller_phone": {"type": "string", "description": "Caller's phone number."},
                    "caller_email": {"type": "string", "description": "Optional email."},
                    "notes": {"type": "string", "description": "Optional booking notes."},
                },
                "required": ["resource_name", "date", "time", "caller_name", "caller_phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_booking",
            "description": "Cancel an existing booking. Verify with the caller before canceling.",
            "parameters": {
                "type": "object",
                "properties": {
                    "caller_phone": {
                        "type": "string",
                        "description": "Caller's phone number to look up their booking.",
                    },
                },
                "required": ["caller_phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_waitlist",
            "description": "Add the caller to a waitlist when no slots are available. Offer this when check_availability returns no open slots.",
            "parameters": {
                "type": "object",
                "properties": {
                    "resource_name": {"type": "string"},
                    "preferred_date": {"type": "string", "description": "YYYY-MM-DD."},
                    "preferred_window": {"type": "string", "description": "Morning/Afternoon/Evening."},
                    "caller_name": {"type": "string"},
                    "caller_phone": {"type": "string"},
                },
                "required": ["resource_name", "preferred_date", "caller_name", "caller_phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_to_human",
            "description": "Transfer the call to a human agent. Use when: the caller explicitly asks for a human, the AI cannot resolve the issue after 2 attempts, or the sentiment is frustrated/urgent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "department": {
                        "type": "string",
                        "description": "Department to route to (billing, support, front_desk, etc.). Infer from caller's need if not stated.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Brief reason for the transfer (shown to the agent).",
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["normal", "urgent"],
                        "description": "Whether this is an urgent escalation.",
                    },
                },
                "required": ["department", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "end_conversation",
            "description": "End the conversation gracefully. Use when the caller's request is resolved or they say goodbye.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Brief summary of what was accomplished to tell the caller before hanging up.",
                    },
                },
                "required": ["summary"],
            },
        },
    },
]
