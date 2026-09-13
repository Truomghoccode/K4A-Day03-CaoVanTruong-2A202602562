"""
🔌 MULTI-PROVIDER LLM ADAPTER (Google Gemini, OpenAI & Offline Mock)
Hỗ trợ Native Tool Calling và chuyển đổi linh hoạt qua biến môi trường LLM_PROVIDER.
"""

import os
import sys
import json
import re
from typing import Dict, Any, List
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

class BaseLLMProvider:
    """Interface cơ sở cho các LLM Provider hỗ trợ Native Tool Calling"""
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        raise NotImplementedError


class MockOfflineProvider(BaseLLMProvider):
    """Offline Mock Provider dùng để chạy thử mà không tốn API Key"""
    def __init__(self):
        self.model_name = "Offline-Mock-Model-2026"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return (
            f"[Mock Chatbot Response]: Tôi đã nhận được câu hỏi '{prompt}'. "
            "Chế độ Chatbot không có dữ liệu đàn gà thời gian thực "
            "và không thể gọi Tool."
        )
    @staticmethod
    def _extract_datetime(text: str) -> str | None:
        """Trích xuất giờ/ngày và chuẩn hóa về dạng mà care_warning chấp nhận."""
        time_first = re.search(
            r"\b(?:[01]?\d|2[0-3]):[0-5]\d\s+\d{1,2}/\d{1,2}/\d{4}\b",
            text,
        )
        if time_first:
            return time_first.group(0)

        date_first = re.search(
            r"\b(\d{1,2}/\d{1,2}/\d{4})\s+(?:lúc\s+)?"
            r"((?:[01]?\d|2[0-3]):[0-5]\d)\b",
            text,
            flags=re.IGNORECASE,
        )
        if date_first:
            return f"{date_first.group(2)} {date_first.group(1)}"
        return None

    @staticmethod
    def _extract_flock_size(text: str) -> int | None:
        """Trích xuất số lượng đàn, hỗ trợ các dạng '2.000 con' và '2000 gà'."""
        match = re.search(r"\b(\d[\d.,]*)\s*(?:con|gà)\b", text.lower())
        if not match:
            return None

        raw_value = match.group(1).replace(".", "").replace(",", "")
        try:
            flock_size = int(raw_value)
        except ValueError:
            return None
        return flock_size if flock_size >= 1 else None

    @staticmethod
    def _extract_current_request(prompt: str) -> str:
        """Lấy riêng lượt hiện tại để không nhầm ví dụ trong câu trả lời cũ."""
        marker = "YÊU CẦU HIỆN TẠI CỦA NGƯỜI DÙNG:"
        if marker not in prompt:
            return prompt

        current = prompt.split(marker, 1)[1]
        current = current.split("\nCÁC OBSERVATION ĐÃ NHẬN ĐƯỢC:", 1)[0]
        current = current.split("\nYÊU CẦU CHO BƯỚC TIẾP THEO:", 1)[0]
        return current.strip()

    @classmethod
    def _extract_user_context(cls, prompt: str) -> str:
        """Ghép các lượt USER và lượt hiện tại, loại ASSISTANT để tránh lấy ví dụ minh họa."""
        previous_user_turns = re.findall(
            r"USER:\s*(.*?)(?=\n(?:USER|ASSISTANT|SYSTEM|TOOL):|\Z)",
            prompt,
            flags=re.IGNORECASE | re.DOTALL,
        )
        return "\n".join(previous_user_turns + [cls._extract_current_request(prompt)])

    @staticmethod
    def _infer_risk_name(text: str) -> str:
        text_lower = text.lower()
        if any(word in text_lower for word in ("gumboro", "gum", "vaccine", "vắc xin", "vaccin", "tiêm")):
            return "Nguy cơ liên quan đến lịch vaccine Gumboro"
        if any(word in text_lower for word in ("stress nhiệt", "nóng", "há mỏ", "thở gấp")):
            return "Nguy cơ stress nhiệt"
        if any(word in text_lower for word in ("tiêu chảy", "phân", "bỏ ăn")):
            return "Nguy cơ rối loạn tiêu hóa"
        if any(word in text_lower for word in ("ho", "khò khè", "hắt hơi", "chảy nước mũi")):
            return "Nguy cơ bệnh hô hấp"
        return "Nguy cơ sức khỏe đàn gà"

    def generate_with_tools(
        self,
        prompt: str,
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = "",
    ) -> Dict[str, Any]:
        prompt_lower = prompt.lower()
        current_request = self._extract_current_request(prompt)
        current_lower = current_request.lower()
        user_context = self._extract_user_context(prompt)
        # Mock chỉ gọi những Tool thực sự được MCP Server công bố.
        available_tools = {tool.get("name", "") for tool in tools_schema}

        schedule_keywords = (
            "lập lịch",
            "đặt lịch",
            "tạo cảnh báo",
            "nhắc chăm sóc",
            "lịch chăm sóc",
            "kiểm tra vào lúc",
            "tiêm vaccine",
            "tiêm vaccin",
            "tiêm vắc xin",
            "tiêm phòng",
        )
        vaccination_keywords = ("tiêm", "vaccine", "vaccin", "vắc xin", "gumboro", "gum")
        symptom_keywords = (
            "khò khè", "ho", "hắt hơi", "chảy nước mũi", "tiêu chảy", "bỏ ăn",
            "phân có máu", "phân ra máu", "đi ngoài ra máu", "máu trong phân",
            "thở gấp", "há mỏ", "ủ rũ", "chậm lớn", "mất nước",
        )

        has_current_schedule = any(keyword in current_lower for keyword in schedule_keywords)
        has_symptoms = any(keyword in current_lower for keyword in symptom_keywords)
        observation_section = ""
        if "các observation đã nhận được:" in prompt_lower:
            observation_section = prompt_lower.split("các observation đã nhận được:", 1)[1]
        has_current_chicken_observation = (
            "tool: chicken_query" in observation_section
            and '"status": "success"' in observation_section
        )
        has_current_care_observation = (
            "tool: care_warning" in observation_section
            and '"status": "success"' in observation_section
        )
        has_previous_chicken_observation = "prior_tool_success: chicken_query" in prompt_lower
        has_previous_care_observation = "prior_tool_success: care_warning" in prompt_lower
        has_chicken_observation = (
            has_current_chicken_observation or has_previous_chicken_observation
        )
        # Lượt follow-up có thể chỉ gửi ngày/giờ hoặc số lượng, nhưng vẫn kế thừa
        # ý định lập lịch và kết quả tra cứu của lượt trước.
        has_follow_up_schedule_data = bool(
            self._extract_datetime(user_context) or self._extract_flock_size(user_context)
        )
        has_previous_schedule_intent = any(
            keyword in prompt_lower for keyword in schedule_keywords
        )
        has_schedule_request = has_current_schedule or (
            has_previous_schedule_intent
            and has_follow_up_schedule_data
            and not has_previous_care_observation
        )

        # Khi Action care_warning đã thành công, kết thúc lượt ReAct để không đặt lịch trùng.
        if has_current_care_observation:
            return {
                "type": "text",
                "content": (
                    "Đã tạo cảnh báo chăm sóc thành công theo thông tin đã cung cấp. "
                    "Tôi sẽ không gọi lại care_warning cho cùng yêu cầu này."
                ),
                "thought": "Observation care_warning đã SUCCESS, nên trả lời kết quả cuối cùng.",
            }

        # Với yêu cầu nhiều bước, luôn tra cứu nguy cơ trước khi lập lịch.
        if has_symptoms and not has_current_chicken_observation and "chicken_query" in available_tools:
            return {
                "type": "tool_call",
                "tool_name": "chicken_query",
                "arguments": {"query": prompt.strip()},
                "thought": (
                    "Người dùng cung cấp triệu chứng, nên tôi tra cứu chicken_query "
                    "trước khi xem xét lịch chăm sóc."
                ),
            }

        if has_schedule_request and "care_warning" in available_tools:
            datetime_str = self._extract_datetime(user_context)
            flock_size = self._extract_flock_size(user_context)
            missing = []
            if not datetime_str:
                missing.append("giờ và ngày cụ thể, ví dụ 14:00 15/09/2026")
            if flock_size is None:
                missing.append("số lượng đàn, ví dụ 2000 con")

            if missing:
                return {
                    "type": "text",
                    "content": (
                        "Để tạo cảnh báo chính xác, bạn vui lòng bổ sung "
                        + " và ".join(missing)
                        + "."
                    ),
                    "thought": "Chưa đủ datetime_str hoặc flock_size bắt buộc cho care_warning.",
                }

            user_context_lower = user_context.lower()
            if any(word in user_context_lower for word in vaccination_keywords):
                task = "Đặt lịch nhân viên thú y tiêm vaccine Gumboro cho đàn gà"
            elif "nhiệt" in user_context_lower or "thông gió" in user_context_lower:
                task = "Kiểm tra nhiệt độ và hệ thống thông gió chuồng gà"
            else:
                task = "Kiểm tra tình trạng đàn gà và điều kiện chuồng trại"

            return {
                "type": "tool_call",
                "tool_name": "care_warning",
                "arguments": {
                    "query": task,
                    "datetime_str": datetime_str,
                    "disease_name": self._infer_risk_name(user_context),
                    "flock_size": flock_size,
                },
                "thought": (
                    "Đã trích xuất đủ công việc, thời gian và flock_size; "
                    "tôi sẽ gọi care_warning."
                ),
            }

        # Sau khi tra cứu xong nhưng không có yêu cầu đặt lịch, trả lời kết thúc.
        if has_chicken_observation:
            return {
                "type": "text",
                "content": (
                    "Tôi đã tra cứu nguy cơ từ Observation của chicken_query. "
                    "Hãy cho biết thời gian cụ thể và số lượng đàn nếu bạn muốn "
                    "tạo thêm cảnh báo chăm sóc."
                ),
                "thought": "Observation chicken_query đã đủ cho lượt tra cứu; không gọi lại Tool.",
            }

        if "chưa xác định" in prompt_lower or "triệu chứng cụ thể" in prompt_lower:
            return {
                "type": "text",
                "content": (
                    "Bạn hãy bổ sung triệu chứng cụ thể, thời điểm bắt đầu, "
                    "số lượng gà bị ảnh hưởng và điều kiện chuồng trại."
                ),
                "thought": "Thông tin hiện tại chưa đủ để tra cứu nguy cơ.",
            }

        return {
            "type": "text",
            "content": (
                "[Mock Agent Response]: Tôi có thể hỗ trợ tra cứu nguy cơ "
                "sức khỏe đàn gà và lập lịch công việc chăm sóc."
            ),
            "thought": "Câu hỏi chưa chứa triệu chứng hoặc yêu cầu lập lịch, nên chưa cần gọi Tool.",
        }


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider (Native Tool Calling với Google GenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-3.6-flash"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(model=self.model_name, contents=contents)
            return response.text
        except Exception as e:
            return f"[Gemini Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            print("ℹ️ [Gemini Provider]: Chưa tìm thấy GEMINI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)
        
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            
            # Chuẩn hóa function declarations cho Gemini SDK
            function_declarations = []
            for tool in tools_schema:
                # Bỏ qua các tool schema chưa được định nghĩa hoàn chỉnh
                if not tool.get("name") or not tool.get("parameters"):
                    continue
                function_declarations.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {})
                })

            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
                tools=[{"function_declarations": function_declarations}] if function_declarations else None,
                temperature=0.2
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )

            # Kiểm tra xem Gemini có trả về Tool Call không
            if response.function_calls:
                call = response.function_calls[0]
                args = dict(call.args) if hasattr(call, 'args') and call.args else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.name,
                    "arguments": args,
                    "thought": f"Gemini quyết định gọi công cụ '{call.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "content": response.text or "",
                    "thought": "Gemini phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }

        except Exception as e:
            print(f"⚠️ [Gemini API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (Native Tool Calling với OpenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return "[OpenAI Error]: Chưa cấu hình OPENAI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(model=self.model_name, messages=messages)
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[OpenAI Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            print("ℹ️ [OpenAI Provider]: Chưa tìm thấy OPENAI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)

            tools = []
            for tool in tools_schema:
                if not tool.get("name"):
                    continue
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {})
                    }
                })

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None
            )

            msg = response.choices[0].message
            if msg.tool_calls:
                call = msg.tool_calls[0]
                args = json.loads(call.function.arguments) if call.function.arguments else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.function.name,
                    "arguments": args,
                    "thought": f"OpenAI quyết định gọi công cụ '{call.function.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "content": msg.content or "",
                    "thought": "OpenAI phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }
        except Exception as e:
            print(f"⚠️ [OpenAI API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)


def get_llm_provider() -> BaseLLMProvider:
    """Factory function khởi tạo Provider theo LLM_PROVIDER env variable"""
    provider_type = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    if provider_type == "gemini":
        key = os.getenv("GEMINI_API_KEY")
        if key and key != "your_gemini_api_key_here":
            return GeminiProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if key and key != "your_openai_api_key_here":
            return OpenAIProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "mock":
        return MockOfflineProvider()
    else:
        return MockOfflineProvider()
