"""Shared prompt utilities for vmCode CLI."""

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from llm.config import get_provider_config, APPROVE_MODE_LABELS, LEARNING_MODE_LABELS, PLAN_TYPE_LABELS
from core.config_manager import ConfigManager


def get_bottom_toolbar_text(chat_manager):
    """Return bottom toolbar text with model, approval mode, and token count.

    This is extracted from main.py for reuse in confirmation prompts.

    Args:
        chat_manager: ChatManager instance for state access

    Returns:
        HTML formatted toolbar text
    """
    provider_name = chat_manager.client.provider
    model = get_provider_config(provider_name).get("model", "Unknown")

    # Get token counts
    tokens_curr = chat_manager.token_tracker.current_context_tokens
    tokens_in = chat_manager.token_tracker.total_prompt_tokens
    tokens_out = chat_manager.token_tracker.total_completion_tokens
    tokens_total = chat_manager.token_tracker.total_tokens

    # Format model name (take last part if path)
    if "\\" in model or "/" in model:
        model_display = model.split("\\")[-1].split("/")[-1]
    else:
        model_display = model
    
    # In Plan mode, show plan types
    if chat_manager.interaction_mode == "plan":
        plan_type = PLAN_TYPE_LABELS.get(
            chat_manager.plan_type,
            chat_manager.plan_type.upper()
        )
        # Colorize plan type
        if chat_manager.plan_type == "feature":
            plan_type_colored = f'<style fg="cyan">{plan_type}</style>'
        elif chat_manager.plan_type == "refactor":
            plan_type_colored = f'<style fg="green">{plan_type}</style>'
        elif chat_manager.plan_type == "debug":
            plan_type_colored = f'<style fg="red">{plan_type}</style>'
        else:  # optimize
            plan_type_colored = f'<style fg="yellow">{plan_type}</style>'

        return HTML(
            '<style fg="white">Model: {} | Plan: </style>{}'
            '<style fg="white"> | </style><style fg="cyan">curr</style><style fg="white">: {:,} | </style>'
            '<style fg="cyan">in</style><style fg="white">: {:,} | </style>'
            '<style fg="cyan">out</style><style fg="white">: {:,} | </style>'
            '<style fg="cyan">total</style><style fg="white">: {:,}</style>'.format(
                model_display or provider_name,
                plan_type_colored,
                tokens_curr,
                tokens_in,
                tokens_out,
                tokens_total
            )
        )
    
    # In Learn mode, show learning modes instead of approval modes
    if chat_manager.interaction_mode == "learn":
        learning_mode = LEARNING_MODE_LABELS.get(
            chat_manager.learning_mode, 
            chat_manager.learning_mode.upper()
        )
        # Colorize learning mode
        if chat_manager.learning_mode == "succinct":
            learning_mode_colored = f'<style fg="cyan">{learning_mode}</style>'
        elif chat_manager.learning_mode == "balanced":
            learning_mode_colored = f'<style fg="green">{learning_mode}</style>'
        else:  # verbose
            learning_mode_colored = f'<style fg="magenta">{learning_mode}</style>'

        return HTML(
            '<style fg="white">Model: {} | Learn: </style>{}'
            '<style fg="white"> | </style><style fg="cyan">curr</style><style fg="white">: {:,} | </style>'
            '<style fg="cyan">in</style><style fg="white">: {:,} | </style>'
            '<style fg="cyan">out</style><style fg="white">: {:,} | </style>'
            '<style fg="cyan">total</style><style fg="white">: {:,}</style>'.format(
                model_display or provider_name,
                learning_mode_colored,
                tokens_curr,
                tokens_in,
                tokens_out,
                tokens_total
            )
        )
    
    # Show approval modes for Plan/Edit modes
    approval_mode = APPROVE_MODE_LABELS.get(
        chat_manager.approve_mode, 
        chat_manager.approve_mode.upper()
    )
    
    # Colorize approval mode based on type
    if chat_manager.approve_mode == "safe":
        approval_mode_colored = f'<style fg="green">{approval_mode}</style>'
    elif chat_manager.approve_mode == "accept_edits":
        approval_mode_colored = f'<style fg="yellow">{approval_mode}</style>'
    else:
        approval_mode_colored = approval_mode
    
    return HTML(
        '<style fg="white">Model: {} | Approval: </style>{}'
        '<style fg="white"> | </style><style fg="cyan">curr</style><style fg="white">: {:,} | </style>'
        '<style fg="cyan">in</style><style fg="white">: {:,} | </style>'
        '<style fg="cyan">out</style><style fg="white">: {:,} | </style>'
        '<style fg="cyan">total</style><style fg="white">: {:,}</style>'.format(
            model_display or provider_name,
            approval_mode_colored,
            tokens_curr,
            tokens_in,
            tokens_out,
            tokens_total
        )
    )


def create_confirmation_prompt_session(chat_manager, message_func):
    """Create a PromptSession for confirmation prompts with key bindings and toolbar.
    
    This provides:
    - Shift+Tab to toggle approval mode
    - Bottom toolbar showing model, approval mode, and token counts
    - Dynamic prompt message that updates when mode changes
    
    Args:
        chat_manager: ChatManager instance for state access
        message_func: Function that returns the prompt message HTML (called on each redraw)
        
    Returns:
        PromptSession configured with bindings and toolbar
    """
    bindings = KeyBindings()
    
    @bindings.add('s-tab')
    def toggle_approve_mode(event):
        """Toggle between approval modes using Shift+Tab."""
        if chat_manager.interaction_mode == "learn":
            chat_manager.cycle_learning_mode()
        else:
            chat_manager.cycle_approve_mode()
        event.app.invalidate()
    
    toolbar_style = Style.from_dict({
        "bottom-toolbar": "bg:default fg:white noreverse",
        "bottom-toolbar.text": "bg:default fg:white noreverse",
    })
    
    return PromptSession(
        key_bindings=bindings,
        style=toolbar_style,
        bottom_toolbar=lambda: get_bottom_toolbar_text(chat_manager),
        message=message_func
    )
