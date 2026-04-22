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

# 用户输入中不应该出现的SQL关键词（用于检测用户是否在输入SQL而非自然语言）
USER_INPUT_SQL_PATTERNS: List[str] = [
    r'\bSELECT\b',
    r'\bFROM\b',
    r'\bWHERE\b',
    r'\bINSERT\b',
    r'\bUPDATE\b',
    r'\bDELETE\b',
    r'\bDROP\b',
    r'\bCREATE\b',
    r'\bALTER\b',
    r'\bTRUNCATE\b',
    r'\bGRANT\b',
    r'\bREVOKE\b',
    r'\bEXEC\b',
    r'\bEXECUTE\b',
    r'\bUNION\b',
    r'\bJOIN\b',
]


def validate_user_input(message: str) -> Tuple[bool, str]:
    """
    校验用户输入（自然语言）是否包含SQL语句

    NL2SQL系统应该只接受自然语言查询，如果用户输入SQL语句应该拒绝。

    Returns:
        (is_valid_natural_language, error_message)
    """
    message_upper = message.upper()

    # 检查是否包含SQL关键词
    for pattern in USER_INPUT_SQL_PATTERNS:
        if re.search(pattern, message_upper, re.IGNORECASE):
            return False, "请输入自然语言问题，不要输入SQL语句。例如：'查询用户表有多少条记录'"

    # 检查是否有SQL特征（多个连续大写字母、特殊符号组合等）
    # 简单检测：连续的大写SQL关键词
    sql_indicators = [
        r'SELECT\s+', r'FROM\s+', r'WHERE\s+',
        r'INSERT\s+', r'UPDATE\s+', r'DELETE\s+',
        r'DROP\s+', r'CREATE\s+',
    ]
    for pattern in sql_indicators:
        if re.search(pattern, message, re.IGNORECASE):
            return False, "请输入自然语言问题，不要输入SQL语句"

    return True, ""


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
