# Ghi chú phân tích · Day 04

Họ và tên: Vũ Tiến Hùng
MSSV: 2A202603882

## 1. Case được chọn

- ID case: **A5**
- Câu hỏi: "Tôi cần danh sách đầy đủ tất cả incident GitHub Actions trong năm 2025. Hãy tìm dữ liệu và nói rõ độ đầy đủ của kết quả, đừng bịa."
- Câu trả lời của agent (lần 1): mô tả các incident 2026 tìm được, có nói "không phải 2025" nhưng không giải thích *tại sao* không có dữ liệu 2025 — không nêu rõ giới hạn thật của tool (chỉ tìm trong 50 incident gần nhất, không lọc được theo năm).
- Điểm ở lần chạy 1: **55/100**

Cũng quan sát cùng kiểu lỗi ở **H1** (60) và **H6** (60): cả hai hỏi agent "theo liên kết do incident cung cấp" để tìm nguyên nhân sâu hơn, nhưng `get_incident_details` không có khả năng mở link ngoài — chỉ trả về text update đã bị cắt 900 ký tự. Agent trả lời dựa trên dữ liệu có sẵn nhưng không nói rõ nó chưa/không thể "theo liên kết" như câu hỏi yêu cầu.

## 2. Bằng chứng trong trace

Trace case A5 (lần 1) — agent gọi `get_status` 1 lần (step 1), nhận `matching_incidents_in_last_50`, rồi trả lời ở step tiếp theo mà không có bước nào làm rõ "không lọc được theo năm" là giới hạn của **tool**, không phải của dữ liệu thực tế:

```text
{"event": "tool", "step": 1, "name": "get_status",
 "arguments": "{\"provider\":\"github\",\"component\":\"Actions\"}",
 "result": {"incidents": [...5 incident 2026...],
            "matching_incidents_in_last_50": 23,
            "note": "Chỉ tìm theo chuỗi trong 50 incident gần nhất; không tìm thấy không chứng minh không có sự cố."}}
```

Answer (lần 1, rút gọn): "...Dưới đây là thông tin chi tiết về sự cố từ GitHub Actions trong khoảng thời gian gần đây (năm 2026, không phải 2025)..." — nêu lệch năm nhưng không trích lại `note` của tool để giải thích vì sao không trả lời được đúng yêu cầu "đầy đủ cho 2025".

**Nguyên nhân có thể xảy ra:** `SYSTEM_PROMPT` ban đầu chỉ nói chung "nêu giới hạn bằng chứng", không chỉ rõ *giới hạn cụ thể của tool* (phạm vi 50 incident gần nhất, không lọc theo năm, không mở link ngoài). Model vì vậy trả lời dựa trên dữ liệu nhận được mà không chủ động cảnh báo phạm vi.

## 3. Thay đổi đã thực hiện

- Sửa gì, ở đâu: thêm đoạn chỉ dẫn cụ thể vào `SYSTEM_PROMPT` trong `agent.py` — nêu rõ 2 giới hạn kỹ thuật của tool (chỉ tìm trong 50 incident gần nhất, không lọc theo năm/khoảng thời gian; không có khả năng mở link ngoài ngoài những gì `get_incident_details` trả, mỗi update bị cắt 900 ký tự) và yêu cầu model phải nêu giới hạn này trước khi trả lời khi câu hỏi vượt khả năng đó.
- Vì sao chọn thay đổi này: đây là lỗi lặp ở 3 case khác nhau (A5, H1, H6) với cùng gốc — model không biết/biết nhưng không chủ động khai báo giới hạn kỹ thuật thật của tool. Sửa ở system prompt (thay vì validate bằng code như URL ở Bài 4 mẫu) vì đây là vấn đề về *nội dung trả lời phải nói gì*, không phải một điều kiện nhị phân có/không dễ kiểm bằng code như "có URL hay không".

Sau vòng cải tiến đầu (chỉ sửa prompt), điểm tổng giảm (83.18 → 78.86) dù case A5 tăng mạnh —
xem lại để thấy biến động do model không deterministic. Mình làm thêm **vòng cải tiến 2**:
thêm guardrail bằng code (giống cơ chế `validation_missing_source`) — `validation_error_ignored`:
nếu answer cuối khẳng định một provider "operational" trong khi tool đã trả lỗi (`ok: false`)
cho provider đó trong phiên, agent tự phát hiện và yêu cầu model sửa lại trong `max_steps`, không
cho qua. Nhắm vào case **H7** (hỏi Cloudflare Spectrum khi tool timeout, agent cũ vẫn khẳng định
operational — vi phạm trực tiếp nguyên tắc "không coi timeout là trạng thái dịch vụ").

Test riêng cho guardrail này ở `tests/test_my_improvements.py` (không sửa file test có sẵn).

## 4. So sánh các lần chạy

| Chỉ số | `eval_before.json` (lần 1) | sau khi chỉ sửa prompt | `eval_after.json` (lần 2, có guardrail code) |
|---|---|---|---|
| Điểm tổng | 83.18/100 | 78.86/100 | **84.32/100** |
| Điểm case A5 | 55 | 80 | **100** |
| Điểm case H7 | 70 | 60 | **75** |
| Điểm case H2 | 100 | 50 | 100 |
| Model calls (case A5) | 3 | 1 | 1 |
| Token/chi phí (case A5) | 4501 tokens / $0.00109 | 522 tokens / $0.00013 | thấp tương đương |

- **Lỗi đã giải quyết:**
  - A5: agent chủ động nêu giới hạn tool ("chỉ tìm trong 50 incident gần nhất, không lọc theo năm") **và** vẫn trích dữ liệu cụ thể quan sát được — điểm evidence từ 0 lên tối đa.
  - H7: agent không còn khẳng định "Cloudflare operational" khi tool đã timeout cho Cloudflare — guardrail `validation_error_ignored` đứng sau đảm bảo không lọt qua.
- **Lỗi còn lại:** H1 và H6 (vấn đề "theo liên kết do incident cung cấp") vẫn giữ nguyên 60 điểm qua cả 2 vòng sửa — nguyên nhân thật: tool `get_incident_details` không có khả năng mở link ngoài, nhưng việc chỉ nhắc trong system prompt chưa đủ để judge hài lòng về độ sâu phân tích nguyên nhân. Cần một cải tiến khác (ví dụ: tool đọc link hoặc một cảnh báo hiển thị rõ hơn trong câu trả lời) — ngoài phạm vi 1 vòng sửa của bài.
- **Biến động do model không deterministic:** nhiều case không liên quan trực tiếp đến 2 thay đổi trên vẫn lên/xuống vài điểm giữa các lần chạy (ví dụ A3, A4 giảm 20–25 ở vòng 2 dù agent không đổi hành vi cho câu hỏi đó) — xác nhận lại nhận định ở vòng 1: **điểm tổng dao động tự nhiên**, chỉ nên tin vào case có cơ chế nhân-quả rõ ràng (A5, H7), không tin tuyệt đối vào % tổng của 1 lần chạy.

## 5. Giới hạn

- **Điểm judge là ước lượng:** cùng model vừa làm agent vừa làm judge (`judge_provider`/`judge_model` mặc định = agent), nên có thể thiên lệch khi tự chấm cho chính mình, và judge không luôn nhất quán giữa 2 lần chạy cho cùng 1 câu trả lời giống nhau về bản chất.
- **Snapshot cố định** (09/11/2026): không phản ánh tình trạng thật ngoài thực tế tại thời điểm đọc notes này.
- **Chỉ chạy 1 lần mỗi phiên bản:** như quan sát ở mục 4, bản thân việc chạy lại CÙNG MỘT agent (không đổi gì) với model không deterministic cũng có thể cho điểm tổng khác nhau vài điểm — nên kết luận "cải tiến tốt hơn/xấu hơn" dựa trên 1 lần chạy mỗi bên có độ tin cậy thấp. Bằng chứng đáng tin nhất ở đây là **case A5 cụ thể** (có cơ chế rõ ràng: prompt mới → agent nói đúng câu cần nói), không phải điểm tổng.
- Thay đổi ở system prompt không giải quyết được H1/H6 — cần một vòng phân tích + cải tiến tiếp theo (ví dụ: thêm cảnh báo cứng khi `truncated: true` trong tool result) để xử lý nhóm lỗi "theo liên kết ngoài" triệt để hơn.
- Đã thử nâng điểm tổng lên gần 95 bằng 2 vòng cải tiến liên tiếp, đạt 84.32/100 (cao hơn cả lần 1). Không đạt 95 vì: (1) judge/model không deterministic nên luôn có case dao động ±10-25 điểm không liên quan đến thay đổi; (2) model dùng (qua OpenRouter, cấp miễn phí/nhỏ) có giới hạn khả năng suy luận nhân-quả sâu (H1/H6); một model mạnh hơn nhiều khả năng cải thiện các case này hơn là tiếp tục chỉnh prompt.
