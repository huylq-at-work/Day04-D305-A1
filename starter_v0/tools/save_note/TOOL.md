---
name: save_note
track: core
kind: action
provider: local filesystem
requires_env: []
inputs: [markdown, filename, confirmed]
outputs: [status, path, characters_written, bytes_written, error, message]
side_effect: local_file_write
requires_confirmation: true
---
# save_note

Lưu một digest Markdown vào thư mục `starter_v0/notes/`.

- Khi `confirmed` là `false`, tool chỉ trả `status: needs_confirmation` và không tạo
  thư mục hoặc file.
- Chỉ ghi file sau khi user xác nhận rõ ràng và agent gọi lại với `confirmed: true`.
- `filename` phải là một tên file đơn, không chứa đường dẫn; `.md` được tự thêm nếu thiếu.
- Tool không ghi đè file đã tồn tại. Hãy chọn tên khác nếu nhận lỗi `already_exists`.
- Tool không dùng để gửi nội dung ra dịch vụ bên ngoài hoặc lưu định dạng khác Markdown.

## Declaration cho `artifacts/tools.yaml`

R1 copy nguyên block sau vào danh sách `tools`. R2 không tự sửa `artifacts/tools.yaml`.

```yaml
  - name: save_note
    description: >
      Lưu một digest Markdown vào thư mục notes/ trên máy. DÙNG khi user yêu cầu lưu hoặc
      ghi nội dung thành note Markdown. KHÔNG dùng để format nội dung, gửi Telegram hay
      trả lời câu hỏi chỉ cần đọc. Đây là action có side effect: luôn gọi lần đầu với
      confirmed=false; chỉ gọi lại confirmed=true sau khi user xác nhận rõ ràng. filename
      là tên file đơn, không chứa path; tool tự thêm .md và không ghi đè file đã tồn tại.
    parameters:
      type: object
      properties:
        markdown:
          type: string
          default: ""
          description: "Nội dung Markdown không rỗng cần lưu."
        filename:
          type: string
          default: ""
          description: "Tên file đơn; có thể bỏ đuôi .md, không được chứa đường dẫn."
        confirmed:
          type: boolean
          default: false
          description: "Chỉ true sau khi user đã xác nhận rõ ràng việc ghi file."
      required: [markdown, filename]
```
