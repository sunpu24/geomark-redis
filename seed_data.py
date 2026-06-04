from landmark_service import add_landmark, clear_landmarks, list_landmarks


CHENGDU_LANDMARKS = [
    {
        "id": "tianfu_square",
        "name": "天府广场",
        "category": "城市地标",
        "address": "成都市青羊区人民南路一段",
        "description": "成都市中心地标广场，是成都重要的城市公共空间。",
        "longitude": 104.06476,
        "latitude": 30.57020,
    },
    {
        "id": "chunxi_road",
        "name": "春熙路",
        "category": "商业街区",
        "address": "成都市锦江区春熙路",
        "description": "成都著名商业步行街和城市消费地标。",
        "longitude": 104.08095,
        "latitude": 30.65501,
    },
    {
        "id": "taikoo_li",
        "name": "成都远洋太古里",
        "category": "商业街区",
        "address": "成都市锦江区中纱帽街8号",
        "description": "开放式、低密度的现代商业街区。",
        "longitude": 104.08361,
        "latitude": 30.65322,
    },
    {
        "id": "kuanzhai_alley",
        "name": "宽窄巷子",
        "category": "历史文化",
        "address": "成都市青羊区长顺上街",
        "description": "由宽巷子、窄巷子和井巷子组成的历史文化街区。",
        "longitude": 104.05623,
        "latitude": 30.66984,
    },
    {
        "id": "wuhou_shrine",
        "name": "武侯祠",
        "category": "历史文化",
        "address": "成都市武侯区武侯祠大街231号",
        "description": "纪念诸葛亮、刘备等蜀汉人物的历史文化景区。",
        "longitude": 104.04303,
        "latitude": 30.65205,
    },
    {
        "id": "jinli",
        "name": "锦里古街",
        "category": "历史文化",
        "address": "成都市武侯区武侯祠大街231号附1号",
        "description": "临近武侯祠的成都民俗商业古街。",
        "longitude": 104.04555,
        "latitude": 30.65005,
    },
    {
        "id": "dufu_cottage",
        "name": "杜甫草堂",
        "category": "历史文化",
        "address": "成都市青羊区青华路37号",
        "description": "唐代诗人杜甫流寓成都时的故居纪念地。",
        "longitude": 104.02889,
        "latitude": 30.66056,
    },
    {
        "id": "panda_base",
        "name": "成都大熊猫繁育研究基地",
        "category": "生态旅游",
        "address": "成都市成华区熊猫大道1375号",
        "description": "以大熊猫保护、繁育和科普展示为特色的景区。",
        "longitude": 104.14538,
        "latitude": 30.73359,
    },
    {
        "id": "wenshu_monastery",
        "name": "文殊院",
        "category": "宗教文化",
        "address": "成都市青羊区文殊院街66号",
        "description": "成都著名佛教寺院和历史文化景点。",
        "longitude": 104.07462,
        "latitude": 30.67595,
    },
    {
        "id": "qingyang_palace",
        "name": "青羊宫",
        "category": "宗教文化",
        "address": "成都市青羊区一环路西二段9号",
        "description": "成都著名道教宫观。",
        "longitude": 104.04134,
        "latitude": 30.66765,
    },
    {
        "id": "eastern_suburb_memory",
        "name": "东郊记忆",
        "category": "文创园区",
        "address": "成都市成华区建设路东二段",
        "description": "由老工业区改造而来的音乐与文创园区。",
        "longitude": 104.12060,
        "latitude": 30.67125,
    },
    {
        "id": "jiuyan_bridge",
        "name": "九眼桥",
        "category": "夜生活地标",
        "address": "成都市锦江区九眼桥附近",
        "description": "成都府河与南河交汇处附近的夜生活地标。",
        "longitude": 104.08927,
        "latitude": 30.64228,
    },
]


def reset_seed_data():
    """清空当前地标并恢复成都示例地标数据。"""
    clear_landmarks()
    for landmark in CHENGDU_LANDMARKS:
        add_landmark(landmark)

    return list_landmarks()


def main():
    landmarks = reset_seed_data()

    print(f"成都景点初始化完成，共写入 {len(landmarks)} 个地标。")


if __name__ == "__main__":
    main()