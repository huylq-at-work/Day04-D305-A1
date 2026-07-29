---
name: rank_sources
track: core
kind: local_knowledge
provider: local policy
requires_env: []
inputs: [items, min_tier]
outputs: [items, ranked, input_count, item_count, filtered_out, tier_counts, min_tier, policy, error]
side_effect: false
---
# rank_sources

Xếp hạng nguồn theo `company_policy/source-citation-policy.md`:

- Tier 1: nguồn gốc, blog/tài liệu chính thức, paper, dataset hoặc regulatory filing.
- Tier 2: báo chí uy tín **có liên kết tới bằng chứng gốc**.
- Tier 3: social/forum/screenshot/claim ẩn danh, summary chưa kiểm chứng hoặc nguồn chưa
  đủ metadata để xác định.

Tool phân loại bảo thủ: một domain báo chí chỉ lên Tier 2 khi item có
`links_primary_evidence: true`; agent không được tự bịa field này. arXiv được xếp Tier 1
vì là paper source nhưng vẫn nhận cảnh báo rằng paper chưa mặc nhiên được peer review.

`min_tier` là tier yếu nhất được phép giữ lại:

- `1`: chỉ Tier 1.
- `2`: Tier 1 và Tier 2.
- `3` (mặc định): giữ cả ba tier và chỉ sắp xếp.

Mỗi item đầu ra giữ nguyên các field ban đầu và được thêm `source_tier`,
`source_tier_label`, `tier_reason`, `needs_verification`; thứ tự ổn định trong cùng tier.
Tool không fetch URL và không xác minh tính đúng sai của claim.

## Declaration cho `artifacts/tools.yaml`

R1 copy nguyên block sau vào danh sách `tools`. R2 không tự sửa `artifacts/tools.yaml`.

```yaml
  - name: rank_sources
    description: >
      Xếp các item đã thu thập theo policy Tier 1/2/3, mạnh nhất trước, và có thể lọc
      nguồn yếu. DÙNG sau lookup/social/papers và trước format hoặc save_note. KHÔNG dùng
      để tìm kiếm, fetch URL hay xác minh claim. Truyền items theo shape {title, url,
      source, summary, section}; chỉ truyền links_primary_evidence=true khi dữ liệu đầu
      vào thực sự chứng minh báo chí có dẫn nguồn gốc. min_tier=1 chỉ giữ Tier 1,
      min_tier=2 giữ Tier 1-2, mặc định 3 giữ tất cả.
    parameters:
      type: object
      properties:
        items:
          type: array
          default: []
          description: "Danh sách item đã thu thập; không tự bịa metadata về nguồn."
          items:
            type: object
            properties:
              title: {type: string}
              url: {type: string}
              source: {type: string}
              summary: {type: string}
              section: {type: string}
              source_type: {type: string}
              links_primary_evidence: {type: boolean}
        min_tier:
          type: integer
          enum: [1, 2, 3]
          default: 3
          description: "Tier yếu nhất được giữ: 1 chỉ Tier 1; 2 giữ Tier 1-2; 3 giữ tất cả."
      required: [items]
```
