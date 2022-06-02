from flask import *
import math

app=Flask(__name__)

app.config["JSON_AS_ASCII"]=False
app.config["TEMPLATES_AUTO_RELOAD"]=True

import mysql.connector

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

# Pages
@app.route("/")
def index():
	return render_template("index.html")

from datetime import datetime
import redis
@app.route("/api/getstrategy", methods=["POST"])
def api_getstrategy():
    stock_number = request.json["stock_number"] # 股票代號
    start_date = request.json["start_date"].replace("-","")
    end_date = request.json["end_date"].replace("-","")

    # 區間策略
    if request.json["highest_price_for_region"] != "": 
        highest_price_for_region = float(request.json["highest_price_for_region"]) # 區間高價
        lowest_price_for_region = float(request.json["lowest_price_for_region"]) # 區間低價
        if stock_number == "23300": # 從redis拿資料
            r = redis.Redis(host="myrediscluster.6sqss0.ng.0001.use1.cache.amazonaws.com", port=6379)
            get_2330 = eval(r.get("2330"))
            result = []
            for i in range(len(get_2330)):
                if get_2330[i][0] >= start_date and get_2330[i][0] <= end_date:
                    result.append(get_2330[i])
        else: # 從MySQL拿資料
            try:
                db_connection = pool.get_connection()
                cursor = db_connection.cursor()
                cursor.execute("SELECT `日期`,`開盤價`,`最高價`,`最低價`,`收盤價`,`漲跌價差` FROM `all_stocks_and_dates_F_test` WHERE `證券代號` = '"+stock_number+"' AND `日期` BETWEEN '"+start_date+"' AND '"+end_date+"' ORDER BY `日期`;")
                result = cursor.fetchall()
            except mysql.connector.Error as err:
                print(err, "error msg")
            finally:
                db_connection.close()

        stock_daily_0_to_full=[]
        for i in range(len(result)):
            # 改date格式
            date_list = list(result[i][0])
            date_list.insert(4,"-")
            date_list.insert(7,"-")
            date = "".join(date_list)
            # 傳送資料
            stock_daily = {
                "open": result[i][1]/100, 
                "high": result[i][2]/100,
                "low": result[i][3]/100,  
                "close": result[i][4]/100, 
                # "volume": result[i][3], 
                "price_change": result[i][5]/100,
                "date": date,
                # "ma5": result[i][12],
                # "ma10": result[i][13],
                # "ma20": result[i][14]
            } 
            stock_daily_0_to_full.append(stock_daily.copy())
        #================================================================

        highest_price_touched = []
        lowest_price_touched = []
        trade_dates = []
        # 如果第一天開盤價低於等於區間低價，開盤買進 ※ result[0][1] 首日開盤價
        if result[0][1] <= float(lowest_price_for_region)*100:
            trade_dates.append(["買進", start_date, result[0][1]/100])
            for i in range(len(result)):
                if result[i][2] >= float(highest_price_for_region)*100:
                    highest_price_touched.append([result[i][0],result[i][1]/100]) # 當日最高價高於區間高價的list
                if result[i][2] <= float(lowest_price_for_region)*100: 
                    lowest_price_touched.append([result[i][0],result[i][1]/100]) # 當日最低價低於區間低價的list
            find_status = "up" # 往區間高價找
            for j in range(len(result)):
                if find_status == "down":
                    for k in range(len(lowest_price_touched)):
                        if lowest_price_touched[k][0] > trade_dates[-1][1]:
                            # lowest_price_touched[k][1] 開盤價
                            if lowest_price_touched[k][1] >= float(lowest_price_for_region):
                                trade_dates.append(["買進", lowest_price_touched[k][0], lowest_price_for_region])
                                del lowest_price_touched[:lowest_price_touched.index(lowest_price_touched[k])+1]
                                find_status = "up"
                                break
                            else:
                                trade_dates.append(["買進", lowest_price_touched[k][0], lowest_price_touched[k][1]])
                                del lowest_price_touched[:lowest_price_touched.index(lowest_price_touched[k])+1]
                                find_status = "up"
                                break
                else:
                    for l in range(len(highest_price_touched)):
                        if highest_price_touched[l][0] > trade_dates[-1][1]:
                            if highest_price_touched[l][1] <= float(highest_price_for_region):
                                trade_dates.append(["賣出", highest_price_touched[l][0], highest_price_for_region])
                                del highest_price_touched[:highest_price_touched.index(highest_price_touched[l])+1]
                                find_status = "down"
                                break
                            else:
                                trade_dates.append(["賣出", highest_price_touched[l][0], highest_price_touched[l][1]])
                                del highest_price_touched[:highest_price_touched.index(highest_price_touched[l])+1]
                                find_status = "down"
                                break
            if len(trade_dates)%2 == 1:
                trade_dates.append(["回測最後一天賣出", result[-1][0], result[-1][4]/100])
        # 如果第一天開盤價高於區間低價，開始搜尋買進日期
        else:
            for i in range(len(result)):
                if result[i][2] >= float(highest_price_for_region)*100:
                    highest_price_touched.append([result[i][0],result[i][1]/100]) # 最高價高於區間高價的list
                if result[i][2] <= float(lowest_price_for_region)*100: 
                    lowest_price_touched.append([result[i][0],result[i][1]/100]) # 最低價低於區間低價的list
            if len(lowest_price_touched) >= 1:
                trade_dates.append(["買進", lowest_price_touched[0][0], lowest_price_for_region])
                find_status = "up" # 往區間高價找
                for j in range(len(result)):
                    if find_status == "down":
                        for k in range(len(lowest_price_touched)):
                            if lowest_price_touched[k][0] > trade_dates[-1][1]:
                                if lowest_price_touched[k][1] >= float(lowest_price_for_region)*100: # 如果開盤價大於區間低價
                                    trade_dates.append(["買進", lowest_price_touched[k][0], lowest_price_for_region]) # 區間低價買進(盤中)
                                    # del lowest_price_touched[:lowest_price_touched.index(lowest_price_touched[k])]
                                    del lowest_price_touched[:lowest_price_touched.index(lowest_price_touched[k])+1]
                                    find_status = "up"
                                    break
                                else: # 如果開盤價小於區間低價
                                    trade_dates.append(["買進", lowest_price_touched[k][0], lowest_price_touched[k][1]]) # 開盤價買進
                                    del lowest_price_touched[:lowest_price_touched.index(lowest_price_touched[k])+1]
                                    find_status = "up"
                                    break
                    else:
                        for l in range(len(highest_price_touched)):
                            if highest_price_touched[l][0] > trade_dates[-1][1]:
                                if highest_price_touched[l][1] <= float(highest_price_for_region)*100:
                                    trade_dates.append(["賣出", highest_price_touched[l][0], highest_price_for_region])
                                    del highest_price_touched[:highest_price_touched.index(highest_price_touched[l])+1]
                                    find_status = "down"
                                    break
                                else:
                                    trade_dates.append(["賣出", highest_price_touched[l][0], highest_price_touched[l][1]])
                                    del highest_price_touched[:highest_price_touched.index(highest_price_touched[l])+1]
                                    find_status = "down"
                                    break
            else:
                trade_dates = [["沒有買入點", "", ""],["", "", ""]]
            if len(trade_dates)%2 == 1:
                trade_dates.append(["回測最後一天賣出", result[-1][0], result[-1][4]/100])
            
    # 均線策略
    elif request.json["how_many_ma"] != "":
        how_many_ma = int(request.json["how_many_ma"]) # 均線

        start_date = datetime.strptime(start_date,"%Y%m%d") # 轉成datetime.datetime格式
        if how_many_ma <= 15:
            if start_date.month !=1:
                buffer_date = start_date.replace(month = start_date.month-1)
            else:
                buffer_date = start_date.replace(month = 12, year = start_date.year-1)
        elif how_many_ma <= 200:
            buffer_date = start_date.replace(year = start_date.year-1)
        elif how_many_ma <= 1000:
            buffer_date = start_date.replace(year = start_date.year-5)
        elif how_many_ma <= 2400:
            buffer_date = start_date.replace(year = start_date.year-11)
        buffer_date = datetime.strftime(buffer_date, "%Y%m%d")
        start_date = datetime.strftime(start_date, "%Y%m%d") # 轉回str格式

        if stock_number == "23300": # 從redis拿資料
            r = redis.Redis(host="myrediscluster.6sqss0.ng.0001.use1.cache.amazonaws.com", port=6379)
            get_2330 = eval(r.get("2330"))
            result_for_m = []
            for i in range(len(get_2330)):
                if get_2330[i][0] >= buffer_date and get_2330[i][0] <= end_date:
                    result_for_ma.append(get_2330[i])
        else: # 從MySQL拿資料
            try: 
                db_connection = pool.get_connection()
                cursor = db_connection.cursor()
                cursor.execute("SELECT `日期`,`開盤價`,`最高價`,`最低價`,`收盤價`,`漲跌價差` FROM `all_stocks_and_dates_F_test` WHERE `證券代號` = '"+stock_number+"' AND `日期` BETWEEN  '"+buffer_date+"' AND '"+end_date+"' ORDER BY `日期` DESC;")
                result_for_ma = cursor.fetchall()
            except mysql.connector.Error as err:
                print(err, "error msg")
            finally:
                db_connection.close()

        trade_dates = [] # 所有交易日期
        above_ma_dates = [] # 列出所有收盤價在均線上方的日期
        under_ma_dates = [] # 列出所有收盤價在均線下方的日期
        result_add_ma = [] # 所有最低價、日期、開盤價、收盤價、均價集合

        for i in range(len(result_for_ma)-how_many_ma+1): # 共有幾天
            if result_for_ma[i][0] >= start_date:
                total = 0
                for j in range(i,i+how_many_ma): # 每天的均線
                    close = result_for_ma[j][4]
                    total = total+close
                result_add_ma.append([result_for_ma[i][3]/100, result_for_ma[i][0], result_for_ma[i][1]/100, result_for_ma[i][4]/100, (math.floor(total/how_many_ma))/100.0, result_for_ma[i][2]/100, result_for_ma[i][5]/100])
            else:
                break
        result_add_ma.reverse()
        for k in range(len(result_add_ma)): # 分類站上與跌破均線的日期集合
            if result_add_ma[k][3] > result_add_ma[k][4]:
                above_ma_dates.append([result_add_ma[k][1], result_add_ma[k][4], result_add_ma[k][3]])
            elif result_add_ma[k][3] < result_add_ma[k][4]:
                under_ma_dates.append([result_add_ma[k][1], result_add_ma[k][4], result_add_ma[k][3]])
        # 當首日開盤價小於等於均線，找尋第一天收盤價在均線之上的日期
        if result_add_ma[0][2] <= result_add_ma[0][4]:
            if len(above_ma_dates) > 0: # 如果有收盤價在均線上方的日期
                trade_dates.append(["買進", above_ma_dates[0][0], above_ma_dates[0][2]])
                find_status = "down" # 往跌破均線找
                for m in range(len(result_add_ma)):
                    if find_status == "down":
                        for n in range(len(under_ma_dates)):
                            if under_ma_dates[n][0] > trade_dates[-1][1]:
                                trade_dates.append(["賣出", under_ma_dates[n][0], under_ma_dates[n][2]])
                                del under_ma_dates[:under_ma_dates.index(under_ma_dates[n])+1]
                                find_status = "up"
                                break
                    else:
                        for p in range(len(above_ma_dates)):
                            if above_ma_dates[p][0] > trade_dates[-1][1]:
                                trade_dates.append(["買進", above_ma_dates[p][0], above_ma_dates[p][2]])
                                del above_ma_dates[:above_ma_dates.index(above_ma_dates[p])+1]
                                find_status = "down"
                                break
            else: # 如果沒有收盤價在均線上方的日期
                trade_dates = [["沒有買入點", "", ""],["", "", ""]]
                            
        else: # 當首日開盤價大於均線，找尋第一天最低價小於等於均價且收盤價大於等於均價的日期
            for q in range(len(result_add_ma)):
                if result_add_ma[q][0] <= result_add_ma[q][4] and result_add_ma[q][3] >= result_add_ma[q][4]:
                    trade_dates.append(["買進", result_add_ma[q][1], result_add_ma[q][3]])
                    find_status = "down"
                    break
            if len(trade_dates) > 0: # 如果有最低價小於等於均價且收盤價大於等於均價的日期
                for m in range(len(result_add_ma)):
                    if find_status == "down":
                        for n in range(len(under_ma_dates)):
                            if under_ma_dates[n][0] > trade_dates[-1][1]:
                                trade_dates.append(["賣出", under_ma_dates[n][0], under_ma_dates[n][2]])
                                del under_ma_dates[:under_ma_dates.index(under_ma_dates[n])+1]
                                find_status = "up"
                                break
                    else:
                        for p in range(len(above_ma_dates)):
                            if above_ma_dates[p][0] > trade_dates[-1][1]:
                                trade_dates.append(["買進", above_ma_dates[p][0], above_ma_dates[p][2]])
                                del above_ma_dates[:above_ma_dates.index(above_ma_dates[p])+1]
                                find_status = "down"
                                break
            else: # 如果沒有最低價小於等於均價且收盤價大於等於均價的日期
                trade_dates = [["沒有買入點", "", ""],["", "", ""]]
            if len(trade_dates)%2 == 1:
                trade_dates.append(["回測最後一天賣出", result_add_ma[-1][1], result_add_ma[-1][3]])

        #================================================================生成圖片需要的資料

        stock_daily_0_to_full=[]
        for i in range(len(result_add_ma)):
            # 改date格式
            date_list = list(result_add_ma[i][1])
            date_list.insert(4,"-")
            date_list.insert(7,"-")
            date = "".join(date_list)
            # 傳送資料
            stock_daily = {
                "open": result_add_ma[i][2], 
                "high": result_add_ma[i][5], 
                "close": result_add_ma[i][3], 
                "low": result_add_ma[i][0], 
                # "volume": result[i][3], 
                "price_change": result_add_ma[i][6],
                "date": date,
                "ma5": result_add_ma[i][4],
                # "ma10": result[i][13],
                # "ma20": result[i][14]
            } 
            stock_daily_0_to_full.append(stock_daily.copy())
        #================================================================
        
    # 算報酬率
    reward = 0
    if trade_dates[0][0] != "沒有買入點":
        for m in range(int(len(trade_dates)/2)):
            reward = reward+(trade_dates[m*2-1][2]-trade_dates[m*2-2][2])/trade_dates[m*2-2][2]*100
    return jsonify({"trade_dates_and_price": trade_dates,"draw_pic_data": stock_daily_0_to_full, "reward": math.floor(reward*100) / 100.0, "stock_name_and_number": stock_number})

# socket================================================================
from flask import Flask, render_template
from flask_socketio import SocketIO, send, emit
from numpy import broadcast

socketio = SocketIO(app)

# step 1: server sends data
# client端會從下面這個any event 接收到後端的message "send data"
@socketio.on("connect")
def test_connect():
    emit("any event", "send data")
      #   觸發事件       傳送參數

# step 2: server receives data
@socketio.on('message')
def handle_message(data):
    print('received message: ' + data)
# 會print出 received message: I'm connected 
    send(data, broadcast=True)
    print(1)

# namespace================================================
@socketio.on('my_event', namespace='/test')
def handle_namespace_event(data):
    print("received:"+str(data))
    emit("my_response", data, broadcast=True)

# 在此請不要使用socketio.emit() function, 這是一個跟此handle_namespace_event函數上下文無關的函數，對此環境一無所知。在此環境下要使用
# emit()函數，且emit()僅能在事件處理程序內部使用，他會從事件內（handle_namespace_event）獲取訊息。他會檢測當前正在處理的事件中使用的namespace，並默認在同一命名空間中發出訊息

#print 出結果：
# "recieved: data from client"
# =========================================================


# room================================================
from flask_socketio import join_room, leave_room
room = 0
@socketio.on('join')
def on_join(data):
    room = data["room"]
    print(data)
		#此為join_room裡的function，
		#代表進入room裡
    join_room(room)
    emit("room-message", "abc", 
		to=room)

@socketio.on('room-message')
def room_message(data):
    emit("room-message", data, 
		to=room)

#print 出結果：
# {'user': 'abc', 'room': 'myroom', 'message': 'ok'}

#如果沒有join_room client端將接收不到來自room emit出來的訊息
# ====================================================    


app.run(host="0.0.0.0",port=3000)