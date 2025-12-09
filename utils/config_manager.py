"""
配置管理模块 - 处理所有的配置参数和设置
提供配置验证、默认值管理、配置持久化等功能
"""

import os
import json
from typing import Any, Dict, Optional, List
from pathlib import Path
from datetime import datetime


class ConfigManager:
    """统一的配置管理器"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        "max_upload_size_mb": 100,
        "max_file_count": 50,
        "max_retries": 3,
        "retry_delay_seconds": 1.0,
        "script_timeout_seconds": 3600,
        "log_retention_days": 30,
        "enable_backup": True,
        "enable_compression": True,
        "thread_pool_size": 4,
        "disk_space_warning_mb": 500,
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file or os.path.join(
            os.path.dirname(__file__), "..", "conf", "config.json"
        )
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()
    
    def load_config(self) -> bool:
        """
        从文件加载配置
        
        Returns:
            是否成功加载
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    # 合并文件配置和默认配置
                    self.config.update(file_config)
                return True
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return False
        return True
    
    def save_config(self) -> bool:
        """
        保存配置到文件
        
        Returns:
            是否成功保存
        """
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
        """
        self.config[key] = value
    
    def reset_to_defaults(self) -> None:
        """重置为默认配置"""
        self.config = self.DEFAULT_CONFIG.copy()
    
    def validate_config(self) -> List[str]:
        """
        验证配置的合法性
        
        Returns:
            验证错误列表
        """
        errors = []
        
        # 检查数值范围
        if self.get("max_upload_size_mb", 0) < 1:
            errors.append("max_upload_size_mb 必须 >= 1")
        
        if self.get("max_file_count", 0) < 1:
            errors.append("max_file_count 必须 >= 1")
        
        if self.get("max_retries", 0) < 1:
            errors.append("max_retries 必须 >= 1")
        
        if self.get("retry_delay_seconds", 0) < 0:
            errors.append("retry_delay_seconds 必须 >= 0")
        
        if self.get("script_timeout_seconds", 0) < 1:
            errors.append("script_timeout_seconds 必须 >= 1")
        
        if self.get("log_retention_days", 0) < 1:
            errors.append("log_retention_days 必须 >= 1")
        
        if self.get("thread_pool_size", 0) < 1:
            errors.append("thread_pool_size 必须 >= 1")
        
        return errors


class FeatureFlags:
    """特性开关管理"""
    
    DEFAULT_FLAGS = {
        "enable_robust_logging": True,
        "enable_auto_retry": True,
        "enable_file_backup": True,
        "enable_compression": True,
        "enable_parallel_processing": False,
        "enable_health_check": True,
        "enable_performance_monitoring": False,
    }
    
    def __init__(self):
        """初始化特性开关"""
        self.flags = self.DEFAULT_FLAGS.copy()
    
    def is_enabled(self, feature: str) -> bool:
        """
        检查特性是否启用
        
        Args:
            feature: 特性名称
            
        Returns:
            特性是否启用
        """
        return self.flags.get(feature, False)
    
    def enable(self, feature: str) -> None:
        """启用特性"""
        self.flags[feature] = True
    
    def disable(self, feature: str) -> None:
        """禁用特性"""
        self.flags[feature] = False
    
    def toggle(self, feature: str) -> None:
        """切换特性状态"""
        self.flags[feature] = not self.flags.get(feature, False)


class PerformanceConfig:
    """性能相关的配置"""
    
    def __init__(self):
        """初始化性能配置"""
        self.start_time = datetime.now()
        self.metrics = {
            "total_files_processed": 0,
            "total_bytes_processed": 0,
            "total_errors": 0,
            "average_processing_time": 0.0,
        }
    
    def record_file_processing(self, file_size: int, duration: float,
                              success: bool = True) -> None:
        """
        记录文件处理信息
        
        Args:
            file_size: 文件大小（字节）
            duration: 处理时间（秒）
            success: 是否成功
        """
        self.metrics["total_files_processed"] += 1
        self.metrics["total_bytes_processed"] += file_size
        
        if not success:
            self.metrics["total_errors"] += 1
        
        # 更新平均处理时间
        current_avg = self.metrics["average_processing_time"]
        total_processed = self.metrics["total_files_processed"]
        
        self.metrics["average_processing_time"] = (
            (current_avg * (total_processed - 1) + duration) / total_processed
        )
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        获取性能指标摘要
        
        Returns:
            性能指标字典
        """
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "elapsed_seconds": elapsed,
            "total_files": self.metrics["total_files_processed"],
            "total_bytes_mb": self.metrics["total_bytes_processed"] / (1024 * 1024),
            "total_errors": self.metrics["total_errors"],
            "average_file_time_ms": self.metrics["average_processing_time"] * 1000,
            "throughput_mbps": (
                self.metrics["total_bytes_processed"] / (1024 * 1024) / elapsed
                if elapsed > 0 else 0
            ),
        }


class SecurityConfig:
    """安全性相关的配置"""
    
    # 允许的文件扩展名
    ALLOWED_EXTENSIONS = {
        '.xlsx', '.xls', '.csv', '.json', '.txt', '.pdf', '.docx', '.doc'
    }
    
    # 禁止的文件名模式
    FORBIDDEN_PATTERNS = ['..', '~', '$', '\x00']
    
    @staticmethod
    def is_safe_filename(filename: str) -> bool:
        """
        检查文件名是否安全
        
        Args:
            filename: 文件名
            
        Returns:
            文件名是否安全
        """
        # 检查禁止的模式
        for pattern in SecurityConfig.FORBIDDEN_PATTERNS:
            if pattern in filename:
                return False
        
        # 检查长度
        if len(filename) > 255:
            return False
        
        return True
    
    @staticmethod
    def is_safe_extension(filename: str) -> bool:
        """
        检查文件扩展名是否被允许
        
        Args:
            filename: 文件名
            
        Returns:
            扩展名是否被允许
        """
        ext = os.path.splitext(filename)[1].lower()
        return ext in SecurityConfig.ALLOWED_EXTENSIONS
    
    @staticmethod
    def validate_file(filename: str, check_extension: bool = True) -> List[str]:
        """
        验证文件安全性
        
        Args:
            filename: 文件名
            check_extension: 是否检查扩展名
            
        Returns:
            验证错误列表
        """
        errors = []
        
        if not SecurityConfig.is_safe_filename(filename):
            errors.append(f"不安全的文件名: {filename}")
        
        if check_extension and not SecurityConfig.is_safe_extension(filename):
            errors.append(f"不支持的文件类型: {filename}")
        
        return errors


class DataDirConfig:
    """数据目录配置管理"""
    
    # 标准的数据目录结构
    STANDARD_DIRS = {
        "ori": "data_00_ori",
        "csv": "data_01_csv",
        "pdf": "data_02_pdf",
        "json": "data_03_json",
        "txt": "data_04_summary_txt",
        "final": "data_05_final_pdf",
        "temp": "temp",
        "logs": "logs",
        "conf": "conf",
    }
    
    def __init__(self, base_dir: str):
        """
        初始化数据目录配置
        
        Args:
            base_dir: 基础目录
        """
        self.base_dir = base_dir
        self.dirs = self._build_dirs()
    
    def _build_dirs(self) -> Dict[str, str]:
        """构建目录字典"""
        dirs = {}
        for key, dirname in self.STANDARD_DIRS.items():
            dirs[key] = os.path.join(self.base_dir, dirname)
        return dirs
    
    def get(self, key: str) -> Optional[str]:
        """获取目录路径"""
        return self.dirs.get(key)
    
    def get_all(self) -> Dict[str, str]:
        """获取所有目录"""
        return self.dirs.copy()
    
    def ensure_all_dirs(self) -> bool:
        """确保所有目录都存在"""
        try:
            for path in self.dirs.values():
                Path(path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"创建目录失败: {e}")
            return False


class CacheConfig:
    """缓存配置和管理"""
    
    def __init__(self, cache_dir: str, ttl_minutes: int = 60):
        """
        初始化缓存配置
        
        Args:
            cache_dir: 缓存目录
            ttl_minutes: 缓存过期时间（分钟）
        """
        self.cache_dir = cache_dir
        self.ttl_minutes = ttl_minutes
        self.cache = {}
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self.cache:
            value, timestamp = self.cache[key]
            elapsed = (datetime.now() - timestamp).total_seconds()
            if elapsed < self.ttl_minutes * 60:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        self.cache[key] = (value, datetime.now())
    
    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()


# ==================== 导出 ====================
__all__ = [
    'ConfigManager',
    'FeatureFlags',
    'PerformanceConfig',
    'SecurityConfig',
    'DataDirConfig',
    'CacheConfig',
]
