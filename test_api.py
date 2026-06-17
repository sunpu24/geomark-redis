import os

os.environ["ADMIN_USERNAMES"] = "stage8_admin_user"

from app import app
from landmark_service import delete_landmark
from user_service import delete_test_user


TEST_ID = "api_test_landmark_stage6"
IMPORT_ID_1 = "import_test_landmark_1"
IMPORT_ID_2 = "import_test_landmark_2"
TEST_USERNAME = "stage7_test_user"
ADMIN_USERNAME = "stage8_admin_user"


REQUIRED_LANDMARK_FIELDS = {
    "id",
    "name",
    "category",
    "address",
    "description",
    "longitude",
    "latitude",
}


def assert_success(response):
    assert response.status_code == 200, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload["success"] is True, payload
    return payload


def assert_no_password_hash(value):
    if isinstance(value, dict):
        assert "password_hash" not in value, value
        for item in value.values():
            assert_no_password_hash(item)
    elif isinstance(value, list):
        for item in value:
            assert_no_password_hash(item)


def cleanup(client):
    delete_landmark(TEST_ID)
    delete_test_user(TEST_USERNAME)
    delete_test_user(ADMIN_USERNAME)


def sample_import_landmarks():
    return [
        {
            "id": IMPORT_ID_1,
            "name": "导入测试点一",
            "category": "导入测试",
            "address": "成都市导入测试地址一",
            "description": "用于阶段六导入成功测试",
            "longitude": 104.061,
            "latitude": 30.571,
        },
        {
            "id": IMPORT_ID_2,
            "name": "导入测试点二",
            "category": "导入测试",
            "address": "成都市导入测试地址二",
            "description": "用于阶段六导入成功测试",
            "longitude": 104.082,
            "latitude": 30.593,
        },
    ]


def main():
    guest_client = app.test_client()
    user_client = app.test_client()
    admin_client = app.test_client()

    cleanup(admin_client)

    admin_payload = {
        "username": ADMIN_USERNAME,
        "password": "123456",
        "nickname": "阶段八管理员",
        "email": "admin@example.com",
    }
    admin_register_payload = assert_success(admin_client.post("/api/users/register", json=admin_payload))
    assert admin_register_payload["data"]["role"] == "admin"
    admin_login_payload = assert_success(
        admin_client.post(
            "/api/users/login",
            json={"username": ADMIN_USERNAME, "password": admin_payload["password"]},
        )
    )
    assert admin_login_payload["data"]["role"] == "admin"
    print("管理员注册登录测试通过")

    unauthorized_reset_response = guest_client.post("/api/landmarks/reset-seed")
    assert unauthorized_reset_response.status_code == 401
    assert unauthorized_reset_response.get_json()["success"] is False
    print("未登录恢复示例数据权限拦截测试通过")

    seed_payload = assert_success(admin_client.post("/api/landmarks/reset-seed"))
    assert seed_payload["count"] == 12
    delete_landmark(TEST_ID)

    home_response = guest_client.get("/")
    assert home_response.status_code == 200
    print("首页测试通过")

    health_payload = assert_success(guest_client.get("/api/health"))
    assert "redis" in health_payload
    print("健康检查测试通过")

    stats_payload = assert_success(guest_client.get("/api/stats"))
    assert stats_payload["data"]["landmark_count"] == 12
    assert stats_payload["data"]["category_count"] >= 1
    assert isinstance(stats_payload["data"]["category_distribution"], dict)
    assert "user_count" in stats_payload["data"]
    assert "redis_ok" in stats_payload["data"]
    print("统计看板接口测试通过")

    user_payload = {
        "username": TEST_USERNAME,
        "password": "123456",
        "nickname": "阶段七测试用户",
        "email": "stage7@example.com",
    }
    register_payload = assert_success(user_client.post("/api/users/register", json=user_payload))
    assert register_payload["message"] == "注册成功"
    assert register_payload["data"]["username"] == TEST_USERNAME
    assert register_payload["data"]["nickname"] == "阶段七测试用户"
    assert register_payload["data"]["email"] == "stage7@example.com"
    assert register_payload["data"]["role"] == "user"
    assert "created_at" in register_payload["data"]
    assert_no_password_hash(register_payload)
    print("用户注册成功测试通过")

    duplicate_user_response = user_client.post("/api/users/register", json=user_payload)
    assert duplicate_user_response.status_code == 400
    assert duplicate_user_response.get_json()["success"] is False
    assert_no_password_hash(duplicate_user_response.get_json())
    print("重复用户名注册失败测试通过")

    invalid_username_response = guest_client.post(
        "/api/users/register",
        json={"username": "bad user", "password": "123456"},
    )
    assert invalid_username_response.status_code == 400
    assert invalid_username_response.get_json()["success"] is False
    assert_no_password_hash(invalid_username_response.get_json())
    print("用户名非法测试通过")

    short_password_response = guest_client.post(
        "/api/users/register",
        json={"username": "short_password_user", "password": "12345"},
    )
    assert short_password_response.status_code == 400
    assert short_password_response.get_json()["success"] is False
    assert_no_password_hash(short_password_response.get_json())
    print("密码过短测试通过")

    unauthorized_get_user_response = guest_client.get(f"/api/users/{TEST_USERNAME}")
    assert unauthorized_get_user_response.status_code == 401
    assert unauthorized_get_user_response.get_json()["success"] is False
    print("未登录查询用户权限拦截测试通过")

    login_payload = assert_success(
        user_client.post(
            "/api/users/login",
            json={"username": TEST_USERNAME, "password": user_payload["password"]},
        )
    )
    assert login_payload["message"] == "登录成功"
    assert login_payload["data"]["username"] == TEST_USERNAME
    assert login_payload["data"]["nickname"] == "阶段七测试用户"
    assert login_payload["data"]["email"] == "stage7@example.com"
    assert login_payload["data"]["role"] == "user"
    assert "created_at" in login_payload["data"]
    assert_no_password_hash(login_payload)
    print("用户登录成功测试通过")

    get_user_payload = assert_success(user_client.get(f"/api/users/{TEST_USERNAME}"))
    assert get_user_payload["data"]["username"] == TEST_USERNAME
    assert get_user_payload["data"]["nickname"] == "阶段七测试用户"
    assert_no_password_hash(get_user_payload)
    print("查询单个用户测试通过")

    normal_list_users_response = user_client.get("/api/users")
    assert normal_list_users_response.status_code == 403
    assert normal_list_users_response.get_json()["success"] is False
    print("普通用户列表权限拦截测试通过")

    list_users_payload = assert_success(admin_client.get("/api/users"))
    assert isinstance(list_users_payload["data"], list)
    assert any(user["username"] == TEST_USERNAME for user in list_users_payload["data"])
    assert_no_password_hash(list_users_payload)
    print(f"用户列表测试通过，当前数量: {list_users_payload['count']}")

    me_before_login_payload = assert_success(guest_client.get("/api/users/me"))
    assert me_before_login_payload["data"] is None
    assert me_before_login_payload["logged_in"] is False
    assert_no_password_hash(me_before_login_payload)
    print("未登录当前用户状态测试通过")

    favorite_before_login_response = guest_client.get("/api/users/me/favorites")
    assert favorite_before_login_response.status_code == 401
    assert favorite_before_login_response.get_json()["success"] is False
    favorite_add_before_login_response = guest_client.post("/api/users/me/favorites/tianfu_square")
    assert favorite_add_before_login_response.status_code == 401
    assert favorite_add_before_login_response.get_json()["success"] is False
    print("未登录收藏权限拦截测试通过")

    me_after_login_payload = assert_success(user_client.get("/api/users/me"))
    assert me_after_login_payload["logged_in"] is True
    assert me_after_login_payload["data"]["username"] == TEST_USERNAME
    assert me_after_login_payload["data"]["nickname"] == "阶段七测试用户"
    assert_no_password_hash(me_after_login_payload)
    print("登录后当前用户状态测试通过")

    empty_favorites_payload = assert_success(user_client.get("/api/users/me/favorites"))
    assert empty_favorites_payload["count"] == 0
    assert empty_favorites_payload["ids"] == []
    add_favorite_payload = assert_success(user_client.post("/api/users/me/favorites/tianfu_square"))
    assert "tianfu_square" in add_favorite_payload["ids"]
    list_favorites_payload = assert_success(user_client.get("/api/users/me/favorites"))
    assert list_favorites_payload["count"] == 1
    assert list_favorites_payload["data"][0]["id"] == "tianfu_square"
    remove_favorite_payload = assert_success(user_client.delete("/api/users/me/favorites/tianfu_square"))
    assert "tianfu_square" not in remove_favorite_payload["ids"]
    missing_favorite_response = user_client.post("/api/users/me/favorites/not_exists_landmark")
    assert missing_favorite_response.status_code == 404
    assert missing_favorite_response.get_json()["success"] is False
    print("用户收藏地标接口测试通过")

    wrong_password_response = guest_client.post(
        "/api/users/login",
        json={"username": TEST_USERNAME, "password": "wrong-password"},
    )
    assert wrong_password_response.status_code == 401
    assert wrong_password_response.get_json()["success"] is False
    assert wrong_password_response.get_json()["message"] == "用户名或密码错误"
    assert_no_password_hash(wrong_password_response.get_json())
    print("密码错误登录失败测试通过")

    missing_user_response = guest_client.post(
        "/api/users/login",
        json={"username": "stage8_missing_user", "password": "123456"},
    )
    assert missing_user_response.status_code == 401
    assert missing_user_response.get_json()["success"] is False
    assert missing_user_response.get_json()["message"] == "用户名或密码错误"
    assert_no_password_hash(missing_user_response.get_json())
    print("用户不存在登录失败测试通过")

    logout_payload = assert_success(user_client.post("/api/users/logout"))
    assert logout_payload["message"] == "已退出登录"
    assert_no_password_hash(logout_payload)
    me_after_logout_payload = assert_success(user_client.get("/api/users/me"))
    assert me_after_logout_payload["data"] is None
    assert me_after_logout_payload["logged_in"] is False
    assert_no_password_hash(me_after_logout_payload)
    print("退出登录后当前用户状态测试通过")

    list_payload = assert_success(guest_client.get("/api/landmarks"))
    assert isinstance(list_payload["data"], list)
    print(f"列表测试通过，当前数量: {list_payload['count']}")

    export_payload = assert_success(guest_client.get("/api/landmarks/export"))
    assert export_payload["count"] == list_payload["count"]
    assert isinstance(export_payload["data"], list)
    assert "exported_at" in export_payload
    if export_payload["data"]:
        assert REQUIRED_LANDMARK_FIELDS.issubset(export_payload["data"][0].keys())
    print(f"导出测试通过，导出数量: {export_payload['count']}")

    test_landmark = {
        "id": TEST_ID,
        "name": "阶段五 API 测试点",
        "category": "测试",
        "address": "成都市测试地址",
        "description": "用于阶段五 API 自动化验证",
        "longitude": 104.06,
        "latitude": 30.57,
    }
    unauthorized_add_response = guest_client.post("/api/landmarks", json=test_landmark)
    assert unauthorized_add_response.status_code == 401
    assert unauthorized_add_response.get_json()["success"] is False
    print("未登录新增地标权限拦截测试通过")

    assert_success(
        user_client.post(
            "/api/users/login",
            json={"username": TEST_USERNAME, "password": user_payload["password"]},
        )
    )
    add_payload = assert_success(user_client.post("/api/landmarks", json=test_landmark))
    assert add_payload["data"]["id"] == TEST_ID
    print("新增测试通过")

    duplicate_response = user_client.post("/api/landmarks", json=test_landmark)
    assert duplicate_response.status_code == 400
    assert duplicate_response.get_json()["success"] is False
    print("重复 ID 测试通过")

    get_payload = assert_success(guest_client.get(f"/api/landmarks/{TEST_ID}"))
    assert get_payload["data"]["name"] == test_landmark["name"]
    print("查询单个测试通过")

    update_payload = assert_success(
        user_client.put(
            f"/api/landmarks/{TEST_ID}",
            json={
                "name": "阶段五 API 测试点-已编辑",
                "category": "测试编辑",
                "address": "成都市测试地址-已编辑",
                "description": "阶段五编辑验证",
                "longitude": 104.07,
                "latitude": 30.58,
            },
        )
    )
    assert update_payload["data"]["name"] == "阶段五 API 测试点-已编辑"
    assert update_payload["data"]["longitude"] == 104.07
    print("编辑测试通过")

    nearby_payload = assert_success(
        guest_client.get("/api/landmarks/nearby?longitude=104.06476&latitude=30.57020&radius=5&unit=km")
    )
    assert isinstance(nearby_payload["data"], list)
    print(f"附近搜索测试通过，命中数量: {nearby_payload['count']}")

    distance_payload = assert_success(guest_client.get("/api/landmarks/distance?from=tianfu_square&to=chunxi_road&unit=km"))
    assert isinstance(distance_payload["distance"], (int, float))
    print("距离计算测试通过")

    normal_delete_response = user_client.delete(f"/api/landmarks/{TEST_ID}")
    assert normal_delete_response.status_code == 403
    assert normal_delete_response.get_json()["success"] is False
    print("普通用户删除地标权限拦截测试通过")

    delete_payload = assert_success(admin_client.delete(f"/api/landmarks/{TEST_ID}"))
    assert delete_payload["id"] == TEST_ID
    print("删除测试通过")

    missing_response = guest_client.get(f"/api/landmarks/{TEST_ID}")
    assert missing_response.status_code == 404
    assert missing_response.get_json()["success"] is False
    print("删除后查询 404 测试通过")

    normal_import_response = user_client.post("/api/landmarks/import", json={"data": sample_import_landmarks()})
    assert normal_import_response.status_code == 403
    assert normal_import_response.get_json()["success"] is False
    print("普通用户导入地标权限拦截测试通过")

    import_payload = assert_success(admin_client.post("/api/landmarks/import", json={"data": sample_import_landmarks()}))
    assert import_payload["count"] == 2
    assert import_payload["message"] == "导入成功"
    assert {item["id"] for item in import_payload["data"]} == {IMPORT_ID_1, IMPORT_ID_2}
    imported_get_payload = assert_success(guest_client.get(f"/api/landmarks/{IMPORT_ID_1}"))
    assert imported_get_payload["data"]["name"] == "导入测试点一"
    print("导入成功测试通过")

    duplicate_import_data = sample_import_landmarks()
    duplicate_import_data[1]["id"] = duplicate_import_data[0]["id"]
    duplicate_import_response = admin_client.post("/api/landmarks/import", json=duplicate_import_data)
    assert duplicate_import_response.status_code == 400
    assert duplicate_import_response.get_json()["success"] is False
    after_duplicate_payload = assert_success(guest_client.get("/api/landmarks"))
    assert after_duplicate_payload["count"] == 2
    assert {item["id"] for item in after_duplicate_payload["data"]} == {IMPORT_ID_1, IMPORT_ID_2}
    print("重复 ID 导入失败测试通过")

    invalid_coordinate_data = sample_import_landmarks()
    invalid_coordinate_data[0]["longitude"] = 181
    invalid_coordinate_response = admin_client.post("/api/landmarks/import", json={"data": invalid_coordinate_data})
    assert invalid_coordinate_response.status_code == 400
    assert invalid_coordinate_response.get_json()["success"] is False
    after_invalid_payload = assert_success(guest_client.get("/api/landmarks"))
    assert after_invalid_payload["count"] == 2
    assert {item["id"] for item in after_invalid_payload["data"]} == {IMPORT_ID_1, IMPORT_ID_2}
    print("非法经纬度导入失败测试通过")

    reset_payload = assert_success(admin_client.post("/api/landmarks/reset-seed"))
    assert reset_payload["count"] == 12
    print("恢复示例数据测试通过，数量: 12")

    print("全部 API 测试通过")


if __name__ == "__main__":
    main()