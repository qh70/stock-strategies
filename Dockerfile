FROM python:3.9-alpine

WORKDIR /stock-strategies

ADD . /stock-strategies

RUN pip install -r requirements.txt
RUN pip install mysql.connector
RUN pip install flask_socketio
RUN pip install python-dotenv
RUN pip install redis

CMD ["python", "app.py"]