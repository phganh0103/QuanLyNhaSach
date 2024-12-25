from app import redis_client

def set_ttl_order(order_id, ttl, status):
    redis_client.setex(order_id, ttl, status)