"""
Core AI coordination engine with hybrid approach:
- Rules-based core
- LLM fallback for conflicts/low confidence
"""
from typing import Any, Callable
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import Event, Constraint, Log


class AICoordinationEngine:
    """Hybrid AI engine - rules first, LLM fallback."""
    
    def __init__(self, session_factory: Callable, fallback_enabled: bool = True):
        self.session_factory = session_factory
        self.fallback_enabled = fallback_enabled
        from ai.rules import RuleBasedEngine
        from ai.llm import LLMClient
        self.rules_engine = RuleBasedEngine()
        self.llm = LLMClient()
    
    async def suggest_event_time(
        self, session: AsyncSession, event_id: int
    ) -> dict[str, Any]:
        """3-layer decision logic for time suggestions."""
        event = await session.get(Event, event_id)
        if not event:
            return {"error": "Event not found"}
        result = await session.execute(
            select(Constraint).where(Constraint.event_id == event_id)
        )
        constraints = result.scalars().all()
        
        try:
            return await self._compute_suggestion(event, constraints)
        except Exception as e:
            if self.fallback_enabled:
                return self.rules_engine.suggest_time_fallback(event)
            return {"error": str(e)}
    
    async def _compute_suggestion(self, event: Event, constraints: list[Constraint]) -> dict[str, Any]:
        """Compute AI suggestion using 3-layer logic."""
        availability = self.rules_engine.check_availability(event, constraints)
        reliability = self.rules_engine.compute_reliability(event)
        confidence = self._calculate_confidence(availability, reliability)
        
        if confidence >= 0.7:
            return self.rules_engine.resolve_conflicts(
                event,
                availability,
                reliability,
                constraints,
            )
        
        return await self.llm.resolve_conflicts(event, availability, reliability)
    
    def _calculate_confidence(self, availability: dict, reliability: dict) -> float:
        """Calculate confidence score for AI decision."""
        if not availability or not reliability:
            return 0.0
        
        avg_availability = sum(availability.values()) / len(availability) if availability else 0
        avg_reliability = sum(reliability.values()) / len(reliability) if reliability else 0
        
        return (avg_availability * 0.5 + avg_reliability / 5 * 0.5)
    
    async def check_constraint_compatibility(self, session: AsyncSession, event_id: int) -> dict[str, Any]:
        """Check and resolve constraint conflicts."""
        event = await session.get(Event, event_id)
        if not event:
            return {"error": "Event not found"}
        
        result = await session.execute(
            select(Constraint).where(Constraint.event_id == event_id)
        )
        constraints = result.scalars().all()
        
        if len(constraints) < 5:
            conflicts = self.rules_engine.check_constraints(constraints)
        else:
            conflicts = await self.llm.analyze_constraints(constraints)
        
        return {
            "conflicts": conflicts,
            "suggestions": self.rules_engine.generate_compromises(conflicts)
        }
    
    async def calculate_threshold_probability(self, session: AsyncSession, event_id: int) -> dict[str, Any]:
        """Calculate probability of reaching threshold attendance."""
        event = await session.get(Event, event_id)
        if not event:
            return {"error": "Event not found"}
        
        result = await session.execute(
            select(Log).where(Log.event_id == event_id)
        )
        logs = result.scalars().all()
        
        availability = self.rules_engine.check_availability(event)
        reliability = self.rules_engine.compute_reliability(event)
        
        return self.rules_engine.calculate_threshold_probability(
            event, availability, reliability, logs
        )
