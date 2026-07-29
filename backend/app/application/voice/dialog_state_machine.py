"""Dialog state machine — Phase 1 FSM with transition table.

The FSM is a pure domain-adjacent component: it depends only on
domain value objects and defines legal state transitions for the
voice conversation flow.

Hybrid architecture: The FSM provides guardrails; the LLM has
freedom within each state. The FSM prevents nonsensical transitions
(e.g., booking → goodbye without confirmation).
"""

import logging
from typing import Optional

from domain.entities.value_objects import DialogState, IntentResult


# ── Transition table ───────────────────────────────────────────────────────
# Maps (from_state, to_state) — a whitelist of legal transitions.
# Any transition not in this set is rejected and falls back to the
# current state (with an error log).

TRANSITION_MAP: dict[DialogState, set[DialogState]] = {
    # Entry
    DialogState.IDLE:        {DialogState.GREETING},
    DialogState.GREETING:    {DialogState.LISTENING, DialogState.GOODBYE},

    # Core listening → processing
    DialogState.LISTENING:   {
        DialogState.ANSWERING_FAQ, DialogState.GIVING_HOURS,
        DialogState.GIVING_LOCATION, DialogState.CHECK_AVAILABILITY,
        DialogState.COLLECT_BOOKING_RESOURCE, DialogState.VERIFY_BOOKING,
        DialogState.ESCALATE_URGENT, DialogState.GOODBYE,
        DialogState.LISTENING,  # self-loop for multi-turn
    },

    # FAQ / Info states → back to listening
    DialogState.ANSWERING_FAQ:    {DialogState.LISTENING, DialogState.GOODBYE},
    DialogState.GIVING_HOURS:     {DialogState.LISTENING, DialogState.GOODBYE},
    DialogState.GIVING_LOCATION:  {DialogState.LISTENING, DialogState.GOODBYE},

    # Booking flow
    DialogState.CHECK_AVAILABILITY:      {DialogState.PROPOSE_SLOTS, DialogState.OFFER_WAITLIST, DialogState.LISTENING},
    DialogState.PROPOSE_SLOTS:           {DialogState.COLLECT_BOOKING_NAME, DialogState.LISTENING},
    DialogState.COLLECT_BOOKING_RESOURCE:{DialogState.COLLECT_BOOKING_DATE},
    DialogState.COLLECT_BOOKING_DATE:    {DialogState.COLLECT_BOOKING_TIME},
    DialogState.COLLECT_BOOKING_TIME:    {DialogState.COLLECT_BOOKING_NAME},
    DialogState.COLLECT_BOOKING_NAME:    {DialogState.COLLECT_BOOKING_PHONE},
    DialogState.COLLECT_BOOKING_PHONE:   {DialogState.CONFIRM_BOOKING},
    DialogState.CONFIRM_BOOKING:         {DialogState.EXECUTE_BOOKING, DialogState.LISTENING},
    DialogState.EXECUTE_BOOKING:         {DialogState.LISTENING, DialogState.GOODBYE},

    # Booking management
    DialogState.VERIFY_BOOKING:          {DialogState.CONFIRM_CANCELLATION, DialogState.LISTENING},
    DialogState.CONFIRM_CANCELLATION:    {DialogState.EXECUTE_CANCELLATION, DialogState.LISTENING},
    DialogState.EXECUTE_CANCELLATION:    {DialogState.LISTENING, DialogState.GOODBYE},
    DialogState.COLLECT_RESCHEDULE_DATE: {DialogState.CHECK_AVAILABILITY},

    # Waitlist
    DialogState.OFFER_WAITLIST:          {DialogState.COLLECT_WAITLIST_INFO, DialogState.LISTENING, DialogState.GOODBYE},
    DialogState.COLLECT_WAITLIST_INFO:   {DialogState.LISTENING, DialogState.GOODBYE},

    # Transfer / Escalation
    DialogState.ESCALATE_URGENT:  {DialogState.INFORM_TRANSFER},
    DialogState.INFORM_TRANSFER:  {DialogState.EXECUTE_TRANSFER},
    DialogState.EXECUTE_TRANSFER: {DialogState.ENDED, DialogState.TRANSFER_FAILED},
    DialogState.TRANSFER_FAILED:  {DialogState.LISTENING, DialogState.GOODBYE},

    # Terminal
    DialogState.GOODBYE: {DialogState.ENDED},
    DialogState.ENDED:   set(),  # dead end
    DialogState.ERROR:   {DialogState.GOODBYE, DialogState.ENDED},
}


# States where we accept any intent (transition is determined by LLM, not FSM)
LLM_DRIVEN_STATES = {
    DialogState.LISTENING,
    DialogState.GREETING,
}


class DialogStateMachine:
    """Finite-state machine for the voice conversation dialog.

    The FSM is stateless; call session state is held in the
    CallSession entity, not here.

    Two modes:
    1. LLM-driven: In LISTENING and GREETING states, the FSM
       delegates to the LLM which returns the next state via
       function calling (e.g., end_conversation → GOODBYE).
    2. Flow-driven: In booking/cancellation flows, the FSM
       enforces a strict linear progression through slot-collection
       states.
    """

    def __init__(self, transitions: Optional[dict] = None):
        """Initialise the FSM with an optional custom transition table.

        Args:
            transitions: Optional override for TRANSITION_MAP.
        """
        self._transitions = transitions or TRANSITION_MAP

    def transition(
        self, current_state: DialogState, target_state: DialogState
    ) -> DialogState:
        """Determine the next dialog state, validating against the table.

        If the transition is invalid, logs a warning and returns
        the current state unchanged.

        Args:
            current_state: The FSM's current dialog state.
            target_state: The desired next state.

        Returns:
            The next DialogState (may stay current if transition is illegal).
        """
        allowed = self._transitions.get(current_state, set())

        if target_state in allowed:
            return target_state

        if current_state != target_state:
            logging.getLogger(__name__).warning(
                f"FSM blocked illegal transition: {current_state.value} → {target_state.value}"
            )

        return current_state  # Stay put

    def can_transition(
        self, current_state: DialogState, target_state: DialogState
    ) -> bool:
        """Check whether a transition is legal without side effects."""
        return target_state in self._transitions.get(current_state, set())

    def is_terminal(self, state: DialogState) -> bool:
        """Check whether a state is terminal (call should end after it)."""
        return state in (DialogState.GOODBYE, DialogState.ENDED, DialogState.ERROR)

    def is_llm_driven(self, state: DialogState) -> bool:
        """Check whether this state delegates next-state to the LLM."""
        return state in LLM_DRIVEN_STATES
