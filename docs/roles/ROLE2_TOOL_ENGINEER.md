# ROLE 2 — Tool Engineer

**Người phụ trách:** Nguyễn Chí Hướng · **Branch:** `role2-tool-engineer`

> Đọc [docs/plan.md](../plan.md) trước. Mọi lệnh chạy từ `starter_v0/`.

## Bạn sở hữu

- `tools/<tên_tool_mới>/tool.py`
- `tools/<tên_tool_mới>/TOOL.md`
- `tools/__init__.py` (chỉ phần thêm import + key mới)

## Bạn không được làm

- **Không sửa `artifacts/tools.yaml`.** Bạn soạn khối YAML declaration trong `TOOL.md`, R1
  dán vào. Đây là để giữ tính đối chứng của thí nghiệm v0–v3.
- Không sửa 10 tool có sẵn trừ khi nhóm thống nhất rename.
- Không đổi chữ ký hàm của tool đang có — `eval_base.json` chấm dựa trên args của chúng.

## Contract bắt buộc

Mỗi tool là một folder:

```text
tools/<tool_name>/
  TOOL.md   # frontmatter + ghi chú
  tool.py   # implementation tự chứa
```

`TOOL.md` frontmatter dùng đúng các field này:

```yaml
---
name: tool_name
track: core | bonus
kind: live_api | local_formatter | local_knowledge | action | control
provider: Tên provider nếu có
requires_env: [ENV_VAR]
inputs: [arg_name]
outputs: [field_name]
side_effect: false | true | local_file_write
requires_confirmation: true   # chỉ với tool ghi/hành động
---
```

Xem mẫu ngắn nhất ở [`tools/clarify/TOOL.md`](../../starter_v0/tools/clarify/TOOL.md).

## Ràng buộc kỹ thuật (đọc kỹ, dễ sai)

**Hàm phải trả về `dict`.** `chat.py` gọi `func(**call.args)` rồi nhét nguyên kết quả vào
`event["result"]` và JSON-serialize. Trả về string cũng chạy nhưng mất cấu trúc, UI của R4
không hiển thị đẹp được.

**Mọi tham số phải có default.** Model có thể bỏ sót arg optional; thiếu default là
`TypeError` và case thành `provider_error`.

**Không raise.** `execute_tool_call` có bắt exception, nhưng kết quả sẽ là
`{"error": ..., "message": ...}` và case đó phải review thủ công. Tự bắt lỗi và trả
`{"error": "...", "message": "..."}` có ý nghĩa thì tốt hơn.

**Cờ `awaiting_user` là dành riêng.** Nếu tool trả `{"awaiting_user": True}` thì
`run_model_tool_loop` **dừng cả vòng lặp** và coi đó là câu hỏi cho user
([chat.py:120](../../starter_v0/chat.py)). Chỉ tool kiểu clarify mới được set cờ này. Set
nhầm là agent đứng im giữa chừng.

**Tool có side effect phải có confirmation boundary.** Theo mẫu `send`: nhận thêm tham số
`confirmed: bool = False`, và khi `confirmed` là `False` thì **không thực thi**, trả về
thông báo cần xác nhận. Mô tả trong declaration phải nói rõ điều này.

## Nhiệm vụ

### T1 — Chọn tool để viết (deadline chốt 10:25)

Bắt buộc **≥1 tool mới**. Muốn ăn bonus phải **>3 tool mới**, và bonus chỉ tính khi UI của
R4 cũng đạt.

Tool mới phải khác thật sự với 10 tool có sẵn (`clarify`, `timeline`, `social_search`,
`lookup`, `fetch`, `format`, `send`, `policy`, `papers`, `paper_text`). Ưu tiên tool
**không cần API key mới** để không bị chặn bởi quota giữa buổi.

Gợi ý an toàn, chạy offline được:

| Tool | kind | Ý tưởng |
| :-- | :-- | :-- |
| `dedupe` | local_formatter | Gộp item trùng theo URL/title trước khi `format` |
| `compare` | local_formatter | So sánh 2 nhóm item thành bảng markdown |
| `save_note` | local_file_write | Ghi digest ra `notes/*.md`, cần `confirmed` |
| `extract_entities` | local_formatter | Bóc tên người/tổ chức/sản phẩm từ text đã fetch |
| `rank_sources` | local_knowledge | Chấm độ tin cậy nguồn theo danh sách domain nội bộ |

Tool `local_formatter` có lợi thế: chạy tức thì, không tốn quota, dễ demo trace trên UI.

### T2 — Viết tool

Ví dụ khung tối thiểu:

```python
from __future__ import annotations

from typing import Any


def dedupe_items(items: list[dict] | None = None, key: str = "url") -> dict[str, Any]:
    items = items or []
    seen: set[str] = set()
    kept: list[dict] = []
    for item in items:
        marker = str(item.get(key, "")).strip().lower()
        if marker and marker in seen:
            continue
        seen.add(marker)
        kept.append(item)
    return {"tool": "dedupe", "kept": kept, "removed": len(items) - len(kept), "key": key}
```

### T3 — Đăng ký vào registry

Trong `tools/__init__.py`, thêm import và một key vào `TOOL_FUNCTIONS`:

```python
from .dedupe.tool import dedupe_items
```

```python
TOOL_FUNCTIONS = {
    ...
    "dedupe": dedupe_items,
}
```

Key trong dict là **tên model nhìn thấy**, phải khớp `name` trong `tools.yaml`. Lệch tên là
eval báo `not declared in tools.yaml`.

### T4 — Smoke test trước khi giao

```bash
.venv\Scripts\python.exe -c "from tools import TOOL_FUNCTIONS; print(sorted(TOOL_FUNCTIONS)); print(TOOL_FUNCTIONS['dedupe'](items=[{'url':'a'},{'url':'a'},{'url':'b'}]))"
```

Phải thấy tên tool mới trong danh sách và kết quả trả về là dict hợp lý. Chưa PASS bước này
thì **không giao cho R1**.

### T5 — Soạn declaration cho R1

Viết khối YAML vào cuối `TOOL.md`, sẵn sàng để R1 copy nguyên:

```yaml
  - name: dedupe
    description: >
      Gộp các item trùng nhau trong một danh sách đã thu thập, so theo url (mặc định)
      hoặc title. DÙNG khi đã có kết quả từ nhiều nguồn và trước khi trình bày digest.
      KHÔNG dùng để tìm kiếm hay lấy dữ liệu mới — tool này chỉ xử lý dữ liệu đã có.
    parameters:
      type: object
      properties:
        items:
          type: array
          default: []
          description: "Danh sách item đã thu thập"
          items:
            type: object
            properties:
              title: {type: string}
              url: {type: string}
        key: {type: string, enum: [url, title], default: "url", description: "Trường dùng để so trùng"}
      required: [items]
```

Description tốt phải có đủ: **DÙNG khi nào**, **KHÔNG dùng khi nào**, và convention cho
argument. Đây là phần được chấm — tên và mô tả tool là một phần của interface với model,
không phải comment.

## Nếu nhóm quyết định rename tool

Rename phải sync đủ, thiếu một chỗ là eval hỏng:

1. `artifacts/system_prompt.md`
2. `artifacts/tools.yaml`
3. `tools/<tool_name>/TOOL.md`
4. `tools/__init__.py`
5. `data/eval_base.json` (**chỉ** field tên tool)
6. `data/eval_research_extension.json`
7. `data/eval_group.json` nếu có nhắc tên đó
8. `artifacts/REPORT.md` và text demo/poster

## Tiêu chí hoàn thành

- [ ] `tools/<tên>/tool.py` chạy được, trả `dict`, mọi arg có default
- [ ] `TOOL.md` có frontmatter đủ field + khối YAML declaration sẵn cho R1
- [ ] Đã thêm vào `TOOL_FUNCTIONS`, smoke test PASS
- [ ] Tool có side effect thì có `confirmed` và mô tả nêu rõ boundary
- [ ] Đã báo R1 và merge vào `main` **trước** khi R1 chạy version kế tiếp

## Bàn giao

- Cho **R1**: khối YAML + tên tool + một câu mô tả khi nào nên route vào tool này.
- Cho **R3**: gợi ý 1–2 eval case chạm vào tool mới (thường là `unnecessary_tool` — agent
  gọi tool mới trong tình huống không cần).
- Cho **R4**: cấu trúc dict trả về, để UI render trace cho đẹp.
