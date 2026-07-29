---
name: extract_entities
track: core
kind: local_formatter
provider: local heuristics
requires_env: []
inputs: [text, kinds]
outputs: [entities, by_kind, counts, entity_count, requested_kinds, text_length, heuristic, error]
side_effect: false
---
# extract_entities

Bóc các entity candidate từ text đã đọc bằng heuristic local, không cần API key:

- `person`: chuỗi tên viết hoa và tên sau honorific/chức danh.
- `organization`: tên có marker như University, Inc., Labs, Foundation, Công ty,
  Tập đoàn, hoặc acronym/brand như NASA và OpenAI.
- `handle`: chuỗi `@handle`; pattern tránh lấy phần `@domain` trong email.

Kết quả được chuẩn hóa bằng `fold_text`, lọc token rỗng bằng `terms`, gộp entity trùng và
đếm `mentions`. Mỗi entity có `method` và `confidence`. Đây là heuristic candidate
extraction, không phải named-entity model hay bằng chứng xác minh danh tính.

`kinds` mặc định gồm cả `person`, `organization`, `handle`. Tool chỉ xử lý text đã có;
không fetch URL, tìm kiếm hoặc xác minh claim.

## Declaration cho `artifacts/tools.yaml`

R1 copy nguyên block sau vào danh sách `tools`. R2 không tự sửa `artifacts/tools.yaml`.

```yaml
  - name: extract_entities
    description: >
      Bóc tên người, tổ chức và @handle từ text đã đọc bằng heuristic local. DÙNG sau
      fetch hoặc paper_text khi cần lập danh sách entity trước khi format/rank. KHÔNG
      dùng để fetch URL, tìm kiếm, xác minh danh tính hoặc coi candidate là fact đã kiểm
      chứng. Truyền toàn bộ nội dung qua text; kinds mặc định gồm person, organization
      và handle, hoặc chọn một tập con trong ba giá trị này.
    parameters:
      type: object
      properties:
        text:
          type: string
          default: ""
          description: "Nội dung plain text hoặc Markdown đã lấy về; không truyền URL thay cho nội dung."
        kinds:
          type: array
          default: [person, organization, handle]
          description: "Các loại entity cần trả về."
          items:
            type: string
            enum: [person, organization, handle]
          minItems: 1
          uniqueItems: true
      required: [text]
```
