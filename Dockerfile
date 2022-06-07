FROM python:3.9-alpine

WORKDIR /stock-strategies

ADD . /stock-strategies

RUN pip install -r requirements.txt
RUN pip install mysql.connector
RUN pip install flask_socketio

CMD ["python", "app.py"]