# Biên bản đàm phán hợp đồng API

- Cặp đàm phán: Pair 09
- Product: Analytics Service
- Provider: Nhóm 9 — Access Gate Service
- Consumer: Nhóm 5 — Analytics Service
- Phiên: v1.0
- Ngày: 19/05/2026

---

## Issue #1

- Raised by: Consumer
- Endpoint: /events
- Concern: Tránh việc dữ liệu hướng di chuyển gửi lên không đồng nhất giữa các bên (ví dụ bên dùng ENTER/EXIT, bên dùng Vao/Ra, bên dùng IN/OUT) khiến hệ thống Analytics không thể gom nhóm (group by) chính xác.
- Proposal: Consumer đề xuất dùng tập hằng số chuỗi viết hoa cố định là `ENTER` và `EXIT`.
- Resolution: Modified
- Rationale: Nhóm 9 phản hồi rằng phần cứng đầu đọc thẻ tại cổng đã được cấu hình mặc định xuất ra chuỗi viết thường là `in` và `out`. Nhóm 5 đồng ý nhượng bộ để giảm tải việc parse dữ liệu ở tầng nhúng của phần cứng, giúp giảm độ trễ của tin nhắn.
- Impact: Thống nhất cấu hình trường `direction` trong file `openapi.yaml` thành `enum: [in, out]`.

---

## Issue #2

- Raised by: Consumer
- Endpoint: /events
- Concern: Cần bảo vệ thông tin định danh cá nhân của sinh viên (PII). Ban đầu Consumer yêu cầu Access Gate phải băm (Hash SHA-256) mã thẻ trước khi đẩy vào luồng sự kiện.
- Proposal: Yêu cầu Provider truyền trường `cardHash` thay vì mã thẻ thô.
- Resolution: Modified
- Rationale: Provider giải thích hệ thống gồm nhiều thiết bị phần cứng chạy song song, việc đồng bộ secret key để hash đồng nhất rất phức tạp, dễ gây rủi ro lệch key dẫn đến dữ liệu phân tích bị sai lệch hệ thống (False data). Hai bên thống nhất ưu tiên tính toàn vẹn dữ liệu lên hàng đầu.
- Impact: Hủy bỏ yêu cầu hash tại nguồn. Nhóm 9 truyền mã thô qua trường `cardId`. Nhóm 5 (Analytics) sẽ tự chịu trách nhiệm băm hoặc ẩn danh hóa mã thẻ này ở tầng lưu trữ nội bộ (Database riêng) sau khi nhận tin.

---

## Issue #3

- Raised by: Consumer
- Endpoint: /events
- Concern: Analytics cần tính toán "Số cảnh báo an ninh trong ngày" và "Tỷ lệ xâm nhập trái phép". Nếu Access Gate chỉ đẩy log các lượt quẹt thẻ thành công (`ALLOW`), Analytics sẽ thiếu dữ liệu đầu vào để tính toán.
- Proposal: Yêu cầu Provider phải bắn cả log sự kiện của các ca quẹt thẻ thất bại.
- Resolution: Accepted
- Rationale: Nhóm 9 cam kết hệ thống tạo log rất đầy đủ và liên tục cho mọi trường hợp phát sinh tại cổng (bao gồm cả các ca lỗi, thẻ hết hạn, sai khu vực).
- Impact: Thống nhất phân loại trạng thái thông qua trường `decision` với hai giá trị là `ALLOW` (thành công) và `DENY` (bị từ chối). Nhóm 5 có thể bóc tách dữ liệu an ninh trực tiếp mà không cần filter thủ công từ log tổng.

---

## Issue #4

- Raised by: Consumer
- Endpoint: Tất cả các Endpoint
- Concern: Các service chạy phân tán trên nhiều container Docker dễ bị lệch múi giờ hệ thống (UTC vs UTC+7), dẫn đến biểu đồ thống kê giờ cao điểm trên Dashboard bị sai lệch hoàn toàn.
- Proposal: Yêu cầu tất cả dữ liệu thời gian phải đồng nhất về một múi giờ gốc.
- Resolution: Accepted
- Rationale: Chuẩn hóa múi giờ gốc giúp Consumer dễ dàng lưu trữ đồng nhất và chủ động chuyển đổi sang múi giờ hiển thị (Local Time) trên giao diện quản trị mà không bị sai số.
- Impact: Thống nhất bắt buộc sử dụng chuẩn ISO 8601 với múi giờ gốc UTC (`Z`). Ví dụ: `2026-05-19T10:00:00Z`.

---

## Issue #5

- Raised by: Consumer
- Endpoint: /events
- Concern: Giao tiếp bất đồng bộ qua Message Queue theo cơ chế "at-least-once" dễ gặp sự cố mạng chập chờn khiến một sự kiện ra vào bị gửi lặp lại nhiều lần, làm tăng ảo số liệu metric (sai lệch thống kê).
- Proposal: Yêu cầu mỗi gói tin gửi đi phải có một ID định danh duy nhất ở tầng root để làm Idempotency Key (chống trùng lặp).
- Resolution: Accepted
- Rationale: Giúp hệ thống Consumer nhận diện được tin nhắn đã xử lý hay chưa. Nếu ID đã tồn tại thì bỏ qua, đảm bảo tính chính xác tuyệt đối cho dữ liệu báo cáo.
- Impact: Bổ sung trường `eventId` định dạng UUID v4 vào payload sự kiện. Cấu hình Mock Server trả về lỗi `409 Conflict` nếu phát hiện gửi trùng `eventId`.

---

## Issue #6

- Raised by: Consumer
- Endpoint: Tất cả các Endpoint
- Concern: Khi xảy ra lỗi truyền nhận giữa các service, nếu mỗi bên trả về một kiểu định dạng lỗi khác nhau (text thuần, HTML, JSON tự chế) sẽ làm sập luồng xử lý lỗi tự động của hệ thống.
- Proposal: Đề xuất áp dụng cấu trúc báo lỗi đồng nhất theo tiêu chuẩn quốc tế.
- Resolution: Accepted
- Rationale: Giúp việc lập trình bắt lỗi (Error Handling), ghi log hệ thống và hiển thị lý do lỗi lên Dashboard trở nên dễ dàng và đồng bộ.
- Impact: Áp dụng nghiêm ngặt chuẩn định dạng dữ liệu lỗi `application/problem+json` (RFC 7807) cho toàn bộ các mã lỗi từ 400 đến 500.

---

# Chốt hợp đồng v1.0

Provider sign-off: [Điền tên đại diện nhóm 9 vào đây]  
Consumer sign-off: Kiều Quang Trường  
Witness (GV/TA):   
Date: 19/05/2026  

---

## Ghi chú warning nếu Spectral còn cảnh báo

| Warning | Lý do chấp nhận tạm thời | Kế hoạch sửa |
|---|---|---|
| Không có | File hợp đồng đã được cấu trúc chuẩn hóa, vượt qua toàn bộ các bài quét kiểm tra của hệ thống (Spectral Lint đạt trạng thái Clean). | Duy trì cấu trúc hiện tại cho các giai đoạn phát triển tiếp theo. |