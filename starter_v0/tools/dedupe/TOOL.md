---
name: dedupe
track: core
kind: local_formatter
provider: local
requires_env: []
inputs: [items, key]
outputs: [items, kept, input_count, item_count, removed, duplicate_indexes, key, error]
side_effect: false
---
# dedupe

Gộp các kết quả nghiên cứu bị trùng và giữ nguyên item xuất hiện đầu tiên.

- Với `key: url`, URL được chuẩn hóa bằng cách bỏ fragment, bỏ các query parameter
  `utm_*`, chuẩn hóa scheme/domain và bỏ dấu `/` cuối path.
- Với `key: title`, title được chuẩn hóa Unicode, chữ hoa/thường và khoảng trắng.
- Item không có trường dùng để so sánh vẫn được giữ lại vì không đủ bằng chứng rằng nó
  trùng với item khác.
- Tool chỉ xử lý danh sách đã có; nó không tìm kiếm, tải nội dung hoặc trình bày digest.

Kết quả luôn là một object. Danh sách sau khi lọc có trong cả `items` và `kept`;
`removed` là số item bị loại, còn `duplicate_indexes` là vị trí của chúng trong input.

## Declaration cho `artifacts/tools.yaml`

R1 copy nguyên block sau vào danh sách `tools`. R2 không tự sửa `artifacts/tools.yaml`.

```yaml
  - name: dedupe
    description: >
      Gộp các item trùng trong một danh sách đã thu thập và giữ item xuất hiện đầu tiên.
      DÙNG sau khi có kết quả từ một hoặc nhiều nguồn, trước khi format hoặc lưu digest.
      KHÔNG dùng để tìm kiếm, tải nội dung hay loại item chỉ vì thiếu URL/title. Truyền
      items theo shape {title, url, source, summary, section}; key là url (mặc định, bỏ
      fragment và utm_*) hoặc title.
    parameters:
      type: object
      properties:
        items:
          type: array
          default: []
          description: "Danh sách item đã thu thập; item đầu tiên trong mỗi nhóm trùng được giữ lại."
          items:
            type: object
            properties:
              title: {type: string}
              url: {type: string}
              source: {type: string}
              summary: {type: string}
              section: {type: string}
        key:
          type: string
          enum: [url, title]
          default: url
          description: "Trường dùng để phát hiện item trùng."
      required: [items]
```
