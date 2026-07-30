from __future__ import annotations

import re
from typing import Optional, Dict, Any, List

from avrae.avrae_parser import AvraeParserService


class AvraeFeedbackService:
    """Process incoming Avrae messages and link them to pending checks.

    Expected workflow:
      - GameCog.search stores a pending_avrae_check in channel_repo with fields:
        {type: 'search', search_type: 'secret'|'trap'|'treasure', initiator_id: str,
         candidates: [{id: str, source: 'node'|'edge', dc: int}], created_at: timestamp}
      - When an Avrae message arrives, this service parses the roll and, if a pending
        check exists for the channel, calls session.search with the roll and DC.
    """

    PENDING_TTL_SECONDS = 120

    def __init__(self, channel_repo, campaign_manager):
        self.channel_repo = channel_repo
        self.campaign_manager = campaign_manager

    def process_avrae_message(self, message) -> Optional[Dict[str, Any]]:
        # Extract full text
        text = AvraeParserService.extract_full_text(message)
        if not text:
            return None

        # Parse roll results
        rolls = AvraeParserService.extract_roll_results(text)
        if not rolls:
            return None

        # Determine check type from Avrae message header if present
        check_type = None
        if re.search(r"Perception check", text, re.I):
            check_type = "perception"
        elif re.search(r"Investigation check", text, re.I) or re.search(r"Investigation", text, re.I):
            check_type = "investigation"

        if not check_type:
            # try to infer from actor line
            if any(re.search(r"makes a Perception check", part.get("actor", "") if isinstance(part, dict) else "", re.I) for part in rolls):
                check_type = "perception"

        # If still unknown, bail
        if not check_type:
            return None

        # Use the first roll total as the authoritative roll
        total = rolls[0].get("total") if isinstance(rolls[0], dict) else None
        if total is None:
            return None

        channel_id = str(message.channel.id)
        state = self.channel_repo.get_state(channel_id) or {}
        pending = state.get("pending_avrae_check")
        if not pending:
            return None

        # Validate TTL
        import time
        created = pending.get("created_at", 0)
        if time.time() - created > self.PENDING_TTL_SECONDS:
            # stale
            self.channel_repo.update_field(channel_id, "pending_avrae_check", None)
            return None

        # Verify check mapping
        mapping = {"secret": "perception", "trap": "investigation", "treasure": "investigation"}
        expected = mapping.get(pending.get("search_type"))
        if expected != check_type:
            return None

        # Now call session.search with roll; pick candidates
        session = self.campaign_manager.get_session(channel_id)
        if not session:
            return None

        # If candidates present, check each candidate's dc against the roll and aggregate results
        candidates = pending.get("candidates", [])
        candidate_results: List[Dict[str, Any]] = []
        for c in candidates:
            candidate_dc = c.get("dc", pending.get("dc", 15))
            success = total >= int(candidate_dc)
            candidate_results.append({"id": c.get("id"), "source": c.get("source"), "dc": candidate_dc, "roll": total, "success": success})

        # Call session.search once using the standard DC (first candidate or default) so engine can produce message
        engine_dc = candidates[0].get("dc") if candidates else pending.get("dc", 15)
        result = session.search(search_type=pending.get("search_type"), dc=int(engine_dc), roll=int(total))

        # Clear pending
        self.channel_repo.update_field(channel_id, "pending_avrae_check", None)

        # Return a dict that the caller (router) can use to send messages
        return {"session_result": result, "candidate_results": candidate_results}
