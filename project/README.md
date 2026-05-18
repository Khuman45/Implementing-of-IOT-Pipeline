# CollabX — RDI Collaboration Platform

CollabX is a web-based Research, Development & Innovation (RDI) platform that connects students with research challenges. Students can discover challenges, submit proposals, and track their progress, while admins manage the platform, review submissions, and monitor activity.

---

## Features

### Student
- Register and log in securely
- Browse open research challenges in the **Research Arena**
- Submit proposals with automatic **ML scoring** based on content quality and skill keyword matching
- Track proposal status (Pending / Approved / Rejected)
- Manage a personal **skills profile**
- Receive real-time **notifications**
- View personal **activity log**

### Admin
- Approve or suspend student accounts
- Create, edit, and manage research challenges
- Review and act on student proposals
- View **analytics dashboard** with charts (proposals by status, top challenges)
- Monitor a full **activity log** across all users
- Post recruitment/job opportunities

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python · Flask |
| Database | SQLite |
| Frontend | Jinja2 Templates · HTML/CSS |
| Charts | Chart.js |
| Auth | Werkzeug password hashing |

---

## Project Structure

```
collabx/
├── app.py                  # Main Flask application & routes
├── init_db.py              # Database initialisation script
├── seed.py                 # Sample data seeder
├── database.db             # SQLite database
├── static/
│   └── style.css           # Global styles
└── templates/
    ├── base.html                # Shared layout & sidebar
    ├── login.html
    ├── register.html
    ├── student_dashboard.html
    ├── student_arena.html
    ├── student_skills.html
    ├── admin_dashboard.html
    ├── admin_students.html
    ├── admin_arena.html
    ├── admin_arena_edit.html
    ├── admin_view_student.html
    ├── admin_approve_form.html
    ├── admin_activity.html
    ├── notifications.html
    └── error.html
```

---

## Getting Started

### Prerequisites
- Python 3.10+
- pip

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/collabx.git
cd collabx

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install flask werkzeug

# 4. Initialise the database
python init_db.py

# 5. (Optional) Seed sample data
python seed.py

# 6. Run the app
flask run
```

Then open [http://localhost:5000](http://localhost:5000) in your browser.

---

## Default Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | singhranakhuman@gmail.com | `1234` |
| Student (seeded) | alice@student.com | `1234` |

> **Important:** Change the admin email and password before deploying to production.

---

## Database Schema

| Table | Description |
|-------|-------------|
| `users` | Students and admins with approval/suspension status |
| `challenges` | Research challenges posted by admins |
| `proposals` | Student proposals with ML scoring |
| `proposal_comments` | Comments on proposals |
| `recruitment` | Job/internship postings |
| `portfolio` | Student skill profiles |
| `notifications` | Per-user notification feed |
| `activity_log` | Full audit trail of user actions |
| `login_attempts` | Tracks login attempts for security |

---

## ML Proposal Scoring

Each proposal is automatically scored out of 100 when submitted:

- **Word count** — up to 30 points (more detail = higher score)
- **Skill keyword matching** — up to 50 points (how well the proposal matches the challenge's required skills)
- **Structure keywords** — up to 20 points (presence of words like *propose*, *implement*, *evaluate*, *objective*, etc.)

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---


