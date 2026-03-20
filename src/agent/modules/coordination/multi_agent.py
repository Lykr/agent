"""
多Agent协调器

实现多个Agent之间的任务分配、协调和通信。
"""

import json
import time
import uuid
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future


class AgentRole(Enum):
    """Agent角色"""
    COORDINATOR = "coordinator"      # 协调者
    EXECUTOR = "executor"            # 执行者
    ANALYST = "analyst"              # 分析者
    VALIDATOR = "validator"          # 验证者
    SPECIALIST = "specialist"        # 专家


class CoordinationStrategy(Enum):
    """协调策略"""
    HIERARCHICAL = "hierarchical"    # 层级式
    PEER_TO_PEER = "peer_to_peer"    # 对等式
    AUCTION = "auction"              # 拍卖式
    BLACKBOARD = "blackboard"        # 黑板式


@dataclass
class AgentInfo:
    """Agent信息"""
    agent_id: str
    role: AgentRole
    capabilities: List[str]  # 能力描述
    busy: bool = False
    performance_score: float = 1.0  # 性能评分
    last_assigned_time: float = field(default_factory=lambda: time.time())


@dataclass
class TaskAssignment:
    """任务分配"""
    task_id: str
    subtask_id: str
    agent_id: str
    description: str
    deadline: Optional[float] = None  # 截止时间
    priority: int = 1
    dependencies: List[str] = field(default_factory=list)  # 依赖的任务ID
    result: Optional[str] = None
    status: str = "pending"  # pending, assigned, in_progress, completed, failed
    assigned_at: float = field(default_factory=lambda: time.time())
    completed_at: Optional[float] = None


@dataclass
class Message:
    """Agent间消息"""
    message_id: str
    sender_id: str
    receiver_id: str
    content: str
    message_type: str  # task_result, question, coordination, notification
    timestamp: float = field(default_factory=lambda: time.time())
    read: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultiAgentCoordinator:
    """多Agent协调器"""

    def __init__(self, strategy: CoordinationStrategy = CoordinationStrategy.HIERARCHICAL):
        """
        初始化多Agent协调器

        Args:
            strategy: 协调策略
        """
        self.strategy = strategy
        self.agents: Dict[str, AgentInfo] = {}
        self.task_assignments: Dict[str, TaskAssignment] = {}
        self.messages: Dict[str, Message] = {}
        self.blackboard: Dict[str, Any] = {}  # 共享信息黑板
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.coordinator_agent = None  # 协调者Agent（如果有）

    def register_agent(self, agent_id: str, role: AgentRole, capabilities: List[str]) -> None:
        """注册Agent"""
        self.agents[agent_id] = AgentInfo(
            agent_id=agent_id,
            role=role,
            capabilities=capabilities
        )
        print(f"注册Agent: {agent_id} ({role.value})")

    def unregister_agent(self, agent_id: str) -> None:
        """注销Agent"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            print(f"注销Agent: {agent_id}")

    def assign_task(self, task_id: str, subtask_id: str, description: str,
                    required_capabilities: List[str] = None,
                    priority: int = 1,
                    deadline: Optional[float] = None) -> Optional[str]:
        """
        分配任务给合适的Agent

        Args:
            task_id: 任务ID
            subtask_id: 子任务ID
            description: 任务描述
            required_capabilities: 所需能力
            priority: 优先级
            deadline: 截止时间

        Returns:
            分配的Agent ID，如果无法分配则返回None
        """
        # 根据策略选择Agent
        if self.strategy == CoordinationStrategy.AUCTION:
            agent_id = self._assign_by_auction(required_capabilities, priority)
        elif self.strategy == CoordinationStrategy.HIERARCHICAL:
            agent_id = self._assign_by_hierarchy(required_capabilities, priority)
        else:  # PEER_TO_PEER or BLACKBOARD
            agent_id = self._assign_by_capability(required_capabilities, priority)

        if not agent_id:
            print(f"警告: 无法为任务 {subtask_id} 分配Agent")
            return None

        # 创建任务分配记录
        assignment_id = f"assign_{task_id}_{subtask_id}"
        assignment = TaskAssignment(
            task_id=task_id,
            subtask_id=subtask_id,
            agent_id=agent_id,
            description=description,
            deadline=deadline,
            priority=priority,
            status="assigned"
        )

        self.task_assignments[assignment_id] = assignment
        self.agents[agent_id].busy = True
        self.agents[agent_id].last_assigned_time = time.time()

        print(f"分配任务 {subtask_id} 给 Agent {agent_id}")
        return agent_id

    def _assign_by_capability(self, required_capabilities: List[str], priority: int) -> Optional[str]:
        """基于能力匹配分配"""
        best_agent = None
        best_score = -1

        for agent_id, agent_info in self.agents.items():
            if agent_info.busy:
                continue

            # 计算匹配分数
            score = self._calculate_capability_match(agent_info.capabilities, required_capabilities)
            score *= agent_info.performance_score  # 考虑性能评分

            if score > best_score:
                best_score = score
                best_agent = agent_id

        return best_agent

    def _assign_by_hierarchy(self, required_capabilities: List[str], priority: int) -> Optional[str]:
        """基于层级分配（优先给协调者分配重要任务）"""
        if priority >= 3:  # 高优先级任务给协调者
            for agent_id, agent_info in self.agents.items():
                if agent_info.role == AgentRole.COORDINATOR and not agent_info.busy:
                    return agent_id

        # 否则按能力匹配
        return self._assign_by_capability(required_capabilities, priority)

    def _assign_by_auction(self, required_capabilities: List[str], priority: int) -> Optional[str]:
        """基于拍卖机制分配"""
        # 简单的拍卖实现：Agent投标，选择最优的
        bids = []

        for agent_id, agent_info in self.agents.items():
            if agent_info.busy:
                continue

            # 计算投标价值（能力匹配度 * 性能评分 / 当前负载）
            match_score = self._calculate_capability_match(agent_info.capabilities, required_capabilities)
            bid_value = match_score * agent_info.performance_score

            bids.append((bid_value, agent_id))

        if not bids:
            return None

        # 选择投标价值最高的
        bids.sort(reverse=True)
        return bids[0][1]

    def _calculate_capability_match(self, agent_capabilities: List[str],
                                   required_capabilities: List[str]) -> float:
        """计算能力匹配度"""
        if not required_capabilities:
            return 1.0

        matched = 0
        for req_cap in required_capabilities:
            for agent_cap in agent_capabilities:
                if req_cap.lower() in agent_cap.lower() or agent_cap.lower() in req_cap.lower():
                    matched += 1
                    break

        return matched / len(required_capabilities)

    def submit_task_result(self, assignment_id: str, result: str, success: bool = True) -> None:
        """提交任务结果"""
        if assignment_id not in self.task_assignments:
            print(f"错误: 任务分配 {assignment_id} 不存在")
            return

        assignment = self.task_assignments[assignment_id]
        assignment.result = result
        assignment.completed_at = time.time()
        assignment.status = "completed" if success else "failed"

        # 释放Agent
        if assignment.agent_id in self.agents:
            self.agents[assignment.agent_id].busy = False

            # 更新性能评分
            if success:
                self.agents[assignment.agent_id].performance_score = min(
                    1.2, self.agents[assignment.agent_id].performance_score * 1.05
                )
            else:
                self.agents[assignment.agent_id].performance_score = max(
                    0.5, self.agents[assignment.agent_id].performance_score * 0.9
                )

        print(f"任务 {assignment.subtask_id} 完成，结果: {success}")

        # 将结果写入黑板（如果使用黑板策略）
        if self.strategy == CoordinationStrategy.BLACKBOARD:
            self.blackboard[assignment.subtask_id] = {
                "result": result,
                "success": success,
                "agent": assignment.agent_id,
                "timestamp": time.time()
            }

    def send_message(self, sender_id: str, receiver_id: str, content: str,
                     message_type: str = "coordination") -> str:
        """发送消息"""
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        message = Message(
            message_id=message_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content,
            message_type=message_type
        )

        self.messages[message_id] = message
        print(f"消息发送: {sender_id} -> {receiver_id}: {content[:50]}...")

        return message_id

    def get_messages(self, agent_id: str, unread_only: bool = True) -> List[Message]:
        """获取Agent的消息"""
        agent_messages = []
        for message in self.messages.values():
            if message.receiver_id == agent_id:
                if not unread_only or not message.read:
                    agent_messages.append(message)
                    if unread_only:
                        message.read = True

        return agent_messages

    def execute_parallel_tasks(self, tasks: List[Dict[str, Any]],
                              callback: Optional[Callable[[str, str, str], None]] = None) -> Dict[str, Future]:
        """并行执行多个任务"""
        futures = {}

        for task in tasks:
            task_id = task.get("task_id", f"task_{uuid.uuid4().hex[:8]}")
            subtask_id = task.get("subtask_id", f"subtask_{uuid.uuid4().hex[:8]}")
            description = task.get("description", "")
            required_capabilities = task.get("required_capabilities", [])

            # 分配任务
            agent_id = self.assign_task(task_id, subtask_id, description, required_capabilities)
            if not agent_id:
                continue

            # 提交到线程池执行
            future = self.executor.submit(
                self._execute_task_async,
                task_id, subtask_id, agent_id, description, callback
            )
            futures[subtask_id] = future

        return futures

    def _execute_task_async(self, task_id: str, subtask_id: str, agent_id: str,
                           description: str, callback: Optional[Callable]) -> str:
        """异步执行任务（实际应用中应该调用Agent的run方法）"""
        try:
            # 这里应该调用实际Agent的run方法
            # 暂时模拟执行
            time.sleep(1)  # 模拟执行时间
            result = f"Agent {agent_id} 完成任务: {description}"

            assignment_id = f"assign_{task_id}_{subtask_id}"
            self.submit_task_result(assignment_id, result, success=True)

            if callback:
                callback(task_id, subtask_id, result)

            return result

        except Exception as e:
            error_msg = f"任务执行失败: {str(e)}"
            assignment_id = f"assign_{task_id}_{subtask_id}"
            self.submit_task_result(assignment_id, error_msg, success=False)

            if callback:
                callback(task_id, subtask_id, error_msg)

            return error_msg

    def coordinate_complex_task(self, task_description: str,
                               subtasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        协调复杂任务的执行

        Args:
            task_description: 任务描述
            subtasks: 子任务列表

        Returns:
            协调结果
        """
        task_id = f"complex_task_{int(time.time())}"

        print(f"开始协调复杂任务: {task_description}")
        print(f"子任务数量: {len(subtasks)}")

        # 执行任务
        futures = self.execute_parallel_tasks(subtasks)

        # 等待所有任务完成
        results = {}
        for subtask_id, future in futures.items():
            try:
                result = future.result(timeout=30)  # 30秒超时
                results[subtask_id] = {
                    "success": True,
                    "result": result
                }
            except Exception as e:
                results[subtask_id] = {
                    "success": False,
                    "error": str(e)
                }

        # 生成汇总报告
        success_count = sum(1 for r in results.values() if r["success"])
        total_count = len(results)

        summary = {
            "task_id": task_id,
            "task_description": task_description,
            "total_subtasks": total_count,
            "successful_subtasks": success_count,
            "success_rate": success_count / total_count if total_count > 0 else 0,
            "results": results,
            "timestamp": time.time()
        }

        print(f"任务协调完成: 成功率 {success_count}/{total_count} ({summary['success_rate']:.1%})")

        return summary

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        total_agents = len(self.agents)
        busy_agents = sum(1 for agent in self.agents.values() if agent.busy)
        pending_tasks = sum(1 for task in self.task_assignments.values() if task.status in ["pending", "assigned"])

        return {
            "total_agents": total_agents,
            "busy_agents": busy_agents,
            "idle_agents": total_agents - busy_agents,
            "total_tasks": len(self.task_assignments),
            "pending_tasks": pending_tasks,
            "completed_tasks": len(self.task_assignments) - pending_tasks,
            "strategy": self.strategy.value,
            "blackboard_entries": len(self.blackboard),
            "unread_messages": sum(1 for msg in self.messages.values() if not msg.read)
        }

    def reset(self) -> None:
        """重置协调器状态"""
        self.task_assignments.clear()
        self.messages.clear()
        self.blackboard.clear()

        for agent in self.agents.values():
            agent.busy = False

        print("协调器状态已重置")


# 简单工厂函数
def create_multi_agent_coordinator(strategy: str = "hierarchical") -> MultiAgentCoordinator:
    """创建多Agent协调器"""
    strategy_enum = CoordinationStrategy(strategy)
    return MultiAgentCoordinator(strategy=strategy_enum)