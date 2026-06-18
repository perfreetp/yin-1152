from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List


WORK_TYPES = [
    "喷漆作业",
    "打磨作业",
    "清洗作业",
    "结构拆装",
    "发动机维修",
    "电气维修",
    "液压系统维修",
    "高空作业",
    "受限空间作业",
    "动火作业",
]


RISK_LEVELS = ["低风险", "中风险", "高风险", "极高风险"]


JOB_STATUSES = ["未开工", "进行中", "已关闭"]


PERMIT_STATUSES = ["有效", "即将过期", "已过期", "未办理"]


PERMIT_WARNING_DAYS = 3


CERT_WARNING_DAYS = 30


@dataclass
class Airline:
    id: Optional[int] = None
    name: str = ""


@dataclass
class MaintenanceBase:
    id: Optional[int] = None
    name: str = ""
    location: str = ""


@dataclass
class ContractProject:
    id: Optional[int] = None
    name: str = ""
    airline_id: Optional[int] = None
    base_id: Optional[int] = None
    contract_no: str = ""


@dataclass
class Personnel:
    id: Optional[int] = None
    name: str = ""
    employee_id: str = ""
    team: str = ""
    position: str = ""
    certificate_no: str = ""
    certificate_expiry: Optional[date] = None
    qualifications: str = ""


@dataclass
class PersonnelQualification:
    id: Optional[int] = None
    personnel_id: Optional[int] = None
    work_type: str = ""
    certificate_no: str = ""
    expiry_date: Optional[date] = None


@dataclass
class QualificationIssue:
    personnel_id: int
    personnel_name: str
    issue_type: str
    work_type: str
    detail: str



@dataclass
class RiskJob:
    id: Optional[int] = None
    project_id: Optional[int] = None
    job_date: Optional[date] = None
    work_type: str = ""
    work_location: str = ""
    aircraft_no: str = ""
    team: str = ""
    team_leader: str = ""
    risk_level: str = "中风险"
    description: str = ""
    isolation_measures: str = ""
    permit_status: str = "未办理"
    permit_expiry: Optional[date] = None
    personnel_ids: List[int] = field(default_factory=list)
    estimated_end_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    close_remark: str = ""
    status: str = "未开工"
    need_client_safety_officer: bool = False
    reviewed_by_pm: bool = False
    pm_comments: str = ""
    issues: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
