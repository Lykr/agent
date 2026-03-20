"""
任务规划模块

实现任务分解和规划功能，支持将复杂任务分解为可执行的子任务序列。
"""

import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class TaskPriority(Enum):
    """任务优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class Subtask:
    """子任务定义"""
    id: str
    description: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)  # 依赖的子任务ID
    estimated_duration: Optional[float] = None  # 预估耗时（秒）
    required_tools: List[str] = field(default_factory=list)  # 需要的工具
    result: Optional[str] = None  # 执行结果
    error: Optional[str] = None  # 错误信息

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "estimated_duration": self.estimated_duration,
            "required_tools": self.required_tools,
            "result": self.result,
            "error": self.error
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Subtask":
        """从字典创建实例"""
        return cls(
            id=data["id"],
            description=data["description"],
            priority=TaskPriority(data["priority"]),
            status=TaskStatus(data["status"]),
            dependencies=data.get("dependencies", []),
            estimated_duration=data.get("estimated_duration"),
            required_tools=data.get("required_tools", []),
            result=data.get("result"),
            error=data.get("error")
        )


@dataclass
class TaskPlan:
    """任务计划"""
    task_id: str
    main_task: str
    subtasks: List[Subtask] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())
    status: TaskStatus = TaskStatus.PENDING
    current_subtask_index: int = 0

    def __post_init__(self):
        import time
        self.created_at = time.time()
        self.updated_at = self.created_at

    def update_status(self) -> None:
        """更新整体任务状态"""
        import time
        self.updated_at = time.time()

        if not self.subtasks:
            self.status = TaskStatus.COMPLETED
            return

        # 检查所有子任务状态
        status_counts = {
            TaskStatus.PENDING: 0,
            TaskStatus.IN_PROGRESS: 0,
            TaskStatus.COMPLETED: 0,
            TaskStatus.FAILED: 0,
            TaskStatus.BLOCKED: 0
        }

        for subtask in self.subtasks:
            status_counts[subtask.status] += 1

        if status_counts[TaskStatus.FAILED] > 0:
            self.status = TaskStatus.FAILED
        elif status_counts[TaskStatus.BLOCKED] > 0 and status_counts[TaskStatus.IN_PROGRESS] == 0:
            self.status = TaskStatus.BLOCKED
        elif status_counts[TaskStatus.IN_PROGRESS] > 0:
            self.status = TaskStatus.IN_PROGRESS
        elif status_counts[TaskStatus.PENDING] == 0:
            self.status = TaskStatus.COMPLETED
        else:
            self.status = TaskStatus.PENDING

    def get_ready_subtasks(self) -> List[Subtask]:
        """获取可以执行的任务（依赖已满足）"""
        ready_subtasks = []
        completed_ids = {st.id for st in self.subtasks if st.status == TaskStatus.COMPLETED}

        for subtask in self.subtasks:
            if subtask.status == TaskStatus.PENDING:
                # 检查依赖是否满足
                if all(dep_id in completed_ids for dep_id in subtask.dependencies):
                    ready_subtasks.append(subtask)

        return ready_subtasks

    def mark_subtask_started(self, subtask_id: str) -> bool:
        """标记子任务开始执行"""
        for subtask in self.subtasks:
            if subtask.id == subtask_id:
                subtask.status = TaskStatus.IN_PROGRESS
                self.update_status()
                return True
        return False

    def mark_subtask_completed(self, subtask_id: str, result: str = None) -> bool:
        """标记子任务完成"""
        for subtask in self.subtasks:
            if subtask.id == subtask_id:
                subtask.status = TaskStatus.COMPLETED
                subtask.result = result
                self.update_status()
                self.current_subtask_index += 1
                return True
        return False

    def mark_subtask_failed(self, subtask_id: str, error: str) -> bool:
        """标记子任务失败"""
        for subtask in self.subtasks:
            if subtask.id == subtask_id:
                subtask.status = TaskStatus.FAILED
                subtask.error = error
                self.update_status()
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "main_task": self.main_task,
            "subtasks": [st.to_dict() for st in self.subtasks],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status.value,
            "current_subtask_index": self.current_subtask_index
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskPlan":
        """从字典创建实例"""
        plan = cls(
            task_id=data["task_id"],
            main_task=data["main_task"],
            subtasks=[Subtask.from_dict(st) for st in data["subtasks"]],
        )
        plan.created_at = data["created_at"]
        plan.updated_at = data["updated_at"]
        plan.status = TaskStatus(data["status"])
        plan.current_subtask_index = data.get("current_subtask_index", 0)
        return plan


class TaskPlanner:
    """任务规划器"""

    def __init__(self, llm=None):
        """
        初始化任务规划器

        Args:
            llm: LLM实例，用于智能任务分解
        """
        self.llm = llm

    def create_plan_from_llm(self, task_description: str, available_tools: List[str] = None) -> TaskPlan:
        """
        使用LLM创建任务计划

        Args:
            task_description: 任务描述
            available_tools: 可用工具列表

        Returns:
            TaskPlan: 任务计划
        """
        import time
        import uuid

        if self.llm is None:
            # 如果没有LLM，创建简单计划
            return self.create_simple_plan(task_description)

        task_id = f"task_{int(time.time())}_{uuid.uuid4().hex[:8]}"

        # 准备系统提示词
        system_prompt = """你是一个任务规划专家。请将复杂的任务分解为可执行的子任务序列。

请按照以下格式输出任务分解：
```json
{
    "main_task": "原始任务描述",
    "subtasks": [
        {
            "id": "subtask_1",
            "description": "子任务1的描述",
            "priority": "high/medium/low",
            "dependencies": [],
            "estimated_duration": 60,
            "required_tools": []
        },
        {
            "id": "subtask_2",
            "description": "子任务2的描述",
            "priority": "medium",
            "dependencies": ["subtask_1"],
            "estimated_duration": 120,
            "required_tools": ["read_file"]
        }
    ]
}
```

注意：
1. 每个子任务必须有唯一的id
2. 优先级必须是 "high", "medium", "low" 之一
3. 依赖关系用id列表表示
4. 预估时间单位是秒
5. 需要的工具列表，如果不知道可以为空"""

        if available_tools:
            tools_str = "\n可用工具: " + ", ".join(available_tools)
            system_prompt += tools_str

        # 调用LLM
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"请分解以下任务:\n{task_description}"}
            ]

            response = self.llm.generate(messages, temperature=0.3)

            # 提取JSON
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接查找JSON
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise ValueError("无法从LLM回复中提取JSON")

            plan_data = json.loads(json_str)

            # 创建任务计划
            subtasks = []
            for i, subtask_data in enumerate(plan_data.get("subtasks", []), 1):
                subtask = Subtask(
                    id=subtask_data.get("id", f"subtask_{i}"),
                    description=subtask_data.get("description", ""),
                    priority=TaskPriority(subtask_data.get("priority", "medium").lower()),
                    dependencies=subtask_data.get("dependencies", []),
                    estimated_duration=subtask_data.get("estimated_duration"),
                    required_tools=subtask_data.get("required_tools", [])
                )
                subtasks.append(subtask)

            plan = TaskPlan(
                task_id=task_id,
                main_task=plan_data.get("main_task", task_description),
                subtasks=subtasks
            )

            return plan

        except Exception as e:
            # 如果LLM规划失败，回退到简单计划
            print(f"LLM规划失败: {e}，使用简单计划")
            return self.create_simple_plan(task_description)

    def create_simple_plan(self, task_description: str) -> TaskPlan:
        """
        创建简单任务计划（不使用LLM）

        Args:
            task_description: 任务描述

        Returns:
            TaskPlan: 简单任务计划
        """
        import time
        import uuid

        task_id = f"task_{int(time.time())}_{uuid.uuid4().hex[:8]}"

        # 基于关键词的简单任务分解
        subtasks = []

        # 检查是否需要文件操作
        if any(keyword in task_description.lower() for keyword in ["文件", "读取", "写入", "查看", "编辑"]):
            subtasks.append(Subtask(
                id="subtask_1",
                description="检查文件系统权限和可用性",
                priority=TaskPriority.HIGH,
                required_tools=["list_files", "get_file_info"]
            ))

            if "读取" in task_description or "查看" in task_description:
                subtasks.append(Subtask(
                    id="subtask_2",
                    description="读取或查看文件内容",
                    priority=TaskPriority.HIGH,
                    dependencies=["subtask_1"],
                    required_tools=["read_file"]
                ))

            if "写入" in task_description or "编辑" in task_description:
                subtasks.append(Subtask(
                    id="subtask_3",
                    description="写入或编辑文件",
                    priority=TaskPriority.HIGH,
                    dependencies=["subtask_1"],
                    required_tools=["write_file"]
                ))

        # 检查是否需要信息收集
        elif any(keyword in task_description.lower() for keyword in ["搜索", "查找", "获取", "收集"]):
            subtasks.append(Subtask(
                id="subtask_1",
                description="明确搜索目标和要求",
                priority=TaskPriority.HIGH
            ))
            subtasks.append(Subtask(
                id="subtask_2",
                description="执行搜索操作",
                priority=TaskPriority.HIGH,
                dependencies=["subtask_1"]
            ))
            subtasks.append(Subtask(
                id="subtask_3",
                description="整理和分析搜索结果",
                priority=TaskPriority.MEDIUM,
                dependencies=["subtask_2"]
            ))

        # 默认任务分解
        else:
            subtasks = [
                Subtask(
                    id="subtask_1",
                    description="分析任务需求",
                    priority=TaskPriority.HIGH
                ),
                Subtask(
                    id="subtask_2",
                    description="制定执行策略",
                    priority=TaskPriority.HIGH,
                    dependencies=["subtask_1"]
                ),
                Subtask(
                    id="subtask_3",
                    description="执行具体操作",
                    priority=TaskPriority.MEDIUM,
                    dependencies=["subtask_2"]
                ),
                Subtask(
                    id="subtask_4",
                    description="验证结果并反馈",
                    priority=TaskPriority.MEDIUM,
                    dependencies=["subtask_3"]
                )
            ]

        plan = TaskPlan(
            task_id=task_id,
            main_task=task_description,
            subtasks=subtasks
        )

        return plan

    def optimize_plan(self, plan: TaskPlan) -> TaskPlan:
        """
        优化任务计划（重新排序、合并任务等）

        Args:
            plan: 原始任务计划

        Returns:
            TaskPlan: 优化后的任务计划
        """
        # 简单的优化：按优先级排序
        plan.subtasks.sort(key=lambda x: (
            x.priority.value,  # 优先级
            len(x.dependencies)  # 依赖少的优先
        ))

        # 更新任务ID顺序
        for i, subtask in enumerate(plan.subtasks, 1):
            subtask.id = f"subtask_{i}"

        plan.update_status()
        return plan


# 简单工厂函数
def create_task_planner(llm=None) -> TaskPlanner:
    """创建任务规划器"""
    return TaskPlanner(llm=llm)