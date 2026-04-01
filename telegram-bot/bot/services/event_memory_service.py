"""
EventMemoryService - Layer 3: Memory Layer.
PRD v2 Section 2.3: Makes events mean something through shared narratives.

This service manages:
- Post-event memory collection via DM
- Memory Weave generation (multi-narrative aggregation)
- Event lineage (referencing prior events)
- Memory storage and retrieval
"""
from __future__ import annotations

import logging
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from telegram import Bot

from db.models import Event, EventMemory, EventParticipant, ParticipantStatus, User

logger = logging.getLogger("coord_bot.services.memory")


class EventMemoryService:
    """
    Manages the Memory Layer - transforming coordination into shared meaning.
    
    Design principles (PRD Section 1.3):
    - Memory over Surveillance: Store what mattered, not everything
    - Preserve plurality: Co-existing voices, not resolved narrative
    - Bot as "absent friend": Relational, low-stakes contribution
    
    Bot persona (PRD Section 5.2):
    - "Absent friend" in memory flows
    - Open-ended prompts, not structured forms
    - No feedback/evaluation framing
    """
    
    # Collection window: 24 hours post-event
    COLLECTION_WINDOW_HOURS = 24
    
    # Delay before starting collection: 1-3 hours post-event
    COLLECTION_DELAY_HOURS = 2
    
    def __init__(self, bot: Bot, session: AsyncSession):
        self.bot = bot
        self.session = session
    
    async def start_memory_collection(self, event: Event) -> None:
        """
        Start memory collection flow after event completion.
        
        Triggered automatically when event state transitions to 'completed'.
        Waits COLLECTION_DELAY_HOURS, then DMs each confirmed participant.
        """
        if not event.completed_at:
            logger.warning("Attempted memory collection for incomplete event %s", event.event_id)
            return
        
        # Get confirmed participants
        result = await self.session.execute(
            select(EventParticipant)
            .where(
                EventParticipant.event_id == event.event_id,
                EventParticipant.status.in_([
                    ParticipantStatus.confirmed,
                    ParticipantStatus.joined,
                ])
            )
        )
        participants = result.scalars().all()
        
        if not participants:
            logger.info("No participants to collect memories from", extra={"event_id": event.event_id})
            return
        
        logger.info(
            "Starting memory collection for %d participants",
            len(participants),
            extra={"event_id": event.event_id}
        )
        
        # DM each participant
        for participant in participants:
            await self._send_memory_request(participant, event)
    
    async def _send_memory_request(
        self,
        participant: EventParticipant,
        event: Event,
    ) -> None:
        """Send DM requesting memory fragment."""
        # Get user for chat_id
        user_result = await self.session.execute(
            select(User).where(User.user_id == participant.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user or not user.telegram_user_id:
            logger.warning("Cannot find user for participant %s", participant.user_id)
            return
        
        # Craft open-ended prompt (PRD: not structured questions)
        message = (
            f"Hey — how was {event.event_type}?\n\n"
            f"Anything that stuck with you? A word, a moment, a photo is enough.\n\n"
            f"(This isn't feedback or a rating — just what you want to remember.)"
        )
        
        try:
            await self.bot.send_message(
                chat_id=user.telegram_user_id,
                text=message,
                parse_mode="HTML",
            )
            logger.info(
                "Sent memory request",
                extra={"event_id": event.event_id, "user": user.user_id}
            )
        except Exception as e:
            logger.error(
                "Failed to send memory request to user %s: %s",
                user.user_id,
                e,
            )
    
    async def collect_memory_fragment(
        self,
        event_id: int,
        user_id: int,
        fragment_text: str,
        tone_tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Collect a memory fragment from a participant.
        
        Called when user replies to the DM or uses /remember command.
        
        Returns fragment dict for storage.
        """
        # Generate anonymous contributor hash (PRD: anonymous by default)
        contributor_hash = hashlib.sha256(
            f"{event_id}:{user_id}:{datetime.utcnow().date()}".encode()
        ).hexdigest()[:8]
        
        fragment = {
            "text": fragment_text,
            "contributor_hash": contributor_hash,
            "tone_tag": tone_tag or "neutral",
            "submitted_at": datetime.utcnow().isoformat(),
        }
        
        logger.info(
            "Collected memory fragment",
            extra={
                "event_id": event_id,
                "contributor_hash": contributor_hash,
                "tone": fragment["tone_tag"],
            }
        )
        
        return fragment
    
    async def add_fragment_to_memory(
        self,
        event_id: int,
        fragment: Dict[str, Any],
    ) -> EventMemory:
        """Add fragment to event memory (create or update EventMemory)."""
        # Get or create EventMemory
        result = await self.session.execute(
            select(EventMemory).where(EventMemory.event_id == event_id)
        )
        memory = result.scalar_one_or_none()
        
        if not memory:
            memory = EventMemory(
                event_id=event_id,
                fragments=[],
                hashtags=[],
                outcome_markers=[],
                tone_palette=[],
            )
            self.session.add(memory)
        
        # Add fragment
        if memory.fragments is None:
            memory.fragments = []
        memory.fragments.append(fragment)
        
        # Update tone palette
        tone = fragment.get("tone_tag", "neutral")
        if memory.tone_palette is None:
            memory.tone_palette = []
        if tone not in memory.tone_palette:
            memory.tone_palette.append(tone)
        
        return memory
    
    async def generate_memory_weave(
        self,
        event: Event,
    ) -> Optional[str]:
        """
        Generate Memory Weave from collected fragments.
        
        PRD Design rule: Preserve plurality. Not a summary, not a log.
        Co-existing voices, not resolved narrative.
        
        Returns weave text (also stored in EventMemory).
        """
        result = await self.session.execute(
            select(EventMemory).where(EventMemory.event_id == event.event_id)
        )
        memory = result.scalar_one_or_none()
        
        if not memory or not memory.fragments:
            logger.info("No fragments to weave", extra={"event_id": event.event_id})
            return None
        
        # Simple weave generation (can be enhanced with LLM)
        # Format: Present fragments as co-existing voices
        
        event_anchor = f"{event.event_type} • {event.scheduled_time.strftime('%d %b %Y') if event.scheduled_time else 'TBD'}"
        
        weave_parts = [f"📿 <b>How people remember: {event_anchor}</b>\n"]
        
        for i, fragment in enumerate(memory.fragments, 1):
            text = fragment.get("text", "")
            tone = fragment.get("tone_tag", "")
            
            if tone and tone != "neutral":
                weave_parts.append(f"• \"{text}\" <i>({tone})</i>")
            else:
                weave_parts.append(f"• \"{text}\"")
        
        # Add tone palette if diverse
        if len(memory.tone_palette) > 1:
            tone_str = ", ".join(memory.tone_palette)
            weave_parts.append(f"\n_Tones: {tone_str}_")
        
        # Add hashtags if present
        if memory.hashtags:
            hashtag_str = " ".join(f"#{tag}" for tag in memory.hashtags)
            weave_parts.append(f"\n{hashtag_str}")
        
        weave_text = "\n\n".join(weave_parts)
        
        # Store in memory
        memory.weave_text = weave_text
        
        logger.info(
            "Generated memory weave with %d fragments",
            len(memory.fragments),
            extra={"event_id": event.event_id}
        )
        
        return weave_text
    
    async def post_memory_weave(
        self,
        event: Event,
        group_chat_id: int,
    ) -> bool:
        """Generate and post memory weave to group chat."""
        weave_text = await self.generate_memory_weave(event)
        
        if not weave_text:
            return False
        
        try:
            await self.bot.send_message(
                chat_id=group_chat_id,
                text=weave_text,
                parse_mode="HTML",
            )
            logger.info("Posted memory weave to group", extra={"event_id": event.event_id})
            return True
        except Exception as e:
            logger.error(
                "Failed to post memory weave to group %s: %s",
                group_chat_id,
                e,
            )
            return False
    
    async def add_hashtags(
        self,
        event_id: int,
        hashtags: List[str],
    ) -> EventMemory:
        """Add group hashtags to event memory."""
        result = await self.session.execute(
            select(EventMemory).where(EventMemory.event_id == event_id)
        )
        memory = result.scalar_one_or_none()
        
        if not memory:
            memory = EventMemory(event_id=event_id)
            self.session.add(memory)
        
        memory.hashtags = hashtags[:3]  # Max 3 per PRD
        return memory
    
    async def add_outcome_marker(
        self,
        event_id: int,
        marker: Dict[str, Any],
    ) -> EventMemory:
        """
        Add outcome marker (e.g., "led to collaboration X").
        
        Marker format: {type, description, related_event_id?, created_at}
        """
        result = await self.session.execute(
            select(EventMemory).where(EventMemory.event_id == event_id)
        )
        memory = result.scalar_one_or_none()
        
        if not memory:
            memory = EventMemory(event_id=event_id)
            self.session.add(memory)
        
        if memory.outcome_markers is None:
            memory.outcome_markers = []
        
        memory.outcome_markers.append(marker)
        return memory
    
    async def link_lineage(
        self,
        current_event_id: int,
        prior_event_ids: List[int],
    ) -> EventMemory:
        """Link current event to prior similar events (lineage)."""
        result = await self.session.execute(
            select(EventMemory).where(EventMemory.event_id == current_event_id)
        )
        memory = result.scalar_one_or_none()
        
        if not memory:
            memory = EventMemory(event_id=current_event_id)
            self.session.add(memory)
        
        memory.lineage_event_ids = prior_event_ids
        logger.info(
            "Linked lineage: %s -> %s",
            current_event_id,
            prior_event_ids,
        )
        return memory
    
    async def get_memory_weave(self, event_id: int) -> Optional[EventMemory]:
        """Get memory weave for an event."""
        result = await self.session.execute(
            select(EventMemory).where(EventMemory.event_id == event_id)
        )
        return result.scalar_one_or_none()
    
    async def get_recent_memories(
        self,
        group_id: int,
        limit: int = 10,
    ) -> List[EventMemory]:
        """Get recent memory weaves for a group (for /recall)."""
        result = await self.session.execute(
            select(EventMemory)
            .join(Event)
            .where(Event.group_id == group_id)
            .order_by(EventMemory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def suggest_hashtags_from_lineage(
        self,
        event_type: str,
        group_id: int,
    ) -> List[str]:
        """Suggest hashtags based on prior similar events."""
        result = await self.session.execute(
            select(EventMemory.hashtags)
            .join(Event)
            .where(
                Event.group_id == group_id,
                Event.event_type == event_type,
            )
            .order_by(Event.created_at.desc())
            .limit(5)
        )
        
        all_hashtags = []
        for hashtags in result.scalars().all():
            if hashtags:
                all_hashtags.extend(hashtags)
        
        # Return most common (up to 3)
        from collections import Counter
        counts = Counter(all_hashtags)
        return [tag for tag, _ in counts.most_common(3)]
