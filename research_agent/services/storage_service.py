"""
存储服务

提供数据持久化存储服务。
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from loguru import logger


class StorageService:
    """
    存储服务
    
    提供数据持久化存储服务。
    
    Features:
        - JSON文件存储
        - 数据读写
        - 数据备份
        - 数据恢复
        - 数据导出
    """
    
    def __init__(
        self,
        storage_dir: str = "data",
        auto_save: bool = True,
        backup_enabled: bool = True,
    ):
        """
        初始化存储服务
        
        Args:
            storage_dir: 存储目录
            auto_save: 是否自动保存
            backup_enabled: 是否启用备份
        """
        self.storage_dir = storage_dir
        self.auto_save = auto_save
        self.backup_enabled = backup_enabled
        self._logger = logger.bind(module="StorageService")
        
        # 创建存储目录
        os.makedirs(storage_dir, exist_ok=True)
        
        # 内存缓存
        self._cache: Dict[str, Any] = {}
        
        # 统计
        self._total_reads = 0
        self._total_writes = 0
    
    def save(
        self,
        key: str,
        data: Any,
        backup: bool = True,
    ) -> bool:
        """
        保存数据
        
        Args:
            key: 数据键
            data: 数据
            backup: 是否备份
            
        Returns:
            bool: 是否成功
        """
        try:
            # 构建文件路径
            filepath = self._get_filepath(key)
            
            # 创建目录
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # 备份现有文件
            if backup and self.backup_enabled and os.path.exists(filepath):
                self._backup_file(filepath)
            
            # 保存数据
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            
            # 更新缓存
            self._cache[key] = data
            
            # 更新统计
            self._total_writes += 1
            
            self._logger.debug(f"Saved: {key}")
            
            return True
            
        except Exception as e:
            self._logger.error(f"Error saving {key}: {e}")
            return False
    
    def load(
        self,
        key: str,
        default: Any = None,
        use_cache: bool = True,
    ) -> Any:
        """
        加载数据
        
        Args:
            key: 数据键
            default: 默认值
            use_cache: 是否使用缓存
            
        Returns:
            Any: 数据
        """
        try:
            # 检查缓存
            if use_cache and key in self._cache:
                self._logger.debug(f"Cache hit: {key}")
                return self._cache[key]
            
            # 构建文件路径
            filepath = self._get_filepath(key)
            
            # 检查文件是否存在
            if not os.path.exists(filepath):
                self._logger.debug(f"File not found: {key}")
                return default
            
            # 加载数据
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 更新缓存
            self._cache[key] = data
            
            # 更新统计
            self._total_reads += 1
            
            self._logger.debug(f"Loaded: {key}")
            
            return data
            
        except Exception as e:
            self._logger.error(f"Error loading {key}: {e}")
            return default
    
    def delete(self, key: str) -> bool:
        """
        删除数据
        
        Args:
            key: 数据键
            
        Returns:
            bool: 是否成功
        """
        try:
            # 构建文件路径
            filepath = self._get_filepath(key)
            
            # 检查文件是否存在
            if not os.path.exists(filepath):
                self._logger.debug(f"File not found: {key}")
                return False
            
            # 备份文件
            if self.backup_enabled:
                self._backup_file(filepath)
            
            # 删除文件
            os.remove(filepath)
            
            # 从缓存中删除
            if key in self._cache:
                del self._cache[key]
            
            self._logger.debug(f"Deleted: {key}")
            
            return True
            
        except Exception as e:
            self._logger.error(f"Error deleting {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        检查数据是否存在
        
        Args:
            key: 数据键
            
        Returns:
            bool: 是否存在
        """
        # 检查缓存
        if key in self._cache:
            return True
        
        # 检查文件
        filepath = self._get_filepath(key)
        return os.path.exists(filepath)
    
    def list_keys(self, prefix: str = "") -> List[str]:
        """
        列出所有键
        
        Args:
            prefix: 键前缀
            
        Returns:
            List[str]: 键列表
        """
        keys = []
        
        # 遍历存储目录
        for root, dirs, files in os.walk(self.storage_dir):
            for file in files:
                if file.endswith('.json'):
                    # 构建键
                    rel_path = os.path.relpath(os.path.join(root, file), self.storage_dir)
                    key = rel_path.replace('.json', '').replace(os.sep, '/')
                    
                    # 过滤前缀
                    if not prefix or key.startswith(prefix):
                        keys.append(key)
        
        return sorted(keys)
    
    def _get_filepath(self, key: str) -> str:
        """
        获取文件路径
        
        Args:
            key: 数据键
            
        Returns:
            str: 文件路径
        """
        # 将键转换为文件路径
        # 将 / 替换为 os.sep
        path_parts = key.replace('/', os.sep).split(os.sep)
        
        # 构建完整路径
        filepath = os.path.join(self.storage_dir, *path_parts)
        
        # 确保以.json结尾
        if not filepath.endswith('.json'):
            filepath += '.json'
        
        return filepath
    
    def _backup_file(self, filepath: str) -> None:
        """
        备份文件
        
        Args:
            filepath: 文件路径
        """
        try:
            # 生成备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(self.storage_dir, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            
            filename = os.path.basename(filepath)
            backup_filename = f"{filename}.{timestamp}.bak"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # 复制文件
            import shutil
            shutil.copy2(filepath, backup_path)
            
            self._logger.debug(f"Backup created: {backup_path}")
            
        except Exception as e:
            self._logger.error(f"Error creating backup: {e}")
    
    def restore_backup(self, key: str, backup_timestamp: str) -> bool:
        """
        恢复备份
        
        Args:
            key: 数据键
            backup_timestamp: 备份时间戳
            
        Returns:
            bool: 是否成功
        """
        try:
            # 构建备份文件路径
            filepath = self._get_filepath(key)
            filename = os.path.basename(filepath)
            backup_dir = os.path.join(self.storage_dir, "backups")
            backup_path = os.path.join(backup_dir, f"{filename}.{backup_timestamp}.bak")
            
            # 检查备份是否存在
            if not os.path.exists(backup_path):
                self._logger.error(f"Backup not found: {backup_path}")
                return False
            
            # 恢复备份
            import shutil
            shutil.copy2(backup_path, filepath)
            
            # 清除缓存
            if key in self._cache:
                del self._cache[key]
            
            self._logger.info(f"Backup restored: {key}")
            
            return True
            
        except Exception as e:
            self._logger.error(f"Error restoring backup: {e}")
            return False
    
    def list_backups(self, key: str) -> List[Dict[str, Any]]:
        """
        列出备份
        
        Args:
            key: 数据键
            
        Returns:
            List[Dict[str, Any]]: 备份列表
        """
        backups = []
        
        try:
            # 构建备份目录路径
            filepath = self._get_filepath(key)
            filename = os.path.basename(filepath)
            backup_dir = os.path.join(self.storage_dir, "backups")
            
            # 检查备份目录是否存在
            if not os.path.exists(backup_dir):
                return backups
            
            # 遍历备份文件
            for file in os.listdir(backup_dir):
                if file.startswith(filename) and file.endswith('.bak'):
                    # 提取时间戳
                    parts = file.split('.')
                    if len(parts) >= 3:
                        timestamp = parts[-2]
                        backup_path = os.path.join(backup_dir, file)
                        
                        backups.append({
                            "timestamp": timestamp,
                            "filepath": backup_path,
                            "size": os.path.getsize(backup_path),
                            "created_at": datetime.fromtimestamp(
                                os.path.getctime(backup_path)
                            ).isoformat(),
                        })
            
            # 按时间戳排序
            backups.sort(key=lambda x: x["timestamp"], reverse=True)
            
        except Exception as e:
            self._logger.error(f"Error listing backups: {e}")
        
        return backups
    
    def export_data(
        self,
        key: str,
        format: str = "json",
        filepath: Optional[str] = None,
    ) -> bool:
        """
        导出数据
        
        Args:
            key: 数据键
            format: 导出格式
            filepath: 导出文件路径
            
        Returns:
            bool: 是否成功
        """
        try:
            # 加载数据
            data = self.load(key)
            if data is None:
                self._logger.error(f"Data not found: {key}")
                return False
            
            # 构建导出文件路径
            if filepath is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                export_dir = os.path.join(self.storage_dir, "exports")
                os.makedirs(export_dir, exist_ok=True)
                filepath = os.path.join(export_dir, f"{key}_{timestamp}.{format}")
            
            # 导出数据
            if format == "json":
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            elif format == "csv":
                import csv
                if isinstance(data, list) and len(data) > 0:
                    with open(filepath, 'w', encoding='utf-8', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=data[0].keys())
                        writer.writeheader()
                        writer.writerows(data)
            else:
                self._logger.error(f"Unsupported format: {format}")
                return False
            
            self._logger.info(f"Data exported: {filepath}")
            
            return True
            
        except Exception as e:
            self._logger.error(f"Error exporting data: {e}")
            return False
    
    def import_data(
        self,
        filepath: str,
        key: str,
        format: str = "json",
    ) -> bool:
        """
        导入数据
        
        Args:
            filepath: 导入文件路径
            key: 数据键
            format: 导入格式
            
        Returns:
            bool: 是否成功
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(filepath):
                self._logger.error(f"File not found: {filepath}")
                return False
            
            # 导入数据
            if format == "json":
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            elif format == "csv":
                import csv
                with open(filepath, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    data = list(reader)
            else:
                self._logger.error(f"Unsupported format: {format}")
                return False
            
            # 保存数据
            self.save(key, data)
            
            self._logger.info(f"Data imported: {key}")
            
            return True
            
        except Exception as e:
            self._logger.error(f"Error importing data: {e}")
            return False
    
    def clear_cache(self) -> None:
        """清除缓存"""
        self._cache.clear()
        self._logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "total_reads": self._total_reads,
            "total_writes": self._total_writes,
            "cache_size": len(self._cache),
            "storage_dir": self.storage_dir,
            "auto_save": self.auto_save,
            "backup_enabled": self.backup_enabled,
        }
    
    def get_storage_size(self) -> Dict[str, Any]:
        """
        获取存储大小
        
        Returns:
            Dict[str, Any]: 存储大小信息
        """
        total_size = 0
        file_count = 0
        
        for root, dirs, files in os.walk(self.storage_dir):
            for file in files:
                filepath = os.path.join(root, file)
                total_size += os.path.getsize(filepath)
                file_count += 1
        
        return {
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_count": file_count,
        }