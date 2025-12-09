"""
鲁棒性工具库 - 提升代码可靠性和稳定性
包含验证、错误处理、日志记录、重试机制、数据清理等功能
"""

import os
import sys
import json
import logging
import traceback
import time
import shutil
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
from functools import wraps
import threading
import queue


# ==================== 日志系统 ====================
class RobustLogger:
    """增强的日志系统，支持文件和控制台输出"""
    
    def __init__(self, log_dir: str = "./logs", log_name: str = "robust_log"):
        """
        初始化日志系统
        
        Args:
            log_dir: 日志目录
            log_name: 日志文件名前缀
        """
        self.log_dir = log_dir
        self.log_name = log_name
        self._ensure_dir(log_dir)
        self.logger = self._setup_logger()
        
    def _ensure_dir(self, directory: str) -> bool:
        """确保目录存在"""
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"无法创建日志目录: {e}")
            return False
            
    def _setup_logger(self) -> logging.Logger:
        """设置日志处理器"""
        logger = logging.getLogger(self.log_name)
        logger.setLevel(logging.DEBUG)
        
        # 日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 文件处理器
        log_file = os.path.join(
            self.log_dir,
            f"{self.log_name}_{datetime.now():%Y%m%d}.log"
        )
        try:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"无法创建文件处理器: {e}")
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def debug(self, msg: str, **kwargs):
        """记录调试信息"""
        self.logger.debug(msg, **kwargs)
    
    def info(self, msg: str, **kwargs):
        """记录信息"""
        self.logger.info(msg, **kwargs)
    
    def warning(self, msg: str, **kwargs):
        """记录警告"""
        self.logger.warning(msg, **kwargs)
    
    def error(self, msg: str, **kwargs):
        """记录错误"""
        self.logger.error(msg, **kwargs)
    
    def critical(self, msg: str, **kwargs):
        """记录严重错误"""
        self.logger.critical(msg, **kwargs)


# ==================== 重试装饰器 ====================
def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, 
          exceptions: Tuple = (Exception,)) -> Callable:
    """
    重试装饰器 - 在失败时自动重试
    
    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟时间（秒）
        backoff: 退避倍数（每次失败延迟 * backoff）
        exceptions: 捕获的异常类型
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = RobustLogger()
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    logger.debug(f"尝试执行 {func.__name__}，第 {attempt + 1}/{max_attempts} 次")
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger.warning(
                        f"{func.__name__} 执行失败，原因: {str(e)}, "
                        f"将在 {current_delay}s 后重试"
                    )
                    if attempt < max_attempts - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"{func.__name__} 在 {max_attempts} 次尝试后仍失败")
            
            raise last_exception or Exception(f"Failed after {max_attempts} attempts")
        
        return wrapper
    return decorator


# ==================== 路径验证和清理 ====================
class PathValidator:
    """路径验证和管理工具"""
    
    @staticmethod
    def validate_path(path: str, must_exist: bool = False, 
                     create: bool = False) -> bool:
        """
        验证路径的合法性和存在性
        
        Args:
            path: 路径字符串
            must_exist: 路径是否必须存在
            create: 路径不存在时是否创建
            
        Returns:
            路径是否有效
        """
        try:
            path_obj = Path(path)
            
            # 检查路径字符合法性
            if not path:
                return False
            
            # 路径必须存在的检查
            if must_exist and not path_obj.exists():
                if create:
                    path_obj.mkdir(parents=True, exist_ok=True)
                    return True
                return False
            
            return True
            
        except (ValueError, OSError, TypeError) as e:
            return False
    
    @staticmethod
    def safe_path_join(*parts: str) -> str:
        """
        安全的路径连接
        
        Args:
            *parts: 路径片段
            
        Returns:
            连接后的路径
        """
        try:
            result = os.path.join(*parts)
            # 规范化路径
            return os.path.normpath(result)
        except Exception:
            return ""
    
    @staticmethod
    def ensure_directory(path: str, max_retries: int = 3) -> bool:
        """
        确保目录存在，带重试机制
        
        Args:
            path: 目录路径
            max_retries: 最大重试次数
            
        Returns:
            是否成功
        """
        logger = RobustLogger()
        
        for attempt in range(max_retries):
            try:
                Path(path).mkdir(parents=True, exist_ok=True)
                logger.debug(f"目录已确保: {path}")
                return True
            except Exception as e:
                logger.warning(f"创建目录 {path} 失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                time.sleep(0.5)
        
        logger.error(f"无法创建目录: {path}")
        return False


# ==================== 文件操作工具 ====================
class FileOperationHelper:
    """文件操作的鲁棒性辅助工具"""
    
    @staticmethod
    @retry(max_attempts=3, delay=0.5)
    def safe_read_file(filepath: str, encoding: str = 'utf-8', 
                      default: str = '') -> str:
        """
        安全读取文件内容
        
        Args:
            filepath: 文件路径
            encoding: 文件编码
            default: 读取失败时的默认值
            
        Returns:
            文件内容或默认值
        """
        logger = RobustLogger()
        
        try:
            if not Path(filepath).exists():
                logger.warning(f"文件不存在: {filepath}")
                return default
            
            with open(filepath, 'r', encoding=encoding) as f:
                content = f.read()
            
            logger.debug(f"成功读取文件: {filepath}")
            return content
            
        except UnicodeDecodeError:
            logger.warning(f"文件编码错误: {filepath}，尝试使用其他编码")
            try:
                with open(filepath, 'r', encoding='gbk') as f:
                    return f.read()
            except Exception:
                return default
        except Exception as e:
            logger.error(f"读取文件失败: {filepath}, 原因: {e}")
            return default
    
    @staticmethod
    @retry(max_attempts=3, delay=0.5)
    def safe_write_file(filepath: str, content: str, encoding: str = 'utf-8',
                       backup: bool = True) -> bool:
        """
        安全写入文件内容
        
        Args:
            filepath: 文件路径
            content: 文件内容
            encoding: 文件编码
            backup: 覆盖前是否备份
            
        Returns:
            是否成功
        """
        logger = RobustLogger()
        
        try:
            # 确保目录存在
            PathValidator.ensure_directory(os.path.dirname(filepath))
            
            # 备份原文件
            if backup and Path(filepath).exists():
                backup_path = f"{filepath}.bak"
                try:
                    shutil.copy2(filepath, backup_path)
                    logger.debug(f"已备份文件: {backup_path}")
                except Exception as e:
                    logger.warning(f"备份失败: {e}")
            
            # 写入新内容
            with open(filepath, 'w', encoding=encoding) as f:
                f.write(content)
            
            logger.debug(f"成功写入文件: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"写入文件失败: {filepath}, 原因: {e}")
            return False
    
    @staticmethod
    def get_file_hash(filepath: str, algorithm: str = 'md5') -> Optional[str]:
        """
        计算文件哈希值
        
        Args:
            filepath: 文件路径
            algorithm: 哈希算法 ('md5', 'sha1', 'sha256')
            
        Returns:
            哈希值或 None
        """
        logger = RobustLogger()
        
        try:
            if not Path(filepath).exists():
                logger.warning(f"文件不存在: {filepath}")
                return None
            
            hash_obj = hashlib.new(algorithm)
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_obj.update(chunk)
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            logger.error(f"计算文件哈希失败: {filepath}, 原因: {e}")
            return None
    
    @staticmethod
    def safe_copy_file(src: str, dst: str, overwrite: bool = False) -> bool:
        """
        安全复制文件
        
        Args:
            src: 源文件路径
            dst: 目标文件路径
            overwrite: 目标文件存在时是否覆盖
            
        Returns:
            是否成功
        """
        logger = RobustLogger()
        
        try:
            if not Path(src).exists():
                logger.error(f"源文件不存在: {src}")
                return False
            
            if Path(dst).exists() and not overwrite:
                logger.warning(f"目标文件已存在，且 overwrite=False: {dst}")
                return False
            
            PathValidator.ensure_directory(os.path.dirname(dst))
            shutil.copy2(src, dst)
            logger.debug(f"成功复制文件: {src} -> {dst}")
            return True
            
        except Exception as e:
            logger.error(f"复制文件失败: {e}")
            return False
    
    @staticmethod
    def safe_remove_file(filepath: str, force: bool = False) -> bool:
        """
        安全删除文件
        
        Args:
            filepath: 文件路径
            force: 是否强制删除（忽略权限问题）
            
        Returns:
            是否成功
        """
        logger = RobustLogger()
        
        try:
            if not Path(filepath).exists():
                logger.warning(f"文件不存在，无需删除: {filepath}")
                return True
            
            os.remove(filepath)
            logger.debug(f"成功删除文件: {filepath}")
            return True
            
        except PermissionError:
            if force:
                try:
                    os.chmod(filepath, 0o777)
                    os.remove(filepath)
                    logger.debug(f"强制删除文件成功: {filepath}")
                    return True
                except Exception as e:
                    logger.error(f"强制删除失败: {filepath}, 原因: {e}")
                    return False
            else:
                logger.error(f"权限不足，无法删除: {filepath}")
                return False
        except Exception as e:
            logger.error(f"删除文件失败: {filepath}, 原因: {e}")
            return False


# ==================== JSON 操作工具 ====================
class JSONHelper:
    """JSON 文件的安全处理"""
    
    @staticmethod
    def safe_load_json(filepath: str, default: Optional[Dict] = None) -> Dict:
        """
        安全加载 JSON 文件
        
        Args:
            filepath: JSON 文件路径
            default: 加载失败时的默认值
            
        Returns:
            JSON 对象或默认值
        """
        logger = RobustLogger()
        default = default or {}
        
        try:
            content = FileOperationHelper.safe_read_file(filepath, default='{}')
            data = json.loads(content)
            
            if not isinstance(data, dict):
                logger.warning(f"JSON 数据不是字典类型: {filepath}")
                return default
            
            logger.debug(f"成功加载 JSON: {filepath}")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {filepath}, 原因: {e}")
            return default
        except Exception as e:
            logger.error(f"加载 JSON 失败: {filepath}, 原因: {e}")
            return default
    
    @staticmethod
    def safe_save_json(filepath: str, data: Dict, pretty: bool = True,
                      backup: bool = True) -> bool:
        """
        安全保存 JSON 文件
        
        Args:
            filepath: JSON 文件路径
            data: 数据字典
            pretty: 是否格式化输出
            backup: 覆盖前是否备份
            
        Returns:
            是否成功
        """
        logger = RobustLogger()
        
        try:
            # 验证数据
            if not isinstance(data, dict):
                logger.error(f"数据不是字典类型: {type(data)}")
                return False
            
            # 尝试序列化，检查是否有不可序列化的对象
            json.dumps(data)
            
            # 保存文件
            indent = 2 if pretty else None
            content = json.dumps(data, ensure_ascii=False, indent=indent)
            
            return FileOperationHelper.safe_write_file(
                filepath, content, backup=backup
            )
            
        except TypeError as e:
            logger.error(f"JSON 序列化失败: {e}")
            return False
        except Exception as e:
            logger.error(f"保存 JSON 失败: {filepath}, 原因: {e}")
            return False
    
    @staticmethod
    def validate_json_structure(data: Dict, schema: Dict) -> bool:
        """
        验证 JSON 数据结构
        
        Args:
            data: 要验证的数据
            schema: 验证模式字典
            
        Returns:
            是否符合结构
        """
        logger = RobustLogger()
        
        try:
            for key, expected_type in schema.items():
                if key not in data:
                    logger.warning(f"缺少必需字段: {key}")
                    return False
                
                if not isinstance(data[key], expected_type):
                    logger.warning(
                        f"字段类型不匹配: {key}, "
                        f"期望 {expected_type}, 实际 {type(data[key])}"
                    )
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证 JSON 结构失败: {e}")
            return False


# ==================== 数据验证工具 ====================
class DataValidator:
    """数据验证和清理"""
    
    @staticmethod
    def is_empty(value: Any) -> bool:
        """检查值是否为空"""
        if value is None:
            return True
        if isinstance(value, (str, list, dict)):
            return len(value) == 0
        return False
    
    @staticmethod
    def clean_string(text: str, strip: bool = True, 
                    remove_empty_lines: bool = False) -> str:
        """
        清理字符串
        
        Args:
            text: 输入文本
            strip: 是否去除前后空格
            remove_empty_lines: 是否移除空行
            
        Returns:
            清理后的文本
        """
        if not isinstance(text, str):
            return ""
        
        if strip:
            text = text.strip()
        
        if remove_empty_lines:
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            text = '\n'.join(lines)
        
        return text
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """验证电子邮件格式"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """验证电话号码格式（中国）"""
        import re
        # 简单的中国电话号码验证
        pattern = r'^1[3-9]\d{9}$'
        return bool(re.match(pattern, phone))
    
    @staticmethod
    def limit_string_length(text: str, max_length: int, 
                           suffix: str = '...') -> str:
        """
        限制字符串长度
        
        Args:
            text: 文本
            max_length: 最大长度
            suffix: 截断后缀
            
        Returns:
            截断后的文本
        """
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix


# ==================== 目录操作工具 ====================
class DirectoryHelper:
    """目录操作的鲁棒性工具"""
    
    @staticmethod
    def safe_clean_directory(directory: str, keep_dirs: Optional[List] = None,
                            keep_files: Optional[List] = None) -> bool:
        """
        安全清理目录（保留指定文件/文件夹）
        
        Args:
            directory: 目录路径
            keep_dirs: 保留的子目录列表
            keep_files: 保留的文件列表
            
        Returns:
            是否成功
        """
        logger = RobustLogger()
        keep_dirs = keep_dirs or []
        keep_files = keep_files or []
        
        try:
            if not Path(directory).exists():
                logger.warning(f"目录不存在: {directory}")
                return True
            
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                
                # 检查是否应该保留
                if item in keep_dirs or item in keep_files:
                    logger.debug(f"保留项目: {item}")
                    continue
                
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                    logger.debug(f"已删除: {item_path}")
                except Exception as e:
                    logger.warning(f"删除失败: {item_path}, 原因: {e}")
            
            logger.debug(f"成功清理目录: {directory}")
            return True
            
        except Exception as e:
            logger.error(f"清理目录失败: {directory}, 原因: {e}")
            return False
    
    @staticmethod
    def get_directory_size(directory: str) -> int:
        """
        获取目录大小（字节）
        
        Args:
            directory: 目录路径
            
        Returns:
            目录大小（字节）
        """
        logger = RobustLogger()
        total_size = 0
        
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except Exception:
                        pass
            
            return total_size
            
        except Exception as e:
            logger.error(f"计算目录大小失败: {directory}, 原因: {e}")
            return 0
    
    @staticmethod
    def list_files(directory: str, pattern: Optional[str] = None,
                  recursive: bool = False) -> List[str]:
        """
        列出目录中的文件
        
        Args:
            directory: 目录路径
            pattern: 文件名模式（glob）
            recursive: 是否递归
            
        Returns:
            文件列表
        """
        logger = RobustLogger()
        files = []
        
        try:
            path_obj = Path(directory)
            
            if not path_obj.exists():
                logger.warning(f"目录不存在: {directory}")
                return files
            
            search_pattern = pattern or "*"
            
            if recursive:
                files = [str(f) for f in path_obj.rglob(search_pattern) 
                        if f.is_file()]
            else:
                files = [str(f) for f in path_obj.glob(search_pattern) 
                        if f.is_file()]
            
            logger.debug(f"找到 {len(files)} 个文件: {directory}")
            return files
            
        except Exception as e:
            logger.error(f"列出文件失败: {directory}, 原因: {e}")
            return files


# ==================== 执行环境检查 ====================
class EnvironmentChecker:
    """检查执行环境的各项条件"""
    
    @staticmethod
    def check_python_version(min_version: Tuple[int, ...] = (3, 6)) -> bool:
        """检查 Python 版本"""
        logger = RobustLogger()
        current = sys.version_info[:len(min_version)]
        
        if current >= min_version:
            logger.info(f"Python 版本: {sys.version.split()[0]} (满足最低要求)")
            return True
        else:
            logger.error(
                f"Python 版本过低: {sys.version.split()[0]}, "
                f"需要至少 {'.'.join(map(str, min_version))}"
            )
            return False
    
    @staticmethod
    def check_disk_space(directory: str, min_free_mb: int = 100) -> bool:
        """检查磁盘空间"""
        logger = RobustLogger()
        
        try:
            import shutil
            stat = shutil.disk_usage(directory)
            free_mb = stat.free / (1024 * 1024)
            
            if free_mb >= min_free_mb:
                logger.info(f"磁盘空间充足: {free_mb:.2f} MB")
                return True
            else:
                logger.warning(f"磁盘空间不足: {free_mb:.2f} MB (需要 {min_free_mb} MB)")
                return False
                
        except Exception as e:
            logger.error(f"检查磁盘空间失败: {e}")
            return False
    
    @staticmethod
    def check_module_availability(*module_names: str) -> Dict[str, bool]:
        """检查模块是否可用"""
        logger = RobustLogger()
        availability = {}
        
        for module_name in module_names:
            try:
                __import__(module_name)
                availability[module_name] = True
                logger.debug(f"模块可用: {module_name}")
            except ImportError:
                availability[module_name] = False
                logger.warning(f"模块不可用: {module_name}")
        
        return availability
    
    @staticmethod
    def check_file_permissions(filepath: str, need_read: bool = False,
                             need_write: bool = False) -> bool:
        """检查文件权限"""
        logger = RobustLogger()
        
        try:
            path_obj = Path(filepath)
            
            if not path_obj.exists():
                logger.warning(f"文件不存在: {filepath}")
                return False
            
            if need_read and not os.access(filepath, os.R_OK):
                logger.error(f"没有读权限: {filepath}")
                return False
            
            if need_write and not os.access(filepath, os.W_OK):
                logger.error(f"没有写权限: {filepath}")
                return False
            
            logger.debug(f"文件权限检查通过: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"检查文件权限失败: {e}")
            return False


# ==================== 异常处理工具 ====================
class ExceptionHandler:
    """异常处理和错误报告"""
    
    @staticmethod
    def get_exception_details(exc: Exception) -> Dict[str, Any]:
        """获取异常的详细信息"""
        return {
            'type': type(exc).__name__,
            'message': str(exc),
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now(timezone(timedelta(hours=8))).isoformat()
        }
    
    @staticmethod
    def safe_execute(func: Callable, *args, logger: Optional[RobustLogger] = None,
                    **kwargs) -> Tuple[bool, Any, Optional[Exception]]:
        """
        安全执行函数
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            logger: 日志记录器
            **kwargs: 关键字参数
            
        Returns:
            (是否成功, 返回值/错误信息, 异常对象)
        """
        if logger is None:
            logger = RobustLogger()
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"成功执行函数: {func.__name__}")
            return True, result, None
        except Exception as e:
            details = ExceptionHandler.get_exception_details(e)
            logger.error(f"执行函数失败: {func.__name__}\n{details['traceback']}")
            return False, details, e


# ==================== 初始化检查 ====================
def run_startup_checks(data_dirs: Dict[str, str]) -> bool:
    """
    启动时的综合检查
    
    Args:
        data_dirs: 数据目录字典
        
    Returns:
        所有检查是否通过
    """
    logger = RobustLogger()
    logger.info("=" * 50)
    logger.info("启动环境检查")
    logger.info("=" * 50)
    
    all_passed = True
    
    # 检查 Python 版本
    if not EnvironmentChecker.check_python_version((3, 6)):
        all_passed = False
    
    # 检查磁盘空间
    if not EnvironmentChecker.check_disk_space(".", min_free_mb=100):
        all_passed = False
    
    # 创建数据目录
    logger.info("创建数据目录...")
    for key, path in data_dirs.items():
        if PathValidator.ensure_directory(path):
            logger.info(f"✓ {key}: {path}")
        else:
            logger.error(f"✗ {key}: {path}")
            all_passed = False
    
    logger.info("=" * 50)
    if all_passed:
        logger.info("✓ 所有检查已通过")
    else:
        logger.warning("⚠ 部分检查未通过，请检查配置")
    logger.info("=" * 50)
    
    return all_passed


# ==================== 导出函数 ====================
__all__ = [
    'RobustLogger',
    'retry',
    'PathValidator',
    'FileOperationHelper',
    'JSONHelper',
    'DataValidator',
    'DirectoryHelper',
    'EnvironmentChecker',
    'ExceptionHandler',
    'run_startup_checks',
]
