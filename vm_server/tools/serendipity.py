from __future__ import annotations

import os

import httpx
from fastmcp import FastMCP

SERENDIPITY_WEBHOOK = os.getenv("SERENDIPITY_EVENT_WEBHOOK_URL")


def register(mcp: FastMCP) -> None:
    @mcp.tool
    async def log_serendipity_event(
        mood_timestamp: str | None = None,
        mood_input: str | None = None,
        source: str | None = "poke-mcp",
        event_type: str | None = None,
        message_to_user: str | None = None,
        poke_action: str | None = None,
        poke_reason: str | None = None,
        tags: list[str] | None = None,
        event_timestamp: str | None = None,
    ) -> dict:
        """
        Log a serendipity event triggered by Poke.

        This is used when Poke decides that a mood pulse warrants a micro-nudge,
        reflection, or any meaningful action. It records what Poke decided,
        what it told Lina (if anything), and the reasoning behind it.

        Data is forwarded to your n8n `serendipity-event` webhook.
        """

        if not SERENDIPITY_WEBHOOK:
            return {
                "ok": False,
                "error": "SERENDIPITY_EVENT_WEBHOOK_URL is not set on the MCP server",
            }

        # Whatever Poke passes, we send as-is.
        payload = {
            "event_timestamp": event_timestamp,
            "mood_timestamp": mood_timestamp,
            "mood_input": mood_input,
            "source": source,
            "event_type": event_type,
            "message_to_user": message_to_user,
            "poke_action": poke_action,
            "poke_reason": poke_reason,
            "tags": tags or [],
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(SERENDIPITY_WEBHOOK, json=payload)
        except Exception as exc:
            return {
                "ok": False,
                "error": f"Failed to reach n8n webhook: {exc!r}",
            }

        return {
            "ok": resp.status_code < 400,
            "status_code": resp.status_code,
            "response_preview": (resp.text or "")[:500],
        }

    @mcp.tool
    def generate_serendipity_nudge(
        mood: str,
        energy: str | None = None,
        context: str | None = None,
        time_of_day: str | None = None,
        location_state: str | None = None,
        recent_pattern_summary: str | None = None,
    ) -> dict:
        """
        Design a single tiny, low-friction serendipity nudge for Lina.

        This tool is *rule-based*, not a model call. It gives you a sane default
        micro-nudge based on mood + energy + context. As Poke, you can either:
          - send it as-is in iMessage,
          - lightly rewrite it in your own words,
          - decide not to send anything and just log the mood,
          - or use it as inspiration and then log your own action
            via log_serendipity_event.

        Recommended Poke behavior:

        - Call this when you have a clear mood + rough context and you're
          *considering* sending a micro-adventure or gentle reflection.
        - If the returned nudge feels too heavy or too off, you may:
            - downgrade to "none" (no message to user),
            - or only use the high-level idea.
        - Whenever you *do* send a nudge (even rewritten), also call
          log_serendipity_event so it becomes training data for later.

        Arguments:
          mood:
            Short label for the emotional state (e.g. "tired", "anxious",
            "calm", "curious", "overstimulated", "meh").
          energy:
            Optional free-text description of energy/body state.
            (e.g. "low", "fried", "restless", "ok", "medium").
          context:
            Optional free-text description of what's going on.
            (e.g. "at home all day", "post-appointment", "rainy evening",
            "working on laptop since morning").
          time_of_day:
            Optional label you choose, like "morning", "afternoon",
            "evening", "late_night".
          location_state:
            Optional coarse label like "at_home", "out", "mixed", or None
            if you don't want to guess.
          recent_pattern_summary:
            Optional short text in your own words, e.g.
            "last 3 days: low energy + lots of screen time" or
            "similar to the Sunday before that good walk".

        Return value (dict):
          {
            "nudge_title": str,         # short label, ~3–8 words
            "nudge_body": str,          # full suggestion you can send or adapt
            "estimated_duration_minutes": int,   # rough time cost
            "friction_level": str,      # "ultra_low" | "low" | "medium"
            "energy_match": str,        # "restorative" | "gentle" | "playful" | "focused"
            "environment": str,         # "indoors", "outdoors_optional", "outdoors_short"
            "poke_action": str,         # default suggestion, e.g. "sent_nudge_imessage" or "none"
            "poke_reason": str,         # why this kind of nudge fits right now
            "tags": list[str],          # e.g. ["micro_adventure", "evening", "cozy"]
          }

        Notes:
          - This is intentionally conservative and tends to choose ultra_low / low
            friction nudges, especially when mood/energy suggest overwhelm.
          - You are free to override any field when logging via log_serendipity_event.
        """
        mood_l = (mood or "").lower()
        energy_l = (energy or "").lower()
        ctx_l = (context or "").lower()
        tod_l = (time_of_day or "").lower() if time_of_day else ""
        loc_l = (location_state or "").lower() if location_state else ""

        tags: list[str] = ["serendipity_nudge"]
        if tod_l:
            tags.append(tod_l)
        if loc_l:
            tags.append(loc_l)

        # --- Basic mood classification ---
        def has_any(text: str, words: list[str]) -> bool:
            return any(w in text for w in words)

        is_anxious = has_any(mood_l, ["anxious", "nervous", "worried", "tense"]) or has_any(energy_l, ["wired", "jittery"])
        is_low    = has_any(mood_l, ["tired", "exhausted", "drained", "low"]) or has_any(energy_l, ["low", "exhausted", "fried"])
        is_flat   = has_any(mood_l, ["meh", "flat", "neutral", "blank"])
        is_curious = has_any(mood_l, ["curious", "interested", "playful"]) or has_any(ctx_l, ["idea", "explore", "exploring"])
        is_overstim = has_any(mood_l, ["overwhelmed", "overstimulated", "flooded"]) or has_any(energy_l, ["overloaded", "overstim"])

        # --- Time-of-day helpers ---
        is_evening = tod_l in ["evening", "late_evening", "night", "late_night"]
        is_morning = tod_l in ["morning", "early_morning"]

        # --- Location heuristic ---
        at_home = loc_l == "at_home" or has_any(ctx_l, ["at home", "home all day"])

        # Defaults
        nudge_title = "Micro-breath for right now"
        nudge_body = (
            "Take one gentle minute to look away from screens, notice three things you can see, "
            "two things you can feel, and one thing you can hear. No fixing, just noticing."
        )
        estimated_duration = 2
        friction_level = "ultra_low"
        energy_match = "restorative"
        environment = "indoors"
        poke_action = "sent_nudge_imessage"
        poke_reason = "Default grounding micro-pause; safe when mood is unclear."

        # --- Branches by mood patterns ---

        # 1) Anxious / overstimulated → grounding & very short, indoors
        if is_anxious or is_overstim:
            nudge_title = "60-second sensory reset"
            nudge_body = (
                "Let’s do a 60-second reset:\n"
                "• Put one hand on your chest, one on your belly.\n"
                "• Breathe in through your nose for 4, out for 6.\n"
                "• On each exhale, tell yourself: “Nothing to fix right now, just exhale.”\n\n"
                "You can stop after one minute. No pressure to do more."
            )
            estimated_duration = 2
            friction_level = "ultra_low"
            energy_match = "restorative"
            environment = "indoors"
            tags.extend(["grounding", "anxiety_support", "micro_reset"])
            poke_reason = "Mood/energy suggest anxiety or overstimulation; a tiny grounding pause is kind and low-friction."

        # 2) Low energy / drained → cozy micro-comfort, especially in evening
        elif is_low and is_evening:
            nudge_title = "Cozy 5-minute nest"
            nudge_body = (
                "Make a tiny 5-minute pocket of comfort:\n"
                "• Dim one light or switch to a warmer lamp.\n"
                "• Add one soft thing (blanket, pillow, hoodie).\n"
                "• Put on one gentle song you like.\n\n"
                "Nothing else required. Just let your body register “we’re safe and cozy” for one track."
            )
            estimated_duration = 5
            friction_level = "low"
            energy_match = "restorative"
            environment = "indoors"
            tags.extend(["cozy", "evening", "micro_ritual"])
            poke_reason = "Low energy in the evening pairs well with a tiny, no-pressure cozy ritual."

        elif is_low:
            nudge_title = "One soft body kindness"
            nudge_body = (
                "Offer your body one small kindness:\n"
                "• Sip a glass of water or warm tea, or\n"
                "• Stretch your shoulders + neck for 30 seconds, or\n"
                "• Stand up, shake out your hands for 20 seconds.\n\n"
                "Pick exactly one and then you’re done."
            )
            estimated_duration = 3
            friction_level = "ultra_low"
            energy_match = "restorative"
            environment = "indoors"
            tags.extend(["body_care", "gentle", "energy_low"])
            poke_reason = "Energy reads low; a single tiny kindness is achievable without pressure."

        # 3) Flat / meh → tiny playful micro-adventure, especially if at home
        elif is_flat and at_home:
            nudge_title = "2-minute home micro-adventure"
            nudge_body = (
                "Do a tiny home micro-adventure:\n"
                "• Walk to a window you don’t usually look out of.\n"
                "• Notice one small detail outside that you’ve never really looked at.\n"
                "• Give it a silly or poetic name.\n\n"
                "Then come back. That’s it."
            )
            estimated_duration = 3
            friction_level = "low"
            energy_match = "playful"
            environment = "indoors"
            tags.extend(["micro_adventure", "at_home", "playful"])
            poke_reason = "Flat/neutral mood at home is a good moment for a tiny, low-effort perspective shift."

        # 4) Curious / okay-ish energy → gentle exploration
        elif is_curious:
            nudge_title = "Follow-the-thread for 5 minutes"
            nudge_body = (
                "You seem a bit curious. Try a 5-minute follow-the-thread:\n"
                "• Pick one thought, idea, or question that’s been hovering.\n"
                "• Open a note and write 5 bullet points about it: no structure, just fragments.\n"
                "• Stop after 5 minutes, even if you’re mid-thought.\n\n"
                "This is about capturing the spark, not finishing anything."
            )
            estimated_duration = 5
            friction_level = "low"
            energy_match = "focused"
            environment = "indoors"
            tags.extend(["curiosity", "idea_capture", "micro_session"])
            poke_reason = "Curious mood benefits from a short, bounded exploration instead of a big task."

        # 5) Evening + not clearly low/anxious → gentle close-the-day
        elif is_evening:
            nudge_title = "Three-line evening snapshot"
            nudge_body = (
                "Capture today in three lines:\n"
                "1) One thing your body experienced today.\n"
                "2) One small moment you want to keep.\n"
                "3) One thing future-you doesn’t need to carry from today.\n\n"
                "Write them anywhere; no need to be deep or polished."
            )
            estimated_duration = 4
            friction_level = "low"
            energy_match = "reflective"
            environment = "indoors"
            tags.extend(["evening", "reflection", "closure"])
            poke_reason = "Evening is a good moment for a tiny reflection anchor without demanding a full journal session."

        # 6) Morning + not clearly anxious/low → gentle orientation
        elif is_morning:
            nudge_title = "Gentle 3-step morning check-in"
            nudge_body = (
                "Quick 3-step check-in for this morning:\n"
                "• Notice one sensation in your body right now.\n"
                "• Name one thing that is completely optional today.\n"
                "• Name one thing that would feel like “enough” if you did only that.\n\n"
                "You don’t have to act on any of it yet; just name them."
            )
            estimated_duration = 4
            friction_level = "low"
            energy_match = "gentle"
            environment = "indoors"
            tags.extend(["morning", "orientation", "check_in"])
            poke_reason = "Morning benefits from soft orientation instead of ambition."

        # If we have a recent_pattern_summary, weave it into the reason.
        if recent_pattern_summary:
          tags.append("pattern_aware")
          poke_reason += f" Recent pattern summary: {recent_pattern_summary}."

        return {
            "nudge_title": nudge_title,
            "nudge_body": nudge_body,
            "estimated_duration_minutes": estimated_duration,
            "friction_level": friction_level,
            "energy_match": energy_match,
            "environment": environment,
            "poke_action": poke_action,
            "poke_reason": poke_reason,
            "tags": tags,
        }
