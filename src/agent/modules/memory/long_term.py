"""
长期记忆模块

使用向量数据库（ChromaDB）实现长期记忆存储和检索。
支持基于语义相似度的记忆检索。
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    print("警告: ChromaDB 未安装，长期记忆功能将不可用")


class LongTermMemoryEntry(BaseModel):
    """长期记忆条目"""
    id: str = Field(description="记忆ID")
    content: str = Field(description="记忆内容")
    embedding: Optional[List[float]] = Field(default=None, description="向量嵌入")
    timestamp: datetime = Field(default_factory=datetime.now, description="记忆时间")
    importance: float = Field(default=0.5, description="重要性评分 (0-1)")
    category: str = Field(default="general", description="记忆类别")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    access_count: int = Field(default=0, description="访问次数")


class LongTermMemory:
    """长期记忆管理器"""

    def __init__(self, persist_path: str = "./data/memory", collection_name: str = "agent_memories",
                 embedding_model: str = "all-MiniLM-L6-v2"):
        """
        初始化长期记忆管理器

        Args:
            persist_path: 持久化路径
            collection_name: 集合名称
            embedding_model: 嵌入模型名称
        """
        self.persist_path = Path(persist_path)
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.client = None
        self.collection = None
        self._initialized = False

        # 创建持久化目录
        self.persist_path.mkdir(parents=True, exist_ok=True)

        self._initialize()

    def _initialize(self) -> None:
        """初始化ChromaDB客户端和集合"""
        if not CHROMA_AVAILABLE:
            print("警告: ChromaDB 未安装，长期记忆功能不可用")
            return

        try:
            # 初始化ChromaDB客户端
            self.client = chromadb.PersistentClient(
                path=str(self.persist_path),
                settings=Settings(anonymized_telemetry=False)
            )

            # 获取或创建集合
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Agent长期记忆存储"}
            )

            self._initialized = True
            print(f"长期记忆初始化完成，路径: {self.persist_path}")
        except Exception as e:
            print(f"长期记忆初始化失败: {e}")
            self._initialized = False

    def is_available(self) -> bool:
        """检查长期记忆是否可用"""
        return self._initialized and CHROMA_AVAILABLE

    def store_memory(self, content: str, importance: float = 0.5,
                     category: str = "general", metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        存储长期记忆

        Args:
            content: 记忆内容
            importance: 重要性评分 (0-1)
            category: 记忆类别
            metadata: 元数据

        Returns:
            记忆ID
        """
        if not self.is_available():
            return "长期记忆不可用"

        if metadata is None:
            metadata = {}

        # 生成唯一ID
        import uuid
        memory_id = str(uuid.uuid4())

        # 创建记忆条目
        memory = LongTermMemoryEntry(
            id=memory_id,
            content=content,
            importance=importance,
            category=category,
            metadata=metadata
        )

        try:
            # 存储到向量数据库
            self.collection.add(
                documents=[content],
                metadatas=[{
                    "id": memory_id,
                    "importance": importance,
                    "category": category,
                    "timestamp": memory.timestamp.isoformat(),
                    "access_count": 0,
                    **metadata
                }],
                ids=[memory_id]
            )

            # 同时存储到JSON文件作为备份
            self._save_to_json(memory)

            return memory_id
        except Exception as e:
            print(f"存储长期记忆失败: {e}")
            return f"存储失败: {e}"

    def retrieve_memories(self, query: str, n_results: int = 5,
                          category_filter: Optional[str] = None) -> List[LongTermMemoryEntry]:
        """
        检索相关记忆

        Args:
            query: 查询文本
            n_results: 返回结果数量
            category_filter: 类别过滤器

        Returns:
            相关记忆列表
        """
        if not self.is_available():
            return []

        try:
            # 构建查询条件
            where = None
            if category_filter:
                where = {"category": category_filter}

            # 查询向量数据库
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"]
            )

            memories = []
            if results["ids"] and results["ids"][0]:
                for i, memory_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i]
                    document = results["documents"][0][i]
                    # distance = results["distances"][0][i]  # 距离信息暂未使用

                    # 更新访问计数
                    access_count = metadata.get("access_count", 0) + 1
                    self.collection.update(
                        ids=[memory_id],
                        metadatas=[{**metadata, "access_count": access_count}]
                    )

                    # 创建记忆条目
                    memory = LongTermMemoryEntry(
                        id=memory_id,
                        content=document,
                        importance=metadata.get("importance", 0.5),
                        category=metadata.get("category", "general"),
                        metadata={k: v for k, v in metadata.items()
                                 if k not in ["id", "importance", "category", "timestamp", "access_count"]},
                        access_count=access_count
                    )

                    # 解析时间戳
                    if "timestamp" in metadata:
                        try:
                            memory.timestamp = datetime.fromisoformat(metadata["timestamp"])
                        except (ValueError, TypeError):
                            pass

                    memories.append(memory)

            return memories
        except Exception as e:
            print(f"检索长期记忆失败: {e}")
            return []

    def get_memory_by_id(self, memory_id: str) -> Optional[LongTermMemoryEntry]:
        """
        根据ID获取记忆

        Args:
            memory_id: 记忆ID

        Returns:
            记忆条目，如果不存在则返回None
        """
        if not self.is_available():
            return None

        try:
            results = self.collection.get(ids=[memory_id])
            if not results["ids"]:
                return None

            metadata = results["metadatas"][0]
            document = results["documents"][0]

            memory = LongTermMemoryEntry(
                id=memory_id,
                content=document,
                importance=metadata.get("importance", 0.5),
                category=metadata.get("category", "general"),
                metadata={k: v for k, v in metadata.items()
                         if k not in ["id", "importance", "category", "timestamp", "access_count"]},
                access_count=metadata.get("access_count", 0)
            )

            # 解析时间戳
            if "timestamp" in metadata:
                try:
                    memory.timestamp = datetime.fromisoformat(metadata["timestamp"])
                except (ValueError, TypeError):
                    pass

            return memory
        except Exception as e:
            print(f"获取记忆失败: {e}")
            return None

    def update_memory(self, memory_id: str, content: Optional[str] = None,
                      importance: Optional[float] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        更新记忆

        Args:
            memory_id: 记忆ID
            content: 新的内容
            importance: 新的重要性评分
            metadata: 新的元数据

        Returns:
            是否成功
        """
        if not self.is_available():
            return False

        try:
            # 获取现有记忆
            existing = self.get_memory_by_id(memory_id)
            if not existing:
                return False

            # 准备更新数据
            update_content = content if content is not None else existing.content
            update_importance = importance if importance is not None else existing.importance
            update_metadata = {**existing.metadata, **(metadata or {})}

            # 更新向量数据库
            self.collection.update(
                ids=[memory_id],
                documents=[update_content],
                metadatas=[{
                    "id": memory_id,
                    "importance": update_importance,
                    "category": existing.category,
                    "timestamp": existing.timestamp.isoformat(),
                    "access_count": existing.access_count,
                    **update_metadata
                }]
            )

            # 更新JSON备份
            updated_memory = LongTermMemoryEntry(
                id=memory_id,
                content=update_content,
                importance=update_importance,
                category=existing.category,
                metadata=update_metadata,
                access_count=existing.access_count,
                timestamp=existing.timestamp
            )
            self._save_to_json(updated_memory)

            return True
        except Exception as e:
            print(f"更新记忆失败: {e}")
            return False

    def delete_memory(self, memory_id: str) -> bool:
        """
        删除记忆

        Args:
            memory_id: 记忆ID

        Returns:
            是否成功
        """
        if not self.is_available():
            return False

        try:
            self.collection.delete(ids=[memory_id])
            self._delete_json_backup(memory_id)
            return True
        except Exception as e:
            print(f"删除记忆失败: {e}")
            return False

    def get_all_memories(self, limit: int = 100, offset: int = 0) -> List[LongTermMemoryEntry]:
        """
        获取所有记忆

        Args:
            limit: 限制数量
            offset: 偏移量

        Returns:
            记忆列表
        """
        if not self.is_available():
            return []

        try:
            results = self.collection.get(limit=limit, offset=offset)
            memories = []

            for i, memory_id in enumerate(results["ids"]):
                metadata = results["metadatas"][i]
                document = results["documents"][i]

                memory = LongTermMemoryEntry(
                    id=memory_id,
                    content=document,
                    importance=metadata.get("importance", 0.5),
                    category=metadata.get("category", "general"),
                    metadata={k: v for k, v in metadata.items()
                             if k not in ["id", "importance", "category", "timestamp", "access_count"]},
                    access_count=metadata.get("access_count", 0)
                )

                # 解析时间戳
                if "timestamp" in metadata:
                    try:
                        memory.timestamp = datetime.fromisoformat(metadata["timestamp"])
                    except (ValueError, TypeError):
                        pass

                memories.append(memory)

            return memories
        except Exception as e:
            print(f"获取所有记忆失败: {e}")
            return []

    def search_by_metadata(self, metadata_filter: Dict[str, Any], limit: int = 10) -> List[LongTermMemoryEntry]:
        """
        根据元数据搜索记忆

        Args:
            metadata_filter: 元数据过滤器
            limit: 限制数量

        Returns:
            记忆列表
        """
        if not self.is_available():
            return []

        try:
            results = self.collection.get(
                where=metadata_filter,
                limit=limit
            )

            memories = []
            for i, memory_id in enumerate(results["ids"]):
                metadata = results["metadatas"][i]
                document = results["documents"][i]

                memory = LongTermMemoryEntry(
                    id=memory_id,
                    content=document,
                    importance=metadata.get("importance", 0.5),
                    category=metadata.get("category", "general"),
                    metadata={k: v for k, v in metadata.items()
                             if k not in ["id", "importance", "category", "timestamp", "access_count"]},
                    access_count=metadata.get("access_count", 0)
                )

                # 解析时间戳
                if "timestamp" in metadata:
                    try:
                        memory.timestamp = datetime.fromisoformat(metadata["timestamp"])
                    except (ValueError, TypeError):
                        pass

                memories.append(memory)

            return memories
        except Exception as e:
            print(f"元数据搜索失败: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计信息字典
        """
        if not self.is_available():
            return {"available": False, "error": "ChromaDB not available"}

        try:
            count = self.collection.count()
            return {
                "available": True,
                "total_memories": count,
                "persist_path": str(self.persist_path),
                "collection_name": self.collection_name
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    def clear_all(self) -> bool:
        """
        清空所有记忆

        Returns:
            是否成功
        """
        if not self.is_available():
            return False

        try:
            self.client.delete_collection(self.collection_name)
            self._initialized = False
            self._initialize()  # 重新初始化空集合
            return True
        except Exception as e:
            print(f"清空记忆失败: {e}")
            return False

    def _save_to_json(self, memory: LongTermMemoryEntry) -> None:
        """保存到JSON备份文件"""
        try:
            backup_dir = self.persist_path / "backup"
            backup_dir.mkdir(exist_ok=True)

            backup_file = backup_dir / f"{memory.id}.json"
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(memory.model_dump(), f, ensure_ascii=False, indent=2,
                         default=str)  # 使用default=str处理datetime
        except Exception as e:
            print(f"保存JSON备份失败: {e}")

    def _delete_json_backup(self, memory_id: str) -> None:
        """删除JSON备份文件"""
        try:
            backup_file = self.persist_path / "backup" / f"{memory_id}.json"
            if backup_file.exists():
                backup_file.unlink()
        except Exception as e:
            print(f"删除JSON备份失败: {e}")

    def __str__(self) -> str:
        """字符串表示"""
        stats = self.get_statistics()
        if stats.get("available", False):
            return f"LongTermMemory(memories={stats['total_memories']}, path={stats['persist_path']})"
        else:
            return "LongTermMemory(不可用)"


if __name__ == "__main__":
    # 测试长期记忆
    print("测试长期记忆模块...")

    if not CHROMA_AVAILABLE:
        print("ChromaDB 未安装，跳过测试")
        print("安装命令: pip install chromadb")
    else:
        # 创建测试记忆管理器
        memory = LongTermMemory(persist_path="./test_memory")

        if memory.is_available():
            # 存储一些记忆
            print("\n1. 存储记忆:")
            id1 = memory.store_memory(
                "用户喜欢Python编程",
                importance=0.8,
                category="user_preference",
                metadata={"source": "conversation", "topic": "programming"}
            )
            print(f"  存储记忆1: {id1}")

            id2 = memory.store_memory(
                "用户需要学习机器学习",
                importance=0.7,
                category="learning_goal",
                metadata={"priority": "high", "deadline": "2024-12-31"}
            )
            print(f"  存储记忆2: {id2}")

            id3 = memory.store_memory(
                "今天是晴天，适合户外活动",
                importance=0.3,
                category="context",
                metadata={"weather": "sunny", "temperature": "25°C"}
            )
            print(f"  存储记忆3: {id3}")

            # 检索记忆
            print("\n2. 检索记忆('编程'):")
            results = memory.retrieve_memories("编程", n_results=2)
            for i, mem in enumerate(results):
                print(f"  结果{i+1}: {mem.content} (重要性: {mem.importance})")

            # 按类别检索
            print("\n3. 按类别检索('user_preference'):")
            results = memory.retrieve_memories("", n_results=2, category_filter="user_preference")
            for i, mem in enumerate(results):
                print(f"  结果{i+1}: {mem.content}")

            # 获取所有记忆
            print("\n4. 获取所有记忆:")
            all_memories = memory.get_all_memories(limit=5)
            print(f"  总数: {len(all_memories)}")
            for mem in all_memories:
                print(f"  - {mem.category}: {mem.content[:50]}...")

            # 获取统计信息
            print("\n5. 统计信息:")
            stats = memory.get_statistics()
            for key, value in stats.items():
                print(f"  {key}: {value}")

            # 清理测试数据
            memory.clear_all()
            print("\n测试完成，已清理测试数据")
        else:
            print("长期记忆初始化失败")