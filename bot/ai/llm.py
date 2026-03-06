"""
OpenAI-compatible LLM client for Qwen3.
"""
import httpx
import json
from typing import Dict, Any, Tuple
from config.settings import settings
from db.models import Event


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
    
    async def resolve_conflicts(self, event: Event, availability: Dict[int, float], reliability: Dict[int, float]) -> Dict[str, Any]:
        """Generate conflict resolution suggestions using LLM."""
        prompt = self._build_conflict_prompt(event, availability, reliability)
        
        try:
            response = await self._call_llm(prompt)
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "suggested_time": "TBD",
                "reasoning": "LLM returned invalid JSON, using fallback",
                "confidence": 0.0,
                "note": "JSON parse error"
            }
        except Exception as e:
            raise Exception(f"LLM resolution failed: {e}")
    
    async def analyze_constraints(self, constraints) -> list[Dict[str, Any]]:
        """Analyze constraints for conflicts."""
        prompt = self._build_constraint_prompt(constraints)
        
        try:
            response = await self._call_llm(prompt)
            return json.loads(response)
        except Exception:
            return []

    async def infer_constraint_from_text(self, text: str) -> Dict[str, Any]:
        """Infer structured constraint from free-form user text."""
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
        try:
            response = await self._call_llm(prompt)
            parsed = json.loads(response)
            return {
                "constraint_type": str(parsed.get("constraint_type", "")).strip(),
                "target_username": (
                    str(parsed.get("target_username")).strip()
                    if parsed.get("target_username") is not None
                    else None
                ),
                "confidence": float(parsed.get("confidence", 0.6)),
                "sanitized_summary": str(
                    parsed.get("sanitized_summary", text)
                ).strip(),
            }
        except Exception:
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

    async def infer_feedback_from_text(
        self, event_type: str, text: str
    ) -> Dict[str, Any]:
        """Infer weighted structured feedback from free-form text."""
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
        try:
            response = await self._call_llm(prompt)
            parsed = json.loads(response)
            score = float(parsed.get("score", 3.0))
            weight = float(parsed.get("weight", 0.7))
            expertise = parsed.get("expertise_adjustments", {})
            if not isinstance(expertise, dict):
                expertise = {}
            return {
                "score": max(1.0, min(5.0, score)),
                "weight": max(0.0, min(1.0, weight)),
                "sanitized_comment": str(
                    parsed.get("sanitized_comment", text)
                ).strip(),
                "expertise_adjustments": {
                    str(k): float(v)
                    for k, v in expertise.items()
                    if isinstance(k, str)
                },
            }
        except Exception:
            cleaned = _sanitize_toxic_text(text)
            sentiment = _simple_sentiment_score(cleaned)
            return {
                "score": sentiment,
                "weight": 0.6,
                "sanitized_comment": cleaned,
                "expertise_adjustments": {event_type: 0.1},
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
        - status
        - event_details
        - suggest_time
        - constraint_add
        - join
        - confirm
        - cancel
        - lock

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
          "action_type": "opinion|status|event_details|suggest_time|constraint_add|join|confirm|cancel|lock",
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
            if action_type not in {
                "opinion",
                "status",
                "event_details",
                "suggest_time",
                "constraint_add",
                "join",
                "confirm",
                "cancel",
                "lock",
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
            if "status" in lowered:
                fallback_action = "status"
            elif "detail" in lowered:
                fallback_action = "event_details"
            elif "suggest" in lowered or "time" in lowered:
                fallback_action = "suggest_time"
            elif "constraint" in lowered or "if " in lowered:
                fallback_action = "constraint_add"
            elif "join" in lowered:
                fallback_action = "join"
            elif "confirm" in lowered:
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
    
    def _build_conflict_prompt(self, event: Event, availability: Dict[int, float], reliability: Dict[int, float]) -> str:
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
