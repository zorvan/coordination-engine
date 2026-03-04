"""
Core AI coordination engine with hybrid approach:
- Rules-based core
- LLM fallback for conflicts/low confidence
"""
import json
from typing import Optional


class AICoordinationEngine:
    """Hybrid AI engine - rules first, LLM fallback."""
    
    def __init__(self, session_factory, fallback_enabled=True):
        self.session_factory = session_factory
        self.fallback_enabled = fallback_enabled
        from ai.rules import RuleBasedEngine
        from ai.llm import LLMClient
        self.rules_engine = RuleBasedEngine()
        self.llm = LLMClient()
    
    async def suggest_event_time(self, event_id: int) -> dict:
        """3-layer decision logic for time suggestions."""
        from db.models import Event
        from sqlalchemy.ext.asyncio import AsyncSession
        
        async with self.session_factory() as session:
            event = await session.get(Event, event_id)
        
        if not event:
            return {"error": "Event not found"}
        
        try:
            result = await self._compute_suggestion(event)
            return result
        except Exception as e:
            if self.fallback_enabled:
                return self.rules_engine.suggest_time_fallback(event)
            return {"error": str(e)}
    
    async def _compute_suggestion(self, event) -> dict:
        """Compute AI suggestion using 3-layer logic."""
        availability = self.rules_engine.check_availability(event)
        reliability = self.rules_engine.compute_reliability(event)
        
        confidence = self._calculate_confidence(availability, reliability)
        
        if confidence >= 0.7:
            return self.rules_engine.resolve_conflicts(event, availability, reliability)
        
        return await self.llm.resolve_conflicts(event, availability, reliability)
    
    def _calculate_confidence(self, availability: dict, reliability: dict) -> float:
        """Calculate confidence score for AI decision."""
        if not availability or not reliability:
            return 0.0
        
        avg_availability = sum(availability.values()) / len(availability) if availability else 0
        avg_reliability = sum(reliability.values()) / len(reliability) if reliability else 0
        
        return (avg_availability * 0.5 + avg_reliability / 5 * 0.5)
    
    async def check_constraint_compatibility(self, event_id: int) -> dict:
        """Check and resolve constraint conflicts."""
        from db.models import Constraint, Event
        from sqlalchemy.ext.asyncio import AsyncSession
        
        async with self.session_factory() as session:
            event = await session.get(Event, event_id)
            if not event:
                return {"error": "Event not found"}
            
            constraints = await self._get_constraints(session, event_id)
        
        if len(constraints) < 5:
            conflicts = self.rules_engine.check_constraints(constraints)
        else:
            conflicts = await self.llm.analyze_constraints(constraints)
        
        return {
            "conflicts": conflicts,
            "suggestions": self.rules_engine.generate_compromises(conflicts)
        }
    
    async def _get_constraints(self, session, event_id: int) -> list:
        """Get constraints for an event."""
        from db.models import Constraint
        result = await session.execute(
            Constraint.__table__.select().where(Constraint.event_id == event_id)
        )
        return result.scalars().all()
    
    async def calculate_threshold_probability(self, event_id: int) -> dict:
        """Calculate probability of reaching threshold attendance."""
        from db.models import Event, Log
        from sqlalchemy.ext.asyncio import AsyncSession
        
        async with self.session_factory() as session:
            event = await session.get(Event, event_id)
            if not event:
                return {"error": "Event not found"}
            
            logs = await self._get_event_logs(session, event_id)
        
        availability = self.rules_engine.check_availability(event)
        reliability = self.rules_engine.compute_reliability(event)
        
        return self.rules_engine.calculate_threshold_probability(
            event, availability, reliability, logs
        )
    
    async def _get_event_logs(self, session, event_id: int) -> list:
        """Get logs for an event."""
        from db.models import Log
        result = await session.execute(
            Log.__table__.select().where(Log.event_id == event_id)
        )
        return result.scalars().all()