from flask import Flask, render_template, request, redirect, session
import sqlite3, math
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "collabx_secret_2024"
PER_PAGE = 10
MAX_ATTEMPTS = 5
LOCKOUT_MIN = 15

def get_db():
    db = sqlite3.connect("database.db")
    db.row_factory = sqlite3.Row
    return db

def log_activity(user_id, action, details=""):
    db = get_db(); db.execute("INSERT INTO activity_log(user_id,action,details) VALUES(?,?,?)",(user_id,action,details)); db.commit(); db.close()

def notify(user_id, message):
    db = get_db(); db.execute("INSERT INTO notifications(user_id,message) VALUES(?,?)",(user_id,message)); db.commit(); db.close()

def unread(user_id):
    db = get_db(); n = db.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0",(user_id,)).fetchone()[0]; db.close(); return n

def login_required(role=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if "user_id" not in session: return redirect("/")
            if role and session.get("role") != role: return render_template("error.html",message="Access denied.",code=403),403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# ── AUTH ──────────────────────────────────────────────────────────────────────
@app.route("/")
def login():
    if "user_id" in session: return redirect(f"/{session['role']}/dashboard")
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def do_login():
    email = request.form["email"].strip().lower()
    password = request.form["password"]
    db = get_db()
    cutoff = datetime.now() - timedelta(minutes=LOCKOUT_MIN)
    attempts = db.execute("SELECT COUNT(*) FROM login_attempts WHERE email=? AND attempted_at>?",(email,cutoff)).fetchone()[0]
    if attempts >= MAX_ATTEMPTS:
        db.close(); return render_template("login.html", error=f"Too many attempts. Wait {LOCKOUT_MIN} minutes.")
    user = db.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
    if not user or not check_password_hash(user["password"], password):
        db.execute("INSERT INTO login_attempts(email) VALUES(?)",(email,)); db.commit(); db.close()
        return render_template("login.html", error=f"Invalid credentials. {MAX_ATTEMPTS-attempts-1} attempts left.")
    if user["role"]=="student" and user["approved"]==0: db.close(); return render_template("login.html", error="Account pending admin approval.")
    if user["role"]=="student" and user["suspended"]==1: db.close(); return render_template("login.html", error="Your account has been suspended.")
    db.execute("DELETE FROM login_attempts WHERE email=?",(email,)); db.commit(); db.close()
    session.update({"user_id":user["id"],"name":user["name"],"email":user["email"],"role":user["role"]})
    log_activity(user["id"],"login",f"{user['name']} logged in")
    return redirect(f"/{user['role']}/dashboard")

@app.route("/logout")
def logout():
    if "user_id" in session: log_activity(session["user_id"],"logout","")
    session.clear(); return redirect("/")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="GET": return render_template("register.html")
    name=request.form["name"].strip(); email=request.form["email"].strip().lower()
    phone=request.form["phone"].strip(); password=request.form["password"]
    if len(password)<6: return render_template("register.html", error="Password must be at least 6 characters.")
    db=get_db()
    try:
        db.execute("INSERT INTO users(name,email,phone,password,role,approved,suspended) VALUES(?,?,?,?,?,?,?)",
                   (name,email,phone,generate_password_hash(password),"student",0,0))
        db.commit(); return render_template("login.html", message="Registration submitted! Awaiting admin approval.")
    except sqlite3.IntegrityError: return render_template("register.html", error="Email already registered.")
    finally: db.close()

@app.route("/notifications")
@login_required()
def notifications():
    db=get_db()
    notes=db.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC",(session["user_id"],)).fetchall()
    db.execute("UPDATE notifications SET is_read=1 WHERE user_id=?",(session["user_id"],)); db.commit(); db.close()
    return render_template("notifications.html", notifications=notes, unread_count=0)

# ── ADMIN DASHBOARD ───────────────────────────────────────────────────────────
@app.route("/admin/dashboard")
@login_required(role="admin")
def admin_dashboard():
    db=get_db()
    stats={
        "students":db.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0],
        "pending":db.execute("SELECT COUNT(*) FROM users WHERE role='student' AND approved=0").fetchone()[0],
        "challenges":db.execute("SELECT COUNT(*) FROM challenges").fetchone()[0],
        "proposals":db.execute("SELECT COUNT(*) FROM proposals").fetchone()[0],
        "recruitment":db.execute("SELECT COUNT(*) FROM recruitment").fetchone()[0],
        "approved_proposals":db.execute("SELECT COUNT(*) FROM proposals WHERE status='Approved'").fetchone()[0],
    }
    statuses=db.execute("SELECT status, COUNT(*) as cnt FROM proposals GROUP BY status").fetchall()
    top_challenges=db.execute("""SELECT c.title, COUNT(p.id) as cnt FROM challenges c
        LEFT JOIN proposals p ON c.id=p.challenge_id GROUP BY c.id ORDER BY cnt DESC LIMIT 5""").fetchall()
    recent_activity=db.execute("""SELECT a.action,a.details,a.created_at,u.name FROM activity_log a
        LEFT JOIN users u ON a.user_id=u.id ORDER BY a.created_at DESC LIMIT 10""").fetchall()
    db.close()
    return render_template("admin_dashboard.html", stats=stats, statuses=statuses,
                           top_challenges=top_challenges, recent_activity=recent_activity,
                           unread_count=unread(session["user_id"]))

# ── ADMIN STUDENTS ────────────────────────────────────────────────────────────
@app.route("/admin/students")
@login_required(role="admin")
def admin_students():
    q=request.args.get("q",""); fs=request.args.get("status","all"); page=int(request.args.get("page",1))
    db=get_db(); base="SELECT * FROM users WHERE role='student'"; params=[]
    if q: base+=" AND (name LIKE ? OR email LIKE ?)"; params+=[f"%{q}%",f"%{q}%"]
    if fs=="pending": base+=" AND approved=0 AND suspended=0"
    elif fs=="approved": base+=" AND approved=1 AND suspended=0"
    elif fs=="suspended": base+=" AND suspended=1"
    total=db.execute(f"SELECT COUNT(*) FROM ({base})",params).fetchone()[0]
    pages=max(1,math.ceil(total/PER_PAGE))
    students=db.execute(base+f" ORDER BY created_at DESC LIMIT {PER_PAGE} OFFSET {(page-1)*PER_PAGE}",params).fetchall()
    db.close()
    return render_template("admin_students.html", students=students, search=q, filter_status=fs,
                           page=page, pages=pages, total=total, unread_count=unread(session["user_id"]))

@app.route("/admin/approve_student/<int:id>")
@login_required(role="admin")
def approve_student(id):
    db=get_db(); s=db.execute("SELECT name FROM users WHERE id=?",(id,)).fetchone()
    db.execute("UPDATE users SET approved=1 WHERE id=?",(id,)); db.commit(); db.close()
    if s: notify(id,"Your account has been approved! You can now log in."); log_activity(session["user_id"],"approve_student",s["name"])
    return redirect("/admin/students")

@app.route("/admin/bulk_approve", methods=["POST"])
@login_required(role="admin")
def bulk_approve():
    ids=request.form.getlist("student_ids"); db=get_db()
    for sid in ids:
        db.execute("UPDATE users SET approved=1 WHERE id=?",(sid,)); notify(int(sid),"Your account has been approved!")
    db.commit(); db.close(); log_activity(session["user_id"],"bulk_approve",f"Bulk approved {len(ids)} students")
    return redirect("/admin/students")

@app.route("/admin/reject_student/<int:id>")
@login_required(role="admin")
def reject_student(id):
    db=get_db(); db.execute("DELETE FROM users WHERE id=?",(id,)); db.commit(); db.close()
    log_activity(session["user_id"],"reject_student",f"Rejected ID {id}"); return redirect("/admin/students")

@app.route("/admin/suspend_student/<int:id>")
@login_required(role="admin")
def suspend_student(id):
    db=get_db(); s=db.execute("SELECT name FROM users WHERE id=?",(id,)).fetchone()
    db.execute("UPDATE users SET suspended=1 WHERE id=?",(id,)); db.commit(); db.close()
    if s: notify(id,"Your account has been suspended."); log_activity(session["user_id"],"suspend",s["name"])
    return redirect("/admin/students")

@app.route("/admin/unsuspend_student/<int:id>")
@login_required(role="admin")
def unsuspend_student(id):
    db=get_db(); db.execute("UPDATE users SET suspended=0 WHERE id=?",(id,)); db.commit(); db.close()
    return redirect("/admin/students")

# ── ADMIN CHALLENGES ──────────────────────────────────────────────────────────
@app.route("/admin/challenges", methods=["GET","POST"])
@login_required(role="admin")
def admin_challenges():
    db=get_db()
    if request.method=="POST":
        db.execute("INSERT INTO challenges(title,description,deadline,skills) VALUES(?,?,?,?)",
                   (request.form["title"],request.form["description"],request.form["deadline"],request.form["skills"]))
        db.commit(); log_activity(session["user_id"],"create_challenge",request.form["title"])
    challenges=db.execute("SELECT * FROM challenges ORDER BY created_at DESC").fetchall(); db.close()
    return redirect("/admin/arena")

@app.route("/admin/edit_challenge/<int:id>", methods=["GET","POST"])
@login_required(role="admin")
def edit_challenge(id):
    db=get_db()
    if request.method=="POST":
        db.execute("UPDATE challenges SET title=?,description=?,deadline=?,skills=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                   (request.form["title"],request.form["description"],request.form["deadline"],request.form["skills"],id))
        db.commit(); db.close(); return redirect("/admin/challenges")
    c=db.execute("SELECT * FROM challenges WHERE id=?",(id,)).fetchone(); db.close()
    return render_template("admin_edit_challenge.html", challenge=c, unread_count=unread(session["user_id"]))

@app.route("/admin/delete_challenge/<int:id>")
@login_required(role="admin")
def delete_challenge(id):
    db=get_db(); db.execute("DELETE FROM challenges WHERE id=?",(id,)); db.commit(); db.close()
    return redirect("/admin/challenges")

# ── ADMIN PROPOSALS ───────────────────────────────────────────────────────────
@app.route("/admin/proposals")
@login_required(role="admin")
def admin_proposals():
    q=request.args.get("q",""); fs=request.args.get("status","all"); page=int(request.args.get("page",1))
    db=get_db()
    base="""SELECT p.*,u.name as student_name,c.title as challenge_title
            FROM proposals p JOIN users u ON p.student_id=u.id JOIN challenges c ON p.challenge_id=c.id WHERE 1=1"""
    params=[]
    if q: base+=" AND (u.name LIKE ? OR p.title LIKE ?)"; params+=[f"%{q}%",f"%{q}%"]
    if fs!="all": base+=" AND p.status=?"; params.append(fs)
    total=db.execute(f"SELECT COUNT(*) FROM ({base})",params).fetchone()[0]
    pages=max(1,math.ceil(total/PER_PAGE))
    proposals=db.execute(base+f" ORDER BY p.created_at DESC LIMIT {PER_PAGE} OFFSET {(page-1)*PER_PAGE}",params).fetchall()
    db.close()
    return redirect("/admin/arena")

@app.route("/admin/proposal/<int:id>", methods=["GET","POST"])
@login_required(role="admin")
def admin_proposal_detail(id):
    db=get_db()
    if request.method=="POST":
        if "status" in request.form:
            status=request.form["status"]
            db.execute("UPDATE proposals SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(status,id))
            db.commit(); p=db.execute("SELECT student_id,title FROM proposals WHERE id=?",(id,)).fetchone()
            if p: notify(p["student_id"],f"Your proposal '{p['title']}' is now: {status}")
        if "comment" in request.form:
            c=request.form["comment"].strip()
            if c: db.execute("INSERT INTO proposal_comments(proposal_id,user_id,comment) VALUES(?,?,?)",(id,session["user_id"],c)); db.commit()
        db.close(); return redirect(f"/admin/proposal/{id}")
    proposal=db.execute("""SELECT p.*,u.name as student_name,u.email as student_email,c.title as challenge_title
        FROM proposals p JOIN users u ON p.student_id=u.id JOIN challenges c ON p.challenge_id=c.id
        WHERE p.id=?""",(id,)).fetchone()
    comments=db.execute("""SELECT pc.*,u.name as commenter_name,u.role as commenter_role
        FROM proposal_comments pc JOIN users u ON pc.user_id=u.id
        WHERE pc.proposal_id=? ORDER BY pc.created_at""",(id,)).fetchall()
    db.close()
    return render_template("admin_proposal_detail.html", proposal=proposal, comments=comments,
                           unread_count=unread(session["user_id"]))

# ── ADMIN RECRUITMENT ─────────────────────────────────────────────────────────
@app.route("/admin/recruitment", methods=["GET","POST"])
@login_required(role="admin")
def admin_recruitment():
    db=get_db()
    if request.method=="POST":
        db.execute("INSERT INTO recruitment(title,description,type,deadline) VALUES(?,?,?,?)",
                   (request.form["title"],request.form["description"],request.form["rtype"],request.form["deadline"]))
        db.commit()
    posts=db.execute("SELECT * FROM recruitment ORDER BY created_at DESC").fetchall(); db.close()
    return redirect("/admin/arena")

@app.route("/admin/delete_recruitment/<int:id>")
@login_required(role="admin")
def delete_recruitment(id):
    db=get_db(); db.execute("DELETE FROM recruitment WHERE id=?",(id,)); db.commit(); db.close()
    return redirect("/admin/recruitment")

# ── ADMIN PORTFOLIOS ──────────────────────────────────────────────────────────
@app.route("/admin/portfolios")
@login_required(role="admin")
def admin_portfolios():
    q=request.args.get("q",""); db=get_db()
    base="SELECT u.name,u.email,p.bio,p.skills,p.projects,p.resume,p.created_at FROM portfolio p JOIN users u ON p.student_id=u.id WHERE 1=1"
    params=[]
    if q: base+=" AND (u.name LIKE ? OR p.skills LIKE ?)"; params+=[f"%{q}%",f"%{q}%"]
    data=db.execute(base+" ORDER BY p.created_at DESC",params).fetchall(); db.close()
    return redirect("/admin/arena")

# ── ADMIN ACTIVITY ────────────────────────────────────────────────────────────
@app.route("/admin/activity")
@login_required(role="admin")
def admin_activity():
    page=int(request.args.get("page",1)); db=get_db()
    total=db.execute("SELECT COUNT(*) FROM activity_log").fetchone()[0]
    pages=max(1,math.ceil(total/PER_PAGE))
    logs=db.execute("""SELECT a.*,u.name FROM activity_log a LEFT JOIN users u ON a.user_id=u.id
        ORDER BY a.created_at DESC LIMIT ? OFFSET ?""",(PER_PAGE,(page-1)*PER_PAGE)).fetchall()
    db.close()
    return render_template("admin_activity.html", logs=logs, page=page, pages=pages,
                           unread_count=unread(session["user_id"]))

# ── STUDENT DASHBOARD ─────────────────────────────────────────────────────────
@app.route("/student/dashboard")
@login_required(role="student")
def student_dashboard():
    db=get_db(); uid=session["user_id"]
    challenges_count=db.execute("SELECT COUNT(*) FROM challenges").fetchone()[0]
    my_proposals=db.execute("SELECT COUNT(*) FROM proposals WHERE student_id=?",(uid,)).fetchone()[0]
    approved_proposals=db.execute("SELECT COUNT(*) FROM proposals WHERE student_id=? AND status='Approved'",(uid,)).fetchone()[0]
    recruit_count=db.execute("SELECT COUNT(*) FROM recruitment").fetchone()[0]
    recent_proposals=db.execute("""SELECT p.title,p.status,p.ml_score,c.title as challenge_title,p.created_at
        FROM proposals p JOIN challenges c ON p.challenge_id=c.id
        WHERE p.student_id=? ORDER BY p.created_at DESC LIMIT 3""",(uid,)).fetchall()
    has_portfolio=db.execute("SELECT id FROM portfolio WHERE student_id=?",(uid,)).fetchone()
    db.close()
    return render_template("student_dashboard.html",
                           challenges_count=challenges_count, my_proposals=my_proposals,
                           approved_proposals=approved_proposals, recruit_count=recruit_count,
                           recent_proposals=recent_proposals, has_portfolio=has_portfolio,
                           unread_count=unread(uid))

# ── STUDENT CHALLENGES ────────────────────────────────────────────────────────
@app.route("/student/challenges")
@login_required(role="student")
def student_challenges():
    q=request.args.get("q",""); skill=request.args.get("skill",""); db=get_db()
    base="SELECT * FROM challenges WHERE 1=1"; params=[]
    if q: base+=" AND (title LIKE ? OR description LIKE ?)"; params+=[f"%{q}%",f"%{q}%"]
    if skill: base+=" AND skills LIKE ?"; params.append(f"%{skill}%")
    challenges=db.execute(base+" ORDER BY created_at DESC",params).fetchall()
    applied_ids=set(r[0] for r in db.execute("SELECT challenge_id FROM proposals WHERE student_id=?",(session["user_id"],)).fetchall())
    db.close()
    return render_template("student_challenges.html", challenges=challenges, applied_ids=applied_ids,
                           search=q, skill_filter=skill, unread_count=unread(session["user_id"]))

@app.route("/student/propose/<int:challenge_id>", methods=["GET","POST"])
@login_required(role="student")
def student_propose(challenge_id):
    db=get_db(); challenge=db.execute("SELECT * FROM challenges WHERE id=?",(challenge_id,)).fetchone()
    if not challenge: db.close(); return render_template("error.html",message="Challenge not found.",code=404),404
    already=db.execute("SELECT id FROM proposals WHERE student_id=? AND challenge_id=?",(session["user_id"],challenge_id)).fetchone()
    if request.method=="POST" and not already:
        db.execute("INSERT INTO proposals(student_id,challenge_id,title,description,status) VALUES(?,?,?,?,?)",
                   (session["user_id"],challenge_id,request.form["title"],request.form["description"],"Pending"))
        db.commit(); db.close(); return redirect("/student/proposals")
    db.close()
    return render_template("student_propose.html", challenge=challenge, already=already,
                           unread_count=unread(session["user_id"]))

@app.route("/student/proposals")
@login_required(role="student")
def student_proposals():
    db=get_db()
    proposals=db.execute("""SELECT p.*,c.title as challenge_title FROM proposals p
        JOIN challenges c ON p.challenge_id=c.id WHERE p.student_id=? ORDER BY p.created_at DESC""",
        (session["user_id"],)).fetchall()
    db.close()
    return redirect("/student/arena")

@app.route("/student/proposal/<int:id>", methods=["GET","POST"])
@login_required(role="student")
def student_proposal_detail(id):
    db=get_db()
    proposal=db.execute("""SELECT p.*,c.title as challenge_title FROM proposals p
        JOIN challenges c ON p.challenge_id=c.id WHERE p.id=? AND p.student_id=?""",(id,session["user_id"])).fetchone()
    if not proposal: db.close(); return render_template("error.html",message="Not found.",code=404),404
    if request.method=="POST":
        c=request.form.get("comment","").strip()
        if c: db.execute("INSERT INTO proposal_comments(proposal_id,user_id,comment) VALUES(?,?,?)",(id,session["user_id"],c)); db.commit()
        db.close(); return redirect(f"/student/proposal/{id}")
    comments=db.execute("""SELECT pc.*,u.name as commenter_name,u.role as commenter_role
        FROM proposal_comments pc JOIN users u ON pc.user_id=u.id WHERE pc.proposal_id=? ORDER BY pc.created_at""",(id,)).fetchall()
    db.close()
    return render_template("student_proposal_detail.html", proposal=proposal, comments=comments,
                           unread_count=unread(session["user_id"]))

# ── STUDENT RECRUITMENT ───────────────────────────────────────────────────────
@app.route("/student/recruitment")
@login_required(role="student")
def student_recruitment():
    db=get_db(); posts=db.execute("SELECT * FROM recruitment ORDER BY created_at DESC").fetchall(); db.close()
    return redirect("/student/arena")

# ── STUDENT PORTFOLIO ─────────────────────────────────────────────────────────
@app.route("/student/portfolio", methods=["GET","POST"])
@login_required(role="student")
def student_portfolio():
    db=get_db(); uid=session["user_id"]
    if request.method=="POST":
        bio=request.form.get("bio",""); skills=request.form.get("skills","")
        projects=request.form.get("projects",""); resume=request.form.get("resume","")
        existing=db.execute("SELECT id FROM portfolio WHERE student_id=?",(uid,)).fetchone()
        if existing:
            db.execute("UPDATE portfolio SET bio=?,skills=?,projects=?,resume=?,updated_at=CURRENT_TIMESTAMP WHERE student_id=?",
                       (bio,skills,projects,resume,uid))
        else:
            db.execute("INSERT INTO portfolio(student_id,bio,skills,projects,resume) VALUES(?,?,?,?,?)",(uid,bio,skills,projects,resume))
        db.commit(); db.close(); return redirect("/student/portfolio")
    portfolio=db.execute("SELECT * FROM portfolio WHERE student_id=?",(uid,)).fetchone()
    proposals_count=db.execute("SELECT COUNT(*) FROM proposals WHERE student_id=?",(uid,)).fetchone()[0]
    approved_count=db.execute("SELECT COUNT(*) FROM proposals WHERE student_id=? AND status='Approved'",(uid,)).fetchone()[0]
    db.close()
    return redirect("/student/arena")

@app.errorhandler(404)
def not_found(e): return render_template("error.html",message="Page not found.",code=404),404
@app.errorhandler(500)
def server_error(e): return render_template("error.html",message="Server error.",code=500),500

# ROUTES ABOVE THIS LINE

# ML SCORING ENGINE
def ml_score_proposal(content, required_skills):
    score = 0
    keywords_matched = 0
    keywords_total = 0
    words = len(content.split())
    if words >= 150: score += 30
    elif words >= 80: score += 20
    elif words >= 40: score += 10
    else: score += 5
    if required_skills:
        skills = [s.strip().lower() for s in required_skills.split(',')]
        keywords_total = len(skills)
        content_lower = content.lower()
        for skill in skills:
            if skill in content_lower:
                keywords_matched += 1
        if keywords_total > 0:
            score += int((keywords_matched / keywords_total) * 50)
    structure_words = ["propose","approach","method","objective","goal","implement","solution","result","analysis","research","develop","design","test","evaluate","outcome"]
    content_lower = content.lower()
    found = sum(1 for w in structure_words if w in content_lower)
    score += min(20, found * 4)
    return min(100, score), keywords_matched, keywords_total

# ADMIN ARENA
@app.route("/admin/arena")
@login_required(role="admin")
def admin_arena():
    db = get_db()
    challenges = db.execute("SELECT * FROM challenges ORDER BY created_at DESC").fetchall()
    result = []
    for c in challenges:
        proposals = db.execute("""SELECT p.*, u.name as student_name FROM proposals p JOIN users u ON p.student_id=u.id WHERE p.challenge_id=? ORDER BY p.ml_score DESC""", (c["id"],)).fetchall()
        result.append({"id":c["id"],"title":c["title"],"description":c["description"],"skills":c["skills"],"deadline":c["deadline"],"proposals":proposals})
    db.close()
    return render_template("admin_arena.html", challenges=result, unread_count=unread(session["user_id"]))

@app.route("/admin/arena/post", methods=["POST"])
@login_required(role="admin")
def admin_arena_post():
    title = request.form["title"]
    description = request.form["description"]
    skills = request.form.get("skills","")
    deadline = request.form.get("deadline","")
    db = get_db()
    db.execute("INSERT INTO challenges(title,description,skills,deadline) VALUES(?,?,?,?)",(title,description,skills,deadline))
    db.commit(); db.close()
    log_activity(session["user_id"],"post_challenge",title)
    return redirect("/admin/arena")

@app.route("/admin/arena/approve/<int:pid>", methods=["GET","POST"])
@login_required(role="admin")
def admin_arena_approve(pid):
    db = get_db()
    if request.method == "POST":
        msg = request.form.get("message", "Your proposal has been approved!")
        p = db.execute("SELECT * FROM proposals WHERE id=?",(pid,)).fetchone()
        db.execute("UPDATE proposals SET status='approved', admin_message=? WHERE id=?",(msg,pid))
        db.commit(); db.close()
        if p: notify(p["student_id"], "Your proposal was approved! Message: " + msg)
        log_activity(session["user_id"],"approve_proposal",str(pid))
        return redirect("/admin/arena")
    p = db.execute("SELECT p.*, u.name as student_name, c.title as challenge_title FROM proposals p JOIN users u ON p.student_id=u.id JOIN challenges c ON p.challenge_id=c.id WHERE p.id=?",(pid,)).fetchone()
    db.close()
    return render_template("admin_approve_form.html", p=p, unread_count=unread(session["user_id"]))

@app.route("/admin/arena/reject/<int:pid>")
@login_required(role="admin")
def admin_arena_reject(pid):
    db = get_db()
    p = db.execute("SELECT * FROM proposals WHERE id=?",(pid,)).fetchone()
    db.execute("UPDATE proposals SET status='rejected' WHERE id=?",(pid,))
    db.commit(); db.close()
    if p: notify(p["student_id"],"Your proposal was not selected this time.")
    log_activity(session["user_id"],"reject_proposal",str(pid))
    return redirect("/admin/arena")

# STUDENT ARENA
@app.route("/student/arena")
@login_required(role="student")
def student_arena():
    db = get_db()
    uid = session["user_id"]
    challenges = db.execute("SELECT * FROM challenges ORDER BY created_at DESC").fetchall()
    result = []
    for c in challenges:
        my_proposal = db.execute("SELECT * FROM proposals WHERE challenge_id=? AND student_id=?",(c["id"],uid)).fetchone()
        result.append({"id":c["id"],"title":c["title"],"description":c["description"],"skills":c["skills"],"deadline":c["deadline"],"my_proposal":my_proposal})
    db.close()
    my_skills = ""
    p = get_db().execute("SELECT skills FROM portfolio WHERE student_id=?", (uid,)).fetchone()
    if p: my_skills = p["skills"] or ""
    return render_template("student_arena.html", challenges=result, my_skills=my_skills, unread_count=unread(uid))

@app.route("/student/arena/submit", methods=["POST"])
@login_required(role="student")
def student_arena_submit():
    uid = session["user_id"]
    challenge_id = request.form["challenge_id"]
    content = request.form["content"]
    db = get_db()
    challenge = db.execute("SELECT * FROM challenges WHERE id=?",(challenge_id,)).fetchone()
    skills = challenge["skills"] if challenge else ""
    score, kw_matched, kw_total = ml_score_proposal(content, skills)
    db.execute("INSERT INTO proposals(challenge_id,student_id,content,status,ml_score,ml_keywords_matched,ml_keywords_total) VALUES(?,?,?,?,?,?,?)",(challenge_id,uid,content,"pending",score,kw_matched,kw_total))
    db.commit(); db.close()
    log_activity(uid,"submit_proposal",f"Score: {score}/100")
    return redirect("/student/arena")

# STUDENT ACTIVITY
@app.route("/student/activity")
@login_required(role="student")
def student_activity():
    db = get_db()
    uid = session["user_id"]
    logs = db.execute("SELECT * FROM activity_log WHERE user_id=? ORDER BY created_at DESC LIMIT 50",(uid,)).fetchall()
    db.close()
    return render_template("admin_activity.html", logs=logs, page=1, pages=1, unread_count=unread(uid))


# SAVE STUDENT SKILLS
@app.route("/student/save_skills", methods=["POST"])
@login_required(role="student")
def save_student_skills():
    uid = session["user_id"]
    skills = request.form.get("skills", "")
    db = get_db()
    existing = db.execute("SELECT id FROM portfolio WHERE student_id=?", (uid,)).fetchone()
    if existing:
        db.execute("UPDATE portfolio SET skills=? WHERE student_id=?", (skills, uid))
    else:
        db.execute("INSERT INTO portfolio(student_id, skills) VALUES(?,?)", (uid, skills))
    db.commit()
    db.close()
    return redirect("/student/arena")

# STUDENT SKILLS PAGE
@app.route("/student/skills")
@login_required(role="student")
def student_skills():
    uid = session["user_id"]
    db = get_db()
    skills = db.execute("SELECT * FROM student_skills WHERE student_id=? ORDER BY skill_name", (uid,)).fetchall()
    challenges = db.execute("SELECT * FROM challenges").fetchall()
    skill_names = set(s["skill_name"] for s in skills)
    matched_challenges = sum(1 for c in challenges if c["skills"] and any(s in c["skills"].lower() for s in skill_names))
    from collections import Counter
    all_required = []
    for c in challenges:
        if c["skills"]:
            all_required.extend([s.strip().lower() for s in c["skills"].split(",")])
    freq = Counter(all_required)
    missing = [(s,c) for s,c in freq.most_common(10) if s not in skill_names]
    completeness = min(100, len(skills) * 20)
    if completeness < 40: msg = "Add more skills to improve your challenge matches"
    elif completeness < 80: msg = "Good progress! Add a few more skills"
    else: msg = "Great profile! You are well positioned for challenges"
    db.close()
    return render_template("student_skills.html", skills=skills, matched_challenges=matched_challenges,
                           total_challenges=len(challenges), missing_skills=missing[:8],
                           top_recommended=missing[:5], completeness=completeness,
                           completeness_msg=msg, unread_count=unread(uid))
    uid = session["user_id"]
    db = get_db()
    if request.method == "POST":
        skills = request.form.get("skills", "")
        existing = db.execute("SELECT id FROM portfolio WHERE student_id=?", (uid,)).fetchone()
        if existing:
            db.execute("UPDATE portfolio SET skills=? WHERE student_id=?", (skills, uid))
        else:
            db.execute("INSERT INTO portfolio(student_id, skills) VALUES(?,?)", (uid, skills))
        db.commit()
        log_activity(uid, "update_skills", skills)
        return redirect("/student/skills")

    portfolio = db.execute("SELECT * FROM portfolio WHERE student_id=?", (uid,)).fetchone()
    my_skills = portfolio["skills"] if portfolio and portfolio["skills"] else ""

    # Get all challenges and their required skills
    challenges = db.execute("SELECT * FROM challenges").fetchall()
    db.close()

    # Skill gap analysis
    all_required = []
    matched_challenges = 0
    for c in challenges:
        if c["skills"]:
            req = [s.strip().lower() for s in c["skills"].split(",")]
            all_required.extend(req)
            student_set = set(s.strip().lower() for s in my_skills.split(",")) if my_skills else set()
            if any(s in student_set for s in req):
                matched_challenges += 1

    # Skill frequency across all challenges
    from collections import Counter
    skill_freq = Counter(all_required)
    student_set = set(s.strip().lower() for s in my_skills.split(",")) if my_skills else set()
    missing_skills = [(s, c) for s, c in skill_freq.most_common(10) if s not in student_set]
    top_recommended = missing_skills[:5]

    return render_template("student_skills.html",
                           my_skills=my_skills,
                           matched_challenges=matched_challenges,
                           total_challenges=len(challenges),
                           top_recommended=top_recommended,
                           missing_skills=missing_skills[:8],
                           unread_count=unread(uid))


@app.route("/student/skills/clear")
@login_required(role="student")
def clear_student_skills():
    uid = session["user_id"]
    db = get_db()
    db.execute("UPDATE portfolio SET skills='' WHERE student_id=?", (uid,))
    db.commit(); db.close()
    return redirect("/student/skills")


# SKILLS ADD
@app.route("/student/skills/add", methods=["POST"])
@login_required(role="student")
def add_skill():
    uid = session["user_id"]
    skill_name = request.form.get("skill_name", "").strip().lower()
    skill_level = request.form.get("skill_level", "Intermediate")
    if skill_name:
        db = get_db()
        try:
            db.execute("INSERT INTO student_skills(student_id,skill_name,skill_level) VALUES(?,?,?)",
                       (uid, skill_name, skill_level))
            db.commit()
        except: pass
        db.close()
    return redirect("/student/skills")

# SKILLS QUICK ADD
@app.route("/student/skills/quickadd/<skill>")
@login_required(role="student")
def quickadd_skill(skill):
    uid = session["user_id"]
    db = get_db()
    try:
        db.execute("INSERT INTO student_skills(student_id,skill_name,skill_level) VALUES(?,?,?)",
                   (uid, skill.lower(), "Intermediate"))
        db.commit()
    except: pass
    db.close()
    return redirect("/student/skills")

# SKILLS EDIT LEVEL
@app.route("/student/skills/edit/<int:sid>", methods=["POST"])
@login_required(role="student")
def edit_skill(sid):
    uid = session["user_id"]
    level = request.form.get("skill_level", "Intermediate")
    db = get_db()
    db.execute("UPDATE student_skills SET skill_level=? WHERE id=? AND student_id=?", (level, sid, uid))
    db.commit(); db.close()
    return redirect("/student/skills")

# SKILLS DELETE
@app.route("/student/skills/delete/<int:sid>")
@login_required(role="student")
def delete_skill(sid):
    uid = session["user_id"]
    db = get_db()
    db.execute("DELETE FROM student_skills WHERE id=? AND student_id=?", (sid, uid))
    db.commit(); db.close()
    return redirect("/student/skills")


@app.route("/admin/arena/edit/<int:cid>", methods=["GET","POST"])
@login_required(role="admin")
def admin_arena_edit(cid):
    db = get_db()
    if request.method == "POST":
        db.execute("UPDATE challenges SET title=?,description=?,skills=?,deadline=? WHERE id=?",
                   (request.form["title"],request.form["description"],
                    request.form.get("skills",""),request.form.get("deadline",""),cid))
        db.commit(); db.close()
        log_activity(session["user_id"],"edit_challenge",str(cid))
        return redirect("/admin/arena")
    c = db.execute("SELECT * FROM challenges WHERE id=?",(cid,)).fetchone()
    db.close()
    return render_template("admin_arena_edit.html", challenge=c, unread_count=unread(session["user_id"]))

@app.route("/admin/arena/delete/<int:cid>")
@login_required(role="admin")
def admin_arena_delete(cid):
    db = get_db()
    db.execute("DELETE FROM proposals WHERE challenge_id=?",(cid,))
    db.execute("DELETE FROM challenges WHERE id=?",(cid,))
    db.commit(); db.close()
    log_activity(session["user_id"],"delete_challenge",str(cid))
    return redirect("/admin/arena")


@app.route("/admin/arena/reject_reason/<int:pid>", methods=["POST"])
@login_required(role="admin")
def admin_arena_reject_reason(pid):
    reason = request.form.get("reason", "Your proposal was not selected.")
    db = get_db()
    p = db.execute("SELECT * FROM proposals WHERE id=?", (pid,)).fetchone()
    db.execute("UPDATE proposals SET status='rejected' WHERE id=?", (pid,))
    db.commit(); db.close()
    if p: notify(p["student_id"], f"Your proposal was not selected. Reason: {reason}")
    log_activity(session["user_id"], "reject_proposal", reason)
    return redirect("/admin/arena")



@app.route("/admin/view_student/<int:sid>")
@login_required(role="admin")
def admin_view_student(sid):
    db = get_db()
    student = db.execute("SELECT * FROM users WHERE id=?", (sid,)).fetchone()
    skills = db.execute("SELECT * FROM student_skills WHERE student_id=?", (sid,)).fetchall()
    proposals = db.execute("""SELECT p.*, c.title as challenge_title FROM proposals p
                               JOIN challenges c ON p.challenge_id=c.id
                               WHERE p.student_id=?""", (sid,)).fetchall()
    db.close()
    return render_template("admin_view_student.html", student=student, skills=skills,
                           proposals=proposals, unread_count=unread(session["user_id"]))


@app.route("/student/arena/accept/<int:pid>")
@login_required(role="student")
def student_accept_proposal(pid):
    uid = session["user_id"]
    db = get_db()
    db.execute("UPDATE proposals SET student_response='accepted', status='active' WHERE id=? AND student_id=?", (pid, uid))
    db.commit(); db.close()
    log_activity(uid, "accepted_proposal", str(pid))
    return redirect("/student/arena")

@app.route("/student/arena/decline/<int:pid>")
@login_required(role="student")
def student_decline_proposal(pid):
    uid = session["user_id"]
    db = get_db()
    db.execute("UPDATE proposals SET student_response='declined', status='declined' WHERE id=? AND student_id=?", (pid, uid))
    db.commit(); db.close()
    log_activity(uid, "declined_proposal", str(pid))
    return redirect("/student/arena")


if __name__ == "__main__":
    app.run(debug=True)
