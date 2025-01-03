from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import redis
from threading import Thread
from app.redis_tasks import pubsub_worker
from dotenv import load_dotenv
import cloudinary
import os
app = Flask(_name_)

app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:12345678@localhost/quanlynhasach?charset=utf8mb4"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.secret_key = "kjasdlkasjdlkasdjlkasdjalskdjalskdj"
app.config['TEMPLATES_AUTO_RELOAD'] = True

db = SQLAlchemy(app)
from flask_login import LoginManager
login_manager = LoginManager()
login_manager.init_app(app)

migrate = Migrate(app, db)

from .models import *

#cloudinary
load_dotenv()
cloudinary.config(
    cloud_name = os.getenv('CLOUD_NAME'),
    api_key=os.getenv('API_KEY'),
    api_secret=os.getenv('API_SECRET'))

# redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

redis_client = redis.StrictRedis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT")),
    password=os.getenv("REDIS_PASSWORD"),
    decode_responses=True
)

# Cấu hình notify-keyspace-events
try:
    redis_client.config_set('notify-keyspace-events', 'Ex')
    print("Cấu hình notify-keyspace-events thành công!")
    current_config = redis_client.config_get('notify-keyspace-events')
    print(f"notify-keyspace-events: {current_config}")
except redis.exceptions.RedisError as e:
    print(f"Lỗi khi cấu hình notify-keyspace-events: {e}")

worker_thread = Thread(target=pubsub_worker.handle_order_expiration, daemon=True)
worker_thread.start()