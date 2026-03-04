"""
AI rules-based engine for coordination.
"""
import math
from datetime import datetime, timedelta


class RuleBasedEngine:
    """Rules-based AI engine - fast, no external dependency."""
    
    def check_availability(self, event) -> dict:
        """Calculate availability scores per user."""
        availability = {}
        scheduled_time = event.scheduled_time
        
        if not scheduled_time:
            return {}
        
        for user_id in event.attendance_list:
            availability[user_id] = 1.0
        
        return availability
    
    def compute_reliability(self, event) -> dict:
        """Calculate reputation-weighted attendance probability."""
        reliability = {}
        for user_id in event.attendance_list:
            reliability[user_id] = 1.0
        
        return reliability
    
    def resolve_conflicts(self, event, availability: dict, reliability: dict) -> dict:
        """Simple constraint resolution (no LLM)."""
        return {
            "suggested_time": str(event.scheduled_time) if event.scheduled_time else "TBD",
            "reasoning": "Using rules-based scheduling (AI fallback enabled)",
            "confidence": 0.5,
            "availability_score": sum(availability.values()) / len(availability) if availability else 0,
            "reliability_score": sum(reliability.values()) / len(reliability) if reliability else 0
        }
    
    def check_constraints(self, constraints: list) -> list:
        """Detect constraint conflicts."""
        conflicts = []
        for c in constraints:
            if c.type == "if_joins":
                conflicts.append({
                    "user": c.user_id,
                    "target": c.target_user_id,
                    "condition": f"User {c.user_id} joins only if User {c.target_user_id} joins"
                })
        return conflicts
    
    def generate_compromises(self, conflicts: list) -> list:
        """Generate compromise suggestions."""
        suggestions = []
        for conflict in conflicts:
            suggestions.append(
                f"Consider scheduling at a time when both User {conflict['user']} and User {conflict['target']} are available"
            )
        return suggestions
    
    def suggest_time_fallback(self, event) -> dict:
        """Fallback when LLM unavailable."""
        return {
            "suggested_time": str(event.scheduled_time) if event.scheduled_time else "TBD",
            "reasoning": "AI fallback - rules-based suggestion only",
            "confidence": 0.3,
            "note": "LLM unavailable, using rules-based suggestion"
        }
    
    def calculate_threshold_probability(self, event, availability: dict, reliability: dict, logs: list) -> dict:
        """Calculate probability of reaching threshold attendance."""
        total_users = len(event.attendance_list)
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