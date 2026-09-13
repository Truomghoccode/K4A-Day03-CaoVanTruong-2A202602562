"""
🚀 CORE AGENT APPLICATION (DAY 03: CHATBOT VS REACT AGENT)
Thực thi so sánh giữa Chatbot Baseline (Cấp 2) và ReAct Agent kết nối MCP Server (Cấp 3).
"""

import json
import os
import sys
import time
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from mcp_server import MCPAcademicServer
from prompts import (
    CHATBOT_BASELINE_PROMPT,
    REACT_AGENT_SYSTEM_PROMPT,
    MAX_ITERATIONS
)
from providers import get_llm_provider

load_dotenv()

# Chỉ giữ một số lượt gần nhất để prompt không phình quá lớn.
# Đây là bộ nhớ trong RAM của một lần chạy interactive CLI.
MAX_HISTORY_MESSAGES = 12

def load_test_cases():
    """Tải danh sách 5 test cases từ config/test_cases.json hoặc config/test_cases.example.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    if not os.path.exists(config_path):
        example_path = os.path.join(base_dir, "config", "test_cases.example.json")
        if os.path.exists(example_path):
            print("⚠️ [CONFIG NOTICE]: Chưa thấy file 'config/test_cases.json'. Đang dùng mẫu 'config/test_cases.example.json'.")
            print("👉 Hãy chạy: copy config/test_cases.example.json config/test_cases.json và viết test cases theo đề tài của bạn!\n")
            config_path = example_path
        else:
            config_path = "test_cases.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_waterfall_trace(trace_data: list):
    """Ghi vết log Waterfall Trace Log ra file docs/trace_waterfall.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    trace_path = os.path.join(docs_dir, "trace_waterfall.json")
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, ensure_ascii=False, indent=2)
    print(f"📊 [OBSERVABILITY]: Đã lưu {len(trace_data)} sự kiện Waterfall Trace tại '{trace_path}'!")


def run_baseline_chatbot(user_query: str, provider):
    """Chạy Chatbot gốc (Cấp 2) không có công cụ gọi Tool"""
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot phản hồi:\n{response}")


def build_agent_context(
    user_query: str,
    observation_history: list,
    conversation_history: list | None = None,
) -> str:
    """Tạo context gồm lịch sử hội thoại, yêu cầu hiện tại và Observation."""
    context_parts = []

    if conversation_history:
        context_parts.append("LỊCH SỬ HỘI THOẠI TRƯỚC ĐÓ:")
        for message in conversation_history[-MAX_HISTORY_MESSAGES:]:
            role = str(message.get("role", "assistant")).upper()
            content = str(message.get("content", "")).strip()
            if content:
                context_parts.append(f"{role}: {content}")

    context_parts.extend([
        "\nYÊU CẦU HIỆN TẠI CỦA NGƯỜI DÙNG:",
        user_query.strip(),
    ])

    if observation_history:
        context_parts.append("\nCÁC OBSERVATION ĐÃ NHẬN ĐƯỢC:")
        for item in observation_history:
            context_parts.append(
                f"\n--- Step {item['step']} | Tool: {item['tool_name']} ---"
            )
            context_parts.append(
                json.dumps(item["observation"], ensure_ascii=False, indent=2)
            )

    context_parts.append(
        """

YÊU CẦU CHO BƯỚC TIẾP THEO:
- Nếu đã đủ dữ liệu, trả lời bằng văn bản cuối cùng.
- Nếu còn thiếu dữ liệu, gọi Tool phù hợp.
- Không gọi lại một Tool nếu Observation đã đủ thông tin.
- Chỉ sử dụng thông tin có trong yêu cầu và Observation.
"""
    )
    return "\n".join(context_parts)


def run_react_agent(
    user_query: str,
    provider,
    mcp_server: MCPAcademicServer,
    conversation_history: list | None = None,
) -> list:
    """
    [REACT AGENT LOOP] Thực thi vòng lặp Thought -> Action -> Observation với MCP Server
    Trả về danh sách trace log của phiên thực thi.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")

    step = 0
    trace_logs = []
    observation_history = []
    active_history = conversation_history if conversation_history is not None else []
    agent_context = build_agent_context(
        user_query,
        observation_history,
        active_history,
    )
    final_answer_created = False
    tools_list = mcp_server.list_tools()
    available_tool_names = {
        tool.get("name") for tool in tools_list if tool.get("name")
    }
    successful_tool_names = set()
    successful_observations = {}

    while step < MAX_ITERATIONS:
        step += 1
        llm_start_time = time.time()
        print(f"\n--- 🔄 Vòng lặp ReAct Loop (Step {step}/{MAX_ITERATIONS}) ---")

        # Gọi LLM với Native Tool Calling Specs
        llm_response = provider.generate_with_tools(
            agent_context,
            tools_list,
            system_prompt=REACT_AGENT_SYSTEM_PROMPT
        )
        llm_latency_ms = round((time.time() - llm_start_time) * 1000, 2)

        if not isinstance(llm_response, dict):
            final_content = "LLM trả về dữ liệu không hợp lệ."
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "thought": "Provider không trả về Dictionary hợp lệ.",
                "output": final_content,
                "latency_ms": llm_latency_ms
            })
            print(f"🏁 [Final Answer]: {final_content}")
            final_answer_created = True
            break

        thought = llm_response.get("thought", "Đang suy luận...")
        print(f"🧠 [Thought]: {thought}")

        # Trường hợp 1: LLM quyết định trả lời bằng văn bản trực tiếp
        if llm_response.get("type") == "text":
            final_content = llm_response.get("content", "").strip()
            if not final_content:
                final_content = "LLM không trả về nội dung câu trả lời."
            print(f"🏁 [Final Answer]: {final_content}")
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "thought": thought,
                "output": final_content,
                "latency_ms": llm_latency_ms
            })
            final_answer_created = True
            break

        # Trường hợp 2: LLM đề xuất gọi Tool (Action)
        elif llm_response.get("type") == "tool_call":
            tool_name = llm_response.get("tool_name")
            arguments = llm_response.get("arguments", {})

            print(f"🛠️ [Action Proposed]: {tool_name}({arguments})")

            if tool_name not in available_tool_names:
                error_data = {
                    "status": "INVALID_TOOL_CALL",
                    "error": f"Tool '{tool_name}' chưa được MCP Server công bố.",
                    "available_tools": sorted(available_tool_names)
                }
                trace_logs.append({
                    "step": step,
                    "query": user_query,
                    "action_type": "TOOL_EXECUTION",
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "observation": error_data,
                    "latency_ms": llm_latency_ms
                })
                print(f"👁️ [Observation từ MCP Server]: {error_data}")
                final_content = (
                    f"Không thể gọi Tool '{tool_name}'. "
                    "Vui lòng kiểm tra Tool Schema và MCP Server."
                )
                trace_logs.append({
                    "step": step + 1,
                    "query": user_query,
                    "action_type": "FINAL_ANSWER",
                    "thought": "Tool được yêu cầu không tồn tại trong MCP Server.",
                    "output": final_content,
                    "latency_ms": 0.0
                })
                print(f"🏁 [Final Answer]: {final_content}")
                final_answer_created = True
                break

            # Chặn việc LLM gọi lặp một Tool đã SUCCESS trong cùng yêu cầu.
            # Đây là guard ở tầng ứng dụng, không phụ thuộc hoàn toàn vào prompt.
            if tool_name in successful_tool_names:
                previous_observation = successful_observations[tool_name]
                final_content = (
                    f"Tool '{tool_name}' đã thực thi thành công ở bước trước. "
                    "Agent dừng để tránh tạo thao tác trùng. "
                    f"Observation: {json.dumps(previous_observation, ensure_ascii=False)}"
                )
                trace_logs.append({
                    "step": step,
                    "query": user_query,
                    "action_type": "DUPLICATE_TOOL_BLOCKED",
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "observation": previous_observation,
                    "thought": "Tool đã SUCCESS trước đó nên không gọi lại MCP Server.",
                    "latency_ms": llm_latency_ms
                })
                print(f"⚠️ [Duplicate Tool Blocked]: {tool_name}")
                print(f"🏁 [Final Answer]: {final_content}")
                final_answer_created = True
                break

            # Thực thi Tool qua MCP Server
            tool_start_time = time.time()
            try:
                mcp_result = mcp_server.call_tool(tool_name, arguments)
                if isinstance(mcp_result, dict) and "result" in mcp_result:
                    obs_data = mcp_result["result"]
                else:
                    obs_data = {
                        "status": "MCP_PROTOCOL_ERROR",
                        "error": "MCP Server không trả về trường 'result'.",
                        "raw_response": mcp_result
                    }
            except Exception as exc:
                obs_data = {
                    "status": "MCP_EXECUTION_ERROR",
                    "error": str(exc)
                }
            tool_latency_ms = round((time.time() - tool_start_time) * 1000, 2)

            obs_str = json.dumps(obs_data, ensure_ascii=False)
            print(f"👁️ [Observation từ MCP Server]: {obs_str}")

            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "TOOL_EXECUTION",
                "tool_name": tool_name,
                "arguments": arguments,
                "observation": obs_data,
                "llm_latency_ms": llm_latency_ms,
                "tool_latency_ms": tool_latency_ms,
                "latency_ms": round(llm_latency_ms + tool_latency_ms, 2)
            })

            observation_history.append({
                "step": step,
                "tool_name": tool_name,
                "observation": obs_data
            })

            if isinstance(obs_data, dict) and obs_data.get("status") == "SUCCESS":
                successful_tool_names.add(tool_name)
                successful_observations[tool_name] = obs_data

            # Observation quay lại LLM ở vòng lặp tiếp theo.
            agent_context = build_agent_context(
                user_query,
                observation_history,
                active_history,
            )
            continue

        # Provider trả về kiểu dữ liệu không được hỗ trợ.
        else:
            final_content = (
                f"Provider trả về response type không hợp lệ: "
                f"{llm_response.get('type')}"
            )
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "thought": "Không nhận diện được loại phản hồi từ Provider.",
                "output": final_content,
                "latency_ms": llm_latency_ms
            })
            print(f"🏁 [Final Answer]: {final_content}")
            final_answer_created = True
            break

    if not final_answer_created:
        final_content = (
            "Agent đã đạt giới hạn số vòng lặp nhưng chưa hoàn tất yêu cầu. "
            "Vui lòng cung cấp thêm thông tin hoặc thử lại."
        )
        trace_logs.append({
            "step": step + 1,
            "query": user_query,
            "action_type": "FINAL_ANSWER",
            "thought": "Đã đạt MAX_ITERATIONS.",
            "output": final_content,
            "latency_ms": 0.0
        })
        print(f"🏁 [Final Answer]: {final_content}")

    # Chỉ lưu lịch sử khi được truyền vào (interactive mode). Test suite vẫn
    # độc lập giữa các test case, tránh việc dữ liệu của TC trước ảnh hưởng TC sau.
    if conversation_history is not None:
        conversation_history.append({"role": "user", "content": user_query.strip()})
        conversation_history.append({"role": "assistant", "content": final_content})

        # Lưu dấu vết ngắn của các Tool SUCCESS để lượt sau hiểu trạng thái.
        # Provider sẽ dùng marker care_warning để không đặt lịch trùng; nếu người
        # dùng đưa ra yêu cầu lập lịch mới rõ ràng thì lượt mới vẫn được phép chạy.
        for item in observation_history:
            observation = item.get("observation", {})
            tool_name = item.get("tool_name")
            if (
                tool_name in {"chicken_query", "care_warning"}
                and isinstance(observation, dict)
                and observation.get("status") == "SUCCESS"
            ):
                conversation_history.append({
                    "role": "system",
                    "content": (
                        f"PRIOR_TOOL_SUCCESS: {tool_name}\n"
                        + json.dumps(observation, ensure_ascii=False)
                    ),
                })

        del conversation_history[:-MAX_HISTORY_MESSAGES]

    return trace_logs


if __name__ == "__main__":
    print("==========================================================")
    print("🐔 AI COURSE - DAY 03 LAB: CHICKEN CARE REACT AGENT")
    print("==========================================================")
    
    provider = get_llm_provider()
    mcp_server = MCPAcademicServer(server_name="chicken-care-mcp-server")
    
    print(f"🔌 LLM Provider: {provider.__class__.__name__}")
    print(f"🌐 MCP Server: {mcp_server.server_name}\n")

    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases thử nghiệm.\n")

    # Bộ nhớ nhiều lượt của Interactive CLI; khởi động lại chương trình sẽ xóa bộ nhớ này.
    conversation_history = []

    if "--interactive" in sys.argv:
        print("🎮 [INTERACTIVE MODE] Trò chuyện trực tiếp với ReAct Agent:")
        print("💡 Gợi ý câu hỏi thử nghiệm:")
        print("   - Câu hỏi chung: 'Làm thế nào để giữ chuồng gà sạch và thông thoáng?'")
        print("   - Tra cứu nguy cơ: 'Đàn gà bỏ ăn, tiêu chảy và thở gấp.'")
        print("   - Tạo cảnh báo: 'Lập lịch kiểm tra nhiệt độ chuồng vào 14:00 15/09/2026 cho đàn 2000 con.'")
        print("   - Gõ '/clear' để xóa lịch sử hội thoại hiện tại.")
        print("   - Gõ 'exit' hoặc 'quit' để kết thúc phiên trò chuyện.\n")
        while True:
            try:
                user_input = input("👤 Bạn: ")
            except EOFError:
                print("\n👋 Tạm biệt!")
                break

            if user_input.lower() in ["exit", "quit"]:
                print("👋 Tạm biệt!")
                break

            if user_input.strip().lower() == "/clear":
                conversation_history.clear()
                print("🧹 Đã xóa lịch sử hội thoại trong phiên hiện tại.")
                continue

            if not user_input.strip():
                continue

            logs = run_react_agent(
                user_input.strip(),
                provider,
                mcp_server,
                conversation_history,
            )
            save_waterfall_trace(logs)

    elif "--all" in sys.argv:
        print("🚀 [TEST SUITE MODE] Kiểm tra 5 Test Cases:")
        completed_count = 0
        all_traces = []

        for tc in tests:
            print("\n==================================================")
            print(
                f"🧪 [{tc['id']}] Loại test: {tc['type']} "
                f"(Độ phức tạp: {tc['complexity']})"
            )
            print(f"📌 Kỳ vọng: {tc['expected_behavior']}")

            question = tc.get("question", "").strip()
            if question.upper().startswith("TODO"):
                print("⏸️ [CHƯA KÍCH HOẠT - ĐANG LÀ TODO]:")
                print(f"   {question}")
                continue

            logs = run_react_agent(question, provider, mcp_server)
            all_traces.extend(logs)
            completed_count += 1

        print("\n==================================================")
        print(
            f"📊 [KẾT QUẢ TEST SUITE]: Đã thực thi "
            f"{completed_count}/{len(tests)} Test Cases"
        )
        if all_traces:
            save_waterfall_trace(all_traces)
        print("💡 Để trò chuyện trực tiếp: python src/app.py --interactive")

    else:
        print("ℹ️ HƯỚNG DẪN SỬ DỤNG CHƯƠNG TRÌNH:")
        print("  1. Chat trực tiếp:       python src/app.py --interactive")
        print("  2. Chạy toàn bộ test:    python src/app.py --all\n")

        if tests:
            sample_query = tests[0]["question"]
            print("--- 🏁 DEMO CHẠY THỬ 1 TEST CASE MẪU ---")
            logs = run_react_agent(sample_query, provider, mcp_server)
            save_waterfall_trace(logs)
