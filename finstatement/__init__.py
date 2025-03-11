# finstatement/__init__.py
from .parser import parse, batch_parse, StatementResult, AccountInfo, Period, Balance, Transaction

__version__ = "0.1.0"
__all__ = ["parse", "batch_parse", "StatementResult", "AccountInfo", "Period", "Balance", "Transaction"]
