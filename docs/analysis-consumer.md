# Phân tích yêu cầu — vai Consumer

- Cặp đàm phán: Pair 09 (Access Gate → Analytics)
- Product: Smart Campus
- Consumer service: Analytics Service (Nhóm 5)
- Provider service: Access Gate (Nhóm 9)
- Người viết: Kiều Quang Trường
- Ngày: 19/05/2026

---

## 1. Resource Consumer cần nhận/gửi

| Resource | Consumer dùng để làm gì? | Field bắt buộc với Consumer | Field có thể tùy chọn |
|---|---|---|---|
| `Event: access.log.created` | Thống kê số lượng người ra/vào và tìm ra mốc giờ cao điểm của các khu vực trong khuôn viên trường. | `event_id`, `timestamp`, `gate_id`, `direction`, `card_hash` | `location_name`, `device_ip` |
| `Event: access.denied` | Tính toán tỷ lệ xâm nhập trái phép (deny rate), hỗ trợ vẽ biểu đồ cảnh báo an ninh theo ngày. | `event_id`, `timestamp`, `gate_id`, `reason_code` | `card_hash` (có thể rỗng nếu thẻ không hợp lệ/không đọc được) |

---

## 2. API Consumer cần gọi

*(Vì cặp 09 giao tiếp thông qua Queue Async, bảng dưới đây mô tả hành động lắng nghe sự kiện từ Queue và một API REST đồng bộ dự phòng khi cần đồng bộ lại dữ liệu).*

| Method | Path / Topic | Lúc nào gọi? | Kỳ vọng response |
|---|---|---|---|
| SUBSCRIBE | `Topic: campus.access.events` | Lắng nghe liên tục theo thời gian thực (realtime) để cập nhật metric ngay lập tức. | JSON payload chứa cấu trúc của sự kiện `access.log.created` hoặc `access.denied`. |
| GET | `/api/v1/access-gates/logs/sync` | Gọi dự phòng khi hệ thống Analytics bị sập hoặc mất message, cần chủ động kéo lại dữ liệu cũ để bù log. | Danh sách mảng (Array) các access logs nằm trong khoảng từ `from_time` đến `to_time`. |

---

## 3. Error case Consumer cần xử lý

Tối thiểu 5 case. (Áp dụng cho cả việc parse gói tin từ Queue và xử lý phản hồi từ API dự phòng).

| Status/Lỗi | Consumer hiểu là gì? | Consumer sẽ xử lý thế nào? |
|---:|---|---|
| 400 (Bad Format) | Event nhận được từ Queue bị sai định dạng hoặc thiếu các trường bắt buộc. | Từ chối xử lý (Drop event), đẩy gói tin lỗi vào Dead Letter Queue (DLQ) và ghi log lỗi hệ thống. |
| 401 | Thẻ xác thực (Token) hết hạn khi gọi API REST kéo dữ liệu dự phòng. | Kích hoạt cơ chế refresh token tự động từ IAM Service rồi thực hiện gửi lại request (Retry). |
| 404 | Giá trị `gate_id` gửi sang không tồn tại trong danh mục quản lý của Analytics. | Vẫn lưu log nhưng tạm thời gán vào khu vực mặc định "Chưa phân loại", gửi cảnh báo cho admin kiểm tra. |
| 409 | Nhận trùng một `event_id` đã xử lý trước đó (Do cơ chế retry của Queue). | Bỏ qua sự kiện này (Ignore), không cộng dồn vào database để tránh làm sai lệch số liệu thống kê. |
| 422 | Vi phạm quy tắc nghiệp vụ dữ liệu (Ví dụ: trường `direction` chứa giá trị khác ngoài `ENTER`/`EXIT`). | Đánh dấu bản ghi là "Dữ liệu không hợp lệ", bỏ qua bước tính toán metric và lưu log phục vụ truy vết. |

---

## 4. Giả định bổ sung

- Giả định 1: Phía Provider (Access Gate) chịu trách nhiệm mã hóa/băm (hash) thông tin định danh thẻ (`card_id`/`student_id`) bằng thuật toán SHA-256 trước khi gửi qua queue để bảo vệ dữ liệu cá nhân (PII).
- Giả định 2: Mọi sự kiện do Provider phát đi bắt buộc phải đính kèm một mã định danh duy nhất `event_id` (định dạng UUIDv4) ở tầng root để Consumer triển khai cơ chế chống trùng lặp (Idempotency).
- Giả định 3: Tất cả dữ liệu thời gian (`timestamp`) phải tuân theo chuẩn ISO 8601 và thống nhất sử dụng múi giờ UTC (`Z`) để tránh lệch giờ khi xử lý phân tán.

---

## 5. Câu hỏi cho Provider

1. Trường dữ liệu hướng di chuyển (`direction`) các bạn sẽ chốt dùng tập giá trị cố định nào? (Analytics đề xuất hằng số chuỗi: `ENTER` và `EXIT`).
2. Nhóm bạn đã tích hợp module băm (hash) mã thẻ ngay tại đầu bài đọc thẻ của Access Gate chưa, hay hệ thống Analytics sẽ nhận chuỗi thô?
3. Khi xảy ra lỗi quẹt thẻ (`access.denied`), cấu trúc lý do từ chối (`reason_code`) sẽ được phân loại thành các mã cụ thể nào (ví dụ: `expired_card`, `blacklisted`, `wrong_zone`)?

---

## 6. Rủi ro tích hợp

| Rủi ro | Tác động | Đề xuất xử lý |
|---|---|---|
| Provider tự ý thay đổi kiểu dữ liệu các trường core (Ví dụ: `gate_id` chuyển từ kiểu Integer sang chuỗi UUID). | Hệ thống nạp dữ liệu (Data Pipeline) của Consumer bị crash hoàn toàn, ngừng cập nhật dashboard. | Chốt cứng định dạng schema trong file hợp đồng chung. Mọi thay đổi cấu trúc phải nâng cấp phiên bản API (Versioning) và báo trước. |
| Sự cố mạng khiến một tin nhắn bị lặp, Queue gửi 1 event đến 2 lần. | Kết quả thống kê lưu lượng bị sai lệch (tăng ảo số lượt ra vào). | Consumer bắt buộc kiểm tra xem `event_id` đã tồn tại trong DB chưa trước khi ghi nhận dữ liệu mới. |
| Mất kết nối diện rộng từ phía Access Gate, Queue không nhận được event nào. | Dashboard hiển thị trạng thái lưu lượng bằng 0, dễ gây hiểu lầm là hệ thống lỗi. | Cài đặt cơ chế kiểm tra trạng thái hoạt động (Heartbeat). Nếu quá thời gian quy định không nhận được tín hiệu, hiển thị cảnh báo "Mất kết nối với Access Gate" lên giao diện Dashboard. |