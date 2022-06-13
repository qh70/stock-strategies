# 找尋今天日期
import datetime
today_str = str(datetime.date.today()).replace("-", "")
# 連RDS
import mysql.connector
import math
# connection pool
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
connection_RDSdb=pool.get_connection()
cursor=connection_RDSdb.cursor()
cursor.execute("USE `stock`")

with open(r"/home/ubuntu/stock-strategies/all_stocks_numbers.txt","r",encoding="utf-8") as file:
    stock_number_list = eval(file.read()) # 把每個檔案中的個股挑出來
    length_older_stocks_list=len(stock_number_list)
    file.close()

with open(r"/home/ubuntu/stock-strategies/no_trade.txt","r",encoding="utf-8") as file:
    no_trade = list(eval(file.read())) # 成交股數為0的股號與日期
    file.close()

with open(r"/home/ubuntu/stock-strategies/new_stocks_numbers.txt","r",encoding="utf-8") as file:
    new_stock_number_list = list(eval(file.read())) # 歷史的新增股號
    file.close()

daily_new_stock_number_list = [] # 新增的股號、日期、股票名稱
new_stock_number_and_name_list = [] # 新增的股號、股票名稱(不重複)
new_no_trade = []

# 抓API
import urllib.request as req
import json
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
url = "https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date="+today_str+"&type=ALL&_=1650028051196l"
request = req.Request(url)
with req.urlopen(request) as response:
    result_str = response.read().decode("utf-8")

    # result=json.loads(result_str) # response.read().decode("utf-8")是str，把它轉成dict
    if json.loads(result_str)["stat"]=='很抱歉，沒有符合條件的資料!':
        req.urlopen(request).close()
        connection_RDSdb.close()
        with open(r"/home/ubuntu/stock-strategies/holidays.txt","a",encoding="utf-8") as file:
            file.write(today_str)   
            file.close()   
    else:
        result_list = eval(str(json.loads(result_str)["data9"]))
        result_dict = {}
        for i in range(len(result_list)):
            if "+" in result_list[i][9]:
                result_up_or_down = "+"
            elif "-" in result_list[i][9]:
                result_up_or_down = "-"
            else:
                result_up_or_down = ""
            result_dict.setdefault(result_list[i][0],[result_list[i][1],result_list[i][2],result_list[i][3],result_list[i][4],result_list[i][5],result_list[i][6],result_list[i][7],result_list[i][8],result_up_or_down,result_list[i][10]])
        daily_stock_number_list = [] # 當日股號
        for j in result_dict.keys():
            if j > "1000" and len(j) == 4:
                daily_stock_number_list.append(j)
                if j not in stock_number_list:
                    daily_new_stock_number_list.append([today_str, j])
                    new_stock_number_list.insert(0, [today_str, j])
                    stock_number_list.append(j)
                    if [j, (result_dict)[j][0]] not in new_stock_number_and_name_list:
                        new_stock_number_and_name_list.append([j, (result_dict)[j][0]])
        try:
            for k in daily_stock_number_list:
                if (result_dict)[k][1] != "0": # 當該股該日有成交股數
                    cursor.execute("INSERT INTO `all_stocks_and_dates_F_test` VALUES('"+k+"', '"+today_str+"', '"+(result_dict)[k][1].replace(",", "")+"', '"+(result_dict)[k][2].replace(",", "")+"', '"+(result_dict)[k][3].replace(",", "")+"', '"+(result_dict)[k][4].replace(",", "").replace(".", "")+"', '"+(result_dict)[k][5].replace(",", "").replace(".", "")+"', '"+(result_dict)[k][6].replace(",", "").replace(".", "")+"', '"+(result_dict)[k][7].replace(",", "").replace(".", "")+"', '"+(result_dict)[k][8]+"', '"+(result_dict)[k][9].replace(",", "").replace(".", "")+"');")
                    print(k)
                    continue
                else:
                    # no_trade.insert(0, [k,today_str])
                    new_no_trade.append([k,today_str])
                    print(k, "當日沒有成交股數", today_str)  
                with open(r"/home/ubuntu/stock-strategies/duty_days.txt","w",encoding="utf-8") as file:
                    file.write(today_str)   
                    file.close()   
                
            
                    
        except mysql.connector.Error as err:
            print(err, "error msg")
            connection_RDSdb.commit()
            connection_RDSdb.close()
        finally:
            connection_RDSdb.commit()
            connection_RDSdb.close()
        req.urlopen(request).close()
# print("new_no_trade", new_no_trade)
new_no_trade.reverse()
for m in new_no_trade:
    no_trade.insert(0, m)
# print("新增股號", daily_new_stock_number_list)
stock_number_list.sort()
# print("舊的歷史股號長度", length_older_stocks_list)
# print("新的歷史股號長度", len(stock_number_list))
with open(r"/home/ubuntu/stock-strategies/new_stocks_numbers.txt","w",encoding="utf-8") as file:
    file.write(str(new_stock_number_list))
    file.close()

with open(r"/home/ubuntu/stock-strategies/no_trade.txt","w",encoding="utf-8") as file:
    file.write(str(no_trade))
    file.close()

with open(r"/home/ubuntu/stock-strategies/all_stocks_numbers.txt","w",encoding="utf-8") as file:
    file.write(str(stock_number_list))   
    file.close()     

        
