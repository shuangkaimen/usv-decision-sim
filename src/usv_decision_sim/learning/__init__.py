"""学习模块的公共接口。"""

from .mlp import USV_ACTION_DIM, USV_STATE_DIM, UsvControlMlp

__all__ = ["USV_ACTION_DIM", "USV_STATE_DIM", "UsvControlMlp"]
