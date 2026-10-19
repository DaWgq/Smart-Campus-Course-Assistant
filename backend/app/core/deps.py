from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.entities import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if cred is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    username = decode_access_token(cred.credentials)
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期")
    user = db.scalar(select(User).where(User.username == username))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


def get_admin_user(me: User = Depends(get_current_user)) -> User:
    """管理员校验：仅 role=admin 可访问。"""
    if me.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return me


def resolve_access_user(db: Session, me: User, username: str | None) -> User:
    """按权限解析可访问的目标用户，防止越权（IDOR）。

    规则：
      - 未指定 username 或指定为自己  -> 返回本人
      - 指定他人 -> 仅管理员可访问，普通用户一律 403
    """
    target_name = (username or "").strip()
    if not target_name or target_name == me.username:
        return me
    if me.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"无权查看其他用户的课表（目标用户：{target_name}）",
        )
    user = db.scalar(select(User).where(User.username == target_name))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"用户 {target_name} 不存在")
    return user
