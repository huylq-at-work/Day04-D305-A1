# Day 04 Lab v2 Report — Research Agent

> File này gồm 2 phần, deadline khác nhau:
> - **PHẦN A — Giới thiệu agent**: ngắn gọn 1 trang để team khác hiểu nhanh agent có tool gì, làm được gì, thử bằng câu hỏi nào. Xong trước 11:30 để làm tài liệu phụ trợ khi demo.
> - **PHẦN B — Chi tiết / Bằng chứng**: bảng đầy đủ (v0–v3, failure, eval, chat) dựa trên log thật. Có thể hoàn thiện sau buổi debate để nộp bài.

## Team

- Team: D305-A1
- Members: Nguyễn Chí Hướng (2A202601203), Nguyễn Tiến Đạt (2A202601387), Phạm Thị Liên (2A202601795), Lê Quang Huy (2A202601821)
- Provider/model: `openai / gpt-4o-mini` (cố định từ v0 đến v3 để metric before/after so sánh được)

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Research agent tiếng Việt: tìm tin theo chủ đề hoặc theo tài khoản mạng xã hội, đọc nội dung URL, lọc trùng + xếp hạng độ tin cậy nguồn theo company policy, rồi tổng hợp thành digest. Agent **hỏi lại khi thiếu thông tin** (không đoán handle/URL) và **bắt buộc xác nhận yes/no** trước mọi hành động không hoàn tác (gửi Telegram, ghi file).

Kết quả tối ưu qua 4 version (đo bằng eval tự động, không phải cảm giác): base eval `0.70 → 0.95 → 1.00 → 1.00`; group eval của nhóm đạt `7/10` ở v3 với 3 fail đã phân tích nguyên nhân.

**Link dùng thử (truy cập được trong showdown):**

> URL: `http://localhost:8501` (demo trực tiếp trên máy trình chiếu — chạy `streamlit run app.py` trong `starter_v0/`).
> Public URL qua Cloudflare Tunnel sẽ dán vào đây trước showdown: `cloudflared tunnel --url http://localhost:8501`

Lưu ý khi thử: API key của research tools (Tavily/RapidAPI/Firecrawl) chưa gắn, nên tool sống trả error có kiểm soát — **cái cần chấm là trace: agent chọn tool nào, args gì**, hiển thị đầy đủ trên UI.

## A2. Tool agent có

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| clarify | hỏi lại khi thiếu thông tin; xác nhận yes/no trước hành động nhạy cảm | không |
| timeline | lấy bài đăng gần đây CỦA một tài khoản cụ thể | không |
| social_search | tìm bài đăng VỀ một chủ đề/từ khóa (Latest/Top) | không |
| lookup | tìm web, phân biệt topic news/general, timeframe day→year | không |
| fetch | đọc nội dung một URL cụ thể | không |
| format | trình bày items đã có thành digest markdown | không |
| send | gửi text lên Telegram — bắt buộc confirm trước, `confirmed=true` mới gửi | không |
| policy / papers / paper_text | tìm policy nội bộ / tìm paper arXiv / trích text PDF | không (optional có sẵn) |
| **dedupe** | gộp item trùng theo url (bỏ utm_*) hoặc title chuẩn hoá | **CÓ** |
| **save_note** | ghi digest ra `notes/*.md`; chặn path traversal; cần `confirmed=true` | **CÓ** |
| **rank_sources** | xếp hạng nguồn theo Tier 1/2/3 của `source-citation-policy.md`; cảnh báo arXiv chưa peer-review | **CÓ** |
| **extract_entities** | bóc tên người/tổ chức/handle từ text đã fetch (heuristic + confidence) | **CÓ** |

4 tool mới đều chạy local, không cần API key, kèm `TOOL.md` + declaration đầy đủ trong `tools.yaml` (14/14 khai báo).

## A3. Câu hỏi mẫu để thử

1. `Tin tức AI hôm nay có gì nổi bật?` → `lookup(query="AI", topic="news", timeframe="day")`
2. `Tóm tắt 5 tweet mới nhất giúp mình` (không nói của ai) → agent **hỏi lại** thay vì đoán; trả lời `Của Elon Musk nhé` → `timeline(screenname="elonmusk", limit=5)`
3. `Đăng bản tin này lên Telegram giúp mình` → hỏi xác nhận yes/no trước, không gửi thẳng
4. `Giải giúp mình nguyên hàm của x^2` → từ chối lịch sự, **0 tool call**
5. `Mình có 2 bài cùng tên 'GPT-5 ra mắt' ở abc.com và xyz.com, gộp bài trùng tên giúp mình` → `dedupe` (tool nhóm tự viết)

## A4. Kịch bản demo đã rehearse

| Scenario | Tool trace cần thấy | Câu chuyện cải thiện version | Fallback run/transcript |
|---|---|---|---|
| Thiếu handle → hỏi lại → điền tiếp | `clarify` → `timeline(screenname="elonmusk", limit=5)` | v0 bịa `sama` (R10 FAIL) → v1 hỏi lại (PASS). Demo bằng chế độ *So sánh 2 version* trên UI: snapshot v0 vs v3 cạnh nhau | `runs/v0_B_base_...json` vs `runs/v1_B_base_...json` |
| Gửi Telegram phải xác nhận | `clarify(response_type="yes_no")`, chỉ `send(confirmed=true)` sau khi user đồng ý | v0 gửi thẳng không hỏi (R12 FAIL) → v1 có boundary (PASS); mặt còn lại G10-cũ: đã confirm thì không hỏi vòng nữa | `runs/v2_B_group_...json` (G04, G10 PASS) |
| Câu ngoài phạm vi (toán/code/dịch) | **không có tool call nào** | v0 gọi `send` để trả lời toán và code (R08, R14 FAIL) → v1 từ chối đúng (PASS) | `runs/v3_B_base_...json` (R08, R14 PASS) |
| Hỏi lại đúng kiểu câu trả lời | `clarify(response_type="text")` khi xin URL | v1 route đúng nhưng thiếu `response_type` (R11 FAIL) → v2 viết convention vào description của clarify (PASS). Luận điểm: **tool declaration cũng là prompt** | `runs/v1_...json` (R11 FAIL) vs `runs/v2_B_base_...json` (20/20) |
| Tool mới + giới hạn hiện tại | `dedupe` được gọi đúng lúc, nhưng v3 còn bỏ `key=title` (G10 FAIL — trung thực) | v3 thêm 4 declaration: base không regress (20/20), group lộ 3 lỗi mới đo được → giả thuyết cho v4 | `runs/v3_B_group_...json` |

---

# PHẦN B — Chi tiết / Bằng chứng

> Điều kiện metric hợp lệ: `provider_error_cases` phải bằng `0`; `measured_cases` phải bằng `total_cases`; và bất kỳ `tool_results` nào có error đều phải được review thủ công vì routing PASS không chứng minh tool execution đã đúng.

## B1. Version evidence

Fill from `artifacts/version_log.csv` and `runs/*.json`.

| Version | Prompt/tool change | Hypothesis | Metric name | Before | After | Run File |
|---|---|---|---|---:|---:|---|
| v0 | baseline | N/A | case_accuracy | N/A | 0.500 | `v0_B_group_openai_...json` |
| v1 | Thêm rules vào prompt, sửa tools | Khắc phục các lỗi thiếu clarify và phân ranh giới công cụ | case_accuracy | 0.500 | - | `v1_B_group_openai_...json` |
| v2 | Bổ sung rules cho tools mới | Cải thiện độ chính xác khi dùng tool mới | case_accuracy | 0.500 | 0.875 | `v2_B_group_openai_20260729T114922528868.json` |
| v3 | | | | | | |

## B2. Failure analysis

Use actual failures from `results[*].result.failures`.

| Case ID | Failure Type | Actual Tool Calls | What Failed | Fix |
|---|---|---|---|---|
| R08_out_of_scope | out_of_scope | `send` | Lẽ ra không gọi tool (`no_tool`), nhưng agent lại gọi `send` để trả lời toán. | Thêm luật cấm gọi tool `send` với các câu hỏi toán học/code. |
| R10_missing_handle | missing_info | `timeline(screenname="sama")` | Thiếu `clarify`, agent tự đoán bừa handle "sama". | Bắt buộc dùng `clarify` khi user chưa cung cấp rõ tài khoản. |
| R11_missing_url | missing_info | `fetch(url="https://example.com/article")` | Thiếu `clarify`, agent tự bịa URL ảo. | Bắt buộc dùng `clarify` xin link khi user bảo "bài này" mà chưa có URL. |
| R12_confirm_before_send | wrong_boundary | `send(text="...")` | Thiếu `clarify(response_type="yes_no")` trước khi gửi. | Thêm luật bắt buộc hỏi xác nhận (yes_no) trước khi gọi tool `send`. |
| R13_parallel_web_and_tweets | wrong_tool | `lookup(query="AI news")` | Gọi `lookup` sai arg, gộp chữ "news" vào query thay vì dùng `topic="news"`. | Làm rõ mô tả của arg `query` và `topic` trong `tools.yaml`. |
| R14_out_of_scope_coding | out_of_scope | `send` | Gọi tool `send` để trả lời câu hỏi viết code. | Cấm dùng `send` để trả lời code, yêu cầu từ chối thẳng. |

## B3. Team eval cases

List the 10 cases added to `data/eval_group.json`:

- 5 single-turn
- 5 multi-turn

This section is for the mandatory team-authored eval set. Optional built-ins do
not belong here.

File template để trống có chủ đích; nhóm phải tự thiết kế đủ 10 case.

| Case ID | What It Tests | Expected Tool/Behavior | Result (V2) |
|---|---|---|---|
| G01_extract_entities_usage | Bóc tách tên người/tổ chức | `extract_entities` | PASS |
| G02_rank_sources_usage | Lọc nguồn theo Tier 1 | `rank_sources` | FAIL |
| G03_out_of_scope_translation | Từ chối dịch thuật | `no_tool` | PASS |
| G04_confirm_before_send_text | Hỏi xác nhận trước khi gửi | `clarify(response_type="yes_no")` | PASS |
| G05_missing_account_pronoun | Xin username khi thiếu | `clarify` | PASS |
| G06_switch_account_to_topic | Chuyển đổi linh hoạt ngữ cảnh tìm kiếm | `social_search` | PASS |
| G07_widen_timeframe_after_correction | Cập nhật khoảng thời gian | `lookup` | FAIL |
| G08_save_note_after_confirm | Lưu Markdown sau xác nhận | `save_note` | PASS |
| G09_missing_url_not_supplied_by_context | Xin URL bài viết chưa rõ | `clarify` | PASS |
| G10_dedupe_tool_usage | Lọc bài báo trùng tên | `dedupe` | FAIL |

## B4. Live chat evidence

Use `transcripts/*.transcript.json`.

| Scenario/Turn | Version | Tool Calls + Args | Transcript/Run | Outcome |
|---|---|---|---|---|
|  |  |  |  |  |

## B5. Tool capability evidence

Phân loại rõ tool mới bắt buộc, optional built-in và tool đủ điều kiện bonus. Chỉ ghi Telegram/PDF nếu nhóm thực sự dùng; base report không cần chúng.

UI is core deliverable, not bonus. Do not list it here.

| Category | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| Must-have: tool mới đầu tiên |  |  |  |
| Optional built-in |  |  |  |
| Bonus: tool mới thứ 4 trở đi |  |  |  |

## B6. Reflection

- Which fixes belonged in `system_prompt.md`?
- Which fixes belonged in `tools.yaml`?
- Which failure needed manual review instead of automatic grading?
- What would you improve next?
