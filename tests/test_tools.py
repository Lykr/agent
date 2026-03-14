"""
工具模块测试
"""

import os
import tempfile
from pathlib import Path
import pytest

from src.agent.tools.base import (
    BaseTool,
    ToolError,
    ToolExecutionError,
    ToolPermissionError,
    FileSystemTool,
    ToolRegistry,
)
from src.agent.tools.file_tools import (
    FileReadTool,
    FileWriteTool,
    FileListTool,
    FileInfoTool,
    FileSearchTool,
    FileToolsFactory,
)


class TestBaseTool:
    """BaseTool 测试"""

    def test_abstract_methods(self):
        """测试抽象方法"""
        # 应该不能直接实例化抽象类
        with pytest.raises(TypeError):
            tool = BaseTool()  # type: ignore

    def test_concrete_implementation(self):
        """测试具体实现"""
        class TestTool(BaseTool):
            @property
            def name(self):
                return "test_tool"

            @property
            def description(self):
                return "Test tool description"

            def _execute_impl(self, input_text: str):
                return f"Processed: {input_text}"

        tool = TestTool()
        assert tool.name == "test_tool"
        assert tool.description == "Test tool description"
        assert tool.timeout == 30
        assert tool.safe_mode is True

        result = tool.execute("test input")
        assert result == "Processed: test input"
        assert tool.call_count == 1

    def test_tool_statistics(self):
        """测试工具统计"""
        class TestTool(BaseTool):
            @property
            def name(self):
                return "test"

            @property
            def description(self):
                return "Test"

            def _execute_impl(self, input_text: str):
                return "result"

        tool = TestTool()

        # 执行多次
        for i in range(3):
            tool.execute(f"input{i}")

        stats = tool.get_stats()
        assert stats["call_count"] == 3
        assert stats["total_execution_time"] > 0
        assert stats["average_time"] > 0

        # 重置统计
        tool.reset_stats()
        stats = tool.get_stats()
        assert stats["call_count"] == 0
        assert stats["total_execution_time"] == 0
        assert stats["average_time"] == 0

    def test_tool_to_dict(self):
        """测试工具转字典"""
        class TestTool(BaseTool):
            @property
            def name(self):
                return "test"

            @property
            def description(self):
                return "Test"

            def _execute_impl(self, input_text: str):
                return "result"

        tool = TestTool(timeout=60, safe_mode=False)
        tool.execute("test")

        tool_dict = tool.to_dict()
        assert tool_dict["name"] == "test"
        assert tool_dict["description"] == "Test"
        assert tool_dict["timeout"] == 60
        assert tool_dict["safe_mode"] is False
        assert tool_dict["call_count"] == 1
        assert tool_dict["total_execution_time"] > 0


class TestFileSystemTool:
    """FileSystemTool 测试"""

    class TestFileSystemToolImpl(FileSystemTool):
        """测试用的具体FileSystemTool实现"""
        @property
        def name(self):
            return "test_filesystem_tool"

        @property
        def description(self):
            return "Test filesystem tool"

        def _execute_impl(self, input_text: str):
            return f"Test: {input_text}"

    def test_filesystem_tool_creation(self):
        """测试文件系统工具创建"""
        tool = self.TestFileSystemToolImpl(allowed_directories=["/tmp", "/home"])
        assert tool.allowed_directories == ["/tmp", "/home"]

        # 默认允许当前目录
        tool2 = self.TestFileSystemToolImpl()
        assert os.getcwd() in tool2.allowed_directories

    def test_path_permission_check(self):
        """测试路径权限检查"""
        # 创建临时目录结构
        with tempfile.TemporaryDirectory() as tmpdir:
            allowed_dir = Path(tmpdir) / "allowed"
            allowed_dir.mkdir()
            disallowed_dir = Path(tmpdir) / "disallowed"
            disallowed_dir.mkdir()

            # 创建允许访问子目录中的文件
            allowed_file = allowed_dir / "test.txt"
            allowed_file.write_text("test")

            # 创建不允许访问的文件
            disallowed_file = disallowed_dir / "test.txt"
            disallowed_file.write_text("test")

            # 创建具体的实现类
            class TestFileSystemToolImpl(FileSystemTool):
                @property
                def name(self):
                    return "test_fs_tool"

                @property
                def description(self):
                    return "Test file system tool"

                def _execute_impl(self, input_text: str):
                    return "Test execution"

            tool = TestFileSystemToolImpl(allowed_directories=[str(allowed_dir)])

            # 测试允许的路径
            tool._check_path_permission(str(allowed_file))
            tool._check_path_permission(str(allowed_dir))

            # 测试不允许的路径
            with pytest.raises(ToolPermissionError):
                tool._check_path_permission(str(disallowed_file))

            with pytest.raises(ToolPermissionError):
                tool._check_path_permission(str(disallowed_dir))

    def test_validate_file_path(self):
        """测试验证文件路径"""
        tool = self.TestFileSystemToolImpl()

        # 有效路径
        with tempfile.NamedTemporaryFile() as f:
            path = tool._validate_file_path(f.name)
            assert isinstance(path, Path)
            assert path.exists()

        # 无效路径（包含非法字符）
        with pytest.raises(ToolExecutionError):
            tool._validate_file_path("/invalid/\0/path")

    def test_read_write_file_safe(self):
        """测试安全读写文件"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Test content\nSecond line")
            temp_file = f.name

        try:
            tool = self.TestFileSystemToolImpl()

            # 测试读取
            content = tool._read_file_safe(temp_file)
            assert "Test content" in content
            assert "Second line" in content

            # 测试写入
            new_content = "New content"
            tool._write_file_safe(temp_file, new_content)

            # 验证写入
            with open(temp_file, 'r') as f:
                assert f.read() == new_content

        finally:
            os.unlink(temp_file)

    def test_list_directory_safe(self):
        """测试安全列出目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # 创建测试文件和目录
            (tmpdir_path / "file1.txt").write_text("test1")
            (tmpdir_path / "file2.txt").write_text("test2")
            (tmpdir_path / "subdir").mkdir()

            tool = self.TestFileSystemToolImpl()

            # 列出目录
            items = tool._list_directory_safe(tmpdir)
            assert len(items) == 3

            # 检查项目信息
            item_names = {item["name"] for item in items}
            assert "file1.txt" in item_names
            assert "file2.txt" in item_names
            assert "subdir" in item_names

            # 检查类型
            for item in items:
                if item["name"] == "subdir":
                    assert item["type"] == "directory"
                    assert item["size"] == 0
                else:
                    assert item["type"] == "file"
                    assert item["size"] > 0


class TestFileReadTool:
    """FileReadTool 测试"""

    def test_file_read_tool_creation(self):
        """测试文件读取工具创建"""
        tool = FileReadTool()
        assert tool.name == "read_file"
        assert "读取文件内容" in tool.description

    def test_file_read_execution(self):
        """测试文件读取执行"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Line 1\nLine 2\nLine 3")
            temp_file = f.name

        try:
            tool = FileReadTool(allowed_directories=[os.path.dirname(temp_file)])

            result = tool.execute(temp_file)
            assert "Line 1" in result
            assert "Line 2" in result
            assert "Line 3" in result
            assert temp_file in result

        finally:
            os.unlink(temp_file)

    def test_file_read_empty_input(self):
        """测试空输入"""
        tool = FileReadTool()
        with pytest.raises(ToolExecutionError, match="请输入文件路径"):
            tool.execute("")

    def test_file_read_nonexistent_file(self):
        """测试不存在的文件"""
        tool = FileReadTool()
        with pytest.raises(ToolExecutionError, match="文件不存在"):
            tool.execute("/nonexistent/file.txt")


class TestFileWriteTool:
    """FileWriteTool 测试"""

    def test_file_write_tool_creation(self):
        """测试文件写入工具创建"""
        tool = FileWriteTool()
        assert tool.name == "write_file"
        assert "写入内容到文件" in tool.description

    def test_file_write_execution(self):
        """测试文件写入执行"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_file = f.name

        try:
            tool = FileWriteTool(allowed_directories=[os.path.dirname(temp_file)])

            content = "This is test content\nWith multiple lines"
            input_text = f"{temp_file}\n{content}"

            result = tool.execute(input_text)
            assert "已成功写入文件" in result
            assert temp_file in result
            assert "写入字符数" in result

            # 验证文件内容
            with open(temp_file, 'r') as f:
                assert f.read() == content

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_file_write_invalid_input(self):
        """测试无效输入"""
        tool = FileWriteTool()

        # 缺少内容
        with pytest.raises(ToolExecutionError, match="输入格式应为：文件路径"):
            tool.execute("path_only")

        # 空文件路径
        with pytest.raises(ToolExecutionError, match="输入格式应为：文件路径"):
            tool.execute("\ncontent")

    def test_file_write_create_directory(self):
        """测试创建目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = Path(tmpdir) / "newdir"
            new_file = new_dir / "test.txt"

            tool = FileWriteTool(allowed_directories=[tmpdir])

            content = "Test content"
            input_text = f"{new_file}\n{content}"

            # 目录不存在，应该自动创建
            result = tool.execute(input_text)
            assert "已成功写入文件" in result

            # 验证文件和目录
            assert new_dir.exists()
            assert new_file.exists()
            with open(new_file, 'r') as f:
                assert f.read() == content


class TestFileListTool:
    """FileListTool 测试"""

    def test_file_list_tool_creation(self):
        """测试文件列表工具创建"""
        tool = FileListTool()
        assert tool.name == "list_files"
        assert "列出目录内容" in tool.description

    def test_file_list_execution(self):
        """测试文件列表执行"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # 创建测试文件
            (tmpdir_path / "file1.txt").write_text("test1")
            (tmpdir_path / "file2.txt").write_text("test2")
            (tmpdir_path / "subdir").mkdir()

            tool = FileListTool(allowed_directories=[tmpdir])

            # 列出目录
            result = tool.execute(tmpdir)
            assert "file1.txt" in result
            assert "file2.txt" in result
            assert "subdir" in result
            assert "总计: 3 个项目" in result

    def test_file_list_current_directory(self):
        """测试列出当前目录"""
        tool = FileListTool(allowed_directories=["."])

        # 空输入应该列出当前目录
        result = tool.execute("")
        assert "目录" in result
        assert "." in result or "当前目录" in result

    def test_file_list_empty_directory(self):
        """测试空目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = FileListTool(allowed_directories=[tmpdir])

            result = tool.execute(tmpdir)
            assert "为空" in result or "0 个项目" in result


class TestFileInfoTool:
    """FileInfoTool 测试"""

    def test_file_info_tool_creation(self):
        """测试文件信息工具创建"""
        tool = FileInfoTool()
        assert tool.name == "file_info"
        assert "获取文件或目录的详细信息" in tool.description

    def test_file_info_execution(self):
        """测试文件信息执行"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Test content")
            temp_file = f.name

        try:
            tool = FileInfoTool(allowed_directories=[os.path.dirname(temp_file)])

            result = tool.execute(temp_file)
            assert "路径信息" in result
            assert temp_file in result
            assert "类型" in result
            assert "文件" in result
            assert "大小" in result
            assert "修改时间" in result

        finally:
            os.unlink(temp_file)

    def test_directory_info_execution(self):
        """测试目录信息执行"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # 创建测试文件
            (tmpdir_path / "test.txt").write_text("test")

            tool = FileInfoTool(allowed_directories=[tmpdir])

            result = tool.execute(tmpdir)
            assert "路径信息" in result
            assert tmpdir in result
            assert "类型" in result
            assert "目录" in result
            assert "项目数量" in result
            assert "文件数量" in result
            assert "目录数量" in result

    def test_file_info_nonexistent_path(self):
        """测试不存在的路径"""
        tool = FileInfoTool()
        with pytest.raises(ToolExecutionError, match="路径不存在"):
            tool.execute("/nonexistent/path")


class TestFileSearchTool:
    """FileSearchTool 测试"""

    def test_file_search_tool_creation(self):
        """测试文件搜索工具创建"""
        tool = FileSearchTool()
        assert tool.name == "search_files"
        assert "在目录中搜索文件" in tool.description

    def test_file_search_execution(self):
        """测试文件搜索执行"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # 创建测试文件
            (tmpdir_path / "test1.txt").write_text("test1")
            (tmpdir_path / "test2.txt").write_text("test2")
            (tmpdir_path / "other.doc").write_text("other")
            (tmpdir_path / "subdir").mkdir()
            (tmpdir_path / "subdir" / "test3.txt").write_text("test3")

            tool = FileSearchTool(allowed_directories=[tmpdir])

            # 搜索txt文件
            input_text = f"{tmpdir}\n*.txt"
            result = tool.execute(input_text)

            assert "test1.txt" in result
            assert "test2.txt" in result
            assert "subdir/test3.txt" in result or "test3.txt" in result
            assert "other.doc" not in result
            assert "找到" in result and "个文件" in result

    def test_file_search_no_matches(self):
        """测试无匹配结果"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = FileSearchTool(allowed_directories=[tmpdir])

            input_text = f"{tmpdir}\n*.nonexistent"
            result = tool.execute(input_text)

            assert "没有找到匹配" in result

    def test_file_search_invalid_input(self):
        """测试无效输入"""
        tool = FileSearchTool()

        # 缺少搜索模式
        with pytest.raises(ToolExecutionError, match="输入格式应为"):
            tool.execute("path_only")

        # 空搜索模式
        with pytest.raises(ToolExecutionError, match="输入格式应为：目录路径"):
            tool.execute("path\n")


class TestFileToolsFactory:
    """FileToolsFactory 测试"""

    def test_create_all_tools(self):
        """测试创建所有工具"""
        tools = FileToolsFactory.create_all_tools(
            allowed_directories=["/tmp"],
            timeout=60,
            safe_mode=False
        )

        assert len(tools) == 5
        tool_names = {tool.name for tool in tools}
        expected_names = {"read_file", "write_file", "list_files", "file_info", "search_files"}
        assert tool_names == expected_names

        # 检查配置
        for tool in tools:
            assert tool.timeout == 60
            assert tool.safe_mode is False
            assert tool.allowed_directories == ["/tmp"]

    def test_create_basic_tools(self):
        """测试创建基础工具"""
        tools = FileToolsFactory.create_basic_tools(allowed_directories=["/home"])

        assert len(tools) == 3
        tool_names = {tool.name for tool in tools}
        expected_names = {"read_file", "write_file", "list_files"}
        assert tool_names == expected_names

        for tool in tools:
            assert tool.allowed_directories == ["/home"]


class TestToolRegistry:
    """ToolRegistry 测试"""

    def test_tool_registry_creation(self):
        """测试工具注册表创建"""
        registry = ToolRegistry()
        assert len(registry) == 0

    def test_register_tool(self):
        """测试注册工具"""
        registry = ToolRegistry()

        class TestTool(BaseTool):
            @property
            def name(self):
                return "test"

            @property
            def description(self):
                return "Test"

            def _execute_impl(self, input_text: str):
                return "result"

        tool = TestTool()
        registry.register(tool)

        assert len(registry) == 1
        assert "test" in registry
        assert registry.get_tool("test") is tool

    def test_register_duplicate_tool(self):
        """测试注册重复工具"""
        registry = ToolRegistry()

        class TestTool(BaseTool):
            @property
            def name(self):
                return "test"

            @property
            def description(self):
                return "Test"

            def _execute_impl(self, input_text: str):
                return "result"

        tool1 = TestTool()
        tool2 = TestTool()

        registry.register(tool1)
        with pytest.raises(ValueError, match="工具已存在"):
            registry.register(tool2)

    def test_unregister_tool(self):
        """测试取消注册工具"""
        registry = ToolRegistry()

        class TestTool(BaseTool):
            @property
            def name(self):
                return "test"

            @property
            def description(self):
                return "Test"

            def _execute_impl(self, input_text: str):
                return "result"

        tool = TestTool()
        registry.register(tool)

        assert "test" in registry
        registry.unregister("test")
        assert "test" not in registry
        assert registry.get_tool("test") is None

    def test_get_all_tools(self):
        """测试获取所有工具"""
        registry = ToolRegistry()

        class TestTool(BaseTool):
            def __init__(self, name):
                self._name = name

            @property
            def name(self):
                return self._name

            @property
            def description(self):
                return "Test"

            def _execute_impl(self, input_text: str):
                return "result"

        tools = [TestTool(f"tool{i}") for i in range(3)]
        for tool in tools:
            registry.register(tool)

        all_tools = registry.get_all_tools()
        assert len(all_tools) == 3
        assert set(all_tools.keys()) == {"tool0", "tool1", "tool2"}

    def test_get_tool_descriptions(self):
        """测试获取工具描述"""
        registry = ToolRegistry()

        class TestTool(BaseTool):
            def __init__(self, name, desc):
                self._name = name
                self._desc = desc

            @property
            def name(self):
                return self._name

            @property
            def description(self):
                return self._desc

            def _execute_impl(self, input_text: str):
                return "result"

        registry.register(TestTool("tool1", "Description 1"))
        registry.register(TestTool("tool2", "Description 2"))

        descriptions = registry.get_tool_descriptions()
        assert len(descriptions) == 2
        assert {"name": "tool1", "description": "Description 1"} in descriptions
        assert {"name": "tool2", "description": "Description 2"} in descriptions

    def test_clear_tools(self):
        """测试清空工具"""
        registry = ToolRegistry()

        class TestTool(BaseTool):
            @property
            def name(self):
                return "test"

            @property
            def description(self):
                return "Test"

            def _execute_impl(self, input_text: str):
                return "result"

        registry.register(TestTool())
        assert len(registry) == 1

        registry.clear()
        assert len(registry) == 0


if __name__ == "__main__":
    # 运行测试
    import pytest
    pytest.main([__file__, "-v"])