import sqlite3
from werkzeug.security import generate_password_hash

db = sqlite3.connect("database.db")

students = [
    ("Alice Johnson",  "alice@student.com"),
    ("Bob Smith",      "bob@student.com"),
    ("Sara Ahmed",     "sara@student.com"),
    ("James Lee",      "james@student.com"),
    ("Priya Patel",    "priya@student.com"),
    ("Raj Kumar",      "raj@student.com"),
    ("Emma Wilson",    "emma@student.com"),
    ("Omar Hassan",    "omar@student.com"),
    ("Lily Chen",      "lily@student.com"),
    ("David Park",     "david@student.com"),
]

student_ids = []
for name, email in students:
    try:
        cur = db.execute(
            "INSERT INTO users(name,email,password,role,approved,suspended) VALUES(?,?,?,?,?,?)",
            (name, email, generate_password_hash("1234"), "student", 1, 0))
        student_ids.append(cur.lastrowid)
        print(f"Added: {name}")
    except:
        row = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if row: student_ids.append(row[0])
        print(f"Exists: {name}")

challenges = [
    ("AI in Healthcare", "Design an AI solution to improve patient diagnosis accuracy.", "Python, Machine Learning, Data Analysis", "2025-07-01"),
    ("Smart Campus App", "Build a mobile app to improve student experience on campus.", "React, Node.js, UI Design", "2025-07-15"),
    ("Sustainability Tracker", "Create a system to track and reduce carbon footprint.", "Python, IoT, Data Visualization", "2025-08-01"),
    ("Cybersecurity Framework", "Develop a security framework for small organisations.", "Linux, Networking, Cybersecurity", "2025-08-15"),
    ("NLP Research Tool", "Build a tool to analyse research papers using NLP.", "Python, NLP, Machine Learning", "2025-09-01"),
]

challenge_ids = []
for title, desc, skills, deadline in challenges:
    try:
        cur = db.execute(
            "INSERT INTO challenges(title,description,skills,deadline) VALUES(?,?,?,?)",
            (title, desc, skills, deadline))
        challenge_ids.append(cur.lastrowid)
        print(f"Added challenge: {title}")
    except:
        row = db.execute("SELECT id FROM challenges WHERE title=?", (title,)).fetchone()
        if row: challenge_ids.append(row[0])

proposals = [
    (0, 0, "I propose to develop a machine learning model using Python to analyse patient data. My approach involves data analysis of medical records, implementing classification algorithms, and evaluating results. The solution will improve diagnosis accuracy by identifying patterns in patient data through systematic research and testing."),
    (0, 1, "Using Python and machine learning techniques, I will research and implement a deep learning solution. The methodology includes data preprocessing, model training, and evaluation. I propose to develop neural networks that can identify medical conditions with high accuracy through careful analysis and testing."),
    (1, 2, "Build app"),
    (1, 3, "I will design and implement a mobile application using React and Node.js. The objective is to improve campus experience through features like timetable management, event notifications, and resource booking. My approach involves user research, UI design prototyping, and iterative development."),
    (2, 4, "I propose a sustainability tracking system using Python and IoT sensors. The goal is to monitor energy consumption and carbon emissions across campus. My solution involves data visualization dashboards and automated alerts to help reduce environmental impact through research and analysis."),
    (2, 5, "Track carbon"),
    (3, 6, "Develop security framework using Linux and networking protocols. I will research existing vulnerabilities, implement security measures, and evaluate the solution through penetration testing. The objective is to provide small organisations with affordable cybersecurity protection."),
    (3, 7, "I will implement network security"),
    (4, 8, "I propose to build an NLP research tool using Python and machine learning. My approach involves natural language processing to extract key insights from research papers. The solution will help researchers identify relevant studies, analyse citations, and discover research gaps through automated text analysis."),
    (4, 9, "Build NLP tool for papers"),
]

for chal_idx, stud_idx, content in proposals:
    if chal_idx < len(challenge_ids) and stud_idx < len(student_ids):
        chal_id = challenge_ids[chal_idx]
        stud_id = student_ids[stud_idx]
        words = len(content.split())
        score = 0
        if words >= 150: score += 30
        elif words >= 80: score += 20
        elif words >= 40: score += 10
        else: score += 5
        challenge = db.execute("SELECT skills FROM challenges WHERE id=?", (chal_id,)).fetchone()
        skills = challenge[0] if challenge else ""
        kw_matched = 0
        kw_total = 0
        if skills:
            skill_list = [s.strip().lower() for s in skills.split(',')]
            kw_total = len(skill_list)
            for skill in skill_list:
                if skill in content.lower():
                    kw_matched += 1
            if kw_total > 0:
                score += int((kw_matched / kw_total) * 50)
        structure_words = ["propose","approach","method","objective","goal","implement","solution","result","analysis","research","develop","design","test","evaluate","outcome"]
        found = sum(1 for w in structure_words if w in content.lower())
        score += min(20, found * 4)
        score = min(100, score)
        try:
            db.execute(
                "INSERT INTO proposals(challenge_id,student_id,content,status,ml_score,ml_keywords_matched,ml_keywords_total) VALUES(?,?,?,?,?,?,?)",
                (chal_id, stud_id, content, "pending", score, kw_matched, kw_total))
            print(f"Proposal added — Score: {score}/100")
        except Exception as e:
            print(f"Skip: {e}")

db.commit()
db.close()
print("\nDone! All passwords are 1234")
