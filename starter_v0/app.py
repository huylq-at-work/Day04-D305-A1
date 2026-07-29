"""Streamlit UI cho Research Agent.

UI này KHÔNG tự viết agent loop. Nó tái sử dụng `run_model_tool_loop` trong chat.py
để trace hiển thị ở đây khớp chính xác với evidence trong runs/ và transcripts/.

Chạy:
    .venv\\Scripts\\streamlit.exe run app.py
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from chat import now_iso, run_model_tool_loop, safe_slug, write_transcript
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import ArtifactVersion, artifact_version_dict, build_artifact_version


ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
VERSIONS_DIR = ARTIFACTS_DIR / "versions"
TRANSCRIPTS_DIR = ROOT / "transcripts"

load_lab_env(ROOT)


# ---------------------------------------------------------------- artifact sets

def artifact_sets() -> dict[str, tuple[Path, Path]]:
    """Các bộ artifact có thể chạy: bản live + mọi snapshot trong artifacts/versions/.

    R1 snapshot mỗi version bằng cách copy system_prompt.md + tools.yaml vào
    artifacts/versions/<label>/. Có snapshot thì UI mới chạy lại cùng một câu hỏi
    trên nhiều version để so sánh được.
    """
    sets: dict[str, tuple[Path, Path]] = {
        "live (artifacts/)": (ARTIFACTS_DIR / "system_prompt.md", ARTIFACTS_DIR / "tools.yaml"),
    }
    if VERSIONS_DIR.is_dir():
        for folder in sorted(VERSIONS_DIR.iterdir()):
            prompt_path = folder / "system_prompt.md"
            tools_path = folder / "tools.yaml"
            if prompt_path.is_file() and tools_path.is_file():
                sets[f"snapshot: {folder.name}"] = (prompt_path, tools_path)
    return sets


def event_status(event: dict[str, Any]) -> str:
    result = event.get("result")
    if isinstance(result, dict):
        if result.get("error"):
            return "error"
        if result.get("awaiting_user"):
            return "awaiting_user"
    return "ok"


STATUS_ICON = {"ok": "✅", "error": "❌", "awaiting_user": "⏸️"}


# ---------------------------------------------------------------- agent runner

def run_agent(
    *,
    user_text: str,
    history: list[dict[str, str]],
    provider_name: str,
    model: str | None,
    prompt_path: Path,
    tools_path: Path,
    max_tool_rounds: int,
    history_window: int,
) -> dict[str, Any]:
    """Gọi đúng loop của chat.py. Trả về result dict, hoặc status=provider_error."""
    messages = [
        {"role": "system", "content": prompt_path.read_text(encoding="utf-8")},
        *(history[-history_window * 2:] if history_window > 0 else []),
        {"role": "user", "content": user_text},
    ]
    declarations = load_tool_declarations(tools_path)
    try:
        return run_model_tool_loop(
            provider=make_provider(provider_name),
            messages=messages,
            tools=to_openai_tools(declarations),
            model=model or None,
            max_tool_rounds=max_tool_rounds,
        )
    except Exception as exc:  # key thiếu, hết quota, API lỗi
        return {
            "status": "provider_error",
            "assistant_text": f"{type(exc).__name__}: {exc}",
            "rounds": [],
            "tool_events": [],
        }


# ---------------------------------------------------------------- render helpers

def render_trace(result: dict[str, Any]) -> None:
    """Trace từng tool: tên, args, round, status, result/error."""
    rounds = result.get("rounds") or []
    if not rounds:
        st.caption("Không có tool call nào trong lượt này.")
        return

    for record in rounds:
        calls = record.get("tool_calls") or []
        results = record.get("tool_results") or []
        header = f"Round {record.get('round')} — {len(calls)} tool call(s)"
        with st.expander(header, expanded=True):
            if record.get("assistant_text"):
                st.caption(record["assistant_text"])
            if not calls:
                st.caption("Model trả lời trực tiếp, không gọi tool.")
            for index, call in enumerate(calls):
                event = results[index] if index < len(results) else {}
                status = event_status(event)
                st.markdown(f"{STATUS_ICON[status]} **`{call['name']}`** · round {record.get('round')} · `{status}`")
                st.caption("args")
                st.json(call.get("args", {}), expanded=False)
                st.caption("result")
                st.json(event.get("result", {}), expanded=False)


def render_result(result: dict[str, Any], artifact: ArtifactVersion) -> None:
    status = result.get("status")
    if status == "provider_error":
        st.error(result["assistant_text"])
    elif status == "waiting_for_user":
        st.warning(f"Agent đang hỏi lại: {result['assistant_text']}")
    else:
        st.markdown(result.get("assistant_text") or "_(trống)_")

    st.caption(
        f"status = `{status}` · artifact_version = `{artifact.artifact_version}` · "
        f"{len(result.get('tool_events') or [])} tool event(s)"
    )
    render_trace(result)


# ---------------------------------------------------------------- transcript

def new_transcript(version_label: str, provider_name: str, model: str | None) -> dict[str, Any]:
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = "_".join([safe_slug(version_label), "ui", safe_slug(provider_name), timestamp])
    return {
        "transcript_id": transcript_id,
        "source": "app.py",
        "provider": provider_name,
        "model": model,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "turns": [],
    }


def record_turn(
    *,
    user_text: str,
    result: dict[str, Any],
    artifact: ArtifactVersion,
    artifact_set: str,
    started_at: str,
) -> dict[str, Any]:
    return {
        "turn_index": len(st.session_state.transcript["turns"]) + 1,
        "started_at": started_at,
        "ended_at": now_iso(),
        "user": user_text,
        "artifact_set": artifact_set,
        **artifact_version_dict(artifact),
        "status": result.get("status"),
        "assistant_text": result.get("assistant_text"),
        "rounds": result.get("rounds", []),
        "tool_events": result.get("tool_events", []),
    }


def save_transcript() -> Path:
    path = TRANSCRIPTS_DIR / f"{st.session_state.transcript['transcript_id']}.transcript.json"
    write_transcript(path, st.session_state.transcript)
    return path


# ---------------------------------------------------------------- page

st.set_page_config(page_title="Research Agent — Day 04", layout="wide")
st.title("🔎 Research Agent")

available_sets = artifact_sets()

with st.sidebar:
    st.header("Cấu hình")
    provider_name = st.selectbox("Provider", ["openrouter", "openai", "anthropic", "gemini"])
    model = st.text_input("Model (để trống = default của provider)", "")
    version_label = st.text_input("Version label", "v0", help="Nhãn ghi vào transcript, ví dụ v0/v1/v2/v3.")

    st.divider()
    st.header("Artifact")
    primary_set = st.selectbox("Bộ artifact chính", list(available_sets), index=0)
    compare_mode = st.toggle(
        "Chế độ so sánh 2 version",
        value=False,
        help="Chạy CÙNG một câu hỏi trên 2 bộ artifact. Chế độ này chạy single-shot, không mang lịch sử hội thoại.",
    )
    compare_set = None
    if compare_mode:
        others = [name for name in available_sets if name != primary_set]
        if others:
            compare_set = st.selectbox("Bộ artifact đối chứng", others)
        else:
            st.info(
                "Chưa có snapshot để so sánh. R1 copy `system_prompt.md` + `tools.yaml` "
                "vào `artifacts/versions/<label>/` sau mỗi version."
            )

    st.divider()
    st.header("Agent loop")
    max_tool_rounds = st.slider("Max tool rounds", 1, 6, 4)
    history_window = st.slider("History window (số cặp user/assistant)", 0, 10, 5)

    st.divider()
    if st.button("🔄 Hội thoại mới", use_container_width=True):
        for key in ("history", "turns", "transcript"):
            st.session_state.pop(key, None)
        st.rerun()

# Session state
st.session_state.setdefault("history", [])
st.session_state.setdefault("turns", [])
if "transcript" not in st.session_state:
    st.session_state.transcript = new_transcript(version_label, provider_name, model or None)

primary_prompt, primary_tools = available_sets[primary_set]
primary_artifact = build_artifact_version(version_label, primary_prompt, primary_tools)

# Thanh version: luôn nhìn được đang chạy artifact nào và transcript nào.
info_left, info_right = st.columns([3, 2])
with info_left:
    st.markdown(f"**artifact_version** · `{primary_artifact.artifact_version}`")
    st.caption(f"prompt_hash `{primary_artifact.prompt_hash[:12]}` · tools_hash `{primary_artifact.tools_hash[:12]}`")
with info_right:
    st.markdown(f"**transcript** · `{st.session_state.transcript['transcript_id']}`")
    st.caption(f"{len(st.session_state.transcript['turns'])} turn đã lưu · provider `{provider_name}`")

declared_tools = [item["name"] for item in load_tool_declarations(primary_tools)]
st.caption(f"{len(declared_tools)} tool đang khai báo: " + ", ".join(f"`{name}`" for name in declared_tools))

st.divider()

# Lịch sử hội thoại đã render
for turn in st.session_state.turns:
    with st.chat_message("user"):
        st.markdown(turn["user"])
    with st.chat_message("assistant"):
        if turn["compare"]:
            left, right = st.columns(2)
            with left:
                st.markdown(f"##### {turn['compare'][0]['label']}")
                render_result(turn["compare"][0]["result"], turn["compare"][0]["artifact"])
            with right:
                st.markdown(f"##### {turn['compare'][1]['label']}")
                render_result(turn["compare"][1]["result"], turn["compare"][1]["artifact"])
        else:
            render_result(turn["result"], turn["artifact"])

user_text = st.chat_input("Hỏi agent...")

if user_text:
    started_at = now_iso()
    with st.chat_message("user"):
        st.markdown(user_text)

    with st.chat_message("assistant"):
        if compare_mode and compare_set:
            compare_prompt, compare_tools = available_sets[compare_set]
            compare_artifact = build_artifact_version(version_label, compare_prompt, compare_tools)
            sides = [
                (primary_set, primary_prompt, primary_tools, primary_artifact),
                (compare_set, compare_prompt, compare_tools, compare_artifact),
            ]
            columns = st.columns(2)
            rendered: list[dict[str, Any]] = []
            for column, (label, prompt_path, tools_path, artifact) in zip(columns, sides):
                with column:
                    st.markdown(f"##### {label}")
                    with st.spinner("Đang chạy..."):
                        # So sánh chạy single-shot: history rỗng để hai bên cùng điều kiện.
                        result = run_agent(
                            user_text=user_text,
                            history=[],
                            provider_name=provider_name,
                            model=model,
                            prompt_path=prompt_path,
                            tools_path=tools_path,
                            max_tool_rounds=max_tool_rounds,
                            history_window=0,
                        )
                    render_result(result, artifact)
                rendered.append({"label": label, "result": result, "artifact": artifact})
                st.session_state.transcript["turns"].append(
                    record_turn(
                        user_text=user_text,
                        result=result,
                        artifact=artifact,
                        artifact_set=label,
                        started_at=started_at,
                    )
                )
            st.session_state.turns.append({"user": user_text, "compare": rendered, "result": None, "artifact": None})
        else:
            with st.spinner("Đang chạy..."):
                result = run_agent(
                    user_text=user_text,
                    history=st.session_state.history,
                    provider_name=provider_name,
                    model=model,
                    prompt_path=primary_prompt,
                    tools_path=primary_tools,
                    max_tool_rounds=max_tool_rounds,
                    history_window=history_window,
                )
            render_result(result, primary_artifact)

            # Kể cả khi agent đang hỏi lại (waiting_for_user), câu hỏi đó vẫn vào history
            # để lượt sau của user là câu trả lời có ngữ cảnh — giống hệt chat.py.
            if result["status"] != "provider_error":
                st.session_state.history.append({"role": "user", "content": user_text})
                st.session_state.history.append({"role": "assistant", "content": result["assistant_text"]})

            st.session_state.turns.append(
                {"user": user_text, "result": result, "artifact": primary_artifact, "compare": None}
            )
            st.session_state.transcript["turns"].append(
                record_turn(
                    user_text=user_text,
                    result=result,
                    artifact=primary_artifact,
                    artifact_set=primary_set,
                    started_at=started_at,
                )
            )

    transcript_path = save_transcript()
    st.caption(f"Transcript đã lưu: `{transcript_path.relative_to(ROOT)}`")

if st.session_state.transcript["turns"]:
    st.divider()
    st.download_button(
        "⬇️ Tải transcript JSON",
        data=json.dumps(st.session_state.transcript, ensure_ascii=False, indent=2, default=str),
        file_name=f"{st.session_state.transcript['transcript_id']}.transcript.json",
        mime="application/json",
    )
