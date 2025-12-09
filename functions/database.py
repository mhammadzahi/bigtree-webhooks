import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Optional


def get_db_connection():
    conn = sqlite3.connect("user_info.db")
    conn.row_factory = sqlite3.Row
    return conn


def insert_product_enquiry(name: str, email: str, phone: Optional[str], company: Optional[str], project: Optional[str], message: Optional[str], request_sample: str, cart_items: str) -> bool:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        timestamp = datetime.now(timezone(timedelta(hours=4))).strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO product_enquiries 
            (name, email, phone, company, project, message, request_sample, cart_items, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, email, phone, company, project, message, request_sample, cart_items, timestamp))
        
        conn.commit()
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"Database error in insert product_enquiry: {e}")
        return False

    except Exception as e:
        print(f"Error in insert product_enquiry: {e}")
        return False


def insert_sample_request(first_name: str, last_name: str, email: str, phone: Optional[str], company: Optional[str], project: Optional[str], quantity: str, product_ids: str, message: Optional[str]) -> bool:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        timestamp = datetime.now(timezone(timedelta(hours=4))).strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO sample_requests 
            (first_name, last_name, email, phone, company, project, quantity, product_ids, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (first_name, last_name, email, phone, company, project, quantity, product_ids, message, timestamp))
        
        conn.commit()
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"Database error in insert sample_request: {e}")
        return False

    except Exception as e:
        print(f"Error in insert sample_request: {e}")
        return False
