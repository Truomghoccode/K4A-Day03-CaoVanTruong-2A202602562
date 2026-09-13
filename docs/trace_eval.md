# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** [Điền Họ và Tên]  
> **Mã Sinh Viên / Mã Học viên:** [Điền MSSV]  
> **Chủ đề Lựa chọn:** Hệ thống Trợ lý Vận hành Chăn nuôi Thông minh

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- | :---: | :--- |
| **1. Multi-step Reasoning** |4 / 5 |Khi người dùng gửi triệu chứng về bệnh hệ thống sẽ phải phân loại các triệu chứng và risk rank các bệnh tiềm năng dựa trên những thông tin về triệu chứng từ đó truy vấn ngược lại lịch sử lịch tiêm phòng, điều kiện chuồng trại 1 tuần gần đây từ đó tra cứu các loại thuốc hay hoạt chất tương tích với các triệu chứng của bệnh sau đó tính toán liều lượng dựa trên tổng đàn và rà soát lại những loại thuốc đang sử dụng có thể gây xung đột|
| **2. Tool Interaction** | 4/ 5 |Cần kết nối với Vector DB / MCP Knowledge Server để có thể truy xuất chính xác từng con số từ cơ sở dữ liệu chuyên ngành tránh LLM hallucination, cần kết nối với Relational DB (PostgreSQL) để tối ưu quá trình quản lý trạng thái của lứa, cần gọi API lập lịch để nhắc nhở các lịch tiêm phòng, đảo chấu hay rắc men vi sinh, cần kết nối với IoT Sensor API để đảm bảo điều kiện chuồng trại tối ưu|
| **3. Dynamic Decision** | 4/ 5 |Việc chăn nuôi luôn có nhiều kịch bản khác nhau có thể xảy ra nên không thể dựa trên lịch sử chăn của lứa trước hay 1 kịch bản cố định được vậy lên hệ thống luôn cần đảm bảo Thought -> Action -> Observation -> Thought. |
| **4. Long Horizon Goal** | 4/ 5 | Hệ thống luôn phải giữ mục tiêu xuyên suốt qua nhiều lượt vì 1 lứa gà sẽ kéo dài khoảng 90 ngày đến 120 ngày vậy nên hệ thống cần trải qua hàng trăm lượt tương tác và hàng nghìn dữ liệu cảm biến đo đạc trong chu kỳ từ 90 đến 120 ngày, với mọi hành động hay thay đổi nào cũng có thể ảnh hưởng đến kết quả sau này, khi chăn nuôi luôn có nhiều biến số có thể xảy ra vậy nên hệ thống cần phải điều chỉnh lộ trình kế hoạch sao cho kết quả cuối cùng phải tối ưu nhất |
| **TỔNG ĐIỂM AGENTIC FIT** | 16/ 20** |: Chăn nuôi thực tế là một chuỗi hành động có liên đới, có rủi ro kinh tế cao và chịu sự chi phối của môi trường sống.Khi xây dựng hệ thống ta cần Multi-step Reasoning vì bệnh thú y luôn có triệu chứng chồng chéo, phải suy luận loại trừ nhiều lớp.Cần Tool Interaction vì phải kết nối CSDL lịch sử đàn, IoT chuồng trại và kho dược thư.Cần Dynamic Decision vì thời tiết và thể trạng đàn gà biến đổi liên tục, hành động sau phải nương theo kết quả bước trước.Cần Long Horizon Goal vì mục tiêu thành bại của đàn gà tính bằng tháng, mọi quyết định điều trị hôm nay đều ràng buộc chất lượng xuất chuồng sau này. |

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

> ⚠️ **YÊU CẦU NGHIỆM THU:** Kết quả dưới đây được tổng hợp từ file `docs/trace_waterfall.json` sau khi chạy `python src/app.py --all` với `GeminiProvider`. Không sử dụng các trace mẫu VinUni hoặc trace sinh từ `MockOfflineProvider` làm bằng chứng nghiệm thu API thật.

### Tóm tắt phiên chạy

- **Tổng số Test Cases đã thực thi:** 5/5.
- **Tổng số sự kiện trace:** 12.
- **Kết quả trực tiếp không cần Tool:** TC01 và TC05.
- **Kết quả gọi `chicken_query`:** TC02 và bước đầu của TC04.
- **Kết quả gọi `care_warning`:** TC03 và TC04.
- **TC04 chưa hoàn toàn đạt:** Agent đã đi đúng bước `chicken_query → care_warning`, nhưng tiếp tục gọi lặp lại `care_warning` từ `CARE-0002` đến `CARE-0005` rồi đạt `MAX_ITERATIONS`. Cần xử lý việc nhận diện cảnh báo đã được tạo trước khi nộp bài.

### Trích đoạn Waterfall Trace tiêu biểu của TC04

```json
[
  {
    "step": 1,
    "action_type": "TOOL_EXECUTION",
    "tool_name": "chicken_query",
    "arguments": {
      "query": "thở gấp, há mỏ, có dấu hiệu nóng"
    },
    "observation": {
      "status": "SUCCESS",
      "risk_count": 1,
      "risks": [
        {
          "rank": 1,
          "risk_name": "Nguy cơ stress nhiệt",
          "risk_score": 0.86,
          "matched_signals": ["thở gấp", "há mỏ", "nóng"],
          "recommended_next_step": "Kiểm tra nhiệt độ, độ ẩm và hệ thống thông gió của chuồng."
        }
      ]
    },
    "latency_ms": 1716.94
  },
  {
    "step": 2,
    "action_type": "TOOL_EXECUTION",
    "tool_name": "care_warning",
    "arguments": {
      "query": "Kiểm tra tình trạng đàn gà và điều kiện chuồng trại",
      "datetime_str": "14:00 15/09/2026",
      "disease_name": "Nguy cơ sức khỏe đàn gà"
    },
    "observation": {
      "status": "SUCCESS",
      "warning_id": "CARE-0002",
      "scheduled_at": "14:00 15/09/2026",
      "risk_name": "Nguy cơ sức khỏe đàn gà"
    },
    "latency_ms": 445.72
  },
  {
    "step": 6,
    "action_type": "FINAL_ANSWER",
    "thought": "Đã đạt MAX_ITERATIONS.",
    "output": "Agent đã đạt giới hạn số vòng lặp nhưng chưa hoàn tất yêu cầu.",
    "latency_ms": 0.0
  }
]
```

### Nhận xét

Trace đã chứng minh được chuỗi suy luận và thực thi Tool qua MCP. `chicken_query` trả về Observation có nguy cơ, điểm rủi ro, tín hiệu khớp và bước chăm sóc tiếp theo; `care_warning` tiếp tục tạo cảnh báo thành công. Tuy nhiên, TC04 cho thấy Agent chưa dừng sau khi cảnh báo được tạo, vì vậy phần ReAct Loop vẫn cần được tối ưu để tránh gọi lặp lại cùng một hành động.

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [ ] Đã điền API Key thật trong `.env` và xác nhận Agent chạy mượt mà trên LLM API thật (Gemini/OpenAI).
- **Tổng số Test Cases đã chạy thành công:** ___ / 5 test cases.
- **Số lượt gọi Tool qua MCP Server chính xác:** ___ lượt.
- **Kết quả đẩy Repo nộp bài:** [ ] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
