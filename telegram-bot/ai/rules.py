"""
AI rules-based engine for coordination.
Provides fallback logic when LLM is unavailable.
"""
from collections import defaultdict
from typing import Any, Dict, List
from datetime import timedelta
from db.models import Event


class RuleBasedEngine:
    """Rules-based AI engine - fast, no external dependency."""
    
    def check_availability(self, event: Event, constraints: List | None = None) -> Dict[Any, float]:
        """Calculate availability scores per user (placeholder)."""
        if constraints:
            slot_users: dict[str, set[int]] = defaultdict(set)
            for constraint in constraints:
                ctype = str(getattr(constraint, "type", ""))
                if not ctype.startswith("available:"):
                    continue
                slot = ctype.replace("available:", "")
                if slot:
                    slot_users[slot].add(int(constraint.user_id))
            if slot_users:
                return {
                    slot: float(len(users))
                    for slot, users in slot_users.items()
                }
        return {user_id: 1.0 for user_id in (event.attendance_list or [])}
    
    def compute_reliability(self, event: Event) -> Dict[int, float]:
        """Calculate reputation-weighted attendance probability (placeholder)."""
        return {user_id: 1.0 for user_id in (event.attendance_list or [])}
    
    def resolve_conflicts(
        self,
        event: Event,
        availability: Dict[Any, float],
        reliability: Dict[int, float],
        constraints: List | None = None,
    ) -> Dict[str, Any]:
        """Simple constraint resolution (no LLM)."""
        suggested_time = str(event.scheduled_time) if event.scheduled_time else "TBD"
        reasoning = "Using rules-based scheduling (AI fallback enabled)"

        if constraints and availability:
            best_slot = max(availability, key=availability.get)
            suggested_time = str(best_slot).replace("T", " ")
            reasoning = (
                "Using attendee availability constraints; selected the slot "
                "with the most declared availability"
            )

        return {
            "suggested_time": suggested_time,
            "reasoning": reasoning,
            "confidence": 0.5,
            "availability_score": sum(availability.values()) / len(availability) if availability else 0,
            "reliability_score": sum(reliability.values()) / len(reliability) if reliability else 0
        }
    
    def check_constraints(self, constraints: List) -> List[Dict[str, Any]]:
        """Detect constraint conflicts."""
        return [
            {
                "user": c.user_id,
                "target": c.target_user_id,
                "condition": f"User {c.user_id} joins only if User {c.target_user_id} joins"
            }
            for c in constraints if c.type == "if_joins"
        ]
    
    def generate_compromises(self, conflicts: List[Dict[str, Any]]) -> List[str]:
        """Generate compromise suggestions."""
        return [
            f"Consider scheduling at a time when both User {c['user']} and User {c['target']} are available"
            for c in conflicts
        ]
    
    def suggest_time_fallback(self, event: Event) -> Dict[str, Any]:
        """Fallback when LLM unavailable."""
        return {
            "suggested_time": str(event.scheduled_time) if event.scheduled_time else "TBD",
            "reasoning": "AI fallback - rules-based suggestion only",
            "confidence": 0.3,
            "note": "LLM unavailable, using rules-based suggestion"
        }
    
    def calculate_threshold_probability(self, event: Event, availability: Dict[int, float], reliability: Dict[int, float], logs: List) -> Dict[str, Any]:
        """Calculate probability of reaching threshold attendance."""
        total_users = len(event.attendance_list or [])
        threshold = event.threshold_attendance or 1
        
        if total_users == 0:
            return {"probability": 0.0, "message": "No attendees"}
        
        avg_reliability = sum(reliability.values()) / len(reliability) if reliability else 0.5
        probability = min(avg_reliability * (total_users / threshold), 1.0)
        
        return {
            "probability": round(probability, 2),
            "total_attendees": total_users,
            "threshold": threshold,
            "confidence": "high" if probability > 0.8 else "medium" if probability > 0.5 else "low"
        }
    
    def apply_decay(self, score: float, decay_rate: float, weeks_inactive: int) -> float:
        """Apply time-based decay to reputation score."""
        return score * ((1 - decay_rate) ** weeks_inactive)
