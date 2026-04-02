"""
OpenAI-compatible LLM client for Qwen3.
PRD v2 Priority 4: Production Hardening (TODO-016).
- Schema validation for all LLM outputs
- Type safety and value range validation
"""
import httpx
import json
import logging
import re
from typing import Dict, Any, Tuple
from config.settings import settings
from db.models import Event

logger = logging.getLogger(__name__)


class LLMClient:
    """OpenAI SDK wrapper for Qwen3 (or any OpenAI-compatible API)."""

    def __init__(self):
        self.base_url = settings.ai_endpoint
        self.api_key = settings.ai_api_key
        self.model = settings.ai_model
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=60.0
        )

    async def resolve_conflicts(
        self,
        event: Event,
        availability: Dict[int, float],
        reliability: Dict[int, float],
        notes: list[str] | None = None,
    ) -> Dict[str, Any]:
        """Generate conflict resolution suggestions using LLM."""
        from ai.schemas import ConflictResolution, validate_llm_output

        prompt = self._build_conflict_prompt(
            event, availability, reliability, notes or []
        )

        def fallback():
            return {
                "conflict_detected": False,
                "suggested_time": "TBD",
                "reasoning": "LLM unavailable, using fallback",
                "compromises": []
            }

        try:
            response = await self._call_llm(prompt)
            return validate_llm_output(
                ConflictResolution,
                response,
                fallback_factory=fallback,
                logger=logger
            )
        except Exception as e:
            logger.exception("Conflict resolution failed: %s", e)
            return fallback()

    async def analyze_constraints(self, constraints) -> list[Dict[str, Any]]:
        """Analyze constraints for conflicts."""
        from ai.schemas import ConstraintAnalysis, validate_llm_output

        prompt = self._build_constraint_prompt(constraints)

        def fallback():
            return {"conflicts": []}

        try:
            response = await self._call_llm(prompt)
            validated = validate_llm_output(
                ConstraintAnalysis,
                response,
                fallback_factory=fallback,
                logger=logger
            )
            return [c.dict() for c in validated.get("conflicts", [])]
        except Exception:
            return []

    async def infer_constraint_from_text(self, text: str) -> Dict[str, Any]:
        """Infer structured constraint from free-form user text."""
        from ai.schemas import ConstraintInference, validate_llm_output

        prompt = f"""
        Convert the user's message into a scheduling constraint JSON.
        Allowed types: if_joins, if_attends, unless_joins.
        Extract target username if present (without @).
        Be concise and deterministic.

        User text:
        {text}

        Output JSON only:
        {{
          "constraint_type": "if_joins|if_attends|unless_joins",
          "target_username": "string or null",
          "confidence": 0.0,
          "sanitized_summary": "clean short summary"
        }}
        """

        def fallback():
            lowered = text.lower()
            inferred_type = "if_joins"
            if "unless" in lowered:
                inferred_type = "unless_joins"
            elif "attend" in lowered:
                inferred_type = "if_attends"

            username = None
            for token in text.split():
                if token.startswith("@") and len(token) > 1:
                    username = token.lstrip("@").strip(".,!?")
                    break
            return {
                "constraint_type": inferred_type,
                "target_username": username,
                "confidence": 0.45,
                "sanitized_summary": text.strip()[:240],
            }

        try:
            response = await self._call_llm(prompt)
            return validate_llm_output(
                ConstraintInference,
                response,
                fallback_factory=fallback,
                logger=logger
            )
        except Exception:
            return fallback()

    async def infer_feedback_from_text(
        self, event_type: str, text: str
    ) -> Dict[str, Any]:
        """Infer weighted structured feedback from free-form text."""
        from ai.schemas import FeedbackInference, validate_llm_output

        prompt = f"""
        Convert user feedback into structured JSON.
        Remove toxicity and abusive wording while preserving meaning.
        Infer:
        - score 1-5
        - weight 0.0-1.0 (confidence/quality of feedback)
        - sanitized_comment
        - expertise_adjustments map for activity tags

        Event type: {event_type}
        User feedback:
        {text}

        Output JSON only:
        {{
          "score": 1.0,
          "weight": 0.7,
          "sanitized_comment": "clean text",
          "expertise_adjustments": {{"tag": 0.1}}
        }}
        """

        def fallback():
            cleaned = _sanitize_toxic_text(text)
            sentiment = _simple_sentiment_score(cleaned)
            return {
                "score": sentiment,
                "weight": 0.6,
                "sanitized_comment": cleaned,
                "expertise_adjustments": {event_type: 0.1},
            }

        try:
            response = await self._call_llm(prompt)
            return validate_llm_output(
                FeedbackInference,
                response,
                fallback_factory=fallback,
                logger=logger
            )
        except Exception:
            return fallback()

    async def infer_event_draft_patch(
        self,
        current_draft: Dict[str, Any],
        message_text: str,
    ) -> Dict[str, Any]:
        """Infer a structured patch for event draft revisions."""
        prompt = f"""
        You update an event draft using user requested modifications.
        Return JSON patch fields only when explicit in user request.
        Keep deterministic and conservative.

        Current draft:
        {current_draft}

        User modification:
        {message_text}

        Output JSON only:
        {{
          "description": "string or null",
          "event_type": "social|sports|work|null",
          "scheduled_time_iso": "YYYY-MM-DDTHH:MM or null",
          "clear_time": true/false,
          "duration_minutes": 90 or null,
          "threshold_attendance": 5 or null,
          "invitees_add": ["alice", "@bob"] or [],
          "invitees_remove": ["charlie"] or [],
          "invite_all_members": true/false/null,
          "scheduling_mode": "fixed|flexible|null",
          "note": "constraint/suggestion note or null"
        }}
        """
        try:
            response = await self._call_llm(prompt)
            parsed = json.loads(response)
            invitees_add = parsed.get("invitees_add")
            invitees_remove = parsed.get("invitees_remove")
            return {
                "description": parsed.get("description"),
                "event_type": parsed.get("event_type"),
                "scheduled_time_iso": parsed.get("scheduled_time_iso"),
                "clear_time": bool(parsed.get("clear_time", False)),
                "duration_minutes": parsed.get("duration_minutes"),
                "threshold_attendance": parsed.get("threshold_attendance"),
                "invitees_add": invitees_add if isinstance(invitees_add, list) else [],
                "invitees_remove": invitees_remove if isinstance(invitees_remove, list) else [],
                "invite_all_members": parsed.get("invite_all_members"),
                "scheduling_mode": parsed.get("scheduling_mode"),
                "note": parsed.get("note"),
            }
        except Exception:
            lowered = message_text.lower()
            patch: Dict[str, Any] = {
                "description": None,
                "event_type": None,
                "scheduled_time_iso": None,
                "clear_time": False,
                "duration_minutes": None,
                "threshold_attendance": None,
                "invitees_add": [],
                "invitees_remove": [],
                "invite_all_members": None,
                "scheduling_mode": None,
                "note": None,
            }

            if "flexible" in lowered:
                patch["scheduling_mode"] = "flexible"
            elif "fixed" in lowered:
                patch["scheduling_mode"] = "fixed"

            if "invite all" in lowered or "@all" in lowered:
                patch["invite_all_members"] = True

            threshold_match = re.search(r"\bthreshold(?:\s+to)?\s+(\d{1,3})\b", lowered)
            if threshold_match:
                patch["threshold_attendance"] = int(threshold_match.group(1))

            duration_match = re.search(
                r"\b(\d{1,3})\s*(minutes|minute|mins|min|hours|hour|hrs|hr)\b",
                lowered,
            )
            if duration_match:
                value = int(duration_match.group(1))
                unit = duration_match.group(2)
                patch["duration_minutes"] = value * 60 if "hour" in unit or "hr" in unit else value

            datetime_match = re.search(
                r"\b(\d{4}-\d{2}-\d{2})[ t](\d{1,2}:\d{2})\b",
                message_text,
            )
            if datetime_match:
                date_part = datetime_match.group(1)
                time_part = datetime_match.group(2)
                hour, minute = time_part.split(":")
                patch["scheduled_time_iso"] = f"{date_part}T{int(hour):02d}:{minute}"

            if (
                "clear time" in lowered
                or "no time" in lowered
                or "time tbd" in lowered
            ):
                patch["clear_time"] = True

            handles = re.findall(r"@([A-Za-z][A-Za-z0-9_]{4,31})", message_text)
            if "remove" in lowered:
                patch["invitees_remove"] = [h.lower() for h in handles]
            elif "add" in lowered or "invite" in lowered:
                patch["invitees_add"] = [h.lower() for h in handles]

            if lowered.startswith("description:"):
                patch["description"] = message_text.split(":", 1)[1].strip()
            elif lowered.startswith("note:") or lowered.startswith("constraint:"):
                patch["note"] = message_text.split(":", 1)[1].strip()

            if any(token in lowered for token in {"social", "sports", "work"}):
                if "sports" in lowered:
                    patch["event_type"] = "sports"
                elif "work" in lowered:
                    patch["event_type"] = "work"
                else:
                    patch["event_type"] = "social"

            return patch

    async def infer_event_draft_from_context(
        self,
        *,
        message_text: str,
        history: list[dict[str, Any]] | None = None,
        scheduling_mode: str = "fixed",
    ) -> Dict[str, Any]:
        """Infer a full event draft from mention text + recent chat context."""
        compact_history = (history or [])[-30:]
        prompt = f"""
        Build an event draft JSON from group context.
        Use conservative defaults when missing.
        Defaults:
        - event_type: social
        - threshold_attendance: 3
        - duration_minutes: 120
        - invite_all_members: true

        User message:
        {message_text}

        Recent chat history:
        {compact_history}

        Requested scheduling mode:
        {scheduling_mode}

        Output JSON only:
        {{
          "description": "short text",
          "event_type": "social|sports|work",
          "scheduled_time_iso": "YYYY-MM-DDTHH:MM or null",
          "duration_minutes": 120,
          "threshold_attendance": 3,
          "invite_all_members": true,
          "invitees": ["@alice", "@bob"],
          "planning_notes": ["note 1", "note 2"]
        }}
        """
        try:
            response = await self._call_llm(prompt)
            parsed = json.loads(response)
            event_type = str(parsed.get("event_type", "social")).strip().lower()
            if event_type not in {"social", "sports", "work"}:
                event_type = "social"
            duration = int(parsed.get("duration_minutes", 120))
            threshold = int(parsed.get("threshold_attendance", 3))
            invitees = parsed.get("invitees", [])
            if not isinstance(invitees, list):
                invitees = []
            normalized_invitees = []
            for raw in invitees:
                s = str(raw).strip()
                if not s:
                    continue
                if not s.startswith("@"):
                    s = f"@{s}"
                normalized_invitees.append(s.lower())
            notes = parsed.get("planning_notes", [])
            if not isinstance(notes, list):
                notes = []
            return {
                "description": str(
                    parsed.get("description", message_text or "Group planned event")
                ).strip()[:500],
                "event_type": event_type,
                "scheduled_time": parsed.get("scheduled_time_iso"),
                "duration_minutes": max(30, min(720, duration)),
                "threshold_attendance": max(1, min(200, threshold)),
                "invite_all_members": bool(parsed.get("invite_all_members", True)),
                "invitees": normalized_invitees,
                "planning_notes": [str(n).strip()[:300] for n in notes if str(n).strip()],
            }
        except Exception:
            return {
                "description": (message_text or "Group planned event").strip()[:500],
                "event_type": "social",
                "scheduled_time": None,
                "duration_minutes": 120,
                "threshold_attendance": 3,
                "invite_all_members": True,
                "invitees": ["@all"],
                "planning_notes": ["Draft auto-generated from limited context."],
            }

    async def infer_early_feedback_from_text(
        self,
        text: str,
    ) -> Dict[str, Any]:
        """Infer early behavioral feedback signal from free text."""
        prompt = f"""
        Convert this peer behavioral feedback into JSON.
        Remove toxicity while preserving intent.
        Output fields:
        - signal_type: overall|reliability|cooperation|toxicity|commitment|trust
        - score: 0..5
        - weight: 0..1
        - confidence: 0..1
        - sanitized_comment: short clean summary

        Feedback text:
        {text}

        Output JSON only:
        {{
          "signal_type": "overall",
          "score": 3.0,
          "weight": 0.6,
          "confidence": 0.7,
          "sanitized_comment": "summary"
        }}
        """
        try:
            response = await self._call_llm(prompt)
            parsed = json.loads(response)
            signal_type = str(parsed.get("signal_type", "overall")).strip().lower()
            if signal_type not in {
                "overall",
                "reliability",
                "cooperation",
                "toxicity",
                "commitment",
                "trust",
            }:
                signal_type = "overall"
            return {
                "signal_type": signal_type,
                "score": max(0.0, min(5.0, float(parsed.get("score", 3.0)))),
                "weight": max(0.0, min(1.0, float(parsed.get("weight", 0.6)))),
                "confidence": max(0.0, min(1.0, float(parsed.get("confidence", 0.7)))),
                "sanitized_comment": str(
                    parsed.get("sanitized_comment", text)
                ).strip()[:500],
            }
        except Exception:
            cleaned = _sanitize_toxic_text(text)
            lowered = cleaned.lower()
            signal_type = "overall"
            score = _simple_sentiment_score(cleaned)
            if "late" in lowered or "no show" in lowered or "unreliable" in lowered:
                signal_type = "reliability"
                score = max(0.0, score - 0.5)
            elif "helpful" in lowered or "cooperate" in lowered:
                signal_type = "cooperation"
                score = min(5.0, score + 0.4)
            return {
                "signal_type": signal_type,
                "score": score,
                "weight": 0.55,
                "confidence": 0.5,
                "sanitized_comment": cleaned[:500],
            }

    async def infer_group_mention_action(
        self, text: str, history: list[dict[str, Any]] | None = None
    ) -> Dict[str, Any]:
        """Infer mention intent into a concrete action payload."""
        compact_history = (history or [])[-20:]
        prompt = f"""
        You are a Telegram group coordination assistant.
        Infer the best action from a message that mentioned the bot.

        Allowed action_type values:
        - opinion
        - organize_event
        - organize_event_flexible
        - status
        - event_details
        - suggest_time
        - constraint_add
        - join
        - confirm
        - cancel
        - lock
        - request_confirmations

        If action is unclear, use opinion.
        If event_id is unknown, set event_id to null.
        For constraint_add, infer target_username and constraint_type when possible.
        Constraint types allowed: if_joins, if_attends, unless_joins.

        Mention text:
        {text}

        Recent chat history (newest last):
        {compact_history}

        Output JSON only:
        {{
          "action_type": "opinion|organize_event|organize_event_flexible|status|event_details|suggest_time|constraint_add|join|confirm|cancel|lock|request_confirmations",
          "event_id": 123 or null,
          "target_username": "alice" or null,
          "constraint_type": "if_joins|if_attends|unless_joins|null",
          "assistant_response": "short response"
        }}
        """
        try:
            response = await self._call_llm(prompt)
            parsed = json.loads(response)
            action_type = str(parsed.get("action_type", "opinion")).strip().lower()
            logger.debug(f"LLM raw response: action_type={action_type}, event_id={parsed.get('event_id')}, text={text[:100]}")
            if action_type not in {
                "opinion",
                "organize_event",
                "organize_event_flexible",
                "status",
                "event_details",
                "suggest_time",
                "constraint_add",
                "join",
                "confirm",
                "cancel",
                "lock",
                "request_confirmations",
            }:
                action_type = "opinion"
            event_id = parsed.get("event_id")
            try:
                event_id = int(event_id) if event_id is not None else None
            except (TypeError, ValueError):
                event_id = None
            constraint_type = parsed.get("constraint_type")
            if constraint_type is not None:
                constraint_type = str(constraint_type).strip().lower()
                if constraint_type not in {"if_joins", "if_attends", "unless_joins"}:
                    constraint_type = None
            target_username = parsed.get("target_username")
            if target_username is not None:
                target_username = str(target_username).strip().lstrip("@")
                if not target_username:
                    target_username = None
            return {
                "action_type": action_type,
                "event_id": event_id,
                "target_username": target_username,
                "constraint_type": constraint_type,
                "assistant_response": str(
                    parsed.get("assistant_response", "")
                ).strip(),
            }
        except Exception:
            lowered = text.lower()
            fallback_action = "opinion"
            if (
                "organize" in lowered
                or "organise" in lowered
                or "create event" in lowered
                or "new event" in lowered
                or "plan event" in lowered
            ):
                if "flexible" in lowered:
                    fallback_action = "organize_event_flexible"
                else:
                    fallback_action = "organize_event"
            elif "status" in lowered:
                fallback_action = "status"
            elif "detail" in lowered:
                fallback_action = "event_details"
            elif "suggest" in lowered or "time" in lowered:
                fallback_action = "suggest_time"
            elif "constraint" in lowered or "if " in lowered:
                fallback_action = "constraint_add"
            elif (
                "request confirmation" in lowered
                or "confirm button" in lowered
                or "ask confirmations" in lowered
            ):
                fallback_action = "request_confirmations"
            elif "join" in lowered:
                fallback_action = "join"
            elif "confirm" in lowered or "interested" in lowered or "interest" in lowered:
                fallback_action = "confirm"
            elif "cancel" in lowered:
                fallback_action = "cancel"
            elif "lock" in lowered:
                fallback_action = "lock"

            # Basic event id extraction fallback
            event_id = None
            for token in text.split():
                if token.isdigit():
                    event_id = int(token)
                    break

            logger.debug(f"LLM fallback inference: action={fallback_action}, event_id={event_id}, text={text[:100]}")

            return {
                "action_type": fallback_action,
                "event_id": event_id,
                "target_username": None,
                "constraint_type": None,
                "assistant_response": "I inferred a best-effort action from your mention.",
            }

    async def _call_llm(self, prompt: str) -> str:
        """Make LLM API call."""
        response = await self.client.post(
            "/chat/completions",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 500
            }
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    async def check_availability(self) -> Tuple[bool, str]:
        """Check if the configured LLM endpoint is reachable."""
        try:
            response = await self.client.get("/models")
            response.raise_for_status()
            payload = response.json()
            models = payload.get("data", [])
            model_count = len(models) if isinstance(models, list) else 0
            return True, f"LLM available (models={model_count})"
        except Exception as e:
            return False, f"LLM unavailable: {type(e).__name__}: {e}"

    def _build_conflict_prompt(
        self,
        event: Event,
        availability: Dict[int, float],
        reliability: Dict[int, float],
        notes: list[str],
    ) -> str:
        """Construct Qwen3 prompt for conflict resolution."""
        return f"""
        You are a scheduling assistant. Resolve conflicts for this event.

        Event: {event.event_type}
        Participants: {len(event.attendance_list)}
        Threshold: {event.threshold_attendance}

        Availability scores (0-1): {availability}
        Reliability scores (0-5): {reliability}

        Constraints:
        - User A: "I join only if Jim joins" (confidence: 0.8)

        Private attendee notes:
        {notes}

        Output JSON:
        {{
            "conflict_detected": true/false,
            "suggested_time": "ISO timestamp or TBD",
            "reasoning": "brief explanation",
            "compromises": ["suggestion 1", "suggestion 2"]
        }}
        """

    def _build_constraint_prompt(self, constraints) -> str:
        """Construct Qwen3 prompt for constraint analysis."""
        return f"""
        Analyze these constraints for conflicts.

        Constraints:
        {constraints}

        Output JSON:
        {{
            "conflicts": [
                {{"user": id, "target": id, "condition": "description"}}
            ]
        }}
        """

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()


def _sanitize_toxic_text(text: str) -> str:
    """Basic toxicity scrub fallback."""
    banned = {"idiot", "stupid", "dumb", "hate", "trash", "moron"}
    tokens = text.split()
    cleaned = []
    for token in tokens:
        normalized = token.lower().strip(".,!?")
        if normalized in banned:
            cleaned.append("[redacted]")
        else:
            cleaned.append(token)
    return " ".join(cleaned).strip()[:500]


def _simple_sentiment_score(text: str) -> float:
    """Simple fallback sentiment to score mapping 1..5."""
    lowered = text.lower()
    positives = sum(
        lowered.count(word) for word in ["good", "great", "nice", "excellent", "love"]
    )
    negatives = sum(
        lowered.count(word) for word in ["bad", "poor", "late", "problem", "boring"]
    )
    raw = 3.0 + min(2.0, positives * 0.4) - min(2.0, negatives * 0.4)
    return max(1.0, min(5.0, raw))
