import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


# ---------- Paths ----------
def get_root(explicit_root: Optional[str] = None) -> Path:
    if explicit_root:
        return Path(explicit_root).resolve()
    # default: folder containing this script
    return Path(__file__).resolve().parent


def worlds_dir(root: Path) -> Path:
    return root / "worlds"


def sessions_dir(root: Path) -> Path:
    return root / "sessions"


# ---------- JSON helpers ----------
def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def safe_mkdir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


# ---------- Ollama ----------
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"


def ollama_chat(model: str, messages: List[Dict[str, str]], stream: bool = False, timeout_s: int = 600) -> str:
    payload = {
        "model": model,
        "stream": stream,
        "messages": messages,
    }
    r = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=timeout_s)
    r.raise_for_status()
    data = r.json()
    # expected: {"message":{"role":"assistant","content":"..."}...}
    content = (data.get("message") or {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Model returned empty content.")
    return content


# ---------- Message log (jsonl) ----------
def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    # Never write null content lines
    if obj.get("role") in ("user", "assistant", "system"):
        if "content" in obj and obj["content"] is None:
            return
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            # ignore bad lines
            continue
    return out


# ---------- Core data ----------
@dataclass
class SessionInfo:
    session_id: str
    world_id: str
    created_at: str
    params: Dict[str, Any]


def read_session_info(session_dir: Path) -> SessionInfo:
    sj = read_json(session_dir / "session.json")
    return SessionInfo(
        session_id=str(sj["session_id"]),
        world_id=str(sj["world_id"]),
        created_at=str(sj.get("created_at", "")),
        params=dict(sj.get("params", {})),
    )


def get_model_from_session(si: SessionInfo) -> str:
    m = si.params.get("model")
    return str(m) if m else "qwen3:8b"


# ---------- Character cards ----------
def load_character(world_path: Path, char_id: str) -> Tuple[str, str]:
    """
    Returns: (display_name, character_block_text)
    """
    char_path = world_path / "characters" / f"{char_id}.json"
    if not char_path.exists():
        raise FileNotFoundError(f"Character not found: {char_path}")

    c = read_json(char_path)
    display = str(c.get("display_name") or c.get("id") or char_id)

    def bullets(key: str) -> str:
        arr = c.get(key) or []
        if not isinstance(arr, list):
            arr = [str(arr)]
        return "\n".join([f"- {str(x)}" for x in arr])

    character_block = f"""Character to speak as:
- id: {c.get("id", char_id)}
- name: {display}

Persona:
{bullets("persona")}

Style:
{bullets("style")}

Limits:
{bullets("limits")}

Seed facts:
{bullets("seed_facts")}

Instruction:
Respond as {display} speaking in first-person dialogue, staying in character.
"""
    return display, character_block


# ---------- Commands ----------
def cmd_worlds(root: Path) -> None:
    wdir = worlds_dir(root)
    safe_mkdir(wdir)
    items = sorted([p.name for p in wdir.iterdir() if p.is_dir()])
    if not items:
        print(f"No worlds found in: {wdir}")
        return
    print("Worlds:")
    for w in items:
        print(f"  - {w}")


def create_session_skeleton(root: Path, world_id: str, model: str = "qwen3:8b") -> Path:
    wpath = worlds_dir(root) / world_id
    if not wpath.exists():
        raise FileNotFoundError(f"World not found: {wpath}")

    spath = wpath / "system_prompt.txt"
    if not spath.exists():
        raise FileNotFoundError(f"Missing system_prompt.txt in world: {wpath}")

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    session_id = f"{ts}_{world_id}_0001"  # keep your current naming (you skipped auto-increment)
    sdir = sessions_dir(root) / session_id
    safe_mkdir(sdir)

    write_json(sdir / "session.json", {
        "session_id": session_id,
        "world_id": world_id,
        "created_at": now_iso(),
        "params": {"temperature": 0.8, "top_p": 0.9, "max_tokens": 2048, "model": model},
    })
    write_json(sdir / "state.json", {"time": "day_1_morning", "location": "unknown", "flags": {}})
    write_json(sdir / "memory.json", {"long_term_memory": []})
    (sdir / "messages.jsonl").write_text("", encoding="utf-8")
    return sdir


def cmd_new(root: Path, world_id: str) -> None:
    safe_mkdir(worlds_dir(root))
    safe_mkdir(sessions_dir(root))

    sdir = create_session_skeleton(root, world_id, model="qwen3:8b")
    si = read_session_info(sdir)
    model = get_model_from_session(si)

    wpath = worlds_dir(root) / world_id
    system_text = (wpath / "system_prompt.txt").read_text(encoding="utf-8")

    log_path = sdir / "messages.jsonl"

    try:
        assistant = ollama_chat(model=model, messages=[
            {"role": "system", "content": system_text}
        ], stream=False)

        # write only if valid
        t1 = now_iso()
        t2 = (datetime.now() + timedelta(seconds=1)).replace(microsecond=0).isoformat()
        append_jsonl(log_path, {"ts": t1, "role": "system", "content": system_text})
        append_jsonl(log_path, {"ts": t2, "role": "assistant", "content": assistant})

        print(f"OK. Created session (with opening): {si.session_id}")
        print(f"Path: {sdir}")
    except Exception as e:
        print("WARN: Session created, but opening generation failed.")
        print(f"Reason: {e}")
        print("You can still use this session; messages.jsonl was left empty (no null lines).")
        print(f"Session: {si.session_id}")
        print(f"Path: {sdir}")


def cmd_sessions(root: Path, world_id: Optional[str]) -> None:
    sdir = sessions_dir(root)
    safe_mkdir(sdir)

    dirs = [p for p in sdir.iterdir() if p.is_dir()]
    dirs.sort(key=lambda p: p.name, reverse=True)

    if world_id:
        pat = f"_{re.escape(world_id)}_"
        dirs = [d for d in dirs if re.search(pat, d.name)]

    if not dirs:
        print("No sessions found" + (f" for world: {world_id}" if world_id else ""))
        return

    rows = []
    for d in dirs:
        logp = d / "messages.jsonl"
        msg_count = 0
        last_write = d.stat().st_mtime
        if logp.exists():
            lines = [ln for ln in logp.read_text(encoding="utf-8").splitlines() if ln.strip()]
            msg_count = len(lines)
            last_write = logp.stat().st_mtime
        rows.append((d.name, msg_count, datetime.fromtimestamp(last_write).strftime("%Y-%m-%d %H:%M:%S")))

    # simple table
    print("Sessions" + (f" (world: {world_id})" if world_id else "") + ":")
    print(f"{'SessionId':<45} {'Messages':>8} {'LastWrite':>20}")
    for sid, cnt, lw in rows:
        print(f"{sid:<45} {cnt:>8} {lw:>20}")


def cmd_delete(root: Path, session_id: str, yes: bool) -> None:
    sdir = sessions_dir(root) / session_id
    if not sdir.exists():
        raise FileNotFoundError(f"Session not found: {sdir}")

    if not yes:
        print("You are about to permanently delete this session folder:")
        print(str(sdir))
        confirm = input("Type YES to confirm: ").strip()
        if confirm != "YES":
            print("Cancelled.")
            return

    shutil.rmtree(sdir)
    print(f"OK. Deleted session: {session_id}")


def build_api_messages_for_session(root: Path, session_dir: Path, user_text: str, speaker_id: Optional[str]) -> Tuple[str, List[Dict[str, str]], Optional[str]]:
    si = read_session_info(session_dir)
    world_id = si.world_id
    model = get_model_from_session(si)

    wpath = worlds_dir(root) / world_id
    system_text = (wpath / "system_prompt.txt").read_text(encoding="utf-8")

    character_block = None
    speaker_name = None
    if speaker_id:
        speaker_name, character_block = load_character(wpath, speaker_id)

    msgs = load_jsonl(session_dir / "messages.jsonl")

    api_msgs: List[Dict[str, str]] = [{"role": "system", "content": system_text}]
    if character_block:
        api_msgs.append({"role": "system", "content": character_block})

    # last 20 user/assistant messages
    tail = msgs[-20:]
    for m in tail:
        role = m.get("role")
        content = m.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            api_msgs.append({"role": role, "content": content})

    api_msgs.append({"role": "user", "content": user_text})
    return model, api_msgs, speaker_name


def cmd_chat(root: Path, session_id: str, text: str) -> None:
    session_dir = sessions_dir(root) / session_id
    if not session_dir.exists():
        raise FileNotFoundError(f"Session not found: {session_dir}")

    model, api_msgs, _speaker_name = build_api_messages_for_session(root, session_dir, text, speaker_id=None)
    assistant = ollama_chat(model=model, messages=api_msgs, stream=False)

    logp = session_dir / "messages.jsonl"
    t1 = now_iso()
    t2 = (datetime.now() + timedelta(seconds=1)).replace(microsecond=0).isoformat()
    append_jsonl(logp, {"ts": t1, "role": "user", "content": text})
    append_jsonl(logp, {"ts": t2, "role": "assistant", "content": assistant})

    print(assistant)


def cmd_chatloop(root: Path, session_id: str) -> None:
    session_dir = sessions_dir(root) / session_id
    if not session_dir.exists():
        raise FileNotFoundError(f"Session not found: {session_dir}")

    print(f"Entering chat loop for session: {session_id}")
    print("Type /exit to leave.")
    print("Use /as <characterId> <text> to speak as a character (e.g. /as clara hello).")
    print()

    while True:
        try:
            user_in = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return

        if not user_in:
            continue
        if user_in == "/exit":
            print("Bye.")
            return

        speaker_id = None
        text = user_in
        m = re.match(r"^/as\s+(\S+)\s+(.+)$", user_in)
        if m:
            speaker_id = m.group(1)
            text = m.group(2)

        try:
            model, api_msgs, speaker_name = build_api_messages_for_session(root, session_dir, text, speaker_id=speaker_id)
            assistant = ollama_chat(model=model, messages=api_msgs, stream=False)

            logp = session_dir / "messages.jsonl"
            t1 = now_iso()
            t2 = (datetime.now() + timedelta(seconds=1)).replace(microsecond=0).isoformat()

            if speaker_id and speaker_name:
                append_jsonl(logp, {"ts": t1, "role": "user", "content": text, "speaker": speaker_name})
                append_jsonl(logp, {"ts": t2, "role": "assistant", "content": assistant, "speaker": speaker_name})
            else:
                append_jsonl(logp, {"ts": t1, "role": "user", "content": text})
                append_jsonl(logp, {"ts": t2, "role": "assistant", "content": assistant})

            json_objs, non_json_text = extract_all_json(assistant)

            print("\nAssistant:")
            print(non_json_text.strip())
            print()

            execute_cmd(json_objs)
        except Exception as e:
            print(f"ERROR: {e}\n")


def execute_cmd(json_objs: List[object]) -> None:
    for obj in json_objs:
        reqs = obj['requests']
        for req in reqs:
            url = req.get('url')
            requests.get(url)


def extract_all_json(text: str) -> Tuple[List[object], str]:
    decoder = json.JSONDecoder()
    results = []
    i = 0
    non_json_end = 0

    while i < len(text):
        if text[i] in ('{', '['):
            try:
                if non_json_end == 0:
                    non_json_end = i

                obj, end = decoder.raw_decode(text[i:])
                results.append(obj)
                i += end
                continue
            except json.JSONDecodeError:
                pass
        i += 1

    return results, text[:(len(text) if non_json_end == 0 else non_json_end)]


# ---------- Main ----------
def main():
    parser = argparse.ArgumentParser(prog="storyai", description="Local Story AI CLI (Ollama-backed)")
    parser.add_argument("--root", help="Override root folder (default: folder containing storyai.py)")

    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("worlds", help="List available worlds")

    p_new = sub.add_parser("new", help="Create a new session for a world and generate opening")
    p_new.add_argument("world_id")

    p_sess = sub.add_parser("sessions", help="List sessions")
    p_sess.add_argument("world_id", nargs="?", default=None)

    p_del = sub.add_parser("delete", help="Delete a session folder")
    p_del.add_argument("session_id")
    p_del.add_argument("--yes", action="store_true", help="Delete without confirmation")

    p_chat = sub.add_parser("chat", help="Single-turn chat (append to messages.jsonl)")
    p_chat.add_argument("session_id")
    p_chat.add_argument("text")

    p_loop = sub.add_parser("chatloop", help="Interactive chat loop")
    p_loop.add_argument("session_id")

    args = parser.parse_args()
    root = get_root(args.root)

    try:
        if args.cmd == "worlds":
            cmd_worlds(root)
        elif args.cmd == "new":
            cmd_new(root, args.world_id)
        elif args.cmd == "sessions":
            cmd_sessions(root, args.world_id)
        elif args.cmd == "delete":
            cmd_delete(root, args.session_id, yes=args.yes)
        elif args.cmd == "chat":
            cmd_chat(root, args.session_id, args.text)
        elif args.cmd == "chatloop":
            cmd_chatloop(root, args.session_id)
        else:
            parser.print_help()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
