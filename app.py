import os
from datetime import datetime

from flask import Flask, jsonify, render_template, request, session

from landmark_service import (
    add_landmark,
    delete_landmark,
    export_landmarks,
    get_distance,
    get_landmark,
    get_landmark_stats,
    import_landmarks,
    list_landmarks,
    search_nearby,
    update_landmark,
)
from redis_client import redis_client
from seed_data import reset_seed_data
from user_service import (
    add_favorite_landmark,
    get_user,
    list_favorite_landmark_ids,
    list_users,
    register_user,
    remove_favorite_landmark,
    verify_user_password,
)


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-me")


def success(data=None, **extra):
    payload = {"success": True}
    if data is not None:
        payload["data"] = data
    payload.update(extra)
    return jsonify(payload)


def error(message: str, status_code: int = 400):
    return jsonify({"success": False, "message": message}), status_code


def current_username() -> str | None:
    return session.get("username")


def current_user() -> dict | None:
    username = current_username()
    if not username:
        return None
    user = get_user(username)
    if not user:
        session.pop("username", None)
        return None
    return user


def require_login() -> str | None:
    user = current_user()
    if not user:
        return None
    return user["username"]


def require_login_response():
    user = current_user()
    if not user:
        return None, error("请先登录后再操作", 401)
    return user, None


def require_admin_response():
    user, response = require_login_response()
    if response:
        return None, response
    if user.get("role") != "admin":
        return None, error("需要管理员权限", 403)
    return user, None


@app.get("/")
def index():
    return render_template(
        "index.html",
        amap_key=os.getenv("AMAP_KEY", ""),
        amap_security_code=os.getenv("AMAP_SECURITY_CODE", ""),
    )


@app.get("/api/health")
def health():
    try:
        redis_ok = bool(redis_client.ping())
    except Exception:
        redis_ok = False

    return success(status="ok" if redis_ok else "error", redis=redis_ok)


@app.post("/api/users/register")
def api_register_user():
    data = request.get_json(silent=True) or {}
    try:
        user = register_user(data)
    except ValueError as exc:
        return error(str(exc))
    except Exception as exc:
        return error(f"注册失败: {exc}", 500)

    return success(data=user, message="注册成功")


@app.post("/api/users/login")
def api_login_user():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username") or "").strip()
    password = str(data.get("password") or "")

    if not username:
        return error("用户名不能为空")
    if not password:
        return error("密码不能为空")

    user = verify_user_password(username, password)
    if not user:
        return error("用户名或密码错误", 401)

    session["username"] = user["username"]
    return success(data=user, message="登录成功")


@app.post("/api/users/logout")
def api_logout_user():
    session.pop("username", None)
    return success(message="已退出登录")


@app.get("/api/users/me")
def api_get_current_user():
    username = session.get("username")
    if not username:
        return jsonify({"success": True, "data": None, "logged_in": False})

    user = get_user(username)
    if not user:
        session.pop("username", None)
        return jsonify({"success": True, "data": None, "logged_in": False})

    return success(data=user, logged_in=True)


@app.get("/api/users/<username>")
def api_get_user(username):
    current, response = require_login_response()
    if response:
        return response
    if current["username"] != username and current.get("role") != "admin":
        return error("只能查看自己的用户信息", 403)

    user = get_user(username)
    if not user:
        return error("用户不存在", 404)
    return success(data=user)


@app.get("/api/users")
def api_list_users():
    _, response = require_admin_response()
    if response:
        return response

    users = list_users()
    return success(data=users, count=len(users))


@app.get("/api/stats")
def api_get_stats():
    try:
        redis_ok = bool(redis_client.ping())
    except Exception:
        redis_ok = False

    stats = get_landmark_stats()
    stats.update(
        user_count=len(list_users()),
        redis_ok=redis_ok,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    return success(data=stats)


@app.get("/api/users/me/favorites")
def api_list_my_favorites():
    username = require_login()
    if not username:
        return error("请先登录后再查看收藏", 401)

    favorite_ids = list_favorite_landmark_ids(username)
    landmarks = [get_landmark(landmark_id) for landmark_id in favorite_ids]
    landmarks = [landmark for landmark in landmarks if landmark]
    return success(data=landmarks, ids=favorite_ids, count=len(landmarks))


@app.post("/api/users/me/favorites/<landmark_id>")
def api_add_my_favorite(landmark_id):
    username = require_login()
    if not username:
        return error("请先登录后再收藏地标", 401)
    if not get_landmark(landmark_id):
        return error("地标不存在", 404)

    favorite_ids = add_favorite_landmark(username, landmark_id)
    return success(ids=favorite_ids, message="已加入收藏")


@app.delete("/api/users/me/favorites/<landmark_id>")
def api_remove_my_favorite(landmark_id):
    username = require_login()
    if not username:
        return error("请先登录后再取消收藏", 401)

    favorite_ids = remove_favorite_landmark(username, landmark_id)
    return success(ids=favorite_ids, message="已取消收藏")


@app.get("/api/landmarks")
def api_list_landmarks():
    landmarks = list_landmarks()
    return success(data=landmarks, count=len(landmarks))


@app.get("/api/landmarks/export")
def api_export_landmarks():
    landmarks = export_landmarks()
    return success(
        data=landmarks,
        count=len(landmarks),
        exported_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


@app.get("/api/landmarks/nearby")
def api_search_nearby():
    try:
        longitude = float(request.args.get("longitude", ""))
        latitude = float(request.args.get("latitude", ""))
        radius = float(request.args.get("radius", "3"))
        unit = request.args.get("unit", "km")
    except ValueError:
        return error("longitude、latitude、radius 必须是数字")

    if unit not in {"m", "km", "mi", "ft"}:
        return error("unit 只能是 m、km、mi 或 ft")

    landmarks = search_nearby(longitude, latitude, radius, unit)
    return success(
        data=landmarks,
        count=len(landmarks),
        center={"longitude": longitude, "latitude": latitude},
        radius=radius,
        unit=unit,
    )


@app.get("/api/landmarks/distance")
def api_get_distance():
    from_id = request.args.get("from")
    to_id = request.args.get("to")
    unit = request.args.get("unit", "km")

    if not from_id or not to_id:
        return error("请提供 from 和 to 两个地标 ID")
    if unit not in {"m", "km", "mi", "ft"}:
        return error("unit 只能是 m、km、mi 或 ft")

    distance = get_distance(from_id, to_id, unit)
    if distance is None:
        return error("地标不存在或无法计算距离", 404)

    return success(from_id=from_id, to_id=to_id, distance=distance, unit=unit)


@app.get("/api/landmarks/<landmark_id>")
def api_get_landmark(landmark_id):
    landmark = get_landmark(landmark_id)
    if not landmark:
        return error("地标不存在", 404)
    return success(data=landmark)


@app.post("/api/landmarks")
def api_add_landmark():
    _, response = require_login_response()
    if response:
        return response

    data = request.get_json(silent=True) or {}
    try:
        landmark = add_landmark(data)
    except ValueError as exc:
        return error(str(exc))
    except Exception as exc:
        return error(f"新增地标失败: {exc}", 500)

    return success(data=landmark, message="地标保存成功")


@app.post("/api/landmarks/reset-seed")
def api_reset_seed_data():
    _, response = require_admin_response()
    if response:
        return response

    try:
        landmarks = reset_seed_data()
    except Exception as exc:
        return error(f"恢复示例数据失败: {exc}", 500)

    return success(
        data=landmarks,
        count=len(landmarks),
        message=f"已恢复 {len(landmarks)} 个成都示例地标",
    )


@app.post("/api/landmarks/import")
def api_import_landmarks():
    _, response = require_admin_response()
    if response:
        return response

    payload = request.get_json(silent=True)
    if payload is None:
        return error("请提交合法的 JSON 数据")

    landmarks = payload.get("data") if isinstance(payload, dict) else payload
    try:
        imported = import_landmarks(landmarks)
    except ValueError as exc:
        return error(str(exc))
    except Exception as exc:
        return error(f"导入地标失败: {exc}", 500)

    return success(data=imported, count=len(imported), message="导入成功")


@app.put("/api/landmarks/<landmark_id>")
def api_update_landmark(landmark_id):
    _, response = require_login_response()
    if response:
        return response

    data = request.get_json(silent=True) or {}
    try:
        landmark = update_landmark(landmark_id, data)
    except KeyError:
        return error("地标不存在", 404)
    except ValueError as exc:
        return error(str(exc))
    except Exception as exc:
        return error(f"更新地标失败: {exc}", 500)

    return success(data=landmark, message="地标更新成功")


@app.delete("/api/landmarks/<landmark_id>")
def api_delete_landmark(landmark_id):
    _, response = require_admin_response()
    if response:
        return response

    deleted = delete_landmark(landmark_id)
    if not deleted:
        return error("地标不存在", 404)
    return success(message="地标删除成功", id=landmark_id)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)