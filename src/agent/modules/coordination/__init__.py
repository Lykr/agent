"""
多Agent协作模块

实现多个Agent之间的协作和协调。
"""

from .multi_agent import MultiAgentCoordinator, AgentRole, CoordinationStrategy, create_multi_agent_coordinator

__all__ = [
    "MultiAgentCoordinator",
    "AgentRole",
    "CoordinationStrategy",
    "create_multi_agent_coordinator"
]