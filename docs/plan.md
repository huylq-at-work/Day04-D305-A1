# PLAN — Day 04 Lab v2: Research Agent Tool Eval

> Tài liệu này là kế hoạch tổng cho cả nhóm. Mỗi role đọc thêm file riêng trong
> [`docs/roles/`](roles/). Phân công và quy trình git ở [TEAMMATES.md](../TEAMMATES.md).

## 1. Mục tiêu bài lab

Đây **không phải** bài "làm chatbot trả lời hay". Đây là bài **đo và cải thiện agent bằng
bằng chứng**.

Vòng lặp trung tâm:

1. Chạy eval bằng API thật → sinh `runs/*.json`.
2. Đọc run JSON: agent sai tool, sai args, thiếu hỏi lại, hay gọi tool thừa?
3. Đặt **một** giả thuyết, sửa **một** thứ trong `system_prompt.md` **hoặc** `tools.yaml`.
4. Chạy lại, so metric before/after, ghi `version_log.csv`.
5. Lặp đủ v1, v2, v3.

Điểm mất nhiều nhất là chạy 3 lần giống hệt nhau rồi đặt tên v1/v2/v3. README nói thẳng
điều đó là không đạt.

## 2. Trạng thái hiện tại

| Hạng mục | Trạng thái |
| :-- | :-- |
| `.venv` + dependencies | ✅ Đã cài (Python 3.14.6) |
| `.env` | ⚠️ Đã tạo, **chưa có API key** |
| `artifacts/system_prompt.md` | ⚠️ Cố tình viết **sai** — xem mục 3 |
| `artifacts/tools.yaml` | ⚠️ 10 tool, mô tả cố tình mơ hồ |
| `artifacts/version_log.csv` | ⚠️ Chỉ có header |
| `data/eval_base.json` | ✅ 20 case cố định — **không được sửa** |
| `data/eval_group.json` | ⚠️ `cases: []` — nhóm tự viết 10 case |
| `app.py` (UI) | ❌ Chưa có, starter không cung cấp |
| Tool mới | ❌ Chưa có |

**Việc chặn cả nhóm:** chưa có `OPENROUTER_API_KEY` trong `starter_v0/.env`. Không có key
thì không ai chạy được gì. Đây là việc đầu tiên phải xong.

## 3. Baseline cố tình sai — đây là đề bài, không phải bug

`artifacts/system_prompt.md` hiện đang chỉ đạo agent làm **đúng những thứ eval trừ điểm**:

- "hates being asked questions... do not ask them back" → làm hỏng các case cần `clarify`
  (`R10_missing_handle`, `R11_missing_url`, `M01`, `M04`).
- "pick a well-known account like Sam Altman" → bịa `screenname` khi user không nói ai.
- "just go ahead and do it" khi user muốn gửi/đăng → phá `R12_confirm_before_send`, là case
  `wrong_boundary`.
- "Always finish the request in a single step. Pick one tool" → phá `R13_parallel_web_and_tweets`.

`tools.yaml` cũng mơ hồ có chủ đích: `lookup` chỉ ghi "Tra cứu thông tin trên internet",
không nói khi nào dùng `topic=news`, khi nào `timeframe=day`. `send` không nêu
confirmation boundary. Không tool nào phân biệt "tin **của** một người" (`timeline`) với
"tin **về** một chủ đề" (`social_search`).

Đây chính là kho giả thuyết cho v1/v2/v3. Đừng sửa hết một lượt ở v1 — sửa hết thì không
biết cái nào có tác dụng.

## 4. Deliverable bắt buộc

| # | Deliverable | Owner | Deadline |
| :-: | :-- | :-- | :-- |
| 1 | Provider chạy được (preflight PASS) | Cả nhóm | 09:40 |
| 2 | Baseline v0 + 4 metric | R1 | 10:15 |
| 3 | UI local chạy được | R4 | 10:15 |
| 4 | ≥1 tool mới (`tool.py` + `TOOL.md` + registry + declaration) | R2 | 10:50 |
| 5 | v1 + version_log | R1 | 10:50 |
| 6 | Đúng 10 eval case nhóm | R3 | 11:30 |
| 7 | v2 + version_log | R1 | 11:30 |
| 8 | Deploy URL truy cập được từ máy khác | R4 | 11:30 |
| 9 | REPORT.md **Phần A** | Cả nhóm | **11:30 (hard)** |
| 10 | Showdown / live test | Cả nhóm | 11:30–12:15 |
| 11 | v3 sau feedback | R1 | 12:35 |
| 12 | ≥3 live chat turn + transcript | R4 | 12:35 |
| 13 | REPORT.md **Phần B** | Cả nhóm | 12:35 |

**Bonus** chỉ tính khi có UI bắt buộc **và** tự viết **>3 tool mới**. Tool optional có sẵn
(`send`, `policy`, `papers`, `paper_text`) **không** tính là tool mới.

## 5. Timeline theo checkpoint

```text
09:00–09:15  Kickoff        — đọc TEAMMATES.md, tạo branch, mở starter_v0/
09:15–09:40  Setup          — .env có key, preflight PASS trên máy R1 và R4
09:40–10:15  Baseline v0    — R1 chạy base eval; R4 dựng UI khung; R3 đọc trace fail đầu tiên
10:15–10:50  v1 + Tool      — R2 giao tool mới; R1 sửa 1 giả thuyết rồi chạy v1
10:50–11:05  Nghỉ
11:05–11:30  Eval + v2      — R3 xong 10 case; R1 chạy v2; R4 deploy; cả nhóm viết Report A
11:30–12:15  Showdown       — demo, live test, phản biện
12:15–12:35  v3 + Report B  — áp dụng feedback, chạy v3, hoàn thiện evidence
12:35–12:40  Final gate     — kiểm tra và chuẩn bị nộp starter_v0/
12:40–13:00  Kahoot recap
```

## 6. Đường găng và rủi ro

**Đường găng là R4 (UI + deploy).** UI là deliverable core, showdown bắt đầu 11:30. Nếu UI
chưa chạy thì v1/v2 tốt đến mấy cũng không demo được. R4 phải dựng khung UI từ 09:40, ngay
cả khi lúc đó chưa có version nào tốt.

**Rủi ro 2 — R1 và R2 chạy song song ở mốc 10:15–10:50.** Cả hai cùng deadline 10:50. R2
không được để R1 ngồi chờ tool. Nếu 10:35 mà tool mới chưa xong, R1 chạy v1 **không kèm
tool mới**, còn tool mới đẩy sang v2.

**Rủi ro 3 — confounding.** Thêm một tool mới vào `tools.yaml` sẽ đổi `tools_hash` và có
thể đổi routing của các case khác. Nếu vòng đó vừa thêm tool vừa sửa prompt thì không giải
thích được metric. Quy ước của nhóm: **vòng nào thêm tool thì không sửa prompt**, và ghi
rõ `changed_artifact=tools.yaml (add tool X)` trong version log.

**Rủi ro 4 — quota / rate limit.** Mỗi lần chạy base eval là 20 case × nhiều round tool.
Đừng chạy lại chỉ vì tò mò. Trước mỗi run phải có giả thuyết viết ra giấy.

## 7. Điều kiện metric hợp lệ

Một run chỉ được dùng làm bằng chứng khi:

- `summary.provider_error_cases == 0`
- `summary.measured_cases == summary.total_cases`
- Mọi `tool_results` có `error` đã được review thủ công

Routing PASS **không** chứng minh tool chạy đúng. Một case có thể PASS routing trong khi
tool trả về lỗi API — đó vẫn là vấn đề phải ghi vào report.

Bốn metric phải ghi lại mỗi version:

| Metric | Nghĩa |
| :-- | :-- |
| `summary.case_accuracy` | tỉ lệ case đạt toàn bộ |
| `summary.tool_routing_accuracy` | chọn đúng tên tool |
| `summary.argument_accuracy` | args đúng (so subset) |
| `summary.multiturn_accuracy` | riêng nhóm case M01–M06 |

## 8. Lệnh dùng chung (Windows PowerShell)

Tất cả lệnh chạy từ `starter_v0/`, dùng python trong venv.

Kích hoạt venv:

```bash
cd D:\VinUni\Lab04\Day04-2A202601821-LeQuangHuy\starter_v0 && .venv\Scripts\Activate.ps1
```

Kiểm tra provider trước khi làm gì khác:

```bash
.venv\Scripts\python.exe scripts\preflight_provider.py --provider openrouter
```

Chạy base eval (đổi `v0` theo version):

```bash
.venv\Scripts\python.exe run_eval.py --provider openrouter --version v0 --suite base --eval-cases data\eval_base.json
```

Chạy eval nhóm:

```bash
.venv\Scripts\python.exe run_eval.py --provider openrouter --version v3 --suite group --eval-cases data\eval_group.json
```

Chat live:

```bash
.venv\Scripts\python.exe chat.py --provider openrouter --version v3
```

Parse run JSON ra CSV:

```bash
.venv\Scripts\python.exe scripts\parse_runs.py runs\ --output analysis\base_runs.csv
```

**Lưu ý:** để `TELEGRAM_BOT_TOKEN` và `TELEGRAM_CHAT_ID` **unset** trong mọi lần chạy
`run_eval`. Case `R12_confirm_before_send` chỉ chấm việc agent gọi
`clarify(response_type="yes_no")`, không cần gửi thật.

## 9. Bản đồ file

| Path | Ai sở hữu | Mục đích |
| :-- | :-- | :-- |
| `artifacts/system_prompt.md` | R1 | instruction cho agent |
| `artifacts/tools.yaml` | R1 | tên, mô tả, schema tool |
| `artifacts/version_log.csv` | R1 | giả thuyết + metric theo version |
| `artifacts/REPORT.md` | Cả nhóm | tài liệu nộp bài |
| `tools/<tên>/tool.py` + `TOOL.md` | R2 | tool mới |
| `tools/__init__.py` | R2 | registry `TOOL_FUNCTIONS` |
| `data/eval_base.json` | **Không ai** | 20 case cố định |
| `data/eval_group.json` | R3 | 10 case nhóm tự viết |
| `analysis/*.csv` | R3 | bảng phân tích run |
| `app.py` | R4 | UI |
| `runs/*.json` | sinh tự động | bằng chứng chính |
| `transcripts/*.transcript.json` | R4 | log chat live |
