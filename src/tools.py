"""
🛠️ TOOL DEFINITIONS & EXECUTION BACKEND
Mã nguồn chứa danh sách Tool Schemas (JSON Schema) và Execution Layer phục vụ cho MCP Server.
"""

import json
from datetime import datetime
from typing import Dict, Any

# ==============================================================================
# 1. KHAI BÁO TOOL SCHEMAS CHUẨN NATIVE JSON SCHEMA (TASK 1.2)
# ==============================================================================

TOOLS_SCHEMA = [
    {
        "name": "chicken_query",
        "description": (
            "Tra cứu và xếp hạng tối đa 5 nguy cơ sức khỏe của đàn gà "
            "dựa trên mô tả triệu chứng và dấu hiệu bất thường. "
            "Kết quả chỉ mang tính tham khảo, không thay thế chẩn đoán "
            "của bác sĩ thú y và không tự động kê thuốc."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Mô tả triệu chứng hoặc dấu hiệu bất thường của đàn gà, "
                        "ví dụ: số lượng gà có triệu chứng, thời gian xuất hiện, "
                        "mức độ ăn uống và các dấu hiệu môi trường nếu biết."
                    )
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "care_warning",
        "description": (
            "Tạo lịch hoặc cảnh báo cho công việc kiểm tra, theo dõi "
            "và chăm sóc đàn gà dựa trên nguy cơ sức khỏe đã phát hiện."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Công việc cần thực hiện, ví dụ: kiểm tra nhiệt độ chuồng, "
                        "cách ly đàn hoặc theo dõi lượng ăn uống."
                    )
                },
                "datetime_str": {
                    "type": "string",
                    "description": (
                        "Giờ và ngày thực hiện cảnh báo, phải là thời gian cụ thể "
                        "theo định dạng 'HH:MM DD/MM/YYYY', ví dụ: '14:00 15/09/2026'. "
                        "Không dùng mô tả mơ hồ như 'chiều mai' và không tự đoán giờ."
                    )
                },
                "disease_name": {
                    "type": "string",
                    "description": (
                        "Tên bệnh hoặc nguy cơ nghi ngờ liên quan đến cảnh báo. "
                        "Không được xem đây là chẩn đoán xác định."
                    )
                },
                "flock_size": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Số lượng gà trong đàn cần được chăm sóc hoặc kiểm tra."
                }
            },
            "required": ["query", "datetime_str", "disease_name", "flock_size"]
        }
    }
]
# ==============================================================================
# 2. MÔ PHỎNG DỮ LIỆU & HÀM THỰC THI TOOL (EXECUTION LAYER)
# ==============================================================================

MOCK_DATABASE = {
    "risk_profiles": [
        {
            "risk_name": "Nguy cơ bệnh hô hấp",
            "keywords": ["khò khè", "ho", "hắt hơi", "chảy nước mũi", "khó thở"],
            "base_score": 0.86,
            "evidence": "Các dấu hiệu liên quan đến đường hô hấp xuất hiện trong mô tả.",
            "recommended_action": "Kiểm tra thông gió, mật độ đàn và cách ly khu vực có dấu hiệu bất thường."
        },
        {
            "risk_name": "Nguy cơ rối loạn tiêu hóa",
            "keywords": [
                "tiêu chảy",
                "phân lỏng",
                "phân có máu",
                "phân ra máu",
                "đi ngoài ra máu",
                "máu trong phân",
                "bỏ ăn"
            ],
            "base_score": 0.82,
            "evidence": "Mô tả có dấu hiệu bất thường về tiêu hóa hoặc lượng ăn.",
            "recommended_action": "Kiểm tra nước uống, thức ăn và theo dõi số lượng cá thể bị ảnh hưởng."
        },
        {
            "risk_name": "Nguy cơ stress nhiệt",
            "keywords": ["thở gấp", "há mỏ", "nóng", "nhiệt độ cao", "tụm cánh"],
            "base_score": 0.80,
            "evidence": "Có dấu hiệu đàn gà chịu ảnh hưởng bởi nhiệt độ hoặc thông thoáng kém.",
            "recommended_action": "Kiểm tra nhiệt độ, độ ẩm và hệ thống thông gió của chuồng."
        },
        {
            "risk_name": "Nguy cơ mất nước",
            "keywords": ["uống nhiều", "lờ đờ", "mất nước", "mào khô"],
            "base_score": 0.74,
            "evidence": "Mô tả cho thấy khả năng thiếu nước hoặc suy giảm thể trạng.",
            "recommended_action": "Kiểm tra máng nước, lưu lượng cấp nước và tình trạng của từng khu vực."
        },
        {
            "risk_name": "Nguy cơ suy giảm thể trạng",
            "keywords": ["chậm lớn", "gầy", "rụng lông", "ủ rũ", "ít vận động"],
            "base_score": 0.70,
            "evidence": "Có dấu hiệu suy giảm vận động, tăng trưởng hoặc thể trạng chung.",
            "recommended_action": "Theo dõi lượng ăn, cân mẫu đàn và kiểm tra điều kiện chuồng trại."
        }
    ],
    "care_warnings": []
}


def execute_chicken_query(query: str) -> str:
    """Tra cứu nguy cơ sức khỏe dựa trên từ khóa trong mô tả triệu chứng.

    Đây là logic Mock có tính quyết định để kiểm thử ReAct, không phải mô hình
    chẩn đoán thú y thực tế.
    """
    if not isinstance(query, str) or not query.strip():
        return json.dumps({
            "status": "INVALID_ARGUMENT",
            "message": "Tham số 'query' phải là mô tả triệu chứng không rỗng."
        }, ensure_ascii=False)

    normalized_query = query.strip().lower()
    matched_risks = []

    for profile in MOCK_DATABASE["risk_profiles"]:
        matched_signals = [
            keyword for keyword in profile["keywords"]
            if keyword in normalized_query
        ]
        if matched_signals:
            score = min(
                0.99,
                profile["base_score"] + 0.03 * (len(matched_signals) - 1)
            )
            matched_risks.append({
                "risk_name": profile["risk_name"],
                "risk_score": round(score, 2),
                "matched_signals": matched_signals,
                "evidence": profile["evidence"],
                "recommended_next_step": profile["recommended_action"]
            })

    matched_risks.sort(key=lambda risk: risk["risk_score"], reverse=True)
    matched_risks = matched_risks[:5]

    if not matched_risks:
        return json.dumps({
            "status": "INSUFFICIENT_DATA",
            "query": query.strip(),
            "risks": [],
            "message": (
                "Chưa nhận diện được nguy cơ từ mô tả hiện tại. "
                "Cần bổ sung triệu chứng, thời gian xuất hiện, số lượng gà bị ảnh hưởng "
                "và điều kiện chuồng trại."
            )
        }, ensure_ascii=False)

    for rank, risk in enumerate(matched_risks, start=1):
        risk["rank"] = rank

    return json.dumps({
        "status": "SUCCESS",
        "query": query.strip(),
        "risk_count": len(matched_risks),
        "risks": matched_risks,
        "disclaimer": (
            "Kết quả là đánh giá nguy cơ từ dữ liệu Mock, không phải chẩn đoán xác định. "
            "Hãy liên hệ bác sĩ thú y khi đàn có dấu hiệu nghiêm trọng."
        )
    }, ensure_ascii=False)


def execute_care_warning(
    query: str,
    datetime_str: str,
    disease_name: str,
    flock_size: int
) -> str:
    """Tạo và lưu một cảnh báo chăm sóc trong bộ nhớ Mock."""
    values = {
        "query": query,
        "datetime_str": datetime_str,
        "disease_name": disease_name
    }
    empty_fields = [
        field_name for field_name, value in values.items()
        if not isinstance(value, str) or not value.strip()
    ]
    if empty_fields:
        return json.dumps({
            "status": "INVALID_ARGUMENT",
            "message": f"Các tham số không được để trống: {', '.join(empty_fields)}."
        }, ensure_ascii=False)

    if isinstance(flock_size, bool) or not isinstance(flock_size, int) or flock_size < 1:
        return json.dumps({
            "status": "INVALID_ARGUMENT",
            "message": "Tham số 'flock_size' phải là số nguyên lớn hơn hoặc bằng 1."
        }, ensure_ascii=False)

    normalized_datetime = datetime_str.strip()
    valid_datetime = False
    for date_format in ("%H:%M %d/%m/%Y", "%Y-%m-%d %H:%M"):
        try:
            datetime.strptime(normalized_datetime, date_format)
            valid_datetime = True
            break
        except ValueError:
            continue

    if not valid_datetime:
        return json.dumps({
            "status": "INVALID_ARGUMENT",
            "message": (
                "'datetime_str' không đúng định dạng. Hãy dùng '14:00 15/09/2026' "
                "hoặc '2026-09-15 14:00'."
            )
        }, ensure_ascii=False)

    warning_id = f"CARE-{len(MOCK_DATABASE['care_warnings']) + 1:04d}"
    warning = {
        "status": "SUCCESS",
        "warning_id": warning_id,
        "task": query.strip(),
        "scheduled_at": normalized_datetime,
        "risk_name": disease_name.strip(),
        "flock_size": flock_size,
        "message": (
            f"Đã tạo cảnh báo chăm sóc '{query.strip()}' vào lúc "
            f"{normalized_datetime} cho đàn {flock_size} con, "
            f"liên quan đến nguy cơ '{disease_name.strip()}'."
        )
    }
    MOCK_DATABASE["care_warnings"].append(warning)
    return json.dumps(warning, ensure_ascii=False)


# Router gọi đúng hàm thực thi tương ứng với tên Tool mà LLM đề xuất.
TOOL_ROUTER = {
    "chicken_query": execute_chicken_query,
    "care_warning": execute_care_warning
}

def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Hàm trung chuyển thực thi tool"""
    if tool_name in TOOL_ROUTER:
        try:
            return TOOL_ROUTER[tool_name](**arguments)
        except Exception as e:
            return json.dumps({"status": "EXECUTION_ERROR", "error": str(e)}, ensure_ascii=False)
    return json.dumps({"status": "UNKNOWN_TOOL", "error": f"Tool '{tool_name}' không tồn tại!"}, ensure_ascii=False)
