"""
反思模块

实现反思和自我改进功能，分析任务执行过程，识别错误和改进点。
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import time


class ReflectionType(Enum):
    """反思类型"""
    SUCCESS_ANALYSIS = "success_analysis"  # 成功分析
    ERROR_ANALYSIS = "error_analysis"      # 错误分析
    PROCESS_IMPROVEMENT = "process_improvement"  # 过程改进
    TOOL_EVALUATION = "tool_evaluation"    # 工具评估
    STRATEGY_OPTIMIZATION = "strategy_optimization"  # 策略优化


class ImprovementArea(Enum):
    """改进领域"""
    TASK_PLANNING = "task_planning"        # 任务规划
    TOOL_USAGE = "tool_usage"              # 工具使用
    DECISION_MAKING = "decision_making"    # 决策制定
    COMMUNICATION = "communication"         # 沟通表达
    EFFICIENCY = "efficiency"              # 执行效率
    ERROR_HANDLING = "error_handling"      # 错误处理


@dataclass
class ReflectionInsight:
    """反思见解"""
    id: str
    reflection_type: ReflectionType
    improvement_areas: List[ImprovementArea]
    insight: str  # 核心见解
    evidence: List[str] = field(default_factory=list)  # 证据
    suggestions: List[str] = field(default_factory=list)  # 改进建议
    confidence: float = 0.8  # 置信度 (0-1)
    created_at: float = field(default_factory=lambda: time.time())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "reflection_type": self.reflection_type.value,
            "improvement_areas": [area.value for area in self.improvement_areas],
            "insight": self.insight,
            "evidence": self.evidence,
            "suggestions": self.suggestions,
            "confidence": self.confidence,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReflectionInsight":
        """从字典创建实例"""
        return cls(
            id=data["id"],
            reflection_type=ReflectionType(data["reflection_type"]),
            improvement_areas=[ImprovementArea(area) for area in data["improvement_areas"]],
            insight=data["insight"],
            evidence=data.get("evidence", []),
            suggestions=data.get("suggestions", []),
            confidence=data.get("confidence", 0.8),
            created_at=data.get("created_at", time.time())
        )


@dataclass
class TaskExecutionRecord:
    """任务执行记录"""
    task_id: str
    task_description: str
    start_time: float
    end_time: float
    steps_taken: int = 0
    successful_steps: int = 0
    failed_steps: int = 0
    tools_used: List[str] = field(default_factory=list)
    tool_results: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    errors_encountered: List[Dict[str, Any]] = field(default_factory=list)
    final_result: Optional[str] = None
    quality_score: float = 0.0  # 质量评分 (0-1)

    @property
    def duration(self) -> float:
        """执行时长"""
        return self.end_time - self.start_time

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.steps_taken == 0:
            return 0.0
        return self.successful_steps / self.steps_taken

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "task_description": self.task_description,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "steps_taken": self.steps_taken,
            "successful_steps": self.successful_steps,
            "failed_steps": self.failed_steps,
            "success_rate": self.success_rate,
            "tools_used": self.tools_used,
            "tool_results": self.tool_results,
            "errors_encountered": self.errors_encountered,
            "final_result": self.final_result,
            "quality_score": self.quality_score
        }


class ReflectionEngine:
    """反思引擎"""

    def __init__(self, llm=None, memory_system=None):
        """
        初始化反思引擎

        Args:
            llm: LLM实例，用于智能反思
            memory_system: 记忆系统，用于存储和检索反思结果
        """
        self.llm = llm
        self.memory_system = memory_system
        self.reflection_history: List[ReflectionInsight] = []

    def analyze_task_execution(self, execution_record: TaskExecutionRecord) -> List[ReflectionInsight]:
        """
        分析任务执行过程

        Args:
            execution_record: 任务执行记录

        Returns:
            List[ReflectionInsight]: 反思见解列表
        """
        insights = []

        # 1. 成功分析
        success_insights = self._analyze_successes(execution_record)
        insights.extend(success_insights)

        # 2. 错误分析
        error_insights = self._analyze_errors(execution_record)
        insights.extend(error_insights)

        # 3. 过程改进分析
        process_insights = self._analyze_process_improvements(execution_record)
        insights.extend(process_insights)

        # 4. 工具使用分析
        tool_insights = self._analyze_tool_usage(execution_record)
        insights.extend(tool_insights)

        # 使用LLM进行深度反思（如果可用）
        if self.llm:
            llm_insights = self._perform_llm_reflection(execution_record)
            insights.extend(llm_insights)

        # 存储反思结果
        for insight in insights:
            self.reflection_history.append(insight)
            if self.memory_system:
                self._store_insight_in_memory(insight)

        return insights

    def _analyze_successes(self, record: TaskExecutionRecord) -> List[ReflectionInsight]:
        """分析成功因素"""
        insights = []

        if record.success_rate > 0.8:
            insight = ReflectionInsight(
                id=f"success_{int(time.time())}",
                reflection_type=ReflectionType.SUCCESS_ANALYSIS,
                improvement_areas=[ImprovementArea.DECISION_MAKING, ImprovementArea.TOOL_USAGE],
                insight=f"任务执行成功率较高 ({record.success_rate:.1%})",
                evidence=[f"成功步骤: {record.successful_steps}/{record.steps_taken}"],
                suggestions=[
                    "继续保持当前的工作流程",
                    "总结成功模式以供未来参考"
                ],
                confidence=0.9
            )
            insights.append(insight)

        # 检查工具使用效率
        if record.tools_used and record.success_rate > 0.7:
            insight = ReflectionInsight(
                id=f"tool_success_{int(time.time())}",
                reflection_type=ReflectionType.SUCCESS_ANALYSIS,
                improvement_areas=[ImprovementArea.TOOL_USAGE],
                insight="工具使用恰当且有效",
                evidence=[f"使用了 {len(record.tools_used)} 个工具: {', '.join(record.tools_used)}"],
                suggestions=[
                    "记录成功的工具使用模式",
                    "在类似任务中优先使用已验证的工具"
                ],
                confidence=0.85
            )
            insights.append(insight)

        return insights

    def _analyze_errors(self, record: TaskExecutionRecord) -> List[ReflectionInsight]:
        """分析错误和失败"""
        insights = []

        if record.failed_steps > 0:
            insight = ReflectionInsight(
                id=f"error_{int(time.time())}",
                reflection_type=ReflectionType.ERROR_ANALYSIS,
                improvement_areas=[ImprovementArea.ERROR_HANDLING],
                insight=f"任务执行中存在失败步骤 ({record.failed_steps} 个)",
                evidence=[f"失败步骤: {record.failed_steps}/{record.steps_taken}"],
                suggestions=[
                    "检查失败步骤的原因",
                    "改进错误处理机制",
                    "考虑添加重试逻辑"
                ],
                confidence=0.95
            )
            insights.append(insight)

        # 分析具体错误
        for error in record.errors_encountered:
            error_type = error.get("type", "unknown")
            error_msg = error.get("message", "")

            insight = ReflectionInsight(
                id=f"specific_error_{int(time.time())}",
                reflection_type=ReflectionType.ERROR_ANALYSIS,
                improvement_areas=[ImprovementArea.ERROR_HANDLING],
                insight=f"遇到 {error_type} 类型错误",
                evidence=[f"错误信息: {error_msg[:100]}"],
                suggestions=[
                    f"研究 {error_type} 错误的预防方法",
                    "改进相关代码的错误处理"
                ],
                confidence=0.9
            )
            insights.append(insight)

        return insights

    def _analyze_process_improvements(self, record: TaskExecutionRecord) -> List[ReflectionInsight]:
        """分析过程改进点"""
        insights = []

        # 检查执行效率
        if record.duration > 30:  # 超过30秒的任务
            insight = ReflectionInsight(
                id=f"efficiency_{int(time.time())}",
                reflection_type=ReflectionType.PROCESS_IMPROVEMENT,
                improvement_areas=[ImprovementArea.EFFICIENCY],
                insight=f"任务执行时间较长 ({record.duration:.1f}秒)",
                evidence=[f"总步数: {record.steps_taken}", f"耗时: {record.duration:.1f}秒"],
                suggestions=[
                    "优化任务分解，减少步骤数",
                    "并行执行独立任务",
                    "缓存中间结果以减少重复计算"
                ],
                confidence=0.8
            )
            insights.append(insight)

        # 检查步骤数量
        if record.steps_taken > 10:
            insight = ReflectionInsight(
                id=f"complexity_{int(time.time())}",
                reflection_type=ReflectionType.PROCESS_IMPROVEMENT,
                improvement_areas=[ImprovementArea.TASK_PLANNING],
                insight=f"任务分解过于细致 ({record.steps_taken} 步)",
                evidence=[f"任务步骤数: {record.steps_taken}"],
                suggestions=[
                    "合并相关步骤",
                    "提高每个步骤的粒度",
                    "重新评估任务分解策略"
                ],
                confidence=0.75
            )
            insights.append(insight)

        return insights

    def _analyze_tool_usage(self, record: TaskExecutionRecord) -> List[ReflectionInsight]:
        """分析工具使用情况"""
        insights = []

        # 检查工具使用多样性
        if len(record.tools_used) == 0 and record.steps_taken > 0:
            insight = ReflectionInsight(
                id=f"tool_missing_{int(time.time())}",
                reflection_type=ReflectionType.TOOL_EVALUATION,
                improvement_areas=[ImprovementArea.TOOL_USAGE],
                insight="任务执行中未使用任何工具",
                evidence=["所有步骤均未调用工具"],
                suggestions=[
                    "评估任务是否需要工具辅助",
                    "扩展工具集以支持更多场景",
                    "改进工具调用策略"
                ],
                confidence=0.7
            )
            insights.append(insight)

        # 检查工具失败情况
        tool_failures = []
        for tool_name, results in record.tool_results.items():
            failed_results = [r for r in results if not r.get("success", True)]
            if failed_results:
                tool_failures.append((tool_name, len(failed_results)))

        if tool_failures:
            tool_names = ", ".join([name for name, _ in tool_failures])
            insight = ReflectionInsight(
                id=f"tool_failure_{int(time.time())}",
                reflection_type=ReflectionType.TOOL_EVALUATION,
                improvement_areas=[ImprovementArea.TOOL_USAGE],
                insight=f"工具执行存在失败: {tool_names}",
                evidence=[f"失败工具: {tool_names}"],
                suggestions=[
                    "检查工具配置和权限",
                    "改进工具的错误处理",
                    "提供更清晰的工具使用指导"
                ],
                confidence=0.85
            )
            insights.append(insight)

        return insights

    def _perform_llm_reflection(self, record: TaskExecutionRecord) -> List[ReflectionInsight]:
        """
        使用LLM进行深度反思

        Args:
            record: 任务执行记录

        Returns:
            List[ReflectionInsight]: LLM生成的反思见解
        """
        try:
            # 准备反思数据
            reflection_data = record.to_dict()

            system_prompt = """你是一个AI反思专家。请分析任务执行过程，提供深刻的见解和改进建议。

请按照以下格式输出反思结果：
```json
{
    "insights": [
        {
            "reflection_type": "success_analysis/error_analysis/process_improvement/tool_evaluation/strategy_optimization",
            "improvement_areas": ["task_planning", "tool_usage", "decision_making", "communication", "efficiency", "error_handling"],
            "insight": "核心见解",
            "evidence": ["证据1", "证据2"],
            "suggestions": ["建议1", "建议2"],
            "confidence": 0.85
        }
    ]
}
```

请专注于提供有价值的、可操作的见解。"""

            user_prompt = f"""请分析以下任务执行记录：
{json.dumps(reflection_data, indent=2, ensure_ascii=False)}

请提供3-5个最关键的反思见解。"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            response = self.llm.generate(messages, temperature=0.5)

            # 提取JSON
            import re
            import uuid

            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    return []

            reflection_result = json.loads(json_str)
            insights_data = reflection_result.get("insights", [])

            insights = []
            for insight_data in insights_data:
                insight = ReflectionInsight(
                    id=f"llm_{uuid.uuid4().hex[:8]}",
                    reflection_type=ReflectionType(insight_data["reflection_type"]),
                    improvement_areas=[ImprovementArea(area) for area in insight_data["improvement_areas"]],
                    insight=insight_data["insight"],
                    evidence=insight_data.get("evidence", []),
                    suggestions=insight_data.get("suggestions", []),
                    confidence=insight_data.get("confidence", 0.8)
                )
                insights.append(insight)

            return insights

        except Exception as e:
            print(f"LLM反思失败: {e}")
            return []

    def _store_insight_in_memory(self, insight: ReflectionInsight) -> None:
        """将反思见解存储到记忆系统"""
        if self.memory_system:
            try:
                memory_content = f"反思见解: {insight.insight}\n改进建议: {', '.join(insight.suggestions)}"
                self.memory_system.store_memory(
                    content=memory_content,
                    importance=0.7,
                    category="reflection",
                    metadata=insight.to_dict()
                )
            except Exception as e:
                print(f"存储反思见解失败: {e}")

    def get_recent_insights(self, count: int = 10) -> List[ReflectionInsight]:
        """获取最近的反思见解"""
        return self.reflection_history[-count:]

    def get_insights_by_area(self, improvement_area: ImprovementArea) -> List[ReflectionInsight]:
        """获取特定改进领域的反思见解"""
        return [
            insight for insight in self.reflection_history
            if improvement_area in insight.improvement_areas
        ]

    def generate_improvement_plan(self) -> str:
        """基于反思见解生成改进计划"""
        if not self.reflection_history:
            return "暂无反思数据，无法生成改进计划。"

        # 按改进领域分组
        insights_by_area: Dict[ImprovementArea, List[ReflectionInsight]] = {}
        for insight in self.reflection_history:
            for area in insight.improvement_areas:
                if area not in insights_by_area:
                    insights_by_area[area] = []
                insights_by_area[area].append(insight)

        # 生成改进计划
        improvement_plan = ["# 基于反思的改进计划", ""]

        for area, insights in insights_by_area.items():
            improvement_plan.append(f"## {area.value.replace('_', ' ').title()}")
            improvement_plan.append("")

            # 统计最常见的建议
            all_suggestions = []
            for insight in insights:
                all_suggestions.extend(insight.suggestions)

            # 去重并计数
            from collections import Counter
            suggestion_counts = Counter(all_suggestions)

            for suggestion, count in suggestion_counts.most_common(5):
                improvement_plan.append(f"- {suggestion} (来自 {count} 个反思)")

            improvement_plan.append("")

        return "\n".join(improvement_plan)


# 简单工厂函数
def create_reflection_engine(llm=None, memory_system=None) -> ReflectionEngine:
    """创建反思引擎"""
    return ReflectionEngine(llm=llm, memory_system=memory_system)