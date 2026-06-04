import re
from typing import Any

from redis_client import redis_client


GEO_KEY = "landmark:geo"
IDS_KEY = "landmark:ids"
DETAIL_KEY_PREFIX = "landmark:detail:"
ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def _detail_key(landmark_id: str) -> str:
    return f"{DETAIL_KEY_PREFIX}{landmark_id}"


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _validate_landmark_id(landmark_id: str) -> None:
    if not landmark_id:
        raise ValueError("缺少必要字段: id")
    if not ID_PATTERN.match(landmark_id):
        raise ValueError("地标 ID 只能包含英文字母、数字、下划线和中划线")


def _validate_coordinates(longitude: float, latitude: float) -> None:
    if not -180 <= longitude <= 180:
        raise ValueError("longitude 必须在 -180 到 180 之间")
    if not -90 <= latitude <= 90:
        raise ValueError("latitude 必须在 -90 到 90 之间")


def _build_landmark_payload(
    landmark_id: str,
    data: dict[str, Any],
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """校验并整理地标数据，供新增和编辑共用。"""
    required_fields = ["name", "longitude", "latitude"]
    missing_fields = [field for field in required_fields if data.get(field) in (None, "")]
    if missing_fields:
        raise ValueError(f"缺少必要字段: {', '.join(missing_fields)}")

    name = str(data["name"]).strip()
    if not name:
        raise ValueError("name 不能为空")

    try:
        longitude = float(data["longitude"])
        latitude = float(data["latitude"])
    except (TypeError, ValueError):
        raise ValueError("longitude 和 latitude 必须是数字") from None

    _validate_coordinates(longitude, latitude)

    base = existing or {}
    return {
        "id": landmark_id,
        "name": name,
        "category": str(data.get("category", base.get("category", "未分类")) or "未分类"),
        "address": str(data.get("address", base.get("address", "")) or ""),
        "description": str(data.get("description", base.get("description", "")) or ""),
        "longitude": str(longitude),
        "latitude": str(latitude),
    }


def _normalize_landmark(data: dict[str, Any]) -> dict[str, Any]:
    """把 Redis Hash 中的字符串数据整理成接口友好的格式。"""
    if not data:
        return {}

    result = dict(data)
    result["longitude"] = _to_float(result.get("longitude"))
    result["latitude"] = _to_float(result.get("latitude"))
    return result


def add_landmark(data: dict[str, Any]) -> dict[str, Any]:
    """新增地标，同时写入 GEO、Hash 和 ID 集合。"""
    landmark_id = str(data.get("id", "")).strip()
    _validate_landmark_id(landmark_id)
    if redis_client.sismember(IDS_KEY, landmark_id):
        raise ValueError("地标 ID 已存在，请换一个 ID")

    landmark = _build_landmark_payload(landmark_id, data)
    longitude = float(landmark["longitude"])
    latitude = float(landmark["latitude"])

    pipe = redis_client.pipeline()
    pipe.geoadd(GEO_KEY, [longitude, latitude, landmark_id])
    pipe.hset(_detail_key(landmark_id), mapping=landmark)
    pipe.sadd(IDS_KEY, landmark_id)
    pipe.execute()

    return _normalize_landmark(landmark)


def update_landmark(landmark_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """更新已有地标，同时更新 GEO 坐标和 Hash 详情。"""
    landmark_id = str(landmark_id).strip()
    _validate_landmark_id(landmark_id)

    existing = get_landmark(landmark_id)
    if not existing:
        raise KeyError(landmark_id)

    if data.get("id") not in (None, "", landmark_id):
        raise ValueError("不支持修改地标 ID")

    landmark = _build_landmark_payload(landmark_id, data, existing)
    longitude = float(landmark["longitude"])
    latitude = float(landmark["latitude"])

    pipe = redis_client.pipeline()
    pipe.geoadd(GEO_KEY, [longitude, latitude, landmark_id])
    pipe.hset(_detail_key(landmark_id), mapping=landmark)
    pipe.execute()

    return _normalize_landmark(landmark)


def get_landmark(landmark_id: str) -> dict[str, Any] | None:
    """查询单个地标详情。"""
    data = redis_client.hgetall(_detail_key(landmark_id))
    if not data:
        return None
    return _normalize_landmark(data)


def list_landmarks() -> list[dict[str, Any]]:
    """查询全部地标。"""
    ids = sorted(redis_client.smembers(IDS_KEY))
    landmarks = []
    for landmark_id in ids:
        landmark = get_landmark(landmark_id)
        if landmark:
            landmarks.append(landmark)
    return landmarks


def export_landmarks() -> list[dict[str, Any]]:
    """导出当前全部地标数据。"""
    return list_landmarks()


def import_landmarks(landmarks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """整体导入地标数据：先完成全部校验，再清空并写入 Redis。"""
    if not isinstance(landmarks, list):
        raise ValueError("导入数据必须是 JSON 数组")

    normalized_landmarks = []
    seen_ids = set()
    for index, item in enumerate(landmarks, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"第 {index} 条地标必须是 JSON 对象")

        landmark_id = str(item.get("id", "")).strip()
        _validate_landmark_id(landmark_id)
        if landmark_id in seen_ids:
            raise ValueError(f"导入数据中存在重复 ID: {landmark_id}")
        seen_ids.add(landmark_id)

        try:
            normalized_landmarks.append(_build_landmark_payload(landmark_id, item))
        except ValueError as exc:
            raise ValueError(f"第 {index} 条地标无效: {exc}") from None

    clear_landmarks()

    pipe = redis_client.pipeline()
    for landmark in normalized_landmarks:
        landmark_id = landmark["id"]
        longitude = float(landmark["longitude"])
        latitude = float(landmark["latitude"])
        pipe.geoadd(GEO_KEY, [longitude, latitude, landmark_id])
        pipe.hset(_detail_key(landmark_id), mapping=landmark)
        pipe.sadd(IDS_KEY, landmark_id)
    pipe.execute()

    return [_normalize_landmark(landmark) for landmark in normalized_landmarks]


def delete_landmark(landmark_id: str) -> bool:
    """删除地标，返回是否删除到了已有数据。"""
    existed = redis_client.sismember(IDS_KEY, landmark_id)

    pipe = redis_client.pipeline()
    pipe.zrem(GEO_KEY, landmark_id)
    pipe.delete(_detail_key(landmark_id))
    pipe.srem(IDS_KEY, landmark_id)
    pipe.execute()

    return bool(existed)


def search_nearby(
    longitude: float,
    latitude: float,
    radius: float,
    unit: str = "km",
) -> list[dict[str, Any]]:
    """按经纬度查询附近地标，结果按距离升序排列。"""
    results = redis_client.geosearch(
        GEO_KEY,
        longitude=longitude,
        latitude=latitude,
        radius=radius,
        unit=unit,
        withdist=True,
        withcoord=True,
        sort="ASC",
    )

    nearby_landmarks = []
    for landmark_id, distance, coord in results:
        landmark = get_landmark(landmark_id) or {"id": landmark_id}
        landmark["distance"] = float(distance)
        landmark["longitude"] = float(coord[0])
        landmark["latitude"] = float(coord[1])
        nearby_landmarks.append(landmark)

    return nearby_landmarks


def get_distance(from_id: str, to_id: str, unit: str = "km") -> float | None:
    """计算两个地标之间的距离。"""
    distance = redis_client.geodist(GEO_KEY, from_id, to_id, unit=unit)
    if distance is None:
        return None
    return float(distance)


def clear_landmarks() -> None:
    """清空地标相关数据，主要用于重新初始化示例数据。"""
    ids = redis_client.smembers(IDS_KEY)
    keys = [GEO_KEY, IDS_KEY]
    keys.extend(_detail_key(landmark_id) for landmark_id in ids)
    redis_client.delete(*keys)