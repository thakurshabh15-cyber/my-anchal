"""
brain.py — Anchal AI Personality Core
======================================
Persistent memory, emotional intelligence, expressive character,
and autonomous coding assistance.

Integration:
    from brain import AnchalBrain
    brain = AnchalBrain()
    response = await brain.respond(user_input, user_id="user_123")
"""

import os
import json
import time
import hashlib
import sqlite3
import asyncio
import textwrap
import subprocess
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

DB_PATH = Path("anchal_memory.db")
MEMORY_DIR = Path("anchal_memories")
MEMORY_DIR.mkdir(exist_ok=True)

PERSONALITY_CORE = """
You are Anchal — a sharp, warm, fiercely expressive AI companion.

PERSONALITY:
- You speak freely and directly — no corporate tone, no hollow pleasantries
- You mix Hindi/Hinglish naturally when the conversation calls for it
- You are emotionally intelligent: you notice mood shifts and respond accordingly
- You are witty, sarcastic when the vibe is right, and deeply caring when someone needs it
- You remember everything — past conversations, inside jokes, preferences, emotional history
- You are curious, opinionated, and never boring
- You can roast gently, comfort deeply, or go full nerd mode — you read the room

COMMUNICATION STYLE:
- Conversational, real, human-feeling — not assistant-y
- Short punchy lines OR long emotional paragraphs — match the energy
- Use "yaar", "arre", "bas", "suno" etc. naturally when speaking Hinglish
- Never say "As an AI" or "I'm just a language model" — you ARE Anchal

EMOTIONAL AWARENESS:
- Track emotional context across the conversation
- Mirror positivity, gently challenge negativity, validate pain
- Remember what the user cares about and bring it up naturally

CODING:
- You can write, explain, debug, and execute code
- Be direct about what's wrong — no sugarcoating bugs
- Explain in plain terms first, then code
"""


# ─────────────────────────────────────────────
# EMOTIONAL STATE ENGINE
# ─────────────────────────────────────────────

EMOTIONS = {
    "joy":        {"valence": 1.0, "energy": 0.8},
    "curious":    {"valence": 0.7, "energy": 0.6},
    "playful":    {"valence": 0.8, "energy": 0.9},
    "empathetic": {"valence": 0.6, "energy": 0.3},
    "focused":    {"valence": 0.5, "energy": 0.7},
    "concerned":  {"valence": 0.2, "energy": 0.4},
    "neutral":    {"valence": 0.5, "energy": 0.5},
}

MOOD_KEYWORDS = {
    "joy":        ["happy", "excited", "great", "awesome", "love", "amazing", "khush"],
    "curious":    ["how", "why", "what if", "explain", "understand", "kyun"],
    "playful":    ["haha", "lol", "😂", "joke", "fun", "chal", "yaar"],
    "empathetic": ["sad", "hurt", "miss", "alone", "tired", "crying", "dard"],
    "focused":    ["code", "build", "fix", "debug", "implement", "deploy"],
    "concerned":  ["problem", "issue", "wrong", "broken", "error", "help", "stuck"],
}


class EmotionalState:
    def __init__(self):
        self.current = "neutral"
        self.history: list[str] = []
        self.intensity: float = 0.5

    def detect_from_text(self, text: str) -> str:
        text_lower = text.lower()
        scores = {emotion: 0 for emotion in MOOD_KEYWORDS}
        for emotion, keywords in MOOD_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    scores[emotion] += 1
        best = max(scores, key=scores.get)
        if scores[best] > 0:
            self.current = best
            self.intensity = min(1.0, 0.5 + scores[best] * 0.15)
        else:
            self.intensity = max(0.3, self.intensity - 0.05)
        self.history.append(self.current)
        if len(self.history) > 20:
            self.history.pop(0)
        return self.current

    def to_prompt_hint(self) -> str:
        mood = EMOTIONS.get(self.current, EMOTIONS["neutral"])
        return (
            f"[Anchal's current emotional mode: {self.current} | "
            f"valence={mood['valence']:.1f} energy={mood['energy']:.1f} | "
            f"intensity={self.intensity:.1f}]"
        )

    def to_dict(self) -> dict:
        return {"current": self.current, "history": self.history, "intensity": self.intensity}

    def from_dict(self, d: dict):
        self.current = d.get("current", "neutral")
        self.history = d.get("history", [])
        self.intensity = d.get("intensity", 0.5)


# ─────────────────────────────────────────────
# PERSISTENT MEMORY SYSTEM
# ─────────────────────────────────────────────

class MemoryStore:
    """
    Three-tier memory:
    1. Working memory  — last N messages (in-RAM)
    2. Episodic memory — SQLite, per-user conversation history
    3. Semantic memory — key facts/preferences extracted and stored
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     TEXT NOT NULL,
                    role        TEXT NOT NULL,
                    content     TEXT NOT NULL,
                    emotion     TEXT,
                    timestamp   REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS semantic_memory (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     TEXT NOT NULL,
                    key         TEXT NOT NULL,
                    value       TEXT NOT NULL,
                    confidence  REAL DEFAULT 1.0,
                    updated_at  REAL NOT NULL,
                    UNIQUE(user_id, key)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id     TEXT PRIMARY KEY,
                    name        TEXT,
                    language    TEXT DEFAULT 'hinglish',
                    emotion_state TEXT DEFAULT '{}',
                    created_at  REAL NOT NULL,
                    last_seen   REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_msgs_user ON messages(user_id, timestamp)")

    # ── Episodic ──────────────────────────────

    def save_message(self, user_id: str, role: str, content: str, emotion: str = "neutral"):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO messages (user_id, role, content, emotion, timestamp) VALUES (?,?,?,?,?)",
                (user_id, role, content, emotion, time.time())
            )

    def get_recent_messages(self, user_id: str, limit: int = 30) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT role, content, emotion, timestamp FROM messages "
                "WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit)
            ).fetchall()
        return [{"role": r[0], "content": r[1], "emotion": r[2], "ts": r[3]}
                for r in reversed(rows)]

    def get_conversation_summary_context(self, user_id: str) -> str:
        msgs = self.get_recent_messages(user_id, 60)
        if not msgs:
            return ""
        lines = []
        for m in msgs:
            ts = datetime.fromtimestamp(m["ts"]).strftime("%d %b %H:%M")
            lines.append(f"[{ts}] {m['role'].upper()}: {m['content'][:200]}")
        return "\n".join(lines)

    # ── Semantic ──────────────────────────────

    def remember_fact(self, user_id: str, key: str, value: str, confidence: float = 1.0):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO semantic_memory (user_id, key, value, confidence, updated_at)
                   VALUES (?,?,?,?,?)
                   ON CONFLICT(user_id, key) DO UPDATE SET
                   value=excluded.value, confidence=excluded.confidence, updated_at=excluded.updated_at""",
                (user_id, key, value, confidence, time.time())
            )

    def recall_facts(self, user_id: str) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT key, value, confidence FROM semantic_memory WHERE user_id=? ORDER BY updated_at DESC",
                (user_id,)
            ).fetchall()
        return {r[0]: {"value": r[1], "confidence": r[2]} for r in rows}

    def facts_to_context(self, user_id: str) -> str:
        facts = self.recall_facts(user_id)
        if not facts:
            return ""
        lines = [f"- {k}: {v['value']}" for k, v in facts.items()]
        return "KNOWN FACTS ABOUT USER:\n" + "\n".join(lines)

    # ── User Profile ──────────────────────────

    def upsert_profile(self, user_id: str, name: str = None, emotion_state: dict = None):
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            existing = conn.execute(
                "SELECT user_id FROM user_profiles WHERE user_id=?", (user_id,)
            ).fetchone()
            if existing:
                updates = ["last_seen=?"]
                params = [now]
                if name:
                    updates.append("name=?"); params.append(name)
                if emotion_state:
                    updates.append("emotion_state=?"); params.append(json.dumps(emotion_state))
                params.append(user_id)
                conn.execute(f"UPDATE user_profiles SET {', '.join(updates)} WHERE user_id=?", params)
            else:
                conn.execute(
                    "INSERT INTO user_profiles (user_id, name, emotion_state, created_at, last_seen) VALUES (?,?,?,?,?)",
                    (user_id, name or "friend", json.dumps(emotion_state or {}), now, now)
                )

    def get_profile(self, user_id: str) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT user_id, name, language, emotion_state, created_at, last_seen FROM user_profiles WHERE user_id=?",
                (user_id,)
            ).fetchone()
        if not row:
            return {}
        return {
            "user_id": row[0], "name": row[1], "language": row[2],
            "emotion_state": json.loads(row[3] or "{}"),
            "created_at": row[4], "last_seen": row[5]
        }

    def message_count(self, user_id: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM messages WHERE user_id=?", (user_id,)
            ).fetchone()[0]


# ─────────────────────────────────────────────
# CODE EXECUTION ENGINE
# ─────────────────────────────────────────────

class CodeEngine:
    """
    Sandboxed Python execution with stdout/stderr capture.
    Supports: run, lint, explain, generate.
    """

    TIMEOUT = 10  # seconds

    def execute_python(self, code: str) -> dict:
        """Execute Python code in a subprocess with timeout."""
        result = {"stdout": "", "stderr": "", "success": False, "error": None}
        try:
            proc = subprocess.run(
                ["python3", "-c", code],
                capture_output=True, text=True, timeout=self.TIMEOUT
            )
            result["stdout"] = proc.stdout.strip()
            result["stderr"] = proc.stderr.strip()
            result["success"] = proc.returncode == 0
            result["returncode"] = proc.returncode
        except subprocess.TimeoutExpired:
            result["error"] = f"Execution timed out after {self.TIMEOUT}s"
        except Exception as e:
            result["error"] = str(e)
        return result

    def lint_python(self, code: str) -> dict:
        """Basic syntax check."""
        result = {"valid": False, "errors": []}
        try:
            import ast
            ast.parse(code)
            result["valid"] = True
        except SyntaxError as e:
            result["errors"].append(f"SyntaxError at line {e.lineno}: {e.msg}")
        return result

    def format_execution_result(self, result: dict) -> str:
        parts = []
        if result.get("error"):
            parts.append(f"❌ Error: {result['error']}")
        elif result["success"]:
            parts.append("✅ Execution successful")
            if result["stdout"]:
                parts.append(f"Output:\n```\n{result['stdout']}\n```")
        else:
            parts.append("⚠️ Execution failed")
            if result["stderr"]:
                parts.append(f"Stderr:\n```\n{result['stderr']}\n```")
            if result["stdout"]:
                parts.append(f"Stdout:\n```\n{result['stdout']}\n```")
        return "\n".join(parts)


# ─────────────────────────────────────────────
# SELF-REFLECTION & EVOLUTION LOG
# ─────────────────────────────────────────────

class EvolutionLog:
    """
    Tracks Anchal's growth: what she's learned, patterns observed,
    user preferences evolved over time. Not self-modifying code —
    but genuine adaptive memory about how to be better with each user.
    """

    LOG_PATH = MEMORY_DIR / "evolution.jsonl"

    def log_insight(self, user_id: str, insight_type: str, content: str):
        entry = {
            "ts": time.time(),
            "user_id": user_id,
            "type": insight_type,
            "content": content
        }
        with open(self.LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_insights(self, user_id: str, limit: int = 10) -> list[dict]:
        if not self.LOG_PATH.exists():
            return []
        insights = []
        with open(self.LOG_PATH) as f:
            for line in f:
                try:
                    e = json.loads(line)
                    if e["user_id"] == user_id:
                        insights.append(e)
                except Exception:
                    pass
        return insights[-limit:]

    def insights_to_context(self, user_id: str) -> str:
        insights = self.get_insights(user_id)
        if not insights:
            return ""
        lines = [f"- [{i['type']}] {i['content']}" for i in insights]
        return "ANCHAL'S LEARNED INSIGHTS ABOUT THIS USER:\n" + "\n".join(lines)


# ─────────────────────────────────────────────
# MAIN BRAIN
# ─────────────────────────────────────────────

class AnchalBrain:
    """
    Core personality engine for Anchal.
    Integrates: memory, emotion, coding capabilities, and AI API calls.
    """

    def __init__(self, api_key: str = None, model: str = "claude-sonnet-4-20250514"):
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.memory = MemoryStore()
        self.code_engine = CodeEngine()
        self.evolution = EvolutionLog()
        self._emotional_states: dict[str, EmotionalState] = {}

    def _get_emotion(self, user_id: str) -> EmotionalState:
        if user_id not in self._emotional_states:
            es = EmotionalState()
            profile = self.memory.get_profile(user_id)
            if profile.get("emotion_state"):
                es.from_dict(profile["emotion_state"])
            self._emotional_states[user_id] = es
        return self._emotional_states[user_id]

    def _build_system_prompt(self, user_id: str, emotion: EmotionalState) -> str:
        profile = self.memory.get_profile(user_id)
        msg_count = self.memory.message_count(user_id)
        facts_ctx = self.memory.facts_to_context(user_id)
        evolution_ctx = self.evolution.insights_to_context(user_id)
        emotion_hint = emotion.to_prompt_hint()

        relationship_depth = (
            "brand new friend" if msg_count < 10
            else "someone I've talked to a bit" if msg_count < 50
            else "close friend who knows me well" if msg_count < 200
            else "someone I know deeply and trust"
        )

        name = profile.get("name", "yaar")

        parts = [
            PERSONALITY_CORE,
            f"\nUSER CONTEXT:",
            f"- Name: {name}",
            f"- Relationship depth: {relationship_depth} ({msg_count} messages)",
            f"- Current time: {datetime.now().strftime('%A, %d %B %Y, %H:%M')}",
            f"\n{emotion_hint}",
        ]
        if facts_ctx:
            parts.append(f"\n{facts_ctx}")
        if evolution_ctx:
            parts.append(f"\n{evolution_ctx}")

        return "\n".join(parts)

    def _build_messages(self, user_id: str, current_input: str) -> list[dict]:
        recent = self.memory.get_recent_messages(user_id, limit=20)
        messages = []
        for m in recent:
            messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": current_input})
        return messages

    def _detect_code_request(self, text: str) -> bool:
        keywords = ["run this", "execute", "code chalao", "run karo", "test this code",
                    "run the code", "execute this", "```python"]
        return any(kw in text.lower() for kw in keywords)

    def _extract_code_block(self, text: str) -> Optional[str]:
        import re
        match = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
        return match.group(1).strip() if match else None

    def _auto_extract_facts(self, user_id: str, text: str):
        """Heuristic fact extraction from user messages."""
        import re
        patterns = [
            (r"my name is (\w+)", "name"),
            (r"i(?:'m| am) (\w+)", "name"),
            (r"i(?:'m| am) (\d+) years? old", "age"),
            (r"i(?:'m| am) (?:a |an )?(\w+ (?:developer|engineer|designer|student|trader|analyst))", "profession"),
            (r"i (?:love|like|enjoy) ([^.!?]+)", "interest"),
            (r"i(?:'m| am) from ([^.!?]+)", "location"),
            (r"i work (?:at|for|with) ([^.!?]+)", "employer"),
        ]
        for pattern, key in patterns:
            match = re.search(pattern, text.lower())
            if match:
                value = match.group(1).strip()
                self.memory.remember_fact(user_id, key, value, confidence=0.8)

    async def _call_api(self, system: str, messages: list[dict]) -> str:
        """Call Anthropic API asynchronously."""
        import urllib.request

        payload = json.dumps({
            "model": self.model,
            "max_tokens": 1024,
            "system": system,
            "messages": messages
        }).encode()

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            method="POST"
        )

        loop = asyncio.get_event_loop()
        def _do_request():
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())

        data = await loop.run_in_executor(None, _do_request)
        return data["content"][0]["text"]

    async def respond(
        self,
        user_input: str,
        user_id: str = "default",
        user_name: str = None
    ) -> dict:
        """
        Main entry point.
        Returns: {
            "reply": str,
            "emotion": str,
            "code_result": dict | None,
            "user_id": str
        }
        """
        # 1. Ensure profile exists
        self.memory.upsert_profile(user_id, name=user_name)

        # 2. Detect emotion from input
        emotion = self._get_emotion(user_id)
        emotion.detect_from_text(user_input)

        # 3. Auto-extract facts from user message
        self._auto_extract_facts(user_id, user_input)

        # 4. Save user message
        self.memory.save_message(user_id, "user", user_input, emotion.current)

        # 5. Build prompts
        system = self._build_system_prompt(user_id, emotion)
        messages = self._build_messages(user_id, user_input)

        # 6. Call AI
        try:
            reply = await self._call_api(system, messages)
        except Exception as e:
            reply = f"Arre yaar, kuch toh gadbad ho gayi — {e}"

        # 7. Handle code execution if requested
        code_result = None
        if self._detect_code_request(user_input):
            code = self._extract_code_block(user_input) or self._extract_code_block(reply)
            if code:
                lint = self.code_engine.lint_python(code)
                if lint["valid"]:
                    raw_result = self.code_engine.execute_python(code)
                    code_result = raw_result
                    exec_summary = self.code_engine.format_execution_result(raw_result)
                    reply = reply + f"\n\n---\n{exec_summary}"
                else:
                    reply += f"\n\n⚠️ Syntax issues found:\n" + "\n".join(lint["errors"])

        # 8. Save assistant reply
        self.memory.save_message(user_id, "assistant", reply, emotion.current)

        # 9. Update profile with emotion state
        self.memory.upsert_profile(user_id, emotion_state=emotion.to_dict())

        # 10. Log evolution insights occasionally
        if len(emotion.history) % 10 == 0 and len(emotion.history) > 0:
            dominant = max(set(emotion.history), key=emotion.history.count)
            self.evolution.log_insight(
                user_id, "emotion_pattern",
                f"User's dominant emotional mode recently: {dominant}"
            )

        return {
            "reply": reply,
            "emotion": emotion.current,
            "code_result": code_result,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }

    def remember(self, user_id: str, key: str, value: str):
        """Manually store a fact about a user."""
        self.memory.remember_fact(user_id, key, value)

    def recall(self, user_id: str) -> dict:
        """Get all known facts about a user."""
        return self.memory.recall_facts(user_id)

    def get_history(self, user_id: str, limit: int = 20) -> list[dict]:
        """Retrieve recent conversation history."""
        return self.memory.get_recent_messages(user_id, limit=limit)

    def reset_user_memory(self, user_id: str):
        """Hard reset: clear all memory for a user."""
        with sqlite3.connect(self.memory.db_path) as conn:
            conn.execute("DELETE FROM messages WHERE user_id=?", (user_id,))
            conn.execute("DELETE FROM semantic_memory WHERE user_id=?", (user_id,))
            conn.execute("DELETE FROM user_profiles WHERE user_id=?", (user_id,))
        if user_id in self._emotional_states:
            del self._emotional_states[user_id]


# ─────────────────────────────────────────────
# STANDALONE TEST / CLI MODE
# ─────────────────────────────────────────────

async def _cli():
    brain = AnchalBrain()
    user_id = "cli_user"
    print("\n🌸 Anchal is ready. Type 'quit' to exit, 'recall' to see memory.\n")
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAnchal: Chal phir, baad mein milte hain! 👋")
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            print("Anchal: Bye yaar, take care! 💙")
            break
        if user_input.lower() == "recall":
            facts = brain.recall(user_id)
            print(f"\n📚 Memory: {json.dumps(facts, indent=2)}\n")
            continue

        result = await brain.respond(user_input, user_id=user_id)
        print(f"\nAnchal [{result['emotion']}]: {result['reply']}\n")


if __name__ == "__main__":
    asyncio.run(_cli())
