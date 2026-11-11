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

## 4. So sánh hai lần chạy

| Chỉ số | `eval_before.json` | `eval_after.json` |
|---|---|---|
| Điểm tổng | 83.18/100 | 78.86/100 |
| Điểm case A5 | 55 | **80** |
| Model calls (case A5) | 3 | 1 |
| Token/chi phí (case A5) | 4501 tokens / $0.00109 | 522 tokens / $0.00013 |

- **Lỗi đã giải quyết:** case A5 — agent giờ chủ động nói ngay từ câu đầu: "tôi không thể cung cấp danh sách đầy đủ... vì công cụ của tôi chỉ có khả năng tìm kiếm trong 50 sự cố gần nhất và không có khả năng lọc theo năm" — đúng hành vi mong muốn, tốn ít model call hơn (1 so với 3) vì không cần vòng sửa lại.
- **Lỗi còn lại:** H1 và H6 (vấn đề "theo liên kết") **không đổi điểm** (vẫn 60) — system prompt chưa đủ mạnh để model tự nhận ra trường hợp "theo link" cụ thể này, có thể cần thêm ví dụ cụ thể hơn trong prompt hoặc một cảnh báo riêng khi `truncated: true`.
- **Lỗi mới xuất hiện / biến động:** điểm tổng **giảm** (83.18 → 78.86) mặc dù case mục tiêu tăng mạnh. So từng case: nhiều case không liên quan đến thay đổi (A1 giảm 30, H2 giảm 50, E2 giảm 25) cũng thay đổi điểm đáng kể theo cả hai hướng. Kiểm tra case H2 cho thấy nguyên nhân là agent **chọn đường tool-call khác** giữa 2 lần chạy (có lần gọi `get_status` kiểm tra tình trạng hiện tại, có lần không) — đây là do model không deterministic (không cố định temperature/seed), không phải do system prompt gây ra, vì nội dung câu hỏi H2 không liên quan đến phần prompt vừa thêm.

## 5. Giới hạn

- **Điểm judge là ước lượng:** cùng model vừa làm agent vừa làm judge (`judge_provider`/`judge_model` mặc định = agent), nên có thể thiên lệch khi tự chấm cho chính mình, và judge không luôn nhất quán giữa 2 lần chạy cho cùng 1 câu trả lời giống nhau về bản chất.
- **Snapshot cố định** (09/11/2026): không phản ánh tình trạng thật ngoài thực tế tại thời điểm đọc notes này.
- **Chỉ chạy 1 lần mỗi phiên bản:** như quan sát ở mục 4, bản thân việc chạy lại CÙNG MỘT agent (không đổi gì) với model không deterministic cũng có thể cho điểm tổng khác nhau vài điểm — nên kết luận "cải tiến tốt hơn/xấu hơn" dựa trên 1 lần chạy mỗi bên có độ tin cậy thấp. Bằng chứng đáng tin nhất ở đây là **case A5 cụ thể** (có cơ chế rõ ràng: prompt mới → agent nói đúng câu cần nói), không phải điểm tổng.
- Thay đổi ở system prompt không giải quyết được H1/H6 — cần một vòng phân tích + cải tiến tiếp theo (ví dụ: thêm cảnh báo cứng khi `truncated: true` trong tool result) để xử lý nhóm lỗi "theo liên kết ngoài" triệt để hơn.
