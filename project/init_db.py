import sqlite3
from werkzeug.security import generate_password_hash

db = sqlite3.connect("database.db")

db.execute("""CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
    phone TEXT, password TEXT NOT NULL, role TEXT DEFAULT 'student',
    approved INTEGER DEFAULT 0, suspended INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

db.execute("""CREATE TABLE IF NOT EXISTS challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT,
    deadline TEXT, skills TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

db.execute("""CREATE TABLE IF NOT EXISTS proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL, challenge_id INTEGER NOT NULL,
    title TEXT NOT NULL, description TEXT, status TEXT DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

db.execute("""CREATE TABLE IF NOT EXISTS proposal_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT, proposal_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
    comment TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

db.execute("""CREATE TABLE IF NOT EXISTS recruitment (
    id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT,
    type TEXT, deadline TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

db.execute("""CREATE TABLE IF NOT EXISTS portfolio (
    id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER UNIQUE NOT NULL,
    bio TEXT, skills TEXT, projects TEXT, resume TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

db.execute("""CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, message TEXT NOT NULL,
    is_read INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

db.execute("""CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT NOT NULL,
    details TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

db.execute("""CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL,
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

db.execute("INSERT OR IGNORE INTO users(name,email,phone,password,role,approved,suspended) VALUES(?,?,?,?,?,?,?)",
           ('Admin','singhranakhuman@gmail.com','0000000000', generate_password_hash('1234'),'admin',1,0))

db.commit()
db.close()
print("Database ready!")
