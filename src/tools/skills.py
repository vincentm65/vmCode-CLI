"""Tools for loading user skills."""

from .helpers.base import tool


@tool(
    name="load_skill",
    description=(
        "Load one saved user skill by name. Call this before continuing when "
        "the user asks to use a skill or saved instruction."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name of the skill to load.",
            }
        },
        "required": ["name"],
    },
)
def load_skill(name: str, chat_manager=None) -> str:
    """Load a skill into the tool result for the next model turn."""
    from core.skills import SkillError, read_skill, render_skill_for_tool, validate_skill_name

    try:
        valid_name = validate_skill_name(name)
        content = read_skill(valid_name)
        if chat_manager and valid_name in getattr(chat_manager, "loaded_skills", set()):
            return f"exit_code=1\nSkill '{valid_name}' is already loaded in this chat."
        return "exit_code=0\n" + render_skill_for_tool(valid_name, content)
    except SkillError as e:
        return f"exit_code=1\n{e}"
