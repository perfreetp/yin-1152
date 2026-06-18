import sqlite3
import os
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any

from app.models.schemas import (
    Airline, MaintenanceBase, ContractProject, Personnel, RiskJob,
    WORK_TYPES, RISK_LEVELS, JOB_STATUSES, PERMIT_STATUSES
)


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "risk_daily.db")


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._connect()

    def _connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def close(self):
        if self.conn:
            self.conn.close()

    def init_db(self):
        cursor = self.conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS airlines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS maintenance_bases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                location TEXT
            );

            CREATE TABLE IF NOT EXISTS contract_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                airline_id INTEGER REFERENCES airlines(id),
                base_id INTEGER REFERENCES maintenance_bases(id),
                contract_no TEXT,
                UNIQUE(name, airline_id, base_id)
            );

            CREATE TABLE IF NOT EXISTS personnel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                employee_id TEXT UNIQUE,
                team TEXT,
                position TEXT,
                certificate_no TEXT,
                certificate_expiry TEXT,
                qualifications TEXT
            );

            CREATE TABLE IF NOT EXISTS risk_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER REFERENCES contract_projects(id),
                job_date TEXT NOT NULL,
                work_type TEXT NOT NULL,
                work_location TEXT,
                aircraft_no TEXT,
                team TEXT,
                team_leader TEXT,
                risk_level TEXT DEFAULT '中风险',
                description TEXT,
                isolation_measures TEXT,
                permit_status TEXT DEFAULT '未办理',
                permit_expiry TEXT,
                personnel_ids TEXT,
                estimated_end_time TEXT,
                actual_end_time TEXT,
                status TEXT DEFAULT '未开工',
                need_client_safety_officer INTEGER DEFAULT 0,
                reviewed_by_pm INTEGER DEFAULT 0,
                pm_comments TEXT,
                issues TEXT,
                created_at TEXT,
                updated_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_risk_jobs_project_date
                ON risk_jobs(project_id, job_date);
            CREATE INDEX IF NOT EXISTS idx_risk_jobs_status
                ON risk_jobs(status);
        """)
        self.conn.commit()

    def ensure_demo_data(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM airlines")
        if cursor.fetchone()[0] > 0:
            return

        today = date.today()

        airlines = [
            Airline(name="中国国际航空"),
            Airline(name="中国东方航空"),
            Airline(name="中国南方航空"),
            Airline(name="海南航空"),
        ]
        for a in airlines:
            cursor.execute("INSERT INTO airlines (name) VALUES (?)", (a.name,))
            a.id = cursor.lastrowid

        bases = [
            MaintenanceBase(name="首都机场维修基地", location="北京"),
            MaintenanceBase(name="浦东机场维修基地", location="上海"),
            MaintenanceBase(name="白云机场维修基地", location="广州"),
        ]
        for b in bases:
            cursor.execute(
                "INSERT INTO maintenance_bases (name, location) VALUES (?, ?)",
                (b.name, b.location)
            )
            b.id = cursor.lastrowid

        projects = [
            ContractProject(name="A330定检维修项目", airline_id=airlines[0].id,
                            base_id=bases[0].id, contract_no="CA-2026-001"),
            ContractProject(name="B737航线维护项目", airline_id=airlines[1].id,
                            base_id=bases[1].id, contract_no="MU-2026-008"),
            ContractProject(name="A320喷漆大修项目", airline_id=airlines[2].id,
                            base_id=bases[2].id, contract_no="CZ-2026-015"),
            ContractProject(name="B787结构维修项目", airline_id=airlines[0].id,
                            base_id=bases[0].id, contract_no="CA-2026-023"),
        ]
        for p in projects:
            cursor.execute(
                "INSERT INTO contract_projects (name, airline_id, base_id, contract_no) VALUES (?, ?, ?, ?)",
                (p.name, p.airline_id, p.base_id, p.contract_no)
            )
            p.id = cursor.lastrowid

        personnel = [
            Personnel(name="张建国", employee_id="E001", team="喷漆一班",
                      position="班组长", certificate_no="CAAC-PT-001",
                      certificate_expiry=today + timedelta(days=180),
                      qualifications="喷漆作业证、高空作业证"),
            Personnel(name="李明辉", employee_id="E002", team="喷漆一班",
                      position="作业员", certificate_no="CAAC-PT-002",
                      certificate_expiry=today + timedelta(days=30),
                      qualifications="喷漆作业证"),
            Personnel(name="王志强", employee_id="E003", team="打磨班",
                      position="班组长", certificate_no="CAAC-DM-001",
                      certificate_expiry=today + timedelta(days=365),
                      qualifications="打磨作业证、受限空间作业证"),
            Personnel(name="赵晓东", employee_id="E004", team="结构维修班",
                      position="技术员", certificate_no="CAAC-ST-001",
                      certificate_expiry=today - timedelta(days=10),
                      qualifications="结构维修证、动火作业证"),
            Personnel(name="陈大力", employee_id="E005", team="清洗班",
                      position="班组长", certificate_no="CAAC-CL-001",
                      certificate_expiry=today + timedelta(days=90),
                      qualifications="清洗作业证、高空作业证"),
            Personnel(name="刘伟", employee_id="E006", team="结构维修班",
                      position="作业员", certificate_no="CAAC-ST-002",
                      certificate_expiry=today + timedelta(days=200),
                      qualifications="结构维修证"),
        ]
        for p in personnel:
            cursor.execute(
                """INSERT INTO personnel (name, employee_id, team, position,
                   certificate_no, certificate_expiry, qualifications)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (p.name, p.employee_id, p.team, p.position,
                 p.certificate_no, p.certificate_expiry.isoformat(), p.qualifications)
            )
            p.id = cursor.lastrowid

        demo_jobs = [
            RiskJob(
                project_id=projects[2].id, job_date=today,
                work_type="喷漆作业", work_location="喷漆机库A区",
                aircraft_no="B-6123", team="喷漆一班", team_leader="张建国",
                risk_level="高风险",
                description="A320整机喷漆，含机身打磨、底漆、面漆工序",
                isolation_measures="喷漆区拉设警戒线，配备2台防爆风机，消防器材4具",
                permit_status="有效", permit_expiry=today + timedelta(days=5),
                personnel_ids=[1, 2],
                estimated_end_time=datetime(today.year, today.month, today.day, 18, 0),
                status="进行中", need_client_safety_officer=True,
                reviewed_by_pm=True, pm_comments="已安排客户安全员刘工到场",
                issues=""
            ),
            RiskJob(
                project_id=projects[0].id, job_date=today,
                work_type="打磨作业", work_location="A330左翼前缘",
                aircraft_no="B-6501", team="打磨班", team_leader="王志强",
                risk_level="中风险",
                description="机翼前缘蒙皮打磨除锈",
                isolation_measures="设置警示围栏，防尘面罩配备，翼下禁止人员通行",
                permit_status="即将过期", permit_expiry=today + timedelta(days=1),
                personnel_ids=[3],
                estimated_end_time=datetime(today.year, today.month, today.day, 15, 30),
                status="进行中", need_client_safety_officer=False,
                reviewed_by_pm=False, pm_comments="",
                issues="许可证明日到期，需提醒班组续办"
            ),
            RiskJob(
                project_id=projects[3].id, job_date=today,
                work_type="结构拆装", work_location="B787机身42段",
                aircraft_no="B-1368", team="结构维修班", team_leader="赵晓东",
                risk_level="极高风险",
                description="机身蒙皮更换，涉及大型部件吊装",
                isolation_measures="吊装区域全封闭，专人指挥，天车作业证有效",
                permit_status="已过期", permit_expiry=today - timedelta(days=3),
                personnel_ids=[4, 6],
                estimated_end_time=datetime(today.year, today.month, today.day, 20, 0),
                status="未开工", need_client_safety_officer=True,
                reviewed_by_pm=False, pm_comments="",
                issues="许可证已过期！作业暂停，待重新办理后开工"
            ),
            RiskJob(
                project_id=projects[1].id, job_date=today,
                work_type="清洗作业", work_location="B737机身及发动机",
                aircraft_no="B-5238", team="清洗班", team_leader="陈大力",
                risk_level="低风险",
                description="航后机身外表及发动机进气道清洗",
                isolation_measures="发动机进气道/尾喷口加盖保护罩，电气插头防水",
                permit_status="有效", permit_expiry=today + timedelta(days=20),
                personnel_ids=[5],
                estimated_end_time=datetime(today.year, today.month, today.day, 22, 0),
                status="已关闭", need_client_safety_officer=False,
                reviewed_by_pm=True, pm_comments="已按时完成，无异常",
                issues=""
            ),
            RiskJob(
                project_id=projects[2].id, job_date=today,
                work_type="动火作业", work_location="喷漆机库辅助间",
                aircraft_no="B-6123", team="结构维修班", team_leader="赵晓东",
                risk_level="高风险",
                description="喷漆挂架焊接修复，超出喷漆项目合同范围",
                isolation_measures="动火点10米内清理可燃物，监火人全程值守",
                permit_status="未办理", permit_expiry=None,
                personnel_ids=[4],
                estimated_end_time=datetime(today.year, today.month, today.day, 12, 0),
                status="未开工", need_client_safety_officer=True,
                reviewed_by_pm=False, pm_comments="",
                issues="超范围作业！需客户书面批准，并重新办理动火许可证"
            ),
        ]

        for job in demo_jobs:
            self._insert_risk_job(cursor, job)

        self.conn.commit()

    def _insert_risk_job(self, cursor, job: RiskJob):
        now = datetime.now().isoformat()
        personnel_ids_str = ",".join(str(pid) for pid in job.personnel_ids) if job.personnel_ids else ""
        cursor.execute(
            """INSERT INTO risk_jobs (
                project_id, job_date, work_type, work_location, aircraft_no,
                team, team_leader, risk_level, description, isolation_measures,
                permit_status, permit_expiry, personnel_ids,
                estimated_end_time, actual_end_time, status,
                need_client_safety_officer, reviewed_by_pm, pm_comments,
                issues, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                job.project_id,
                job.job_date.isoformat() if job.job_date else None,
                job.work_type, job.work_location, job.aircraft_no,
                job.team, job.team_leader, job.risk_level,
                job.description, job.isolation_measures,
                job.permit_status,
                job.permit_expiry.isoformat() if job.permit_expiry else None,
                personnel_ids_str,
                job.estimated_end_time.isoformat() if job.estimated_end_time else None,
                job.actual_end_time.isoformat() if job.actual_end_time else None,
                job.status,
                1 if job.need_client_safety_officer else 0,
                1 if job.reviewed_by_pm else 0,
                job.pm_comments, job.issues, now, now
            )
        )
        return cursor.lastrowid

    # ===== Airlines =====
    def get_all_airlines(self) -> List[Airline]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name FROM airlines ORDER BY name")
        return [Airline(id=r["id"], name=r["name"]) for r in cursor.fetchall()]

    # ===== Bases =====
    def get_all_bases(self) -> List[MaintenanceBase]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, location FROM maintenance_bases ORDER BY name")
        return [MaintenanceBase(id=r["id"], name=r["name"], location=r["location"])
                for r in cursor.fetchall()]

    # ===== Projects =====
    def get_projects(self, airline_id: Optional[int] = None,
                     base_id: Optional[int] = None) -> List[ContractProject]:
        cursor = self.conn.cursor()
        sql = "SELECT * FROM contract_projects WHERE 1=1"
        params = []
        if airline_id:
            sql += " AND airline_id = ?"
            params.append(airline_id)
        if base_id:
            sql += " AND base_id = ?"
            params.append(base_id)
        sql += " ORDER BY name"
        cursor.execute(sql, params)
        return [ContractProject(
            id=r["id"], name=r["name"], airline_id=r["airline_id"],
            base_id=r["base_id"], contract_no=r["contract_no"]
        ) for r in cursor.fetchall()]

    # ===== Personnel =====
    def get_all_personnel(self) -> List[Personnel]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM personnel ORDER BY team, name")
        return [self._row_to_personnel(r) for r in cursor.fetchall()]

    def get_personnel_by_ids(self, ids: List[int]) -> List[Personnel]:
        if not ids:
            return []
        cursor = self.conn.cursor()
        placeholders = ",".join("?" * len(ids))
        cursor.execute(f"SELECT * FROM personnel WHERE id IN ({placeholders}) ORDER BY name", ids)
        return [self._row_to_personnel(r) for r in cursor.fetchall()]

    def _row_to_personnel(self, r: sqlite3.Row) -> Personnel:
        return Personnel(
            id=r["id"], name=r["name"], employee_id=r["employee_id"],
            team=r["team"], position=r["position"], certificate_no=r["certificate_no"],
            certificate_expiry=date.fromisoformat(r["certificate_expiry"]) if r["certificate_expiry"] else None,
            qualifications=r["qualifications"] or ""
        )

    # ===== Risk Jobs =====
    def get_risk_jobs(self, project_id: Optional[int] = None,
                      job_date: Optional[date] = None,
                      status: Optional[str] = None) -> List[RiskJob]:
        cursor = self.conn.cursor()
        sql = "SELECT * FROM risk_jobs WHERE 1=1"
        params = []
        if project_id:
            sql += " AND project_id = ?"
            params.append(project_id)
        if job_date:
            sql += " AND job_date = ?"
            params.append(job_date.isoformat())
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY CASE risk_level WHEN '极高风险' THEN 1 WHEN '高风险' THEN 2 WHEN '中风险' THEN 3 ELSE 4 END, id"
        cursor.execute(sql, params)
        return [self._row_to_risk_job(r) for r in cursor.fetchall()]

    def _row_to_risk_job(self, r: sqlite3.Row) -> RiskJob:
        personnel_ids = []
        if r["personnel_ids"]:
            personnel_ids = [int(x) for x in r["personnel_ids"].split(",") if x]
        return RiskJob(
            id=r["id"], project_id=r["project_id"],
            job_date=date.fromisoformat(r["job_date"]) if r["job_date"] else None,
            work_type=r["work_type"], work_location=r["work_location"],
            aircraft_no=r["aircraft_no"], team=r["team"], team_leader=r["team_leader"],
            risk_level=r["risk_level"], description=r["description"] or "",
            isolation_measures=r["isolation_measures"] or "",
            permit_status=r["permit_status"],
            permit_expiry=date.fromisoformat(r["permit_expiry"]) if r["permit_expiry"] else None,
            personnel_ids=personnel_ids,
            estimated_end_time=datetime.fromisoformat(r["estimated_end_time"]) if r["estimated_end_time"] else None,
            actual_end_time=datetime.fromisoformat(r["actual_end_time"]) if r["actual_end_time"] else None,
            status=r["status"],
            need_client_safety_officer=bool(r["need_client_safety_officer"]),
            reviewed_by_pm=bool(r["reviewed_by_pm"]),
            pm_comments=r["pm_comments"] or "",
            issues=r["issues"] or "",
            created_at=datetime.fromisoformat(r["created_at"]) if r["created_at"] else None,
            updated_at=datetime.fromisoformat(r["updated_at"]) if r["updated_at"] else None
        )

    def save_risk_job(self, job: RiskJob) -> int:
        cursor = self.conn.cursor()
        personnel_ids_str = ",".join(str(pid) for pid in job.personnel_ids) if job.personnel_ids else ""
        now = datetime.now().isoformat()

        if job.id:
            cursor.execute(
                """UPDATE risk_jobs SET
                    project_id=?, job_date=?, work_type=?, work_location=?, aircraft_no=?,
                    team=?, team_leader=?, risk_level=?, description=?, isolation_measures=?,
                    permit_status=?, permit_expiry=?, personnel_ids=?,
                    estimated_end_time=?, actual_end_time=?, status=?,
                    need_client_safety_officer=?, reviewed_by_pm=?, pm_comments=?,
                    issues=?, updated_at=?
                WHERE id=?""",
                (
                    job.project_id,
                    job.job_date.isoformat() if job.job_date else None,
                    job.work_type, job.work_location, job.aircraft_no,
                    job.team, job.team_leader, job.risk_level,
                    job.description, job.isolation_measures,
                    job.permit_status,
                    job.permit_expiry.isoformat() if job.permit_expiry else None,
                    personnel_ids_str,
                    job.estimated_end_time.isoformat() if job.estimated_end_time else None,
                    job.actual_end_time.isoformat() if job.actual_end_time else None,
                    job.status,
                    1 if job.need_client_safety_officer else 0,
                    1 if job.reviewed_by_pm else 0,
                    job.pm_comments, job.issues, now, job.id
                )
            )
        else:
            job.id = self._insert_risk_job(cursor, job)
        self.conn.commit()
        return job.id

    def delete_risk_job(self, job_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM risk_jobs WHERE id=?", (job_id,))
        self.conn.commit()

    # ===== 统计 =====
    def get_job_count_by_status(self, project_id: int, job_date: date) -> Dict[str, int]:
        result = {s: 0 for s in JOB_STATUSES}
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT status, COUNT(*) as cnt FROM risk_jobs WHERE project_id=? AND job_date=? GROUP BY status",
            (project_id, job_date.isoformat())
        )
        for r in cursor.fetchall():
            result[r["status"]] = r["cnt"]
        return result

    def get_issue_count(self, project_id: int, job_date: date) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM risk_jobs WHERE project_id=? AND job_date=? AND issues <> ''",
            (project_id, job_date.isoformat())
        )
        return cursor.fetchone()[0]
