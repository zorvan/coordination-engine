"""
OpenAI-compatible LLM client for Qwen3.
"""
import os
import httpx
import json


class LLMClient:
    """OpenAI SDK wrapper for Qwen3 (or any OpenAI-compatible API)."""
    
    def __init__(self):
        self.base_url = os.getenv("AI_ENDPOINT", "http://127.0.0.1:8080/v1/")
        self.api_key = os.getenv("AI_API_KEY", "dummy-key")
        self.model = os.getenv("AI_MODEL", "qwen/qwen-3-coder-next")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=60.0
        )
    
    async def resolve_conflicts(self, event, availability: dict, reliability: dict) -> dict:
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
    
    async def analyze_constraints(self, constraints: list) -> list:
        """Analyze constraints for conflicts."""
        prompt = self._build_constraint_prompt(constraints)
        
        try:
            response = await self._call_llm(prompt)
            return json.loads(response)
        except Exception:
            return []
    
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

    async def check_availability(self) -> tuple[bool, str]:
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
    
    def _build_conflict_prompt(self, event, availability: dict, reliability: dict) -> str:
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
    
    def _build_constraint_prompt(self, constraints: list) -> str:
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
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
