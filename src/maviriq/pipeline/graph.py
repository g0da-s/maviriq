"""Entry point for LangGraph Studio.

Exposes the compiled StateGraph at module level so `langgraph dev`
can discover and render it visually.
"""

from maviriq.pipeline.runner import PipelineGraph

_pipeline = PipelineGraph()
graph = _pipeline.graph
