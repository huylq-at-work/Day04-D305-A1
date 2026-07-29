# ROLE 4 — UI, Deploy & Integrator

**Người phụ trách:** Lê Quang Huy · **Branch:** `role4-ui-deploy`

> Đọc [docs/plan.md](../plan.md) trước. Mọi lệnh chạy từ `starter_v0/`.

## Bạn sở hữu

- `starter_v0/app.py` — UI (starter **không** cung cấp file này)
- `starter_v0/requirements.txt` — thêm dependency của UI
- `starter_v0/transcripts/` — log chat live
- Vai trò integrator: review và merge PR của cả nhóm

## Bạn là đường găng

UI là **deliverable core, không phải bonus**. Showdown bắt đầu 11:30. Nếu UI chưa chạy được
thì v1/v2 tốt đến mấy cũng không demo được. Checkpoint yêu cầu **UI local chạy được từ
10:15** — dựng khung ngay từ 09:40, kể cả khi lúc đó agent còn dùng prompt baseline sai.

## Ràng buộc quan trọng nhất

**Bắt buộc tái sử dụng `run_model_tool_loop` trong [`chat.py`](../../starter_v0/chat.py).**
Không được viết agent loop riêng. Lý do: run JSON và transcript là bằng chứng chấm điểm; UI
chạy loop khác thì trace hiển thị không khớp với evidence đã nộp.

Chữ ký hàm:

```python
run_model_tool_loop(
    *,
    provider,            # từ providers.make_provider(...)
    messages,            # [{"role": "system"|"user"|"assistant", "content": str}]
    tools,               # từ to_openai_tools(load_tool_declarations(path))
    model,               # str | None
    max_tool_rounds,     # int, mặc định 4
) -> dict
```

Kết quả trả về:

| Key | Nội dung |
| :-- | :-- |
| `status` | `answered` \| `waiting_for_user` \| `max_tool_rounds` |
| `assistant_text` | text cuối cùng cho user |
| `rounds` | list, mỗi phần tử có `round`, `assistant_text`, `tool_calls`, `tool_results` |
| `tool_events` | list phẳng mọi lần gọi tool, mỗi item có `tool`, `args`, `result` |

`status == "waiting_for_user"` nghĩa là agent đã gọi tool clarify và đang chờ user bổ sung
thông tin. UI phải hiển thị `assistant_text` như một câu hỏi và cho user trả lời tiếp trong
cùng session — **đừng coi đó là kết thúc hội thoại**. Đây chính là cách demo được boundary
`missing_info`.

## Bằng chứng tối thiểu UI phải hiện

README chấm UI theo bốn thứ:

1. Request và response cuối cùng
2. **Trace từng tool**: tên tool, args, round, status, result/error
3. `transcript` / `run` / `artifact_version` đang xem là version nào
4. Cùng một scenario chạy qua nhiều version để thấy cải thiện

Điểm 3 và 4 hay bị bỏ quên. `artifact_version` lấy từ:

```python
from versioning import build_artifact_version, artifact_version_dict

av = build_artifact_version(version_label, Path("artifacts/system_prompt.md"), Path("artifacts/tools.yaml"))
st.caption(f"artifact_version = {av.artifact_version}")
```

Cho phép **chọn version label ở sidebar** để chạy lại cùng một câu hỏi trên artifact khác
nhau — đó là cách rẻ nhất để đạt điểm 4.

## Nhiệm vụ

## Trạng thái: T1 và T2 đã xong

[`starter_v0/app.py`](../../starter_v0/app.py) đã được implement và smoke-test:
server lên `http://localhost:8501`, submit query render đúng, provider error được bắt và
hiển thị thay vì crash, transcript ghi ra `transcripts/*.transcript.json` đúng schema.

Chạy:

```bash
cd D:\VinUni\Lab04\Day04-2A202601821-LeQuangHuy\starter_v0 && .venv\Scripts\streamlit.exe run app.py
```

Những gì app.py đang có:

| Tiêu chí chấm | Đã có |
| :-- | :-- |
| Request + response cuối | chat message, kèm `status` |
| Trace từng tool | expander theo round: tên tool, args, status icon, result/error |
| artifact_version / transcript | thanh header hiện `artifact_version`, `prompt_hash`, `tools_hash`, `transcript_id` |
| Cùng scenario qua nhiều version | toggle **Chế độ so sánh 2 version** — chạy song song 2 bộ artifact |

Chế độ so sánh quét `artifacts/versions/<label>/`. **Cần R1 snapshot mỗi version vào đó**,
nếu không selectbox chỉ có bản `live`. Chế độ này chạy single-shot (history rỗng cho cả hai
bên) để hai version cùng điều kiện.

Còn lại: **T3 deploy**, **T4 live chat**, **T5 integrator**.

<details>
<summary>Hướng dẫn gốc để dựng lại từ đầu (giữ để tham khảo)</summary>

### T1 — Dựng khung UI (09:40–10:15)

Thêm vào `requirements.txt`:

```text
streamlit>=1.30.0
```

Cài:

```bash
.venv\Scripts\python.exe -m pip install "streamlit>=1.30.0"
```

Khung `app.py` tối thiểu:

```python
from pathlib import Path

import streamlit as st

from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from chat import run_model_tool_loop
from versioning import build_artifact_version

ROOT = Path(__file__).parent
load_lab_env(ROOT)

st.set_page_config(page_title="Research Agent", layout="wide")

with st.sidebar:
    provider_name = st.selectbox("Provider", ["openrouter", "openai", "anthropic", "gemini"])
    version_label = st.text_input("Version", "v0")
    max_rounds = st.slider("Max tool rounds", 1, 6, 4)

system_prompt_path = ROOT / "artifacts" / "system_prompt.md"
tools_path = ROOT / "artifacts" / "tools.yaml"
artifact = build_artifact_version(version_label, system_prompt_path, tools_path)
st.caption(f"artifact_version = `{artifact.artifact_version}`")

if "history" not in st.session_state:
    st.session_state.history = []

user_text = st.chat_input("Hỏi agent...")
if user_text:
    messages = [
        {"role": "system", "content": system_prompt_path.read_text(encoding="utf-8")},
        *st.session_state.history,
        {"role": "user", "content": user_text},
    ]
    provider = make_provider(provider_name)
    result = run_model_tool_loop(
        provider=provider,
        messages=messages,
        tools=to_openai_tools(load_tool_declarations(tools_path)),
        model=None,
        max_tool_rounds=max_rounds,
    )
    st.session_state.history.append({"role": "user", "content": user_text})
    st.session_state.history.append({"role": "assistant", "content": result["assistant_text"]})

    st.markdown(result["assistant_text"])
    st.caption(f"status = `{result['status']}`")

    for rnd in result["rounds"]:
        with st.expander(f"Round {rnd['round']} — {len(rnd['tool_calls'])} tool call(s)"):
            for call, res in zip(rnd["tool_calls"], rnd["tool_results"]):
                st.write(f"**{call['name']}**")
                st.json(call["args"])
                st.json(res["result"])
```

Chạy:

```bash
.venv\Scripts\streamlit.exe run app.py
```

**PASS khi mở được `http://localhost:8501`.**

### T2 — Lưu transcript từ UI

Đừng viết định dạng transcript riêng. Dùng lại `write_transcript` trong `chat.py` để file
sinh ra từ UI cùng schema với file sinh ra từ CLI:

```python
from chat import write_transcript, now_iso
```

Transcript phải có `artifact_version`, `provider`, `model`, và list `turns` với đủ `rounds`
và `tool_events`.

</details>

### T3 — Deploy (deadline 11:30)

UI local chỉ đủ cho máy nhóm mình. Nhóm khác test từ máy khác thì phải có URL public.

Cài `cloudflared` (xem [TOOL-SETUP.md](../../TOOL-SETUP.md)), rồi:

```bash
cloudflared tunnel --url http://localhost:8501
```

Lấy URL `trycloudflare.com` sinh ra, **test lại bằng điện thoại hoặc máy khác**, rồi dán vào
`REPORT.md` Phần A.

**Bảo mật:** tunnel là public. Không hiển thị API key, không log `.env`, không để lộ token
trong screenshot hay trong phần trace của UI. Kiểm tra trace render ra không chứa header
Authorization trước khi mở tunnel.

### T4 — Chat live ≥3 turn (deadline 12:35)

```bash
.venv\Scripts\python.exe chat.py --provider openrouter --version v3
```

Ba tình huống bắt buộc:

1. Một request research bình thường
2. Một request **thiếu thông tin**, rồi bổ sung ở lượt sau — để thấy `waiting_for_user`
3. Một request có **hành động nhạy cảm** — để kiểm tra boundary hỏi xác nhận

Transcript tự lưu vào `transcripts/*.transcript.json` sau mỗi turn.

### T5 — Integrator

Bạn review và merge PR của cả nhóm. Thứ tự bắt buộc: **R2 → R3 → R1**. Chi tiết ở
[TEAMMATES.md](../../TEAMMATES.md) mục 3.

Trước showdown, khóa artifact và kiểm tra:

- [ ] API key còn quota
- [ ] Link tunnel còn sống
- [ ] Đã mở sẵn run JSON / transcript cần chiếu
- [ ] Có fallback run hoặc transcript đã lưu nếu mạng chập chờn
- [ ] Không có secret trong screenshot, log, hay poster

## Tiêu chí hoàn thành

- [ ] `app.py` chạy được, mở `http://localhost:8501` thành công
- [ ] UI hiện đủ 4 thứ ở mục "Bằng chứng tối thiểu"
- [ ] UI dùng `run_model_tool_loop`, không có agent loop tự viết
- [ ] Xử lý được `status == "waiting_for_user"` (hỏi lại trong cùng session)
- [ ] `streamlit>=1.30.0` đã ghi vào `requirements.txt`
- [ ] URL public test được từ máy/thiết bị khác
- [ ] `transcripts/` có ≥1 file với ≥3 turn đúng 3 tình huống trên

## Bàn giao

- Cho **cả nhóm**: URL demo, dán vào REPORT.md Phần A.
- Cho **report**: mục live chat Phần B + screenshot UI.
