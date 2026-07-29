"""Response composer — templates + entities → spoken response text.

Phase 1 component that renders human-readable response strings from
templates, collected entity slots, tool results, and the current
dialog state. Feeds directly into the TTS provider.
"""

from typing import Optional

from domain.entities.value_objects import DialogState


# ── Built-in templates (overridable by domain profile) ─────────────────────

DEFAULT_TEMPLATES = {
    "greeting": "Hello, thank you for calling {organization}. How can I help you today?",
    "returning_greeting": "Welcome back{name}, thank you for calling {organization}. How can I help you today?",
    "goodbye": "Thank you for calling {organization}.{extra} Have a great day!",
    "transfer": "Let me connect you to a {department} agent now. One moment please.",
    "transfer_failed": "I'm sorry, no one is available right now. I can take a message and have them call you back.",
    "waitlist": "Unfortunately, all slots for {date} are currently full. I can add you to our waitlist so we'll notify you if something opens up.",
    "no_availability": "I don't see any available slots on {date}. Would you like to try a different date?",
    "confirm_booking": "I have you booked for {date} at {time} with {resource}. Your confirmation code is {code}. Would you like a reminder via SMS?",
    "confirm_cancellation": "I've cancelled your booking for {date} at {time}. Is there anything else I can help with?",
    "faq_answer": "{answer}",
    "clarification": "I'm sorry, I didn't quite catch that. Could you say it again?",
    "ask_name": "May I have your name, please?",
    "ask_phone": "What's the best phone number to reach you at?",
    "ask_date": "What date would you like?",
    "ask_time": "And what time works best for you?",
    "error": "I'm experiencing a technical issue. Let me transfer you to a team member.",
}

class ResponseComposer:
    """Compose spoken responses by rendering templates with context.

    Pulls templates from the domain profile (with fallbacks to
    DEFAULT_TEMPLATES) and fills in slots like caller name,
    organization name, dates, and times.
    """

    def compose(
        self,
        template_key: str,
        domain_profile=None,   # DomainProfile (optional in Phase 1)
        context: Optional[dict] = None,
    ) -> str:
        """Render a response string from a template key and context.

        Template keys map to: DEFAULT_TEMPLATES entries, domain profile
        templates, or state-based auto-selection.

        Args:
            template_key: Identifies which template to use
                          (e.g. 'greeting', 'confirm_booking', 'goodbye').
            domain_profile: Domain profile with optional template overrides.
            context: Slot values collected during the conversation.

        Returns:
            A fully rendered response string ready for TTS synthesis.
        """
        ctx = context or {}

        # 1. Try domain profile overrides
        template = None
        if domain_profile:
            template = self._get_profile_template(domain_profile, template_key)

        # 2. Fall back to built-in defaults
        if template is None:
            template = DEFAULT_TEMPLATES.get(template_key, "I'm sorry, how can I help?")

        # 3. Interpolate context
        try:
            return template.format(**ctx)
        except KeyError:
            # Missing context vars — return template as-is
            return template

    def get_greeting(self, domain_profile=None, is_returning: bool = False, caller_name: str = "") -> str:
        """Compose the initial greeting for an inbound call."""
        org = getattr(domain_profile, "organization_name", "") if domain_profile else ""
        org = org or "us"  # fallback so it says "calling us" not "calling "

        if is_returning and caller_name:
            return DEFAULT_TEMPLATES["returning_greeting"].format(organization=org, name=f", {caller_name}")

        return DEFAULT_TEMPLATES["greeting"].format(organization=org)

    def state_response(
        self,
        state: DialogState,
        domain_profile=None,
        context: Optional[dict] = None,
    ) -> str:
        """Select the appropriate template key for a given dialog state.

        Args:
            state: Current dialog state.
            domain_profile: Domain profile with templates.
            context: Slot values.

        Returns:
            Rendered response string.
        """
        state_templates = {
            DialogState.GREETING:         "greeting",
            DialogState.GOODBYE:          "goodbye",
            DialogState.INFORM_TRANSFER:  "transfer",
            DialogState.TRANSFER_FAILED:  "transfer_failed",
            DialogState.CONFIRM_BOOKING:  "confirm_booking",
            DialogState.CONFIRM_CANCELLATION: "confirm_cancellation",
            DialogState.OFFER_WAITLIST:   "waitlist",
            DialogState.COLLECT_BOOKING_NAME:  "ask_name",
            DialogState.COLLECT_BOOKING_PHONE: "ask_phone",
            DialogState.COLLECT_BOOKING_DATE:  "ask_date",
            DialogState.COLLECT_BOOKING_TIME:  "ask_time",
            DialogState.ERROR:            "error",
        }

        key = state_templates.get(state, "clarification")
        return self.compose(key, domain_profile, context)

    def _get_profile_template(self, domain_profile, key: str) -> str | None:
        """Extract a named template from a DomainProfile entity (Phase 2+)."""
        # Phase 1: domain profiles are stubs — use defaults
        # Phase 2: domain_profile.templates dict lookup
        return None
