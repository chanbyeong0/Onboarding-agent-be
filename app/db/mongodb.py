"""
mongodb 모듈은 MongoDB 초기화 함수의 명시적인 별칭을 제공한다.
기존 구조의 session.py를 유지하면서도 Mongo 단일 스택임을 드러내는 import 경로를 제공한다.
"""

from app.db.session import close_db, get_database, get_mongo_client, init_db

__all__ = ["close_db", "get_database", "get_mongo_client", "init_db"]
