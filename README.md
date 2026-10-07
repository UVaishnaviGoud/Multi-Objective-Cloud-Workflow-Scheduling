# CloudFlow AI

**Multi-Objective Cloud Workflow Scheduling Using Two-Stage Deep Reinforcement Learning and Graph Neural Networks**

CloudFlow AI is a complete student-friendly Flask web project for modelling cloud workflows as directed acyclic graphs (DAGs), scheduling their tasks across heterogeneous cloud resources, and comparing three existing algorithms with a proposed graph-aware two-stage policy.

## Included modules

### Admin

- Secure admin login and visual dashboard
- Cloud resource creation, activation and deactivation
- CPU, RAM, MIPS, cost and energy configuration
- Existing algorithm evaluation: FCFS, Min-Min and HEFT
- Proposed two-stage GNN–DRL training simulation
- Hyperparameter configuration and saved model metadata
- Comparison metrics and registered-user monitoring
- Complete scheduling history

### User

- Registration, login and dashboard
- Manual workflow task entry
- Workflow CSV upload with validation
- DAG cycle and dependency validation
- Optimization preference selection: balanced, time, cost or energy
- Existing and proposed scheduling execution
- Makespan, cost, energy, utilization, throughput and deadline metrics
- Algorithm comparison chart and table
- Proposed-model betterment analysis
- DAG and Gantt visualizations
- Scheduling history and downloadable CSV reports

## Technology

- Python 3.10+
- Flask 3
- Flask-SQLAlchemy
- SQLite by default; optional MySQL 8 with PyMySQL
- HTML5, CSS3 and vanilla JavaScript
- Chart.js for browser charts

## Quick start on Windows

1. Extract the ZIP file.
2. Open the extracted `cloudflow_ai` folder.
3. Double-click `start_windows.bat`.
4. Wait for dependency installation and open <http://127.0.0.1:5000>.

Manual commands:

```bat
py -3.10 -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

## Default login accounts

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@cloudflow.local` | `admin123` |
| User | `user@cloudflow.local` | `user123` |

Change the seeded passwords before any real deployment.

## Workflow CSV format

```csv
id,duration,cpu,memory,deadline,dependencies
T1,18,2,2,45,
T2,22,4,4,70,T1
T3,14,2,3,65,T1
T4,26,4,6,105,T2;T3
```

- Every task ID must be unique.
- Separate multiple dependencies with semicolons.
- Every dependency must refer to another task in the same file.
- Cyclic dependencies are rejected because the workflow must be a DAG.

The project includes `static/data/sample_workflow.csv` for testing.

## Optional MySQL 8 configuration

SQLite runs automatically and requires no database setup. To use MySQL:

1. Run `mysql_setup.sql` in MySQL Workbench or phpMyAdmin.
2. Install the requirements.
3. Set `DATABASE_URL` before starting Flask:

```bat
set DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost/cloudflow_ai
set SECRET_KEY=replace-with-a-long-random-value
python app.py
```

Flask-SQLAlchemy creates the project tables automatically.

## Algorithms

| Type | Algorithm | Purpose |
| --- | --- | --- |
| Existing | FCFS | Schedules ready tasks in arrival order |
| Existing | Min-Min | Selects the ready task with the shortest resource runtime |
| Existing | HEFT | Uses dependency-aware upward task ranks and earliest finish time |
| Proposed | Two-Stage GNN–DRL | Uses graph-context priority followed by multi-objective resource action scoring |

The proposed implementation is an **educational, executable simulation** of GNN embeddings and learned policy decisions. It exposes the complete scheduling pipeline and reward calculation without requiring a GPU or a long neural-network training process. The training screen stores evaluated model configuration in `instance/trained_model.json`. A research deployment can replace these policy functions with trained PyTorch checkpoints while preserving the same web interface.

## Multi-objective metrics

- Makespan (lower is better)
- Total cloud cost (lower is better)
- Energy consumption (lower is better)
- Resource utilization (higher is better)
- Deadline violations (lower is better)
- Throughput (higher is better)
- Scheduling decision time

## Run automated tests

```bat
python -m unittest discover -s tests -v
```

## Important folders

```text
cloudflow_ai/
├── app.py                 Flask routes, models and database setup
├── scheduler.py           DAG parsing and scheduling algorithms
├── templates/             Admin, user and public pages
├── static/css/style.css   Responsive colourful interface
├── static/js/app.js       Charts, DAG and Gantt rendering
├── static/data/            Sample workflow dataset
├── tests/                 Automated functional tests
└── instance/              Runtime database and trained metadata
```

