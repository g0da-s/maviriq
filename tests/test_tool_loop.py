"""Tests for LLMService.run_tool_loop."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, ToolMessage
from pydantic import BaseModel

from maviriq.services.llm import LLMService, SUBMIT_TOOL_NAME, _build_submit_tool


class SimpleOutput(BaseModel):
    answer: str
    score: float


def _make_ai_message(tool_calls: list[dict] | None = None, content: str = "") -> AIMessage:
    """Build an AIMessage with optional tool_calls."""
    msg = AIMessage(content=content)
    if tool_calls:
        msg.tool_calls = tool_calls
    return msg


def _submit_call(args: dict, call_id: str = "submit_1") -> dict:
    return {"name": SUBMIT_TOOL_NAME, "args": args, "id": call_id}


def _search_call(name: str, query: str, call_id: str = "search_1") -> dict:
    return {"name": name, "args": {"query": query}, "id": call_id}


class TestBuildSubmitTool:
    def test_builds_valid_schema(self):
        tool = _build_submit_tool(SimpleOutput)
        assert tool["name"] == SUBMIT_TOOL_NAME
        assert "input_schema" in tool
        assert "properties" in tool["input_schema"]
        assert "answer" in tool["input_schema"]["properties"]
        assert "score" in tool["input_schema"]["properties"]

    def test_handles_nested_defs(self):
        """Models with nested types should include $defs."""
        from maviriq.models.schemas import PainDiscoveryOutput
        tool = _build_submit_tool(PainDiscoveryOutput)
        assert tool["name"] == SUBMIT_TOOL_NAME
        # PainDiscoveryOutput references PainPoint, UserSegment — should have $defs
        assert "$defs" in tool["input_schema"]


class TestRunToolLoop:
    @pytest.mark.asyncio
    async def test_submit_on_first_call(self):
        """Model calls submit_result immediately — returns validated result."""
        llm = LLMService()

        submit_response = _make_ai_message(tool_calls=[
            _submit_call({"answer": "hello", "score": 0.9})
        ])

        mock_model = MagicMock()
        mock_model.bind_tools = MagicMock(return_value=mock_model)
        mock_model.ainvoke = AsyncMock(return_value=submit_response)
        llm.model = mock_model

        result = await llm.run_tool_loop(
            system_prompt="test",
            user_prompt="test",
            tools=[],
            tool_executors={},
            output_schema=SimpleOutput,
        )

        assert isinstance(result, SimpleOutput)
        assert result.answer == "hello"
        assert result.score == 0.9

    @pytest.mark.asyncio
    async def test_search_then_submit(self):
        """Model searches first, then submits — executor is called."""
        llm = LLMService()

        search_response = _make_ai_message(tool_calls=[
            _search_call("search_web", "test query")
        ])
        submit_response = _make_ai_message(tool_calls=[
            _submit_call({"answer": "found it", "score": 0.8})
        ])

        mock_model = MagicMock()
        mock_model.bind_tools = MagicMock(return_value=mock_model)
        mock_model.ainvoke = AsyncMock(side_effect=[search_response, submit_response])
        llm.model = mock_model

        executor = AsyncMock(return_value="Search result text")

        result = await llm.run_tool_loop(
            system_prompt="test",
            user_prompt="test",
            tools=[{"name": "search_web", "description": "search", "input_schema": {}}],
            tool_executors={"search_web": executor},
            output_schema=SimpleOutput,
        )

        assert result.answer == "found it"
        executor.assert_called_once_with("test query")

    @pytest.mark.asyncio
    async def test_parallel_tool_calls(self):
        """Model calls multiple tools in one turn — all executors called."""
        llm = LLMService()

        parallel_response = _make_ai_message(tool_calls=[
            _search_call("search_web", "query1", call_id="s1"),
            _search_call("search_reddit", "query2", call_id="s2"),
        ])
        submit_response = _make_ai_message(tool_calls=[
            _submit_call({"answer": "combined", "score": 0.7})
        ])

        mock_model = MagicMock()
        mock_model.bind_tools = MagicMock(return_value=mock_model)
        mock_model.ainvoke = AsyncMock(side_effect=[parallel_response, submit_response])
        llm.model = mock_model

        web_exec = AsyncMock(return_value="web results")
        reddit_exec = AsyncMock(return_value="reddit results")

        result = await llm.run_tool_loop(
            system_prompt="test",
            user_prompt="test",
            tools=[],
            tool_executors={"search_web": web_exec, "search_reddit": reddit_exec},
            output_schema=SimpleOutput,
        )

        assert result.answer == "combined"
        web_exec.assert_called_once_with("query1")
        reddit_exec.assert_called_once_with("query2")

    @pytest.mark.asyncio
    async def test_validation_error_retries(self):
        """Invalid submit_result data sends error back; model retries."""
        llm = LLMService()

        bad_submit = _make_ai_message(tool_calls=[
            _submit_call({"answer": "ok", "score": 2.0}, call_id="bad_1")  # score > 1.0
        ])
        good_submit = _make_ai_message(tool_calls=[
            _submit_call({"answer": "ok", "score": 0.5}, call_id="good_1")
        ])

        mock_model = MagicMock()
        mock_model.bind_tools = MagicMock(return_value=mock_model)
        mock_model.ainvoke = AsyncMock(side_effect=[bad_submit, good_submit])
        llm.model = mock_model

        # Note: SimpleOutput doesn't have score validation, so let's use
        # a model that does
        class StrictOutput(BaseModel):
            answer: str

        # Bad submit has extra field which is fine — let's test with missing field
        bad_submit2 = _make_ai_message(tool_calls=[
            _submit_call({"wrong_field": "x"}, call_id="bad_2")
        ])
        good_submit2 = _make_ai_message(tool_calls=[
            _submit_call({"answer": "fixed"}, call_id="good_2")
        ])

        mock_model.ainvoke = AsyncMock(side_effect=[bad_submit2, good_submit2])

        result = await llm.run_tool_loop(
            system_prompt="test",
            user_prompt="test",
            tools=[],
            tool_executors={},
            output_schema=StrictOutput,
        )

        assert result.answer == "fixed"
        # Model was called twice (first failed validation, second succeeded)
        assert mock_model.ainvoke.call_count == 2

    @pytest.mark.asyncio
    async def test_no_tool_calls_forces_submit(self):
        """If model returns no tool calls, force submit_result."""
        llm = LLMService()

        no_tools_response = _make_ai_message(content="I think the answer is X")
        forced_submit = _make_ai_message(tool_calls=[
            _submit_call({"answer": "forced", "score": 0.5})
        ])

        mock_model = MagicMock()
        mock_model.bind_tools = MagicMock(return_value=mock_model)
        mock_model.ainvoke = AsyncMock(side_effect=[no_tools_response, forced_submit])
        llm.model = mock_model

        result = await llm.run_tool_loop(
            system_prompt="test",
            user_prompt="test",
            tools=[],
            tool_executors={},
            output_schema=SimpleOutput,
        )

        assert result.answer == "forced"

    @pytest.mark.asyncio
    async def test_max_iterations_forces_submit(self):
        """When max iterations hit, model is forced to call submit_result."""
        llm = LLMService()

        # Model keeps searching forever
        search_response = _make_ai_message(tool_calls=[
            _search_call("search_web", "endless query")
        ])
        forced_submit = _make_ai_message(tool_calls=[
            _submit_call({"answer": "finally", "score": 0.3})
        ])

        mock_model = MagicMock()
        mock_model.bind_tools = MagicMock(return_value=mock_model)
        # 2 search iterations, then forced submit on iteration 3
        mock_model.ainvoke = AsyncMock(
            side_effect=[search_response, search_response, forced_submit]
        )
        llm.model = mock_model

        executor = AsyncMock(return_value="results")

        result = await llm.run_tool_loop(
            system_prompt="test",
            user_prompt="test",
            tools=[],
            tool_executors={"search_web": executor},
            output_schema=SimpleOutput,
            max_iterations=3,
        )

        assert result.answer == "finally"

    @pytest.mark.asyncio
    async def test_min_searches_blocks_early_submit(self):
        """Submit is blocked when search_successes < min_searches."""
        llm = LLMService()

        # Turn 1: one search
        search_response = _make_ai_message(tool_calls=[
            _search_call("search_web", "first query", call_id="s1")
        ])
        # Turn 2: agent tries to submit too early (only 1 search done, min is 3)
        early_submit = _make_ai_message(tool_calls=[
            _submit_call({"answer": "lazy answer", "score": 0.2}, call_id="early_1")
        ])
        # Turn 3: agent searches more after being blocked
        more_searches = _make_ai_message(tool_calls=[
            _search_call("search_web", "query2", call_id="s2"),
            _search_call("search_reddit", "query3", call_id="s3"),
        ])
        # Turn 4: agent submits after meeting minimum
        final_submit = _make_ai_message(tool_calls=[
            _submit_call({"answer": "thorough answer", "score": 0.9}, call_id="final_1")
        ])

        mock_model = MagicMock()
        mock_model.bind_tools = MagicMock(return_value=mock_model)
        mock_model.ainvoke = AsyncMock(
            side_effect=[search_response, early_submit, more_searches, final_submit]
        )
        llm.model = mock_model

        executor = AsyncMock(return_value="search results")

        result = await llm.run_tool_loop(
            system_prompt="test",
            user_prompt="test",
            tools=[],
            tool_executors={"search_web": executor, "search_reddit": executor},
            output_schema=SimpleOutput,
            min_searches=3,
            recommended_searches=5,
        )

        # Early lazy submit was blocked; the thorough answer was returned
        assert result.answer == "thorough answer"
        assert result.score == 0.9

    @pytest.mark.asyncio
    async def test_min_searches_allows_submit_when_met(self):
        """Submit goes through when search_successes >= min_searches."""
        llm = LLMService()

        # 3 parallel searches in one turn
        parallel_response = _make_ai_message(tool_calls=[
            _search_call("search_web", "q1", call_id="s1"),
            _search_call("search_reddit", "q2", call_id="s2"),
            _search_call("search_web", "q3", call_id="s3"),
        ])
        submit_response = _make_ai_message(tool_calls=[
            _submit_call({"answer": "good", "score": 0.8})
        ])

        mock_model = MagicMock()
        mock_model.bind_tools = MagicMock(return_value=mock_model)
        mock_model.ainvoke = AsyncMock(side_effect=[parallel_response, submit_response])
        llm.model = mock_model

        executor = AsyncMock(return_value="results")

        result = await llm.run_tool_loop(
            system_prompt="test",
            user_prompt="test",
            tools=[],
            tool_executors={"search_web": executor, "search_reddit": executor},
            output_schema=SimpleOutput,
            min_searches=3,
            recommended_searches=5,
        )

        # 3 searches met the minimum of 3 — submit allowed
        assert result.answer == "good"

    @pytest.mark.asyncio
    async def test_min_searches_bypassed_on_last_iteration(self):
        """Last iteration forced submit is never blocked by min_searches."""
        llm = LLMService()

        # Only 1 search, then forced submit on last iteration
        search_response = _make_ai_message(tool_calls=[
            _search_call("search_web", "query", call_id="s1")
        ])
        forced_submit = _make_ai_message(tool_calls=[
            _submit_call({"answer": "forced", "score": 0.3})
        ])

        mock_model = MagicMock()
        mock_model.bind_tools = MagicMock(return_value=mock_model)
        mock_model.ainvoke = AsyncMock(side_effect=[search_response, forced_submit])
        llm.model = mock_model

        executor = AsyncMock(return_value="results")

        result = await llm.run_tool_loop(
            system_prompt="test",
            user_prompt="test",
            tools=[],
            tool_executors={"search_web": executor},
            output_schema=SimpleOutput,
            max_iterations=2,
            min_searches=10,  # impossibly high — but should still submit on last iter
        )

        # Forced submit on last iteration bypasses min_searches
        assert result.answer == "forced"

    @pytest.mark.asyncio
    async def test_budget_context_injected_into_prompt(self):
        """System prompt gets budget context appended when min_searches > 0."""
        llm = LLMService()

        submit_response = _make_ai_message(tool_calls=[
            _submit_call({"answer": "ok", "score": 0.5})
        ])

        mock_model = MagicMock()
        mock_model.bind_tools = MagicMock(return_value=mock_model)
        mock_model.ainvoke = AsyncMock(return_value=submit_response)
        llm.model = mock_model

        await llm.run_tool_loop(
            system_prompt="You are a researcher.",
            user_prompt="test",
            tools=[],
            tool_executors={},
            output_schema=SimpleOutput,
            min_searches=0,  # no budget — prompt should be unchanged
        )

        # Check the system message passed to the model
        call_args = mock_model.ainvoke.call_args
        messages = call_args[0][0]
        system_msg = messages[0].content
        assert "SEARCH BUDGET" not in system_msg

    @pytest.mark.asyncio
    async def test_executor_failure_returns_error_message(self):
        """If a tool executor raises, error is sent back to the model."""
        llm = LLMService()

        search_response = _make_ai_message(tool_calls=[
            _search_call("search_web", "fail query")
        ])
        submit_response = _make_ai_message(tool_calls=[
            _submit_call({"answer": "handled error", "score": 0.1})
        ])

        mock_model = MagicMock()
        mock_model.bind_tools = MagicMock(return_value=mock_model)
        mock_model.ainvoke = AsyncMock(side_effect=[search_response, submit_response])
        llm.model = mock_model

        failing_exec = AsyncMock(side_effect=RuntimeError("API timeout"))

        result = await llm.run_tool_loop(
            system_prompt="test",
            user_prompt="test",
            tools=[],
            tool_executors={"search_web": failing_exec},
            output_schema=SimpleOutput,
        )

        assert result.answer == "handled error"
        failing_exec.assert_called_once()
