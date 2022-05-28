import redis
from redis import Redis

r = redis.Redis(host="myrediscluster.6sqss0.ng.0001.use1.cache.amazonaws.com", port=6379)

r.set("France", "Paris")
r.set("Germany", "Berlin")

france_capital = r.get("France")
germany_capital = r.get("Germany")

print(france_capital)
print(germany_capital)