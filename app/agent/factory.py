from typing import Any, Dict, Optional, Type

from app.agent.base import BaseAgent
from app.agent.manus import Manus
from app.agent.task_completion_agent import TaskCompletionAgent

# Registry of available agent classes
AGENT_REGISTRY: Dict[str, Type[BaseAgent]] = {
    "manus": Manus,
    "task_completion": TaskCompletionAgent,
}


def create_agent(agent_type: str = "manus", **kwargs) -> BaseAgent:
    """
    Factory function to create and configure an agent of the specified type.

    Args:
        agent_type: The type of agent to create (e.g., "manus", "task_completion")
        **kwargs: Additional parameters to pass to the agent constructor

    Returns:
        An initialized agent instance

    Raises:
        ValueError: If the specified agent_type is not found in the registry
    """
    agent_class = AGENT_REGISTRY.get(agent_type)
    if not agent_class:
        raise ValueError(f"Unknown agent type: {agent_type}. Available types: {list(AGENT_REGISTRY.keys())}")

    return agent_class(**kwargs)
