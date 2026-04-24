"""pytest 配置文件"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 添加 tests/e2e 到 Python 路径
E2E_DIR = Path(__file__).parent / 'e2e'
sys.path.insert(0, str(E2E_DIR))


def pytest_configure(config):
    """pytest 配置"""
    # 确保输出目录存在
    (PROJECT_ROOT / 'output').mkdir(exist_ok=True)
    (PROJECT_ROOT / 'drafts').mkdir(exist_ok=True)
    (PROJECT_ROOT / 'tests' / 'e2e' / 'reports').mkdir(parents=True, exist_ok=True)
