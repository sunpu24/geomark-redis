from redis_client import redis_client as r

print("Redis连接状态：", r.ping())

r.geoadd("landmark:geo", [104.06476, 30.57020, "tianfu_square"])
print("天府广场坐标：", r.geopos("landmark:geo", "tianfu_square"))