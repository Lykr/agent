"""
工具系统基类

定义工具的标准接口和基础功能。
"""

import os
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime


class ToolError(Exception):
    """工具相关错误"""
    pass


class ToolExecutionError(ToolError):
    """工具执行错误"""
    pass


class ToolPermissionError(ToolError):
    """工具权限错误"""
    pass


class ToolTimeoutError(ToolError):
    """工具超时错误"""
    pass


class BaseTool(ABC):
    """工具抽象基类"""

    def __init__(self, timeout: int = 30, safe_mode: bool = True):
        """
        初始化工具

        Args:
            timeout: 执行超时时间（秒）
            safe_mode: 安全模式
        """
        self.timeout = timeout
        self.safe_mode = safe_mode
        self.call_count = 0
        self.total_execution_time = 0.0

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass

    @abstractmethod
    def _execute_impl(self, input_text: str) -> str:
        """工具执行实现"""
        pass

    def execute(self, input_text: str) -> str:
        """
        执行工具（包装方法，添加统计和错误处理）

        Args:
            input_text: 输入文本

        Returns:
            执行结果
        """
        self.call_count += 1
        start_time = time.time()

        try:
            # 安全检查
            if self.safe_mode:
                self._safe_check(input_text)

            # 执行工具
            result = self._execute_impl(input_text)

            # 记录执行时间
            execution_time = time.time() - start_time
            self.total_execution_time += execution_time

            return result

        except ToolError:
            raise
        except Exception as e:
            raise ToolExecutionError(f"工具执行失败: {str(e)}")

    def _safe_check(self, input_text: str) -> None:
        """安全检查（子类可以重写）"""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "timeout": self.timeout,
            "safe_mode": self.safe_mode,
            "call_count": self.call_count,
            "total_execution_time": self.total_execution_time,
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        avg_time = (
            self.total_execution_time / self.call_count
            if self.call_count > 0 else 0
        )
        return {
            "call_count": self.call_count,
            "total_execution_time": self.total_execution_time,
            "average_time": avg_time,
        }

    def reset_stats(self) -> None:
        """重置统计信息"""
        self.call_count = 0
        self.total_execution_time = 0.0

    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.__class__.__name__}(name={self.name})"


class FileSystemTool(BaseTool):
    """文件系统工具基类"""

    def __init__(
        self,
        allowed_directories: Optional[list[str]] = None,
        **kwargs
    ):
        """
        初始化文件系统工具

        Args:
            allowed_directories: 允许访问的目录列表
            **kwargs: 传递给父类的参数
        """
        super().__init__(**kwargs)
        self.allowed_directories = allowed_directories or [os.getcwd()]

    def _safe_check(self, input_text: str) -> None:
        """文件系统安全检查"""
        # 检查路径是否在允许的目录内
        if hasattr(self, '_get_path_from_input'):
            try:
                path = self._get_path_from_input(input_text)
                if path:
                    self._check_path_permission(path)
            except Exception:
                # 如果无法解析路径，跳过检查
                pass

    def _check_path_permission(self, path: str) -> None:
        """检查路径权限"""
        try:
            abs_path = os.path.abspath(path)
            allowed = False

            for allowed_dir in self.allowed_directories:
                allowed_abs = os.path.abspath(allowed_dir)
                try:
                    # 检查路径是否在允许的目录内
                    if os.path.commonpath([abs_path, allowed_abs]) == allowed_abs:
                        allowed = True
                        break
                except ValueError:
                    # 路径没有共同前缀
                    continue

            if not allowed:
                raise ToolPermissionError(
                    f"路径不在允许的目录内: {path}\n"
                    f"允许的目录: {self.allowed_directories}"
                )

        except Exception as e:
            raise ToolPermissionError(f"路径检查失败: {str(e)}")

    def _validate_file_path(self, file_path: str) -> Path:
        """验证文件路径"""
        try:
            path = Path(file_path).expanduser().resolve()
            return path
        except Exception as e:
            raise ToolExecutionError(f"无效的文件路径: {file_path} - {str(e)}")

    def _read_file_safe(self, file_path: str) -> str:
        """安全读取文件"""
        path = self._validate_file_path(file_path)

        if not path.exists():
            raise ToolExecutionError(f"文件不存在: {file_path}")

        if not path.is_file():
            raise ToolExecutionError(f"不是文件: {file_path}")

        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(path, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception as e:
                raise ToolExecutionError(f"读取文件失败: {str(e)}")
        except Exception as e:
            raise ToolExecutionError(f"读取文件失败: {str(e)}")

    def _write_file_safe(self, file_path: str, content: str) -> None:
        """安全写入文件"""
        path = self._validate_file_path(file_path)

        # 检查目录是否存在，如果不存在则创建
        parent_dir = path.parent
        if not parent_dir.exists():
            try:
                parent_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ToolExecutionError(f"创建目录失败: {str(e)}")

        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            raise ToolExecutionError(f"写入文件失败: {str(e)}")

    def _list_directory_safe(self, dir_path: str) -> list[Dict[str, Any]]:
        """安全列出目录内容"""
        path = self._validate_file_path(dir_path)

        if not path.exists():
            raise ToolExecutionError(f"目录不存在: {dir_path}")

        if not path.is_dir():
            raise ToolExecutionError(f"不是目录: {dir_path}")

        try:
            items = []
            for item in path.iterdir():
                item_info = {
                    "name": item.name,
                    "type": "file" if item.is_file() else "directory",
                    "size": item.stat().st_size if item.is_file() else 0,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                }
                items.append(item_info)
            return items
        except Exception as e:
            raise ToolExecutionError(f"列出目录失败: {str(e)}")


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """注册工具"""
        if tool.name in self._tools:
            raise ValueError(f"工具已存在: {tool.name}")
        self._tools[tool.name] = tool

    def unregister(self, tool_name: str) -> None:
        """取消注册工具"""
        if tool_name in self._tools:
            del self._tools[tool_name]

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self._tools.get(tool_name)

    def get_all_tools(self) -> Dict[str, BaseTool]:
        """获取所有工具"""
        return self._tools.copy()

    def get_tool_descriptions(self) -> list[Dict[str, str]]:
        """获取所有工具描述"""
        return [
            {"name": name, "description": tool.description}
            for name, tool in self._tools.items()
        ]

    def clear(self) -> None:
        """清空所有工具"""
        self._tools.clear()

    def __len__(self) -> int:
        """工具数量"""
        return len(self._tools)

    def __contains__(self, tool_name: str) -> bool:
        """检查工具是否存在"""
        return tool_name in self._tools


if __name__ == "__main__":
    # 测试代码
    print("工具基类测试")

    # 测试简单工具
    class TestTool(BaseTool):
        @property
        def name(self):
            return "test_tool"

        @property
        def description(self):
            return "测试工具"

        def _execute_impl(self, input_text: str):
            return f"测试工具执行: {input_text}"

    tool = TestTool()
    print(f"创建工具: {tool}")
    print(f"工具信息: {tool.to_dict()}")

    result = tool.execute("测试输入")
    print(f"执行结果: {result}")
    print(f"执行后统计: {tool.get_stats()}")

    # 测试工具注册表
    registry = ToolRegistry()
    registry.register(tool)
    print(f"\n注册表工具数量: {len(registry)}")
    print(f"工具描述: {registry.get_tool_descriptions()}")