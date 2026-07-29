# ROLE 1 — Prompt & Tool-Declaration Optimizer

**Người phụ trách:** Phạm Thị Liên · **Branch:** `role1-prompt-optimizer`

> Đọc [docs/plan.md](../plan.md) trước. Mọi lệnh chạy từ `starter_v0/`.

## Bạn sở hữu

- `artifacts/system_prompt.md`
- `artifacts/tools.yaml`
- `artifacts/version_log.csv`

Bạn là **người duy nhất** được sửa hai file đầu. Lý do ở [TEAMMATES.md](../../TEAMMATES.md)
mục 2.

## Bạn không được làm

- Không sửa `data/eval_base.json`. Ngoại lệ duy nhất: field tên tool khi rename, và phải
  sync đủ 8 file theo checklist README. Không đụng `query`, `expect`, `metadata`.
- Không sửa hai file mình sở hữu **cùng lúc trong một version**. Mỗi version đổi đúng một
  artifact.
- Không chạy 3 lệnh v1/v2/v3 liên tiếp. Mỗi version phải có một giả thuyết viết ra trước.

## Nhiệm vụ

### T1 — Baseline v0 (deadline 10:15)

```bash
.venv\Scripts\python.exe run_eval.py --provider openrouter --version v0 --suite base --eval-cases data\eval_base.json
```

**Không sửa gì trước khi chạy v0.** v0 phải là baseline nguyên bản, kể cả khi bạn đã thấy
system prompt sai rành rành.

Mở `runs/` lấy file mới nhất, ghi lại 4 số:

- `summary.case_accuracy`
- `summary.tool_routing_accuracy`
- `summary.argument_accuracy`
- `summary.multiturn_accuracy`

Kiểm tra điều kiện hợp lệ: `summary.provider_error_cases` phải `== 0` và
`summary.measured_cases == summary.total_cases`. Nếu không đạt, run này **không dùng làm
baseline được** — sửa lỗi provider rồi chạy lại với vẫn nhãn `v0`.

Ghi dòng `v0` vào `version_log.csv`, cột `metric_before` để trống, `metric_after` là số v0.

### T2 — Đọc failure, đặt giả thuyết

Với mỗi case FAIL, đọc theo thứ tự:

1. `results[*].result.observed_mismatch` — hệ thống nói lệch cái gì
2. `results[*].result.failures` — chi tiết
3. `results[*].actual_tool_calls` — agent thực sự gọi gì
4. `results[*].tool_results` — tool trả về gì

Rồi hỏi: **vì sao model chọn như vậy?** Câu trả lời phải trỏ về một câu cụ thể trong
`system_prompt.md` hoặc một mô tả cụ thể trong `tools.yaml`.

### T3 — Ba vòng tối ưu

Thứ tự đề xuất, ưu tiên theo số case ảnh hưởng:

**v1 — sửa `system_prompt.md`.** Baseline đang chỉ đạo agent bịa thông tin và không hỏi
lại. Bốn case `R10`, `R11`, `M01`, `M04` phụ thuộc vào việc agent chịu gọi `clarify`, và
`R12` phụ thuộc vào việc agent hỏi xác nhận trước khi gửi. Giả thuyết gợi ý: *"Bỏ chỉ đạo
'không hỏi lại' và 'đoán tài khoản nổi tiếng' sẽ kéo các case missing_info và
wrong_boundary từ FAIL sang PASS."*

**v2 — sửa `tools.yaml`.** Mô tả tool hiện không phân biệt được "tin **của** một người"
(`timeline`) với "tin **về** một chủ đề" (`social_search`), và không nêu convention cho
`topic`/`timeframe`/`search_type`. Giả thuyết gợi ý: *"Viết rõ khi nào dùng / khi nào không
dùng trong description sẽ cải thiện `tool_routing_accuracy` mà không cần đụng prompt."*

**v3 — sau feedback showdown.** Chọn điểm yếu mà nhóm khác chỉ ra được.

Mỗi vòng:

```bash
.venv\Scripts\python.exe run_eval.py --provider openrouter --version v1 --suite base --eval-cases data\eval_base.json
```

Chạy xong mới sửa tiếp cho vòng sau.

### T4 — Ghi version log

Sau **mỗi** run, thêm một dòng vào `artifacts/version_log.csv`:

```text
version,author,changed_artifact,artifact_version,prompt_hash,tools_hash,reason,hypothesis,metric_name,metric_before,metric_after,run_file
```

- `artifact_version`, `prompt_hash`, `tools_hash` copy **nguyên văn từ run JSON**, không tự
  gõ lại.
- `hypothesis` viết trước khi chạy, không viết lùi sau khi thấy kết quả.
- `metric_before` là số của version liền trước, cùng `metric_name`.
- `run_file` là tên file trong `runs/`.

Nếu metric **giảm**, vẫn ghi lại. Một giả thuyết bị bác bỏ là bằng chứng tốt cho report,
không phải thất bại.

### T5 — Nhận tool mới từ R2

R2 sẽ đưa cho bạn khối YAML declaration đã soạn sẵn trong `TOOL.md` của tool đó. Bạn dán
vào `tools.yaml`. Trước khi dán, kiểm tra:

- `name` trong YAML khớp **chính xác** key trong `TOOL_FUNCTIONS` ở `tools/__init__.py`
- `parameters` là JSON Schema hợp lệ, có `type: object` và `required`
- description nói rõ **khi nào dùng và khi nào không dùng**

**Vòng nào thêm tool thì không sửa prompt.** Ghi `changed_artifact` là
`tools.yaml (add tool X)`.

## Tiêu chí hoàn thành

- [ ] `version_log.csv` có tối thiểu 4 dòng: `v0`, `v1`, `v2`, `v3`
- [ ] Mỗi dòng có `hypothesis` khác nhau và `changed_artifact` khác nhau
- [ ] Mọi `prompt_hash`/`tools_hash` khớp với run JSON tương ứng
- [ ] Có ít nhất một version cải thiện `tool_routing_accuracy` hoặc `argument_accuracy` đo được
- [ ] `runs/` có đủ file JSON cho cả 4 version

## Bàn giao

- Cho **R3**: đường dẫn run JSON ngay sau mỗi lần chạy, để R3 phân tích failure.
- Cho **R4**: nhãn version nào đáng demo, và một cặp v0-vs-vN cho cùng một scenario.
- Cho **report**: bảng v0–v3 ở Phần B do bạn viết.
