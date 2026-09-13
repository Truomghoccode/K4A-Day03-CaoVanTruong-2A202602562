# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** Cao Văn Trường<br>
> **Mã Sinh Viên / Mã Học viên:** 2A202602562<br>
> **Chủ đề Lựa chọn:** Trợ lý phát hiện rủi ro sức khỏe đàn gà và lập lịch công việc chăm sóc

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- | :---: | :--- |
| **1. Multi-step Reasoning** | 4 / 5 | Khi người dùng mô tả triệu chứng, Agent cần phân tích dấu hiệu, gọi Tool tra cứu nguy cơ, đọc Observation rồi quyết định có lập cảnh báo chăm sóc hay không. TC04 trong trace đã thể hiện chuỗi `chicken_query → care_warning → final answer`. |
| **2. Tool Interaction** | 4 / 5 | Chủ đề cần Tool tra cứu nguy cơ từ dữ liệu chuyên ngành và Tool lập lịch/cảnh báo. Hai Tool hiện tại giúp giảm việc LLM tự bịa dữ liệu; việc kết nối cơ sở dữ liệu lịch sử đàn hoặc IoT là hướng mở rộng, chưa phải phạm vi triển khai hiện tại. |
| **3. Dynamic Decision** | 4 / 5 | Agent không lập lịch ngay một cách cố định: với TC04, Agent tra cứu nguy cơ stress nhiệt trước, sau đó dựa vào Observation mới gọi `care_warning`. |
| **4. Long Horizon Goal** | 4 / 5 | Chăm sóc một đàn gà diễn ra theo chu kỳ dài, cần duy trì mục tiêu theo dõi nguy cơ và lịch chăm sóc qua nhiều lượt. Phiên bản hiện tại mới có bộ nhớ hội thoại trong RAM của một phiên chạy, chưa có bộ nhớ bền vững theo toàn bộ chu kỳ nuôi. |
| **TỔNG ĐIỂM AGENTIC FIT** | **16 / 20** | Chủ đề có tính Agentic rõ vì cần phối hợp nhiều bước, dùng Tool, quyết định theo Observation và theo dõi công việc chăm sóc. Điểm chưa tối đa vì phiên bản hiện tại mới triển khai phạm vi Mock Database, hai Tool và bộ nhớ trong phiên. |

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE)

> ⚠️ **LƯU Ý NGHIỆM THU:** Kết quả dưới đây được trích xuất trực tiếp từ `docs/trace_waterfall.json`. File JSON chưa lưu metadata `provider` hoặc `model` cho từng event. Vì vậy, cần đối chiếu console của đúng lần chạy để xác nhận phiên này dùng Gemini API thật và không fallback về Mock.

### Tóm tắt phiên chạy

- **Tổng số Test Cases đã thực thi:** 5/5.
- **Tổng số sự kiện trace:** 9.
- **Phân loại event:** 4 `TOOL_EXECUTION` và 5 `FINAL_ANSWER`.
- **Số lượt gọi `chicken_query`:** 2 lượt — TC02 và bước 1 của TC04.
- **Số lượt gọi `care_warning`:** 2 lượt — TC03 và bước 2 của TC04.
- **Tổng số lượt gọi Tool qua MCP Server:** **4 lượt**.
- **Trạng thái Tool:** Cả 4 Observation đều trả về `SUCCESS`.
- **TC04:** Đã hoàn tất đúng chuỗi `chicken_query → care_warning → FINAL_ANSWER` ở các bước 1 → 2 → 3; không còn gọi lặp và không đạt `MAX_ITERATIONS`.

### Kết quả theo từng Test Case

- **TC01 — direct_query:** Agent trả lời trực tiếp ở bước 1, không gọi Tool.
- **TC02 — single_tool_query:** Gọi `chicken_query` một lần. Tool trả về 2 nguy cơ: bệnh hô hấp hạng 1 với điểm 0.89 và rối loạn tiêu hóa hạng 2 với điểm 0.82; sau đó Agent trả lời ở bước 2.
- **TC03 — care_warning:** Gọi `care_warning` một lần với `datetime_str = 14:00 15/09/2026`, `disease_name = Stress nhiệt`, `flock_size = 2000`; tạo cảnh báo `CARE-0001`, sau đó trả lời ở bước 2.
- **TC04 — multi_step_reasoning:** Bước 1 nhận diện nguy cơ stress nhiệt với điểm 0.86; bước 2 tạo cảnh báo `CARE-0002` cho đàn 2000 con vào `14:00 15/09/2026`; bước 3 trả lời cuối cùng.
- **TC05 — insufficient_information:** Không gọi Tool; Agent yêu cầu bổ sung triệu chứng, thời điểm xuất hiện, số lượng gà bị ảnh hưởng và điều kiện chuồng trại.

### Trích đoạn Waterfall Trace tiêu biểu của TC04

```json
[
  {
    "step": 1,
    "action_type": "TOOL_EXECUTION",
    "tool_name": "chicken_query",
    "arguments": {
      "query": "Đàn gà thở gấp, há mỏ và có dấu hiệu nóng"
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
    "latency_ms": 2385.48
  },
  {
    "step": 2,
    "action_type": "TOOL_EXECUTION",
    "tool_name": "care_warning",
    "arguments": {
      "query": "Kiểm tra nhiệt độ và hệ thống thông gió chuồng gà",
      "datetime_str": "14:00 15/09/2026",
      "disease_name": "Nguy cơ stress nhiệt",
      "flock_size": 2000
    },
    "observation": {
      "status": "SUCCESS",
      "warning_id": "CARE-0002",
      "scheduled_at": "14:00 15/09/2026",
      "risk_name": "Nguy cơ stress nhiệt",
      "flock_size": 2000
    },
    "latency_ms": 477.62
  },
  {
    "step": 3,
    "action_type": "FINAL_ANSWER",
    "thought": "Observation care_warning đã SUCCESS, nên trả lời kết quả cuối cùng.",
    "output": "Đã tạo cảnh báo chăm sóc thành công theo thông tin đã cung cấp. Tôi sẽ không gọi lại care_warning cho cùng yêu cầu này.",
    "latency_ms": 516.06
  }
]
```

### Nhận xét

Trace hiện tại đã chứng minh được luồng thực thi thành công của cả 5 Test Case. TC04 đã thể hiện quyết định nhiều bước: tra cứu nguy cơ stress nhiệt trước, đọc Observation, sau đó tạo cảnh báo với đúng thời gian và `flock_size = 2000`.

Tuy nhiên, các event `TOOL_EXECUTION` trong JSON chưa lưu trường `thought`; Thought của Tool Call mới xuất hiện trên console hoặc được thể hiện gián tiếp qua event tiếp theo. Vì vậy, file hiện tại chứng minh rõ `Action → Observation`, nhưng chưa lưu đầy đủ `Thought → Action → Observation` cho từng lượt.

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [ ] Đã xác nhận toàn bộ phiên trace này chạy bằng LLM API thật và không fallback về Mock; cần đối chiếu console vì JSON chưa lưu metadata provider/model.
- **Tổng số Test Cases đã chạy thành công:** 5 / 5 test cases.
- **Số lượt gọi Tool qua MCP Server chính xác:** 4 lượt
- **Kết quả đẩy Repo nộp bài:** [x] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
