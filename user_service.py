import re
from datetime import datetime
from typing import Any

from werkzeug.security import check_password_hash, generate_password_hash

from redis_client import redis_client


USER_IDS_KEY = "user:ids"
USER_DETAIL_KEY_PREFIX = "user:detail:"
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def _user_detail_key(username: str) -> str:
    return f"{USER_DETAIL_KEY_PREFIX}{username}"


def _safe_user(data: dict[str, Any]) -> dict[str, Any]:
    """返回用户公开信息，避免暴露 password_hash。"""
    user = dict(data)
    user.pop("password_hash", None)
    return user


def validate_username(username: str) -> str:
    """校验并标准化用户名。"""
    username = str(username or "").strip()
    if not username:
        raise ValueError("用户名不能为空")
    if not 3 <= len(username) <= 32:
        raise ValueError("用户名长度必须为 3 到 32 位")
    if not USERNAME_PATTERN.match(username):
        raise ValueError("用户名只能包含英文字母、数字、下划线和中划线")
    return username


def validate_password(password: str) -> str:
    """校验注册密码。"""
    password = str(password or "")
    if not password:
        raise ValueError("密码不能为空")
    if len(password) < 6:
        raise ValueError("密码长度至少 6 位")
    return password


def register_user(data: dict[str, Any]) -> dict[str, Any]:
    """注册用户，写入 Redis Set 和 Hash，返回安全用户信息。"""
    username = validate_username(data.get("username", ""))
    password = validate_password(data.get("password", ""))

    if redis_client.sismember(USER_IDS_KEY, username):
        raise ValueError("用户名已存在")

    nickname = str(data.get("nickname") or username).strip() or username
    email = str(data.get("email") or "").strip()
    user = {
        "username": username,
        "password_hash": generate_password_hash(password),
        "nickname": nickname,
        "email": email,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    pipe = redis_client.pipeline()
    pipe.sadd(USER_IDS_KEY, username)
    pipe.hset(_user_detail_key(username), mapping=user)
    pipe.execute()

    return _safe_user(user)


def get_user(username: str) -> dict[str, Any] | None:
    """查询单个用户公开信息。"""
    username = str(username or "").strip()
    if not username:
        return None

    data = redis_client.hgetall(_user_detail_key(username))
    if not data:
        return None
    return _safe_user(data)


def verify_user_password(username: str, password: str) -> dict[str, Any] | None:
    """校验用户登录密码，成功时返回不含 password_hash 的安全用户信息。"""
    username = str(username or "").strip()
    password = str(password or "")
    if not username or not password:
        return None

    data = redis_client.hgetall(_user_detail_key(username))
    if not data:
        return None

    password_hash = data.get("password_hash")
    if not password_hash or not check_password_hash(password_hash, password):
        return None

    return _safe_user(data)


def list_users() -> list[dict[str, Any]]:
    """查询全部用户公开信息，按用户名排序。"""
    usernames = sorted(redis_client.smembers(USER_IDS_KEY))
    users = []
    for username in usernames:
        user = get_user(username)
        if user:
            users.append(user)
    return users


def delete_test_user(username: str) -> None:
    """删除指定测试用户，仅供自动化测试清理使用，不暴露为 API。"""
    username = str(username or "").strip()
    if not username:
        return

    pipe = redis_client.pipeline()
    pipe.srem(USER_IDS_KEY, username)
    pipe.delete(_user_detail_key(username))
    pipe.execute()