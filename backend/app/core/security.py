"""
SQL安全校验模块
"""
import re
from typing import Tuple, List


# 危险SQL关键词
DANGEROUS_KEYWORDS: List[str] = [
    r'\bDROP\b',
    r'\bDELETE\b',
    r'\bTRUNCATE\b',
    r'\bALTER\b',
    r'\bCREATE\b',
    r'\bGRANT\b',
    r'\bREVOKE\b',
    r'\bINSERT\b',  # 可根据需求调整
    r'\bUPDATE\b',  # 可根据需求调整
    r'\bEXEC\b',
    r'\bEXECUTE\b',
    r'\bXP_',
]

# 只允许的SQL类型
ALLOWED_SQL_TYPES: List[str] = ['SELECT']


def validate_sql(sql: str) -> Tuple[bool, str]:
    """
    校验SQL安全性

    Returns:
        (is_safe, error_message)
    """
    sql_upper = sql.upper()

    # 检查是否只包含SELECT
    if not sql_upper.strip().startswith('SELECT'):
        return False, "只允许 SELECT 查询语句"

    # 检查危险关键词
    for pattern in DANGEROUS_KEYWORDS:
        if re.search(pattern, sql_upper, re.IGNORECASE):
            # 特殊处理：SELECT 中可能包含带引号的危险词
            if "'" in sql or '"' in sql:
                # 如果有引号，可能是LIKE查询等，跳过这个检查
                pass
            else:
                return False, f"检测到危险SQL关键词: {pattern}"

    # 检查是否有注释
    if '--' in sql or '/*' in sql:
        return False, "不允许SQL注释"

    # 检查多语句
    if ';' in sql.rstrip():
        statements = [s.strip() for s in sql.split(';') if s.strip()]
        if len(statements) > 1:
            return False, "不允许多条SQL语句"

    return True, ""


def sanitize_table_name(name: str) -> bool:
    """
    校验表名是否安全

    Args:
        name: 表名

    Returns:
        是否安全
    """
    # 只允许字母、数字、下划线
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name))
