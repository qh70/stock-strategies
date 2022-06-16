import mysql.connector
from mysql.connector import Error, pooling

import os
from dotenv import load_dotenv
load_dotenv()
mysql_password=os.getenv("mysql_password")

pool=pooling.MySQLConnectionPool(
	host = "database-2.cimqjjdbvr4l.us-west-2.rds.amazonaws.com",
    port = 3306,
	user = "admin",
	password = mysql_password,
	database = "stock",
	pool_name= "connection_pool",
	pool_size= 10,
)

try:
    db_connection = pool.get_connection()
    cursor = db_connection.cursor()
    cursor.execute("SELECT `日期`,`開盤價`,`最高價`,`最低價`,`收盤價`,`漲跌價差` FROM `all_stocks_and_dates_F_test` WHERE `證券代號` = '2330' ORDER BY `日期`;")
    result = str(cursor.fetchall())

except mysql.connector.Error as err:
    print(err, "error msg")
db_connection.close()

import redis
from redis import Redis

r = redis.Redis(host="myrediscluster.6sqss0.ng.0001.use1.cache.amazonaws.com", port=6379)

r.set("2330", result)
