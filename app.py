import csv
import io
import json
import os
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, Response, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

from scheduler import ALGORITHM_LABELS, compare_algorithms, parse_task_csv


BASE_DIR = Path(__file__).resolve().parent
db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user", nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CloudResource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    cpu = db.Column(db.Integer, nullable=False)
    ram = db.Column(db.Float, nullable=False)
    mips = db.Column(db.Float, nullable=False)
    cost = db.Column(db.Float, nullable=False)
    energy = db.Column(db.Float, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)

    def as_dict(self):
        return {"id": self.id, "name": self.name, "cpu": self.cpu, "ram": self.ram,
                "mips": self.mips, "cost": self.cost, "energy": self.energy}


class Workflow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    deadline = db.Column(db.Float, default=100)
    budget = db.Column(db.Float, default=100)
    objective = db.Column(db.String(30), default="balanced")
    tasks_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    owner = db.relationship("User", backref="workflows")

    @property
    def tasks(self):
        return json.loads(self.tasks_json)


class ScheduleRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey("workflow.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    result_json = db.Column(db.Text, nullable=False)
    best_algorithm = db.Column(db.String(40), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    workflow = db.relationship("Workflow", backref="runs")
    user = db.relationship("User", backref="schedule_runs")

    @property
    def result(self):
        return json.loads(self.result_json)


def create_app(test_config=None):
    app = Flask(__name__)
    default_db = "sqlite:///" + str(BASE_DIR / "instance" / "cloudflow.db")
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "cloudflow-dev-key-change-in-production"),
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", default_db),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=4 * 1024 * 1024,
    )
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("mysql://"):
        app.config["SQLALCHEMY_DATABASE_URI"] = app.config["SQLALCHEMY_DATABASE_URI"].replace("mysql://", "mysql+pymysql://", 1)
    if test_config:
        app.config.update(test_config)
    (BASE_DIR / "instance").mkdir(exist_ok=True)
    db.init_app(app)

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            return view(*args, **kwargs)
        return wrapped

    def admin_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id") or session.get("role") != "admin":
                flash("Administrator access is required.", "danger")
                return redirect(url_for("login"))
            return view(*args, **kwargs)
        return wrapped

    @app.context_processor
    def globals_for_templates():
        return {"algorithm_labels": ALGORITHM_LABELS, "current_year": datetime.now().year}

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            if not name or not email or len(password) < 6:
                flash("Enter a name, valid email and password of at least 6 characters.", "danger")
            elif User.query.filter_by(email=email).first():
                flash("This email is already registered.", "warning")
            else:
                db.session.add(User(name=name, email=email, password_hash=generate_password_hash(password)))
                db.session.commit()
                flash("Registration successful. You can now log in.", "success")
                return redirect(url_for("login"))
        return render_template("auth.html", mode="register")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            user = User.query.filter_by(email=email).first()
            if not user or not user.active or not check_password_hash(user.password_hash, request.form.get("password", "")):
                flash("Invalid credentials or inactive account.", "danger")
            else:
                session.clear()
                session.update(user_id=user.id, name=user.name, role=user.role)
                flash(f"Welcome back, {user.name}!", "success")
                return redirect(url_for("admin_dashboard" if user.role == "admin" else "user_dashboard"))
        return render_template("auth.html", mode="login")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("You have been logged out.", "info")
        return redirect(url_for("index"))

    @app.route("/dashboard")
    @login_required
    def user_dashboard():
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        uid = session["user_id"]
        workflows = Workflow.query.filter_by(user_id=uid).order_by(Workflow.created_at.desc()).all()
        runs = ScheduleRun.query.filter_by(user_id=uid).order_by(ScheduleRun.created_at.desc()).all()
        latest = runs[0].result if runs else None
        return render_template("user_dashboard.html", workflows=workflows, runs=runs, latest=latest)

    @app.route("/workflow/new", methods=["GET", "POST"])
    @login_required
    def create_workflow():
        if request.method == "POST":
            try:
                upload = request.files.get("workflow_file")
                if upload and upload.filename:
                    content = upload.read().decode("utf-8-sig")
                else:
                    content = request.form.get("tasks_csv", "")
                tasks = parse_task_csv(content)
                wf = Workflow(
                    user_id=session["user_id"], name=request.form.get("name", "Untitled Workflow").strip(),
                    description=request.form.get("description", "").strip(),
                    deadline=float(request.form.get("deadline", 100)), budget=float(request.form.get("budget", 100)),
                    objective=request.form.get("objective", "balanced"), tasks_json=json.dumps(tasks),
                )
                db.session.add(wf)
                db.session.commit()
                flash(f"Workflow created with {len(tasks)} tasks.", "success")
                return redirect(url_for("workflow_detail", workflow_id=wf.id))
            except (ValueError, UnicodeDecodeError) as exc:
                flash(str(exc), "danger")
        return render_template("workflow_form.html")

    def accessible_workflow(workflow_id):
        wf = db.session.get(Workflow, workflow_id)
        if not wf or (session.get("role") != "admin" and wf.user_id != session.get("user_id")):
            return None
        return wf

    @app.route("/workflow/<int:workflow_id>")
    @login_required
    def workflow_detail(workflow_id):
        wf = accessible_workflow(workflow_id)
        if not wf:
            flash("Workflow not found or access denied.", "danger")
            return redirect(url_for("user_dashboard"))
        return render_template("workflow_detail.html", workflow=wf)

    @app.route("/workflow/<int:workflow_id>/schedule", methods=["POST"])
    @login_required
    def schedule_workflow(workflow_id):
        wf = accessible_workflow(workflow_id)
        if not wf:
            flash("Workflow not found or access denied.", "danger")
            return redirect(url_for("user_dashboard"))
        resources = [r.as_dict() for r in CloudResource.query.filter_by(active=True).all()]
        if not resources:
            flash("No active cloud resources are available. Ask the administrator to add one.", "danger")
            return redirect(url_for("workflow_detail", workflow_id=wf.id))
        weights = objective_weights(wf.objective)
        results = compare_algorithms(wf.tasks, resources, weights)
        run = ScheduleRun(workflow_id=wf.id, user_id=session["user_id"], result_json=json.dumps(results), best_algorithm="proposed")
        db.session.add(run)
        db.session.commit()
        flash("Scheduling completed successfully.", "success")
        return redirect(url_for("schedule_result", run_id=run.id))

    @app.route("/result/<int:run_id>")
    @login_required
    def schedule_result(run_id):
        run = db.session.get(ScheduleRun, run_id)
        if not run or (session.get("role") != "admin" and run.user_id != session.get("user_id")):
            flash("Scheduling result not found or access denied.", "danger")
            return redirect(url_for("user_dashboard"))
        return render_template("result.html", run=run, results=run.result, workflow=run.workflow)

    @app.route("/result/<int:run_id>/download")
    @login_required
    def download_result(run_id):
        run = db.session.get(ScheduleRun, run_id)
        if not run or (session.get("role") != "admin" and run.user_id != session.get("user_id")):
            return redirect(url_for("user_dashboard"))
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["Algorithm", "Makespan", "Cost", "Energy", "Utilization", "Deadline Violations"])
        for key, item in run.result["algorithms"].items():
            m = item["metrics"]
            writer.writerow([ALGORITHM_LABELS[key], m["makespan"], m["total_cost"], m["energy"], m["utilization"], m["deadline_violations"]])
        return Response(out.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename=workflow_{run.workflow_id}_comparison.csv"})

    @app.route("/history")
    @login_required
    def history():
        uid = session["user_id"]
        query = ScheduleRun.query if session.get("role") == "admin" else ScheduleRun.query.filter_by(user_id=uid)
        return render_template("history.html", runs=query.order_by(ScheduleRun.created_at.desc()).all())

    @app.route("/admin")
    @admin_required
    def admin_dashboard():
        runs = ScheduleRun.query.order_by(ScheduleRun.created_at.desc()).all()
        return render_template("admin_dashboard.html", users=User.query.count(), workflows=Workflow.query.count(),
                               resources=CloudResource.query.filter_by(active=True).count(), runs=runs)

    @app.route("/admin/resources", methods=["GET", "POST"])
    @admin_required
    def resources():
        if request.method == "POST":
            try:
                db.session.add(CloudResource(name=request.form["name"], cpu=int(request.form["cpu"]),
                    ram=float(request.form["ram"]), mips=float(request.form["mips"]),
                    cost=float(request.form["cost"]), energy=float(request.form["energy"])))
                db.session.commit()
                flash("Cloud resource added.", "success")
                return redirect(url_for("resources"))
            except (ValueError, KeyError):
                flash("Enter valid resource values.", "danger")
        return render_template("resources.html", resources=CloudResource.query.order_by(CloudResource.id).all())

    @app.route("/admin/resource/<int:resource_id>/toggle", methods=["POST"])
    @admin_required
    def toggle_resource(resource_id):
        resource = db.session.get(CloudResource, resource_id)
        if resource:
            resource.active = not resource.active
            db.session.commit()
            flash("Resource status updated.", "success")
        return redirect(url_for("resources"))

    @app.route("/admin/training", methods=["GET", "POST"])
    @admin_required
    def training():
        evaluation = None
        if request.method == "POST":
            resources_data = [r.as_dict() for r in CloudResource.query.filter_by(active=True).all()]
            sample = sample_tasks()
            evaluation = compare_algorithms(sample, resources_data, {"time": .35, "cost": .25, "energy": .2, "balance": .2})
            model = {"model": "Two-Stage GNN-DRL Educational Scheduler", "trained_at": datetime.utcnow().isoformat(),
                     "episodes": int(request.form.get("episodes", 250)), "learning_rate": float(request.form.get("learning_rate", .001)),
                     "gamma": float(request.form.get("gamma", .95)), "evaluation": evaluation["algorithms"]}
            (BASE_DIR / "instance" / "trained_model.json").write_text(json.dumps(model, indent=2), encoding="utf-8")
            flash("Training simulation completed and model configuration saved.", "success")
        return render_template("training.html", evaluation=evaluation)

    @app.route("/admin/users")
    @admin_required
    def users():
        return render_template("users.html", users=User.query.order_by(User.created_at.desc()).all())

    @app.errorhandler(413)
    def too_large(_):
        flash("File is too large. Maximum upload size is 4 MB.", "danger")
        return redirect(request.referrer or url_for("create_workflow"))

    with app.app_context():
        db.create_all()
        seed_database()
    return app


def objective_weights(objective):
    options = {
        "time": {"time": .55, "cost": .15, "energy": .1, "balance": .2},
        "cost": {"time": .15, "cost": .55, "energy": .1, "balance": .2},
        "energy": {"time": .15, "cost": .1, "energy": .55, "balance": .2},
        "balanced": {"time": .3, "cost": .25, "energy": .2, "balance": .25},
    }
    return options.get(objective, options["balanced"])


def sample_tasks():
    return [
        {"id": "T1", "duration": 18, "cpu": 2, "memory": 2, "deadline": 45, "dependencies": []},
        {"id": "T2", "duration": 22, "cpu": 4, "memory": 4, "deadline": 70, "dependencies": ["T1"]},
        {"id": "T3", "duration": 14, "cpu": 2, "memory": 3, "deadline": 65, "dependencies": ["T1"]},
        {"id": "T4", "duration": 26, "cpu": 4, "memory": 6, "deadline": 105, "dependencies": ["T2", "T3"]},
        {"id": "T5", "duration": 12, "cpu": 2, "memory": 2, "deadline": 100, "dependencies": ["T3"]},
        {"id": "T6", "duration": 20, "cpu": 4, "memory": 5, "deadline": 145, "dependencies": ["T4", "T5"]},
    ]


def seed_database():
    if not User.query.filter_by(email="admin@cloudflow.local").first():
        db.session.add(User(name="System Admin", email="admin@cloudflow.local", password_hash=generate_password_hash("admin123"), role="admin"))
    if not User.query.filter_by(email="user@cloudflow.local").first():
        db.session.add(User(name="Demo User", email="user@cloudflow.local", password_hash=generate_password_hash("user123"), role="user"))
    if CloudResource.query.count() == 0:
        db.session.add_all([
            CloudResource(name="Edge-S", cpu=2, ram=4, mips=1200, cost=.18, energy=.7),
            CloudResource(name="Cloud-M", cpu=4, ram=8, mips=2500, cost=.34, energy=1.05),
            CloudResource(name="Compute-L", cpu=8, ram=16, mips=4800, cost=.62, energy=1.55),
            CloudResource(name="Eco-Node", cpu=4, ram=12, mips=2100, cost=.28, energy=.58),
        ])
    db.session.commit()


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)

