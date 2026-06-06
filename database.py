import sqlite3
from datetime import datetime

DB_NAME = "remont.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS objects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            object_id INTEGER,
            stage_name TEXT,
            plan_amount REAL,
            FOREIGN KEY (object_id) REFERENCES objects(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS warehouse (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material TEXT UNIQUE,
            quantity REAL,
            price_per_unit REAL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS site_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            object_id INTEGER,
            material TEXT,
            quantity REAL,
            FOREIGN KEY (object_id) REFERENCES objects(id),
            UNIQUE(object_id, material)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS finance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            type TEXT,
            object_id INTEGER,
            amount REAL,
            comment TEXT,
            FOREIGN KEY (object_id) REFERENCES objects(id)
        )
    ''')
    
    conn.commit()
    conn.close()

def add_object(address):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO objects (address, created_at) VALUES (?, ?)", 
                   (address, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    object_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return object_id

def get_objects():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, address, status FROM objects WHERE status = 'active'")
    objects = [{"object_id": row[0], "address": row[1], "status": row[2]} for row in cursor.fetchall()]
    conn.close()
    return objects

def get_object_by_id(object_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, address, status FROM objects WHERE id = ?", (object_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"object_id": row[0], "address": row[1], "status": row[2]}
    return None

def add_stage(object_id, stage_name, plan_amount):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO stages (object_id, stage_name, plan_amount) VALUES (?, ?, ?)",
                   (object_id, stage_name, plan_amount))
    conn.commit()
    conn.close()

def get_stages_by_object(object_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT stage_name, plan_amount FROM stages WHERE object_id = ?", (object_id,))
    stages = [{"stage_name": row[0], "plan_amount": row[1]} for row in cursor.fetchall()]
    conn.close()
    return stages

def add_material_to_warehouse(material, quantity, price_per_unit):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT quantity, price_per_unit FROM warehouse WHERE material = ?", (material,))
    existing = cursor.fetchone()
    if existing:
        new_qty = existing[0] + quantity
        new_price = (existing[0] * existing[1] + quantity * price_per_unit) / new_qty
        cursor.execute("UPDATE warehouse SET quantity = ?, price_per_unit = ? WHERE material = ?",
                       (new_qty, new_price, material))
    else:
        cursor.execute("INSERT INTO warehouse (material, quantity, price_per_unit) VALUES (?, ?, ?)",
                       (material, quantity, price_per_unit))
    conn.commit()
    conn.close()

def get_warehouse():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT material, quantity, price_per_unit FROM warehouse WHERE quantity > 0")
    materials = [{"material": row[0], "quantity": row[1], "price_per_unit": row[2]} for row in cursor.fetchall()]
    conn.close()
    return materials

def remove_from_warehouse(material, quantity):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT quantity FROM warehouse WHERE material = ?", (material,))
    row = cursor.fetchone()
    if row and row[0] >= quantity:
        new_qty = row[0] - quantity
        if new_qty == 0:
            cursor.execute("DELETE FROM warehouse WHERE material = ?", (material,))
        else:
            cursor.execute("UPDATE warehouse SET quantity = ? WHERE material = ?", (new_qty, material))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def add_material_to_site(object_id, material, quantity):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT quantity FROM site_materials WHERE object_id = ? AND material = ?", 
                   (object_id, material))
    existing = cursor.fetchone()
    if existing:
        new_qty = existing[0] + quantity
        cursor.execute("UPDATE site_materials SET quantity = ? WHERE object_id = ? AND material = ?",
                       (new_qty, object_id, material))
    else:
        cursor.execute("INSERT INTO site_materials (object_id, material, quantity) VALUES (?, ?, ?)",
                       (object_id, material, quantity))
    conn.commit()
    conn.close()

def remove_material_from_site(object_id, material, quantity):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT quantity FROM site_materials WHERE object_id = ? AND material = ?", 
                   (object_id, material))
    row = cursor.fetchone()
    if row and row[0] >= quantity:
        new_qty = row[0] - quantity
        if new_qty == 0:
            cursor.execute("DELETE FROM site_materials WHERE object_id = ? AND material = ?", 
                           (object_id, material))
        else:
            cursor.execute("UPDATE site_materials SET quantity = ? WHERE object_id = ? AND material = ?",
                           (new_qty, object_id, material))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def get_site_materials(object_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT material, quantity FROM site_materials WHERE object_id = ? AND quantity > 0", 
                   (object_id,))
    materials = [{"material": row[0], "quantity": row[1]} for row in cursor.fetchall()]
    conn.close()
    return materials

def add_finance_record(object_id, trans_type, amount, comment):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO finance (date, type, object_id, amount, comment) VALUES (?, ?, ?, ?, ?)",
                   (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), trans_type, object_id, amount, comment))
    conn.commit()
    conn.close()

def get_finance_by_object(object_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT type, amount, comment, date FROM finance WHERE object_id = ? ORDER BY date", 
                   (object_id,))
    records = [{"type": row[0], "amount": row[1], "comment": row[2], "date": row[3]} for row in cursor.fetchall()]
    conn.close()
    return records

def get_salary_work_types():
    return ["Демонтаж", "Штукатурка", "Стяжка", "Электрика", "Сантехника", "Финиш", "Плитка", "Покраска"]

def get_object_finance_summary(object_id):
    records = get_finance_by_object(object_id)
    total_income = sum(r['amount'] for r in records if r['type'] == 'income')
    total_expense_materials = sum(r['amount'] for r in records if r['type'] == 'expense_material')
    total_expense_salary = sum(r['amount'] for r in records if r['type'] == 'expense_salary')
    balance = total_income - (total_expense_materials + total_expense_salary)
    return {
        "total_income": total_income,
        "total_expense_materials": total_expense_materials,
        "total_expense_salary": total_expense_salary,
        "balance": balance
    }