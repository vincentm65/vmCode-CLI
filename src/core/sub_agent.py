"""Sub-agent for delegated tasks.

Uses existing AgenticOrchestrator with isolated message context
and read-only tools to execute generic delegated tasks.
"""

from pathlib import Path
from typing import Optional

from core.agentic import AgenticOrchestrator
from core.chat_manager import ChatManager
from llm.prompts import build_sub_agent_prompt


# Read-only tools allowed for sub-agent
SUB_AGENT_TOOLS = ["rg", "read_file", "list_directory", "web_search"]


def _create_chat_manager():
    """Create a fresh ChatManager instance for sub-agent use.

    Returns:
        ChatManager: A new ChatManager instance with pre-configured system prompt
    """
    # Subagent uses 75k soft limit (vs 100k for main agent)
    chat_manager = ChatManager(compact_trigger_tokens=75_000)

    # Build sub-agent prompt with token awareness
    base_prompt = build_sub_agent_prompt()
    token_usage = chat_manager.token_tracker.get_usage_for_prompt(context_limit=200_000)

    # Inject token usage into sub-agent system prompt
    chat_manager.messages = [{"role": "system", "content": f"{base_prompt}\n\n{token_usage}"}]
    
    # Load agents.md if it exists in current working directory
    agents_path = Path.cwd() / "agents.md"
    if agents_path.exists():
        map_content = agents_path.read_text(encoding="utf-8").strip()
        user_msg = (
            "Here is the codebase map for this project. "
            "This provides an overview of the repository structure and file purposes. "
            "Use this as a reference when exploring the codebase.\n\n"
            f"## Codebase Map (auto-generated from agents.md)\n\n{map_content}"
        )
        assistant_msg = (
            "I've received the codebase map. I'll use this as a reference when "
            "exploring the repository, but I'll always verify current state by "
            "reading files and searching the codebase before making changes."
        )
        chat_manager.messages.append({"role": "user", "content": user_msg})
        chat_manager.messages.append({"role": "assistant", "content": assistant_msg})
    
    # No conversation logging for sub-agent (isolated)
    chat_manager.conversation_logger = None
    # CRITICAL: Force plan mode to restrict dangerous tools
    chat_manager.interaction_mode = "plan"
    return chat_manager


def run_sub_agent(
    task_query: str,
    repo_root: Path,
    rg_exe_path: str,
    console=None,
    panel_updater=None,
) -> dict:
    """Run sub-agent using existing AgenticOrchestrator for delegated tasks.

    Args:
        task_query: Generic task query to execute (e.g., "Read file config.json")
        repo_root: Repository root path
        rg_exe_path: Path to rg executable
        console: Optional Rich console for output
        panel_updater: Optional SubAgentPanel for live panel updates

    Returns:
        Dict with:
            - 'result': Formatted markdown string (goes into chat history)
            - 'usage': Usage data for billing
            - 'error': Error message if failed (None if success)
    """
    # Validate panel_updater type if provided
    if panel_updater is not None and not hasattr(panel_updater, 'append'):
        panel_updater = None

    # Create fresh ChatManager for sub-agent
    temp_chat_manager = _create_chat_manager()

    # Create orchestrator (reuses existing implementation)
    orchestrator = AgenticOrchestrator(
        chat_manager=temp_chat_manager,
        repo_root=repo_root,
        rg_exe_path=rg_exe_path,
        console=console,
        debug_mode=False,
        suppress_result_display=True,
        is_sub_agent=True,
        panel_updater=panel_updater,
        pre_tool_planning_enabled=False,
        force_parallel_execution=True  # Enable parallel execution for read-only tools
    )

    try:
        # Run sub-agent task
        orchestrator.run(
            task_query,
            thinking_indicator=None,
            allowed_tools=SUB_AGENT_TOOLS
        )
    except Exception as e:
        return {
            "result": "",
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            },
            "error": str(e)
        }

    # Get final token usage (no need for delta calculation on fresh instance)
    delta_prompt = temp_chat_manager.token_tracker.total_prompt_tokens
    delta_completion = temp_chat_manager.token_tracker.total_completion_tokens
    delta_total = temp_chat_manager.token_tracker.total_tokens

    # Extract final response (last assistant message with content)
    final_content = ""
    for msg in reversed(temp_chat_manager.messages):
        if msg.get("role") == "assistant" and msg.get("content"):
            final_content = msg["content"].strip()
            break

    # Format with usage at end
    result = (
        f"{final_content}\n\n"
        f"---\n"
        f"Sub-agent used: {delta_prompt} prompt tokens, {delta_completion} completion tokens ({delta_total} total)"
    )

    return {
        "result": result,
        "usage": {
            "prompt_tokens": delta_prompt,
            "completion_tokens": delta_completion,
            "total_tokens": delta_total
        },
        "error": None
    }
