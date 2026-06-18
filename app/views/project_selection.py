from datetime import date
from typing import Optional, List

from PySide6.QtCore import Qt, QDate, Signal, QSize
from PySide6.QtWidgets import (
    QWidget, QLabel, QComboBox, QDateEdit, QPushButton, QVBoxLayout,
    QHBoxLayout, QGroupBox, QListWidget, QListWidgetItem, QFrame, QMessageBox,
    QToolButton, QScrollArea, QMenu, QSizePolicy
)

from app.db.database import Database
from app.models.schemas import ContractProject, WORK_TYPES, RISK_LEVELS, JOB_STATUSES, RecentProject
from app.views.risk_entry import RiskEntryWindow
from app.views.daily_report import DailyReportWindow
from app.views.personnel_qualification import PersonnelQualificationWindow


RISK_COLORS = {
    "低风险": "#27ae60",
    "中风险": "#f39c12",
    "高风险": "#e67e22",
    "极高风险": "#c0392b",
}


class ProjectSelectionWindow(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.current_project: Optional[ContractProject] = None
        self.current_date: date = date.today()
        self.risk_entry_window: Optional[RiskEntryWindow] = None
        self.report_window: Optional[DailyReportWindow] = None
        self.personnel_window: Optional[PersonnelQualificationWindow] = None
        self._init_ui()
        self._load_airlines()
        self._load_bases()
        self._refresh_job_list()

    def _init_ui(self):
        self.setWindowTitle("民航维修现场风险日报系统 - 项目选择")
        self.setMinimumSize(1000, 650)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("民航维修现场风险日报系统")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2c3e50;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        sub = QLabel("承包商项目经理专用 · 每日风险协调看板")
        sub.setStyleSheet("font-size: 13px; color: #7f8c8d;")
        sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub)

        self._build_recent_projects(layout)

        filter_box = QGroupBox("筛选条件")
        filter_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold; font-size: 14px;
                border: 1px solid #bdc3c7; border-radius: 8px;
                margin-top: 10px; padding: 15px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 5px; }
        """)
        filter_layout = QHBoxLayout(filter_box)
        filter_layout.setSpacing(15)

        self.airline_combo = QComboBox()
        self.base_combo = QComboBox()
        self.project_combo = QComboBox()
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate.currentDate())

        for label_text, widget in [
            ("客户航司", self.airline_combo),
            ("维修基地", self.base_combo),
            ("合同项目", self.project_combo),
            ("作业日期", self.date_edit),
        ]:
            col = QVBoxLayout()
            lab = QLabel(label_text)
            lab.setStyleSheet("font-size: 12px; color: #34495e; margin-bottom: 3px;")
            col.addWidget(lab)
            widget.setMinimumHeight(32)
            widget.setStyleSheet("QComboBox, QDateEdit { padding: 4px 8px; }")
            col.addWidget(widget)
            filter_layout.addLayout(col)

        self.btn_search = QPushButton("查看今日风险")
        self.btn_search.setMinimumHeight(40)
        self.btn_search.setStyleSheet("""
            QPushButton {
                background: #2980b9; color: white; font-weight: bold;
                border: none; border-radius: 6px; padding: 0 20px;
            }
            QPushButton:hover { background: #3498db; }
            QPushButton:pressed { background: #1f6391; }
        """)
        btn_col = QVBoxLayout()
        btn_col.addSpacing(18)
        btn_col.addWidget(self.btn_search)
        filter_layout.addLayout(btn_col)

        layout.addWidget(filter_box)

        self.airline_combo.currentIndexChanged.connect(self._on_filter_changed)
        self.base_combo.currentIndexChanged.connect(self._on_filter_changed)
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        self.date_edit.dateChanged.connect(self._on_date_changed)
        self.btn_search.clicked.connect(self._on_search)

        content = QHBoxLayout()
        content.setSpacing(15)

        left = QVBoxLayout()
        list_title = QLabel("今日高风险作业列表")
        list_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        left.addWidget(list_title)

        self.job_list = QListWidget()
        self.job_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #bdc3c7; border-radius: 6px;
                background: white; padding: 4px;
            }
            QListWidget::item {
                padding: 10px; border-radius: 4px; margin: 2px 0;
                border-bottom: 1px solid #ecf0f1;
            }
            QListWidget::item:selected { background: #e8f4fc; }
        """)
        left.addWidget(self.job_list, 1)

        btn_row = QHBoxLayout()
        self.btn_fill = QPushButton("风险填报 / 审核")
        self.btn_fill.setMinimumHeight(38)
        self.btn_fill.setStyleSheet("""
            QPushButton {
                background: #27ae60; color: white; font-weight: bold;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background: #2ecc71; }
            QPushButton:disabled { background: #95a5a6; }
        """)
        self.btn_fill.clicked.connect(self._open_risk_entry)
        btn_row.addWidget(self.btn_fill)

        self.btn_report = QPushButton("生成日报")
        self.btn_report.setMinimumHeight(38)
        self.btn_report.setStyleSheet("""
            QPushButton {
                background: #8e44ad; color: white; font-weight: bold;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background: #9b59b6; }
            QPushButton:disabled { background: #95a5a6; }
        """)
        self.btn_report.clicked.connect(self._open_daily_report)
        btn_row.addWidget(self.btn_report)
        left.addLayout(btn_row)

        content.addLayout(left, 2)

        right = QVBoxLayout()

        summary_box = QGroupBox("今日概览")
        summary_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold; font-size: 14px;
                border: 1px solid #bdc3c7; border-radius: 8px;
                margin-top: 10px; padding: 15px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 5px; }
        """)
        summary_layout = QVBoxLayout(summary_box)

        self.lbl_total = QLabel("风险作业总数：0")
        self.lbl_pending = QLabel("未开工：0")
        self.lbl_doing = QLabel("进行中：0")
        self.lbl_closed = QLabel("已关闭：0")
        self.lbl_issues = QLabel("存在问题：0")

        for lbl in [self.lbl_total, self.lbl_pending, self.lbl_doing, self.lbl_closed, self.lbl_issues]:
            lbl.setStyleSheet("font-size: 14px; padding: 6px 0;")
            summary_layout.addWidget(lbl)

        self.lbl_issues.setStyleSheet("font-size: 14px; padding: 6px 0; color: #c0392b; font-weight: bold;")

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("color: #ecf0f1;")
        summary_layout.addWidget(separator)

        hint = QLabel("提示：\n1. 先选择客户航司、基地与项目\n2. 点击「风险填报/审核」录入或审核作业\n3. 点击「生成日报」输出协调会看板")
        hint.setStyleSheet("font-size: 12px; color: #7f8c8d; line-height: 1.6;")
        hint.setWordWrap(True)
        summary_layout.addWidget(hint)

        self.btn_personnel = QPushButton("👤 人员资质管理")
        self.btn_personnel.setMinimumHeight(36)
        self.btn_personnel.setStyleSheet("""
            QPushButton {
                background: #16a085; color: white; font-weight: bold;
                border: none; border-radius: 6px; font-size: 13px;
            }
            QPushButton:hover { background: #1abc9c; }
        """)
        self.btn_personnel.clicked.connect(self._open_personnel_qual)
        summary_layout.addWidget(self.btn_personnel)

        right.addWidget(summary_box)
        right.addStretch(1)
        content.addLayout(right, 1)

        layout.addLayout(content, 1)

        self._update_buttons_state()
        self._refresh_recent_projects()

    def _build_recent_projects(self, parent_layout: QVBoxLayout):
        box = QGroupBox("⭐ 常用 / 最近项目（一键直达）")
        box.setStyleSheet("""
            QGroupBox {
                font-weight: bold; font-size: 13px;
                border: 1px dashed #f39c12; border-radius: 8px;
                margin-top: 6px; padding: 10px 10px 10px 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #d35400; }
        """)
        box_v = QVBoxLayout(box)
        box_v.setContentsMargins(6, 8, 6, 6)
        box_v.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMaximumHeight(78)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        self.recent_container = QWidget()
        self.recent_layout = QHBoxLayout(self.recent_container)
        self.recent_layout.setContentsMargins(2, 2, 2, 2)
        self.recent_layout.setSpacing(8)
        self.recent_layout.addStretch(1)

        self.lbl_recent_empty = QLabel("暂无记录——查看任意项目后会自动出现在这里。右键卡片可置顶为常用项目。")
        self.lbl_recent_empty.setStyleSheet("color: #95a5a6; font-size: 11px; padding: 8px;")
        self.lbl_recent_empty.setAlignment(Qt.AlignCenter)
        self.recent_layout.insertWidget(0, self.lbl_recent_empty)

        scroll.setWidget(self.recent_container)
        box_v.addWidget(scroll)

        parent_layout.addWidget(box)

    def _refresh_recent_projects(self):
        while self.recent_layout.count() > 1:
            item = self.recent_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        recent_list = self.db.get_recent_projects(limit=12)
        if not recent_list:
            self.lbl_recent_empty.show()
            self.recent_layout.insertWidget(0, self.lbl_recent_empty)
            return
        self.lbl_recent_empty.hide()

        all_projects = {p.id: p for p in self.db.get_projects()}

        for rp in recent_list:
            project = all_projects.get(rp.project_id)
            if not project:
                continue

            card = QFrame()
            pinned = self.db.is_project_pinned(rp.project_id)
            border_color = "#f1c40f" if pinned else "#bdc3c7"
            bg_color = "#fef9e7" if pinned else "white"
            star = "⭐ " if pinned else ""
            card.setStyleSheet(f"""
                QFrame {{
                    background: {bg_color};
                    border: 1px solid {border_color};
                    border-left: 3px solid {border_color};
                    border-radius: 5px;
                    padding: 6px 8px;
                }}
                QFrame:hover {{ background: #f8f9fa; }}
            """)
            card.setCursor(Qt.PointingHandCursor)
            card.setMinimumWidth(220)
            card.setMaximumWidth(260)
            card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            card.setContextMenuPolicy(Qt.CustomContextMenu)

            card_v = QVBoxLayout(card)
            card_v.setContentsMargins(6, 4, 6, 4)
            card_v.setSpacing(2)

            project_name = project.name
            if len(project_name) > 14:
                project_name = project_name[:14] + "…"
            t = QLabel(f"{star}<b>{project_name}</b>")
            t.setTextFormat(Qt.RichText)
            t.setStyleSheet("font-size: 12px; color: #2c3e50;")
            t.setWordWrap(False)
            card_v.addWidget(t)

            extra = []
            if project.contract_no:
                cn = project.contract_no
                if len(cn) > 18:
                    cn = cn[:18] + "…"
                extra.append(f"📋 {cn}")
            if rp.last_viewed_at:
                extra.append(f"🕐 {rp.last_viewed_at.strftime('%m-%d %H:%M')}")
            extra.append(f"👁 {rp.view_count}次")
            info = QLabel(" · ".join(extra))
            info.setStyleSheet("font-size: 10px; color: #7f8c8d;")
            info.setWordWrap(False)
            card_v.addWidget(info)

            card.mousePressEvent = lambda e, pid=rp.project_id: self._quick_open_project(pid)
            card.customContextMenuRequested.connect(
                lambda pos, w=card, pid=rp.project_id: self._show_recent_menu(pos, w, pid))

            self.recent_layout.insertWidget(self.recent_layout.count() - 1, card)

    def _show_recent_menu(self, pos, widget: QWidget, project_id: int):
        menu = QMenu(self)
        pinned = self.db.is_project_pinned(project_id)
        text = "📌 取消置顶" if pinned else "📌 设为常用置顶"
        act_pin = menu.addAction(text)
        act_open_fill = menu.addAction("📝 打开填报")
        act_open_report = menu.addAction("📊 生成日报")
        chosen = menu.exec(widget.mapToGlobal(pos))
        if chosen == act_pin:
            self.db.toggle_pin_project(project_id)
            self._refresh_recent_projects()
        elif chosen == act_open_fill:
            self._quick_open_project(project_id, mode="fill")
        elif chosen == act_open_report:
            self._quick_open_project(project_id, mode="report")

    def _quick_open_project(self, project_id: int, mode: str = "select"):
        projects = self.db.get_projects()
        target = next((p for p in projects if p.id == project_id), None)
        if not target:
            return

        idx_a = self.airline_combo.findData(target.airline_id)
        if idx_a < 0:
            self.airline_combo.blockSignals(True)
            self.airline_combo.clear()
            self.airline_combo.addItem("全部航司", None)
            airlines = self.db.get_all_airlines()
            for a in airlines:
                self.airline_combo.addItem(a.name, a.id)
            self.airline_combo.blockSignals(False)
            idx_a = self.airline_combo.findData(target.airline_id)
        if idx_a >= 0:
            self.airline_combo.setCurrentIndex(idx_a)

        idx_b = self.base_combo.findData(target.base_id)
        if idx_b < 0:
            self.base_combo.blockSignals(True)
            self.base_combo.clear()
            self.base_combo.addItem("全部基地", None)
            bases = self.db.get_all_bases()
            for b in bases:
                self.base_combo.addItem(b.name, b.id)
            self.base_combo.blockSignals(False)
            idx_b = self.base_combo.findData(target.base_id)
        if idx_b >= 0:
            self.base_combo.setCurrentIndex(idx_b)

        self._load_projects()
        idx_p = self.project_combo.findData(target.id)
        if idx_p >= 0:
            self.project_combo.setCurrentIndex(idx_p)

        self._refresh_job_list()
        self._update_buttons_state()

        if mode == "fill":
            self._open_risk_entry()
        elif mode == "report":
            self._open_daily_report()

    def _load_airlines(self):
        airlines = self.db.get_all_airlines()
        self.airline_combo.clear()
        self.airline_combo.addItem("全部航司", None)
        for a in airlines:
            self.airline_combo.addItem(a.name, a.id)

    def _load_bases(self):
        bases = self.db.get_all_bases()
        self.base_combo.clear()
        self.base_combo.addItem("全部基地", None)
        for b in bases:
            self.base_combo.addItem(b.name, b.id)

    def _load_projects(self):
        airline_id = self.airline_combo.currentData()
        base_id = self.base_combo.currentData()
        projects = self.db.get_projects(airline_id, base_id)
        self.project_combo.clear()
        self.project_combo.addItem("-- 请选择合同项目 --", None)
        for p in projects:
            self.project_combo.addItem(f"{p.name} ({p.contract_no})", p.id)

    def _on_filter_changed(self):
        self._load_projects()
        self._refresh_job_list()

    def _on_project_changed(self):
        project_id = self.project_combo.currentData()
        if project_id:
            projects = self.db.get_projects()
            for p in projects:
                if p.id == project_id:
                    self.current_project = p
                    break
        else:
            self.current_project = None
        self._refresh_job_list()
        self._update_buttons_state()

    def _on_date_changed(self, qdate: QDate):
        self.current_date = date(qdate.year(), qdate.month(), qdate.day())
        self._refresh_job_list()

    def _on_search(self):
        self._refresh_job_list()

    def _refresh_job_list(self):
        self.job_list.clear()

        project_id = self.project_combo.currentData()
        if not project_id:
            self._update_summary(None)
            return

        jobs = self.db.get_risk_jobs(project_id=project_id, job_date=self.current_date)
        for job in jobs:
            item = QListWidgetItem()
            color = RISK_COLORS.get(job.risk_level, "#34495e")
            status_icon = {"未开工": "⏳", "进行中": "🔄", "已关闭": "✅"}.get(job.status, "•")
            issue_tag = " ⚠" if job.issues else ""
            client_tag = " 👤" if job.need_client_safety_officer else ""
            item.setText(
                f"{status_icon} [{job.risk_level}] {job.work_type} "
                f"- {job.work_location} ({job.aircraft_no}){issue_tag}{client_tag}\n"
                f"    班组：{job.team} | 负责人：{job.team_leader}"
                f"{' | 未审核' if not job.reviewed_by_pm else ''}"
            )
            item.setForeground(Qt.black)
            item.setData(Qt.UserRole, job.id)
            self.job_list.addItem(item)

        self._update_summary(jobs)

    def _update_summary(self, jobs):
        if not jobs:
            self.lbl_total.setText("风险作业总数：0")
            self.lbl_pending.setText("未开工：0")
            self.lbl_doing.setText("进行中：0")
            self.lbl_closed.setText("已关闭：0")
            self.lbl_issues.setText("存在问题：0")
            return

        total = len(jobs)
        pending = sum(1 for j in jobs if j.status == "未开工")
        doing = sum(1 for j in jobs if j.status == "进行中")
        closed = sum(1 for j in jobs if j.status == "已关闭")
        issues = sum(1 for j in jobs if j.issues)

        self.lbl_total.setText(f"风险作业总数：{total}")
        self.lbl_pending.setText(f"未开工：{pending}")
        self.lbl_doing.setText(f"进行中：{doing}")
        self.lbl_closed.setText(f"已关闭：{closed}")
        self.lbl_issues.setText(f"存在问题：{issues}")

    def _update_buttons_state(self):
        has_project = self.current_project is not None
        self.btn_fill.setEnabled(has_project)
        self.btn_report.setEnabled(has_project)

    def _open_risk_entry(self):
        if not self.current_project:
            QMessageBox.warning(self, "提示", "请先选择合同项目")
            return
        self.db.touch_recent_project(self.current_project.id)
        self._refresh_recent_projects()
        self.risk_entry_window = RiskEntryWindow(self.db, self.current_project, self.current_date)
        self.risk_entry_window.jobs_updated.connect(self._refresh_job_list)
        self.risk_entry_window.show()

    def _open_daily_report(self):
        if not self.current_project:
            QMessageBox.warning(self, "提示", "请先选择合同项目")
            return
        self.db.touch_recent_project(self.current_project.id)
        self._refresh_recent_projects()
        self.report_window = DailyReportWindow(self.db, self.current_project, self.current_date)
        self.report_window.show()

    def _open_personnel_qual(self):
        self.personnel_window = PersonnelQualificationWindow(self.db)
        self.personnel_window.personnel_updated.connect(self._on_personnel_updated)
        self.personnel_window.show()

    def _on_personnel_updated(self):
        if self.risk_entry_window and self.risk_entry_window.isVisible():
            self.risk_entry_window._refresh_personnel_list()
        self._refresh_job_list()
