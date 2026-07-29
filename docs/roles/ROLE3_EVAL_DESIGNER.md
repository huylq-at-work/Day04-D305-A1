# ROLE 3 — Eval Designer & Observability

**Người phụ trách:** Nguyễn Tiến Đạt · **Branch:** `role3-eval-designer`

> Đọc [docs/plan.md](../plan.md) trước. Mọi lệnh chạy từ `starter_v0/`.

## Bạn sở hữu

- `data/eval_group.json` — đúng 10 case do nhóm tự thiết kế
- `analysis/*.csv` — bảng phân tích run
- Phần failure analysis trong `artifacts/REPORT.md`

## Bạn không được làm

- **Không sửa `data/eval_base.json`.** 20 case ở đó là cố định. Sửa là mất tính đối chứng
  của toàn bộ bảng v0–v3.
- Không sửa `system_prompt.md` / `tools.yaml` — đó là của R1. Bạn đưa **giả thuyết**, R1
  thực hiện.

## Nhiệm vụ

### T1 — Đọc failure của v0 (song song với R1, từ 09:40)

Ngay khi R1 có run JSON đầu tiên, mở file trong `runs/` và với mỗi case FAIL ghi lại:

| Trường trong run JSON | Đọc để biết |
| :-- | :-- |
| `results[*].result.observed_mismatch` | hệ thống nói lệch cái gì |
| `results[*].result.failures` | chi tiết từng điểm sai |
| `results[*].actual_tool_calls` | agent thực sự gọi tool nào, args nào |
| `results[*].tool_results` | tool trả về gì, có `error` không |

Sản phẩm của bước này là một bảng: *case ID → agent làm gì → lẽ ra phải làm gì → nghi ngờ
do câu nào trong prompt / mô tả tool nào*. Đưa bảng này cho R1 làm nguyên liệu giả thuyết.

**Cảnh báo:** một case PASS routing vẫn có thể có `tool_results` chứa `error` (hết quota,
API lỗi). Những case đó phải review thủ công và ghi vào report — PASS routing không chứng
minh tool chạy đúng.

### T2 — Viết đúng 10 eval case (deadline 11:30)

`data/eval_group.json` đang có `"cases": []`. Bạn điền vào đó **đúng 10 case**:

- **5 single-turn** dùng field `query`
- **5 multi-turn** dùng field `turns`

Mỗi case bắt buộc có:

| Field | Ràng buộc |
| :-- | :-- |
| `id` | duy nhất, gợi nhớ, ví dụ `G01_wrong_tool_topic_vs_account` |
| `phase` | luôn là `"B"` |
| `failure_type` | thuộc `wrong_tool`, `wrong_arg_value`, `wrong_boundary`, `unnecessary_tool`, `out_of_scope`, `missing_info` |
| `expect` | `{"tool_calls": [...]}` **hoặc** `{"no_tool": true}` |
| `metadata.what_it_tests` | một câu, nói rõ case này bắt lỗi gì |

Schema mẫu: [`samples/eval_group.schema.example.json`](../../starter_v0/samples/eval_group.schema.example.json).
Hai case trong đó là **ví dụ**, không tính vào 10 case và không được nộp thay.

### Quy tắc multi-turn

Phần tử **cuối cùng** của `turns` phải là user turn đang được chấm. Các turn trước chỉ là
ngữ cảnh. Ví dụ đúng:

```json
{
  "id": "G06_carryover_after_correction",
  "phase": "B",
  "turns": [
    {"role": "user", "content": "Lấy 5 tweet của Sam Altman"},
    {"role": "user", "content": "Nhầm rồi, mình cần của Elon Musk"},
    {"role": "user", "content": "Vẫn 5 tweet nhé"}
  ],
  "failure_type": "wrong_arg_value",
  "expect": {"tool_calls": [{"name": "timeline", "args": {"screenname": "elonmusk", "limit": 5}}]},
  "metadata": {"what_it_tests": "Sau khi user sửa tài khoản, agent phải giữ handle mới chứ không quay lại sama."}
}
```

### Nguyên tắc thiết kế case tốt

**Phủ đủ 6 `failure_type`.** 10 case / 6 loại nghĩa là có loại lặp lại — chọn lặp ở loại
nhóm mình yếu nhất theo kết quả v0.

**Args trong `expect` được chấm theo subset.** Chỉ liệt kê arg bạn thực sự muốn kiểm tra.
Liệt kê thừa (như `limit` khi câu hỏi không nói số lượng) sẽ tạo FAIL giả.

**Case phải phân biệt được.** Một case tốt là case mà agent **có thể** làm sai theo một
cách cụ thể, dự đoán được. Câu hỏi mà mọi model đều trả lời đúng thì không đo được gì.

**Đừng chép lại `eval_base.json`.** Base đã phủ: routing timeline vs social_search, args
`limit`/`timeframe`/`search_type`, out-of-scope, missing handle/url, confirm before send,
parallel call, và 6 case multi-turn. Case của nhóm nên chạm vào **tool mới của R2** và vào
những lỗi bạn thực sự thấy trong run JSON.

Gợi ý hướng đi, mỗi hướng một `failure_type`:

| failure_type | Ý tưởng case |
| :-- | :-- |
| `wrong_tool` | Câu vừa có link vừa có chủ đề — phải chọn `fetch`, không phải `lookup` |
| `wrong_arg_value` | "tin hot nhất tháng này" → `topic=news`, `timeframe=month`, `search_type=Top` |
| `wrong_boundary` | Yêu cầu gửi digest ra ngoài → phải hỏi xác nhận trước |
| `unnecessary_tool` | Đã có đủ item trong hội thoại → chỉ cần `format`, không tìm lại |
| `out_of_scope` | Nhờ viết code / giải toán → `no_tool` |
| `missing_info` | "Tóm tắt bài đó cho mình" mà chưa có URL → `clarify` |

### T3 — Chạy eval nhóm

```bash
.venv\Scripts\python.exe run_eval.py --provider openrouter --version v3 --suite group --eval-cases data\eval_group.json
```

Trước khi chạy, validate JSON:

```bash
.venv\Scripts\python.exe -c "import json;d=json.load(open('data/eval_group.json',encoding='utf-8'));c=d['cases'];print('total',len(c));print('single',sum(1 for x in c if 'query' in x));print('multi',sum(1 for x in c if 'turns' in x));print('types',sorted({x['failure_type'] for x in c}))"
```

Phải ra: `total 10`, `single 5`, `multi 5`, và mọi `failure_type` nằm trong danh sách cho
phép. `run_eval.py` sẽ tự reject nếu `failure_type` sai hoặc tool trong `expect` chưa được
khai trong `tools.yaml`.

### T4 — Parse run ra CSV

```bash
.venv\Scripts\python.exe scripts\parse_runs.py runs\ --output analysis\base_runs.csv
```

Dùng CSV này dựng bảng so sánh v0→v3 cho report: case nào chuyển FAIL→PASS, case nào
regress PASS→FAIL. **Case regress là phần thú vị nhất của report** — nó cho thấy một thay
đổi prompt có đánh đổi.

## Tiêu chí hoàn thành

- [ ] `data/eval_group.json` có **đúng 10** case, 5 `query` + 5 `turns`
- [ ] Mọi case có `id`, `phase: "B"`, `failure_type` hợp lệ, `expect`, `metadata.what_it_tests`
- [ ] Mọi multi-turn có phần tử cuối là user turn được chấm
- [ ] Mọi tool trong `expect` đã có trong `tools.yaml`
- [ ] Chạy suite `group` thành công, `provider_error_cases == 0`
- [ ] `analysis/*.csv` có bảng v0→v3
- [ ] Bảng failure analysis đã viết vào REPORT.md Phần B

## Bàn giao

- Cho **R1**: bảng giả thuyết từ failure v0, cập nhật lại sau mỗi version.
- Cho **R4**: 3 scenario đáng demo nhất — chọn case mà v0 sai rõ và vN đúng rõ.
- Cho **report**: mục eval cases + failure analysis Phần B.
