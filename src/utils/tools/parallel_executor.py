"""Concurrent tool execution engine.

This module provides parallel execution of multiple tool calls using
ThreadPoolExecutor for I/O-bound operations like file reads and web searches.
"""

import concurrent.futures
from typing import List, Dict, Callable, Any, Tuple
from dataclasses import dataclass


@dataclass
class ToolCall:
    """Represents a single tool call.

    Attributes:
        tool_id: Unique identifier for this tool call
        function_name: Name of the tool function to execute
        arguments: Dict of arguments to pass to the tool handler
        call_index: Index in original tool_calls array (for order preservation)
    """
    tool_id: str
    function_name: str
    arguments: dict
    call_index: int


@dataclass
class ToolResult:
    """Result of a tool execution.

    Attributes:
        tool_id: Unique identifier for the tool call
        call_index: Index in original tool_calls array (for order preservation)
        success: Whether the tool executed successfully
        result: String result from tool execution (if successful)
        error: Error message (if failed)
        should_exit: Whether the tool requested the orchestration loop to exit
    """
    tool_id: str
    call_index: int
    success: bool
    result: str
    error: str = None
    should_exit: bool = False


class ParallelToolExecutor:
    """Executes multiple tool calls concurrently with proper error handling.

    This class provides thread-safe concurrent execution of tool calls using
    ThreadPoolExecutor. Key features:
    - Executes independent tools concurrently for performance
    - Preserves result order using call_index tracking
    - Isolates errors (one failure doesn't stop others)
    - Fast-path optimization for single tool calls (no threading overhead)
    """

    def __init__(self, max_workers: int = 5):
        """Initialize executor.

        Args:
            max_workers: Maximum number of concurrent tool executions
        """
        self.max_workers = max_workers

    def execute_tools(
        self,
        tool_calls: List[ToolCall],
        handler_map: Dict[str, Callable],
        context: dict
    ) -> Tuple[List[ToolResult], bool]:
        """Execute multiple tools concurrently.

        Args:
            tool_calls: List of ToolCall objects
            handler_map: Dict mapping function_name to handler callable
            context: Dict containing repo_root, console, chat_manager, etc.

        Returns:
            Tuple of (results in call_index order, had_any_errors)
        """
        if len(tool_calls) == 1:
            # Fast path for single tool (no threading overhead)
            return self._execute_single(tool_calls[0], handler_map, context)

        # Parallel execution for multiple tools
        results = []

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(self.max_workers, len(tool_calls))
        ) as executor:
            # Submit all tool executions
            future_to_call = {
                executor.submit(
                    self._execute_single_tool,
                    tool_call,
                    handler_map,
                    context
                ): tool_call
                for tool_call in tool_calls
            }

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_call):
                tool_call = future_to_call[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(ToolResult(
                        tool_id=tool_call.tool_id,
                        call_index=tool_call.call_index,
                        success=False,
                        result="",
                        error=str(e)
                    ))

        # Sort by call_index to maintain order
        results.sort(key=lambda r: r.call_index)

        # Check for errors
        had_errors = any(not r.success for r in results)

        return results, had_errors

    def _execute_single(
        self,
        tool_call: ToolCall,
        handler_map: Dict[str, Callable],
        context: dict
    ) -> Tuple[List[ToolResult], bool]:
        """Execute single tool (fast path, no threading overhead).

        Args:
            tool_call: Single ToolCall to execute
            handler_map: Handler function mapping
            context: Execution context dict

        Returns:
            Tuple of (single-element result list, had_errors)
        """
        result = self._execute_single_tool(tool_call, handler_map, context)
        return [result], not result.success

    def _execute_single_tool(
        self,
        tool_call: ToolCall,
        handler_map: Dict[str, Callable],
        context: dict
    ) -> ToolResult:
        """Execute a single tool call with error handling.

        Args:
            tool_call: ToolCall to execute
            handler_map: Handler function mapping
            context: Execution context dict

        Returns:
            ToolResult with execution outcome
        """
        handler = handler_map.get(tool_call.function_name)

        if not handler:
            return ToolResult(
                tool_id=tool_call.tool_id,
                call_index=tool_call.call_index,
                success=False,
                result="",
                error=f"Unknown tool '{tool_call.function_name}'"
            )

        try:
            should_exit, tool_result = handler(
                tool_call.tool_id,
                tool_call.arguments,
                context.get('thinking_indicator')
            )

            return ToolResult(
                tool_id=tool_call.tool_id,
                call_index=tool_call.call_index,
                success=True,
                result=tool_result,
                should_exit=should_exit
            )

        except Exception as e:
            return ToolResult(
                tool_id=tool_call.tool_id,
                call_index=tool_call.call_index,
                success=False,
                result="",
                error=str(e)
            )
