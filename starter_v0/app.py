"""Streamlit UI cho Research Agent.

UI này KHÔNG tự viết agent loop. Nó tái sử dụng `run_model_tool_loop` trong chat.py
để trace hiển thị ở đây khớp chính xác với evidence trong runs/ và transcripts/.

Bố cục theo kiểu ChatGPT: khu chat sạch ở giữa, mọi cấu hình và thông tin version
nằm trong sidebar. Trace tool vẫn hiển thị inline dưới câu trả lời vì đó là bằng chứng
bắt buộc phải nhìn thấy khi demo.

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

# v0 là baseline, v1–v3 là ba vòng tối ưu bắt buộc, v4 để dành nếu nhóm chạy thêm.
VERSION_LABELS = ["v0", "v1", "v2", "v3", "v4"]

SUGGESTIONS = [
    "Tin tức AI hôm nay có gì nổi bật?",
    "Tweet mới nhất của Sam Altman là gì?",
    "Tóm tắt bài này: https://openai.com/blog/gpt-5",
]


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
    events = result.get("tool_events") or []
    if not events:
        return

    labels = " · ".join(f"{STATUS_ICON[event_status(e)]} {e.get('tool')}" for e in events)
    with st.expander(f"🔧 {len(events)} tool call · {labels}", expanded=False):
        for record in rounds:
            calls = record.get("tool_calls") or []
            results = record.get("tool_results") or []
            if not calls:
                continue
            st.markdown(f"<div class='trace-round'>Round {record.get('round')}</div>", unsafe_allow_html=True)
            if record.get("assistant_text"):
                st.caption(record["assistant_text"])
            for index, call in enumerate(calls):
                event = results[index] if index < len(results) else {}
                status = event_status(event)
                st.markdown(
                    f"{STATUS_ICON[status]} **`{call['name']}`** "
                    f"<span class='trace-meta'>round {record.get('round')} · {status}</span>",
                    unsafe_allow_html=True,
                )
                st.caption("args")
                st.json(call.get("args", {}), expanded=False)
                st.caption("result")
                st.json(event.get("result", {}), expanded=False)


def render_result(result: dict[str, Any], artifact: ArtifactVersion) -> None:
    status = result.get("status")
    if status == "provider_error":
        st.error(result["assistant_text"])
    elif status == "waiting_for_user":
        st.markdown(result.get("assistant_text") or "")
        st.caption("⏸️ Agent đang chờ bạn bổ sung thông tin.")
    else:
        st.markdown(result.get("assistant_text") or "_(trống)_")

    render_trace(result)
    st.markdown(
        f"<div class='msg-meta'>{artifact.artifact_version} · status <code>{status}</code></div>",
        unsafe_allow_html=True,
    )


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

st.set_page_config(
    page_title="Research Agent",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

available_sets = artifact_sets()

# --------------------------------------------------------------------- sidebar

with st.sidebar:
    if st.button("＋  Hội thoại mới", use_container_width=True):
        for key in ("history", "turns", "transcript"):
            st.session_state.pop(key, None)
        st.rerun()

    st.markdown("<div class='side-label'>Model</div>", unsafe_allow_html=True)
    provider_name = st.selectbox("Provider", ["openrouter", "openai", "anthropic", "gemini"], label_visibility="collapsed")
    model = st.text_input("Model", "", placeholder="Model (trống = default)", label_visibility="collapsed")

    st.markdown("<div class='side-label'>Artifact</div>", unsafe_allow_html=True)
    version_label = st.selectbox("Version", VERSION_LABELS, index=0, label_visibility="collapsed")
    primary_set = st.selectbox("Bộ artifact", list(available_sets), index=0, label_visibility="collapsed")
    compare_mode = st.toggle(
        "So sánh 2 version",
        value=False,
        help="Chạy CÙNG một câu hỏi trên 2 bộ artifact. Chế độ này single-shot, không mang lịch sử hội thoại.",
    )
    compare_set = None
    if compare_mode:
        others = [name for name in available_sets if name != primary_set]
        if others:
            compare_set = st.selectbox("Bộ đối chứng", others, label_visibility="collapsed")
        else:
            st.caption(
                "Chưa có snapshot. R1 copy `system_prompt.md` + `tools.yaml` "
                "vào `artifacts/versions/<label>/`."
            )

    with st.expander("⚙️ Agent loop"):
        max_tool_rounds = st.slider("Max tool rounds", 1, 6, 4)
        history_window = st.slider("History window (cặp user/assistant)", 0, 10, 5)

# --------------------------------------------------------------------- styling

MAIN_WIDTH = "70rem" if (compare_mode and compare_set) else "48rem"

st.markdown(
    f"""
    <style>
      /* ---- chrome ---- */
      [data-testid="stHeader"] {{ background: transparent; }}
      [data-testid="stAppDeployButton"] {{ display: none; }}
      [data-testid="stMainBlockContainer"] {{
          max-width: {MAIN_WIDTH};
          padding-top: 3rem;
          padding-bottom: 7rem;
      }}

      /* ---- sidebar ---- */
      [data-testid="stSidebar"] {{
          background: #171717;
          border-right: 1px solid #2a2a2a;
      }}
      [data-testid="stSidebar"] .side-label {{
          font-size: .7rem;
          letter-spacing: .08em;
          text-transform: uppercase;
          color: #8e8e8e;
          margin: 1.15rem 0 .35rem 0;
      }}
      [data-testid="stSidebar"] [data-testid="stExpander"] {{
          border: none;
          background: transparent;
      }}

      /* ---- messages ---- */
      [data-testid="stChatMessage"] {{
          background: transparent;
          padding: .1rem 0 1.4rem 0;
          gap: .75rem;
      }}
      [data-testid="stChatMessageAvatarUser"] {{ display: none; }}
      [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {{
          justify-content: flex-end;
      }}
      [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"])
      [data-testid="stChatMessageContent"] {{
          background: #303030;
          border-radius: 1.35rem;
          padding: .65rem 1.05rem;
          flex-grow: 0;
          max-width: 75%;
      }}
      [data-testid="stChatMessageAvatarAssistant"] {{
          background: transparent;
          border: 1px solid #4a4a4a;
          color: #ececec;
      }}

      /* ---- tool trace ---- */
      [data-testid="stMainBlockContainer"] [data-testid="stExpander"] {{
          border: 1px solid #3a3a3a;
          border-radius: .85rem;
          background: #1b1b1b;
          margin-top: .5rem;
      }}
      [data-testid="stMainBlockContainer"] [data-testid="stExpander"] summary {{
          font-size: .82rem;
          color: #a8a8a8;
      }}
      .trace-round {{
          font-size: .7rem;
          letter-spacing: .08em;
          text-transform: uppercase;
          color: #8e8e8e;
          margin: .6rem 0 .3rem 0;
          border-top: 1px solid #2f2f2f;
          padding-top: .6rem;
      }}
      .trace-meta {{ color: #8e8e8e; font-size: .78rem; }}
      .msg-meta {{
          color: #6f6f6f;
          font-size: .72rem;
          margin-top: .45rem;
          font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      }}

      /* ---- composer ---- */
      [data-testid="stBottomBlockContainer"] {{
          max-width: {MAIN_WIDTH};
          padding-bottom: 1.25rem;
      }}
      [data-testid="stChatInput"] {{
          background: #303030;
          border: 1px solid #4a4a4a;
          border-radius: 1.6rem;
      }}

      /* ---- empty state ---- */
      .hero {{ text-align: center; margin: 5.5rem 0 2rem 0; }}
      .hero h1 {{ font-size: 1.85rem; font-weight: 600; margin-bottom: .4rem; }}
      .hero p {{ color: #9b9b9b; font-size: .92rem; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------- state

st.session_state.setdefault("history", [])
st.session_state.setdefault("turns", [])
if "transcript" not in st.session_state:
    st.session_state.transcript = new_transcript(version_label, provider_name, model or None)

primary_prompt, primary_tools = available_sets[primary_set]
primary_artifact = build_artifact_version(version_label, primary_prompt, primary_tools)
declared_tools = [item["name"] for item in load_tool_declarations(primary_tools)]

# Evidence panel: luôn nhìn được đang chạy artifact nào, transcript nào.
with st.sidebar:
    st.markdown("<div class='side-label'>Phiên hiện tại</div>", unsafe_allow_html=True)
    st.code(primary_artifact.artifact_version, language=None)
    st.caption(
        f"prompt_hash `{primary_artifact.prompt_hash[:12]}` · "
        f"tools_hash `{primary_artifact.tools_hash[:12]}`"
    )
    st.caption(f"transcript `{st.session_state.transcript['transcript_id']}`")
    st.caption(f"{len(st.session_state.transcript['turns'])} turn đã lưu")

    with st.expander(f"🧰 {len(declared_tools)} tool đang khai báo"):
        for name in declared_tools:
            st.markdown(f"- `{name}`")

    if st.session_state.transcript["turns"]:
        st.download_button(
            "⬇️ Tải transcript JSON",
            data=json.dumps(st.session_state.transcript, ensure_ascii=False, indent=2, default=str),
            file_name=f"{st.session_state.transcript['transcript_id']}.transcript.json",
            mime="application/json",
            use_container_width=True,
        )

# --------------------------------------------------------------------- main

if not st.session_state.turns:
    st.markdown(
        "<div class='hero'><h1>Research Agent</h1>"
        "<p>Tìm tin theo chủ đề hoặc theo tài khoản, đọc URL, rồi tổng hợp thành digest.</p></div>",
        unsafe_allow_html=True,
    )
    columns = st.columns(len(SUGGESTIONS))
    for column, suggestion in zip(columns, SUGGESTIONS):
        if column.button(suggestion, use_container_width=True):
            st.session_state.pending = suggestion
            st.rerun()

for turn in st.session_state.turns:
    with st.chat_message("user"):
        st.markdown(turn["user"])
    with st.chat_message("assistant"):
        if turn["compare"]:
            left, right = st.columns(2)
            for column, side in zip((left, right), turn["compare"]):
                with column:
                    st.markdown(f"**{side['label']}**")
                    render_result(side["result"], side["artifact"])
        else:
            render_result(turn["result"], turn["artifact"])

user_text = st.chat_input("Hỏi agent...") or st.session_state.pop("pending", None)

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
                    st.markdown(f"**{label}**")
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

    save_transcript()
    st.rerun()
