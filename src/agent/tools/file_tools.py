"""
文件操作工具

提供文件读写、目录列表等文件系统操作。
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import FileSystemTool, ToolExecutionError


class FileReadTool(FileSystemTool):
    """文件读取工具"""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "读取文件内容。输入应为文件路径。"

    def _get_path_from_input(self, input_text: str) -> str:
        """从输入中提取文件路径"""
        return input_text.strip()

    def _execute_impl(self, input_text: str) -> str:
        """读取文件内容"""
        file_path = input_text.strip()
        if not file_path:
            raise ToolExecutionError("请输入文件路径")

        try:
            content = self._read_file_safe(file_path)
            return f"文件 '{file_path}' 的内容:\n```\n{content}\n```"
        except ToolExecutionError:
            raise
        except Exception as e:
            raise ToolExecutionError(f"读取文件失败: {str(e)}")


class FileWriteTool(FileSystemTool):
    """文件写入工具"""

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "写入内容到文件。输入格式：文件路径\\n内容"

    def _get_path_from_input(self, input_text: str) -> str:
        """从输入中提取文件路径"""
        lines = input_text.strip().split('\n', 1)
        return lines[0].strip() if lines else ""

    def _execute_impl(self, input_text: str) -> str:
        """写入文件内容"""
        lines = input_text.strip().split('\n', 1)
        if len(lines) < 2:
            raise ToolExecutionError("输入格式应为：文件路径\\n内容")

        file_path = lines[0].strip()
        content = lines[1]

        if not file_path:
            raise ToolExecutionError("请输入文件路径")

        try:
            self._write_file_safe(file_path, content)
            return f"已成功写入文件: {file_path}\n写入字符数: {len(content)}"
        except ToolExecutionError:
            raise
        except Exception as e:
            raise ToolExecutionError(f"写入文件失败: {str(e)}")


class FileListTool(FileSystemTool):
    """文件列表工具"""

    @property
    def name(self) -> str:
        return "list_files"

    @property
    def description(self) -> str:
        return "列出目录内容。输入应为目录路径，如果为空则列出当前目录。"

    def _get_path_from_input(self, input_text: str) -> str:
        """从输入中提取目录路径"""
        path = input_text.strip()
        return path if path else "."

    def _execute_impl(self, input_text: str) -> str:
        """列出目录内容"""
        dir_path = input_text.strip() or "."

        try:
            items = self._list_directory_safe(dir_path)

            if not items:
                return f"目录 '{dir_path}' 为空"

            # 格式化输出
            output_lines = [f"目录 '{dir_path}' 的内容:"]
            output_lines.append("-" * 50)

            for item in items:
                item_type = "📁" if item["type"] == "directory" else "📄"
                size_str = f"{item['size']:,} bytes" if item["type"] == "file" else ""
                output_lines.append(
                    f"{item_type} {item['name']:30} {size_str:15} {item['modified']}"
                )

            output_lines.append("-" * 50)
            output_lines.append(f"总计: {len(items)} 个项目")

            return "\n".join(output_lines)

        except ToolExecutionError:
            raise
        except Exception as e:
            raise ToolExecutionError(f"列出目录失败: {str(e)}")


class FileInfoTool(FileSystemTool):
    """文件信息工具"""

    @property
    def name(self) -> str:
        return "file_info"

    @property
    def description(self) -> str:
        return "获取文件或目录的详细信息。输入应为路径。"

    def _get_path_from_input(self, input_text: str) -> str:
        """从输入中提取路径"""
        return input_text.strip()

    def _execute_impl(self, input_text: str) -> str:
        """获取文件/目录信息"""
        path_str = input_text.strip()
        if not path_str:
            raise ToolExecutionError("请输入路径")

        try:
            path = self._validate_file_path(path_str)

            if not path.exists():
                raise ToolExecutionError(f"路径不存在: {path_str}")

            stat = path.stat()
            info = {
                "路径": str(path),
                "类型": "目录" if path.is_dir() else "文件",
                "大小": f"{stat.st_size:,} bytes",
                "创建时间": self._format_timestamp(stat.st_ctime),
                "修改时间": self._format_timestamp(stat.st_mtime),
                "访问时间": self._format_timestamp(stat.st_atime),
                "权限": oct(stat.st_mode)[-3:],
                "所有者": f"{stat.st_uid}:{stat.st_gid}",
            }

            if path.is_file():
                # 文件特定信息
                suffix = path.suffix
                info["扩展名"] = suffix if suffix else "无"
                info["文件名"] = path.name
                info["父目录"] = str(path.parent)

            elif path.is_dir():
                # 目录特定信息
                try:
                    items = list(path.iterdir())
                    info["项目数量"] = len(items)
                    info["文件数量"] = sum(1 for item in items if item.is_file())
                    info["目录数量"] = sum(1 for item in items if item.is_dir())
                except Exception:
                    info["项目数量"] = "无法读取"

            # 格式化输出
            output_lines = [f"路径信息: {path_str}"]
            output_lines.append("=" * 50)

            for key, value in info.items():
                output_lines.append(f"{key:10}: {value}")

            return "\n".join(output_lines)

        except ToolExecutionError:
            raise
        except Exception as e:
            raise ToolExecutionError(f"获取文件信息失败: {str(e)}")

    def _format_timestamp(self, timestamp: float) -> str:
        """格式化时间戳"""
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


class FileSearchTool(FileSystemTool):
    """文件搜索工具"""

    @property
    def name(self) -> str:
        return "search_files"

    @property
    def description(self) -> str:
        return "在目录中搜索文件。输入格式：目录路径\\n搜索模式（支持通配符）"

    def _get_path_from_input(self, input_text: str) -> str:
        """从输入中提取目录路径"""
        lines = input_text.strip().split('\n', 1)
        return lines[0].strip() if lines else "."

    def _execute_impl(self, input_text: str) -> str:
        """搜索文件"""
        lines = input_text.strip().split('\n', 1)
        if len(lines) < 2:
            raise ToolExecutionError("输入格式应为：目录路径\\n搜索模式")

        dir_path = lines[0].strip() or "."
        pattern = lines[1].strip()

        if not pattern:
            raise ToolExecutionError("请输入搜索模式")

        try:
            path = self._validate_file_path(dir_path)

            if not path.exists():
                raise ToolExecutionError(f"目录不存在: {dir_path}")

            if not path.is_dir():
                raise ToolExecutionError(f"不是目录: {dir_path}")

            # 搜索文件
            matches = []
            for item in path.rglob(pattern):
                if item.is_file():
                    matches.append({
                        "path": str(item.relative_to(path)),
                        "size": item.stat().st_size,
                        "modified": self._format_timestamp(item.stat().st_mtime),
                    })

            if not matches:
                return f"在 '{dir_path}' 中没有找到匹配 '{pattern}' 的文件"

            # 格式化输出
            output_lines = [f"在 '{dir_path}' 中搜索 '{pattern}' 的结果:"]
            output_lines.append("-" * 60)

            for match in matches[:50]:  # 限制显示数量
                size_str = f"{match['size']:,} bytes"
                output_lines.append(f"{match['path']:40} {size_str:15} {match['modified']}")

            output_lines.append("-" * 60)
            output_lines.append(f"找到 {len(matches)} 个文件")

            if len(matches) > 50:
                output_lines.append(f"（显示前 50 个，共 {len(matches)} 个）")

            return "\n".join(output_lines)

        except ToolExecutionError:
            raise
        except Exception as e:
            raise ToolExecutionError(f"搜索文件失败: {str(e)}")

    def _format_timestamp(self, timestamp: float) -> str:
        """格式化时间戳"""
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


class FileToolsFactory:
    """文件工具工厂类"""

    @staticmethod
    def create_all_tools(
        allowed_directories: Optional[List[str]] = None,
        **kwargs
    ) -> List[FileSystemTool]:
        """创建所有文件工具"""
        common_kwargs = {
            "allowed_directories": allowed_directories,
            **kwargs
        }

        return [
            FileReadTool(**common_kwargs),
            FileWriteTool(**common_kwargs),
            FileListTool(**common_kwargs),
            FileInfoTool(**common_kwargs),
            FileSearchTool(**common_kwargs),
        ]

    @staticmethod
    def create_basic_tools(
        allowed_directories: Optional[List[str]] = None,
        **kwargs
    ) -> List[FileSystemTool]:
        """创建基础文件工具（读写和列表）"""
        common_kwargs = {
            "allowed_directories": allowed_directories,
            **kwargs
        }

        return [
            FileReadTool(**common_kwargs),
            FileWriteTool(**common_kwargs),
            FileListTool(**common_kwargs),
        ]


if __name__ == "__main__":
    # 测试代码
    print("文件操作工具测试")

    # 创建测试目录和文件
    test_dir = Path("./test_data")
    test_dir.mkdir(exist_ok=True)

    test_file = test_dir / "test.txt"
    test_file.write_text("这是一个测试文件。\n第二行内容。")

    # 测试文件读取工具
    print("\n1. 测试文件读取工具:")
    read_tool = FileReadTool(allowed_directories=["./test_data"])
    try:
        result = read_tool.execute(str(test_file))
        print(result)
    except Exception as e:
        print(f"错误: {e}")

    # 测试文件列表工具
    print("\n2. 测试文件列表工具:")
    list_tool = FileListTool(allowed_directories=["."])
    try:
        result = list_tool.execute("./test_data")
        print(result)
    except Exception as e:
        print(f"错误: {e}")

    # 测试文件信息工具
    print("\n3. 测试文件信息工具:")
    info_tool = FileInfoTool(allowed_directories=["."])
    try:
        result = info_tool.execute(str(test_file))
        print(result)
    except Exception as e:
        print(f"错误: {e}")

    # 清理测试数据
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)
    print("\n测试完成，已清理测试数据。")