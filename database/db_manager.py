"""
AI Quiz Platform - Database Manager
Version: 1.0.0
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
import streamlit as st
from config.settings import settings

class DatabaseManager:
    """PostgreSQL database connection manager with connection pooling"""
    
    def __init__(self):
        self.pool = None
        
    def initialize_pool(self, minconn=1, maxconn=10):
        """Initialize connection pool"""
        if self.pool is None:
            try:
                self.pool = SimpleConnectionPool(
                    minconn,
                    maxconn,
                    settings.DATABASE_URL
                )
                if settings.DEBUG_MODE:
                    print("✅ Database connection pool initialized")
            except Exception as e:
                raise Exception(f"Failed to initialize database pool: {str(e)}")
    
    @contextmanager
    def get_connection(self):
        """Get connection from pool"""
        if self.pool is None:
            self.initialize_pool()
        
        conn = self.pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self.pool.putconn(conn)
    
    def execute_query(self, query, params=None, fetch=True):
        """Execute query and return results"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params or ())
                if fetch:
                    return cur.fetchall()
                return None
    
    def execute_one(self, query, params=None):
        """Execute query and return single result"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params or ())
                return cur.fetchone()
    
    def execute_many(self, query, params_list):
        """Execute query with multiple parameter sets"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(query, params_list)
    
    def close_pool(self):
        """Close all connections in pool"""
        if self.pool:
            self.pool.closeall()
            if settings.DEBUG_MODE:
                print("Database connection pool closed")

# Singleton instance
_db_manager_instance = None

def get_db_manager():
    """Get or create database manager singleton"""
    global _db_manager_instance
    if _db_manager_instance is None:
        _db_manager_instance = DatabaseManager()
        _db_manager_instance.initialize_pool()
    return _db_manager_instance

# Create instance only when explicitly called
db_manager = None

def init_db_manager():
    """Initialize database manager - call this after set_page_config"""
    global db_manager
    if db_manager is None:
        db_manager = get_db_manager()
    return db_manager