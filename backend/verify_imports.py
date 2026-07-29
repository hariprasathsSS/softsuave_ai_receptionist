"""Quick import verification for Phase 1 modules."""
import sys
sys.path.insert(0, '.')

def check(module_name, description):
    try:
        exec(f"from {module_name} import *", {})
        print(f"OK: {description}")
    except Exception as e:
        print(f"FAIL {description}: {e}")

# Domain
from app.domain.entities.value_objects import DialogState, IntentResult, ConversationTurn, Sentiment
print("OK: domain/entities/value_objects.py")

# Application
from app.application.voice.dialog_state_machine import DialogStateMachine
fsm = DialogStateMachine()
print("OK: dialog_state_machine.py")

from app.application.voice.response_composer import ResponseComposer
comp = ResponseComposer()
print(f"OK: response_composer.py (greeting: '{comp.get_greeting()[:50]}...')")

from app.application.voice.tool_dispatcher import ToolDispatcher, ToolCall, ToolResult
td = ToolDispatcher()
print("OK: tool_dispatcher.py")

print("\nAll core modules load correctly!")
