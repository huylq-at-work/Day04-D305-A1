# DANH SÁCH THÀNH VIÊN NHÓM

> Day 04 Lab v2 — Research Agent Tool Eval · Đại học VinUni
> Repo: `Day04-D305-A1` · Thư mục làm việc: [`starter_v0/`](starter_v0/)

## 1. Thành viên

| STT | Họ và tên | Mã sinh viên |
| :-: | :-- | :-- |
| 1 | Nguyễn Chí Hướng | 2A202601203 |
| 2 | Nguyễn Tiến Đạt | 2A202601387 |
| 3 | Phạm Thị Liên | 2A202601795 |
| 4 | Lê Quang Huy | 2A202601821 |

## 2. Phân công vai trò & Branch

Bài lab này **không có sẵn role docs** như Lab 03 — README chỉ ghi "chia nhóm, phân vai" ở
Kickoff. Bốn vai dưới đây được nhóm tự định nghĩa, chia theo **file sở hữu** để không
conflict và để cột `author` trong `version_log.csv` có ý nghĩa.

| Thành viên | Vai trò | Branch | File sở hữu (chỉ người này được sửa) | Hướng dẫn |
| :-- | :-- | :-- | :-- | :-- |
| Phạm Thị Liên | Prompt & Tool-Declaration Optimizer | `role1-prompt-optimizer` | `artifacts/system_prompt.md`, `artifacts/tools.yaml`, `artifacts/version_log.csv` | [ROLE1](docs/roles/ROLE1_PROMPT_OPTIMIZER.md) |
| Nguyễn Chí Hướng | Tool Engineer | `role2-tool-engineer` | `tools/<tool_mới>/`, `tools/__init__.py` | [ROLE2](docs/roles/ROLE2_TOOL_ENGINEER.md) |
| Nguyễn Tiến Đạt | Eval Designer & Observability | `role3-eval-designer` | `data/eval_group.json`, `analysis/*.csv` | [ROLE3](docs/roles/ROLE3_EVAL_DESIGNER.md) |
| Lê Quang Huy | UI, Deploy & Integrator | `role4-ui-deploy` | `app.py`, `requirements.txt`, `transcripts/` | [ROLE4](docs/roles/ROLE4_UI_DEPLOY.md) |

Kế hoạch tổng theo mốc thời gian: [docs/plan.md](docs/plan.md)

### Quy tắc sở hữu file — đọc kỹ

**Chỉ R1 được sửa `system_prompt.md` và `tools.yaml`.** Đây không phải để phân biệt đối xử:
lab chấm dựa trên việc mỗi version chỉ đổi **đúng một thứ**. Nếu hai người cùng sửa hai file
này trong một vòng thì metric before/after không còn giải thích được, và cả bảng v0–v3 mất
giá trị làm bằng chứng.

R2 viết tool mới thì **soạn sẵn khối YAML declaration trong `TOOL.md`**, rồi R1 dán vào
`tools.yaml`. R2 không tự sửa `tools.yaml`.

**Không ai được sửa `data/eval_base.json`** — kể cả R3. Ngoại lệ duy nhất là field tên tool
khi rename, và phải sync đủ checklist 8 file trong README.

## 3. Quy trình Git

Bốn branch đã được tạo sẵn trên remote. **Không ai commit thẳng vào `main`** — mọi thay đổi
vào `main` phải đi qua Pull Request và được R4 review.

| Branch | Người dùng |
| :-- | :-- |
| `role1-prompt-optimizer` | Phạm Thị Liên |
| `role2-tool-engineer` | Nguyễn Chí Hướng |
| `role3-eval-designer` | Nguyễn Tiến Đạt |
| `role4-ui-deploy` | Lê Quang Huy |

**Lấy branch của mình về (lần đầu):**

```bash
git fetch origin && git checkout role1-prompt-optimizer
```

*(đổi tên branch theo bảng trên)*

**Trong lúc làm — lấy code mới nhất từ main vào branch của mình:**

```bash
git pull origin main
```

**Làm xong — đẩy lên branch của mình:**

```bash
git add . && git commit -m "Role X: mo ta ngan" && git push origin HEAD
```

**Mở Pull Request:**

```bash
gh pr create --base main --head role1-prompt-optimizer --title "Role 1: v1 prompt tuning" --body "Doi 1 gia thuyet, kem metric before/after"
```

Hoặc mở trên web GitHub. PR body nên nói rõ **đổi cái gì và vì sao**, vì đó cũng là nguyên
liệu cho REPORT.md.

**R4 review và merge:**

```bash
gh pr list && gh pr merge <số PR> --merge --delete-branch=false
```

Giữ branch lại (`--delete-branch=false`) vì mỗi người còn dùng tiếp cho version sau.

### Thứ tự merge bắt buộc

R1 chạy eval trên artifact đã gồm tool mới của R2 và eval case của R3. Nên thứ tự là:

1. PR của **R2** (tool mới + declaration đã duyệt) merge vào `main` **trước**.
2. PR của **R3** (`eval_group.json`) merge tiếp.
3. **R1** `git pull origin main` rồi mới chạy version tiếp theo — nếu không, `tools_hash`
   ghi trong `version_log.csv` sẽ không khớp với artifact thật lúc chạy.

### Xử lý conflict

Bảng sở hữu file ở mục 2 được thiết kế để **không có conflict**. Nếu vẫn xảy ra conflict,
nghĩa là ai đó đã sửa file không thuộc phần mình — dừng lại, hỏi trong nhóm, đừng tự
resolve. File hay bị đụng nhất là `artifacts/REPORT.md` vì cả nhóm cùng viết; quy ước: mỗi
người chỉ sửa đúng mục của mình, pull `main` ngay trước khi viết.

## 4. Không commit

`.env`, API key dưới mọi dạng, `.venv/`, `__pycache__/`, và output build.
Kiểm tra bằng `git status` trước mỗi lần commit.
