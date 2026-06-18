from datetime import date, datetime
from typing import Optional, List

from PySide6.QtCore import Qt, QDate, QTime, Signal
from PySide6.QtWidgets import (
    QWidget, QLabel, QComboBox, QDateEdit, QTimeEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QGroupBox, QListWidget, QListWidgetItem,
    QLineEdit, QTextEdit, QCheckBox, QMessageBox, QFormLayout,
    QFrame, QScrollArea, QSplitter
)

from app.db.database import Database
from app.models.schemas import (
    ContractProject, RiskJob, WORK_TYPES, RISK_LEVELS,
    JOB_STATUSES, PERMIT_STATUSES, Personnel
)


RISK_COLORS = {
    "低风险": "#27ae60",
    "中风险": "#f39c12",
    "高风险": "#e67e22",
    "极高风险": "#c0392b",
}


class RiskEntryWindow(QWidget):
    jobs_updated = Signal()

    def __init__(self, db: Database, project: ContractProject, job_date: date):
        super().__init__()
        self.db = db
        self.project = project
        self.job_date = job_date
        self.current_job: Optional[RiskJob] = None
        self.all_personnel: List[Personnel] = self.db.get_all_personnel()
        self._init_ui()
        self._refresh_job_list()

    def _init_ui(self):
        self.setWindowTitle(f"风险填报 / 审核 - {self.project.name} ({self.job_date.isoformat()})")
        self.setMinimumSize(1200, 720)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel(f"风险填报与项目经理审核")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        header.addWidget(title)
        header.addStretch(1)
        info = QLabel(f"项目：{self.project.name} · 日期：{self.job_date.isoformat()}")
        info.setStyleSheet("font-size: 13px; color: #7f8c8d;")
        header.addWidget(info)
        layout.addLayout(header)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #bdc3c7; width: 2px; }")

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 10, 0)

        list_header = QHBoxLayout()
        list_title = QLabel("当日风险作业")
        list_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        list_header.addWidget(list_title)
        list_header.addStretch(1)

        self.btn_new = QPushButton("+ 新增作业")
        self.btn_new.setStyleSheet("""
            QPushButton {
                background: #2980b9; color: white; padding: 6px 14px;
                border: none; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background: #3498db; }
        """)
        self.btn_new.clicked.connect(self._new_job)
        list_header.addWidget(self.btn_new)
        left_layout.addLayout(list_header)

        self.job_list = QListWidget()
        self.job_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #bdc3c7; border-radius: 6px;
                background: white; padding: 4px;
            }
            QListWidget::item {
                padding: 8px; border-radius: 4px; margin: 2px 0;
                border-bottom: 1px solid #ecf0f1;
            }
            QListWidget::item:selected { background: #e8f4fc; color: #2c3e50; }
        """)
        self.job_list.currentItemChanged.connect(self._on_job_selected)
        left_layout.addWidget(self.job_list, 1)

        self.btn_delete = QPushButton("删除所选作业")
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background: #e74c3c; color: white; padding: 8px;
                border: none; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background: #ec7063; }
            QPushButton:disabled { background: #95a5a6; }
        """)
        self.btn_delete.clicked.connect(self._delete_job)
        left_layout.addWidget(self.btn_delete)

        splitter.addWidget(left_panel)

        right_panel = QScrollArea()
        right_panel.setWidgetResizable(True)
        right_panel.setFrameShape(QFrame.NoFrame)
        right_content = QWidget()
        self.form_layout = QVBoxLayout(right_content)
        self.form_layout.setContentsMargins(10, 0, 0, 10)
        self.form_layout.setSpacing(10)
        right_panel.setWidget(right_content)

        self._build_form()
        splitter.addWidget(right_panel)
        splitter.setSizes([350, 850])

        layout.addWidget(splitter, 1)

        self._enable_form(False)

    def _build_form(self):
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)

        self.work_type_combo = QComboBox()
        for wt in WORK_TYPES:
            self.work_type_combo.addItem(wt)

        self.risk_level_combo = QComboBox()
        for rl in RISK_LEVELS:
            self.risk_level_combo.addItem(rl)

        self.status_combo = QComboBox()
        for s in JOB_STATUSES:
            self.status_combo.addItem(s)

        self.permit_status_combo = QComboBox()
        for ps in PERMIT_STATUSES:
            self.permit_status_combo.addItem(ps)

        self.work_location_edit = QLineEdit()
        self.work_location_edit.setPlaceholderText("如：喷漆机库A区、机身42段等")
        self.aircraft_no_edit = QLineEdit()
        self.aircraft_no_edit.setPlaceholderText("如：B-6123")
        self.team_edit = QLineEdit()
        self.team_edit.setPlaceholderText("如：喷漆一班")
        self.team_leader_edit = QLineEdit()
        self.team_leader_edit.setPlaceholderText("班组长姓名")
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("作业内容简述，如：整机喷漆含打磨、底漆、面漆工序")
        self.description_edit.setMaximumHeight(70)
        self.isolation_edit = QTextEdit()
        self.isolation_edit.setPlaceholderText("隔离措施，如：拉设警戒线、配备消防器材、专人值守等")
        self.isolation_edit.setMaximumHeight(70)

        self.permit_expiry_edit = QDateEdit()
        self.permit_expiry_edit.setCalendarPopup(True)
        self.permit_expiry_edit.setDisplayFormat("yyyy-MM-dd")
        self.permit_expiry_edit.setDate(QDate.currentDate().addDays(7))

        self.est_end_date = QDateEdit()
        self.est_end_date.setCalendarPopup(True)
        self.est_end_date.setDisplayFormat("yyyy-MM-dd")
        self.est_end_date.setDate(QDate.currentDate())
        self.est_end_time = QTimeEdit()
        self.est_end_time.setDisplayFormat("HH:mm")
        self.est_end_time.setTime(QTime(18, 0))
        est_end_layout = QHBoxLayout()
        est_end_layout.addWidget(self.est_end_date)
        est_end_layout.addWidget(self.est_end_time)
        est_end_widget = QWidget()
        est_end_widget.setLayout(est_end_layout)

        self.personnel_list_widget = QListWidget()
        self.personnel_list_widget.setSelectionMode(QListWidget.MultiSelection)
        self.personnel_list_widget.setMaximumHeight(120)
        self.personnel_list_widget.setStyleSheet("""
            QListWidget { border: 1px solid #bdc3c7; border-radius: 4px; }
        """)
        for p in self.all_personnel:
            expiry_str = p.certificate_expiry.isoformat() if p.certificate_expiry else "无"
            item = QListWidgetItem(f"{p.name} ({p.team}) - 证到期：{expiry_str}")
            item.setData(Qt.UserRole, p.id)
            self.personnel_list_widget.addItem(item)

        info_box = QGroupBox("作业基础信息")
        info_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold; font-size: 13px;
                border: 1px solid #bdc3c7; border-radius: 6px;
                margin-top: 8px; padding: 12px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)
        info_form = QFormLayout(info_box)
        info_form.setSpacing(8)
        info_form.addRow("作业类型：", self.work_type_combo)
        info_form.addRow("风险等级：", self.risk_level_combo)
        info_form.addRow("作业状态：", self.status_combo)
        info_form.addRow("作业位置：", self.work_location_edit)
        info_form.addRow("飞机注册号：", self.aircraft_no_edit)
        info_form.addRow("作业班组：", self.team_edit)
        info_form.addRow("班组负责人：", self.team_leader_edit)
        info_form.addRow("作业描述：", self.description_edit)
        self.form_layout.addWidget(info_box)

        safety_box = QGroupBox("安全与许可")
        safety_box.setStyleSheet(info_box.styleSheet())
        safety_form = QFormLayout(safety_box)
        safety_form.setSpacing(8)
        safety_form.addRow("隔离措施：", self.isolation_edit)
        safety_form.addRow("许可证状态：", self.permit_status_combo)
        safety_form.addRow("许可证到期日：", self.permit_expiry_edit)
        safety_form.addRow("参与人员：", self.personnel_list_widget)
        safety_form.addRow("预计结束时间：", est_end_widget)
        self.form_layout.addWidget(safety_box)

        review_box = QGroupBox("项目经理审核")
        review_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold; font-size: 13px;
                border: 2px solid #2980b9; border-radius: 6px;
                margin-top: 8px; padding: 12px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #2980b9; }
        """)
        review_layout = QVBoxLayout(review_box)

        self.chk_need_client = QCheckBox("需要客户方安全员到场监督")
        self.chk_need_client.setStyleSheet("font-size: 13px; padding: 4px 0;")
        review_layout.addWidget(self.chk_need_client)

        self.chk_reviewed = QCheckBox("已审核（项目经理）")
        self.chk_reviewed.setStyleSheet("font-size: 13px; padding: 4px 0; font-weight: bold;")
        review_layout.addWidget(self.chk_reviewed)

        pm_label = QLabel("项目经理审核意见 / 备注：")
        pm_label.setStyleSheet("font-size: 12px; color: #34495e; margin-top: 4px;")
        review_layout.addWidget(pm_label)
        self.pm_comments_edit = QTextEdit()
        self.pm_comments_edit.setMaximumHeight(50)
        self.pm_comments_edit.setPlaceholderText("审核意见、注意事项等")
        review_layout.addWidget(self.pm_comments_edit)

        issues_label = QLabel("发现的问题（超范围作业 / 证照不匹配 / 许可证过期等）：")
        issues_label.setStyleSheet("font-size: 12px; color: #c0392b; margin-top: 6px; font-weight: bold;")
        review_layout.addWidget(issues_label)
        self.issues_edit = QTextEdit()
        self.issues_edit.setMaximumHeight(50)
        self.issues_edit.setPlaceholderText("如：许可证明日到期，需续办；超合同范围作业需客户书面批准等")
        self.issues_edit.setStyleSheet("QTextEdit { border: 1px solid #e74c3c; }")
        review_layout.addWidget(self.issues_edit)

        self.form_layout.addWidget(review_box)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_save = QPushButton("💾 保存作业信息")
        self.btn_save.setMinimumHeight(40)
        self.btn_save.setMinimumWidth(160)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background: #27ae60; color: white; font-weight: bold;
                border: none; border-radius: 6px; font-size: 14px;
            }
            QPushButton:hover { background: #2ecc71; }
            QPushButton:pressed { background: #1e8449; }
        """)
        self.btn_save.clicked.connect(self._save_job)
        btn_row.addWidget(self.btn_save)

        self.btn_quick_issue = QPushButton("⚡ 快速标记问题")
        self.btn_quick_issue.setMinimumHeight(40)
        self.btn_quick_issue.setMinimumWidth(140)
        self.btn_quick_issue.setStyleSheet("""
            QPushButton {
                background: #e67e22; color: white; font-weight: bold;
                border: none; border-radius: 6px; font-size: 13px;
            }
            QPushButton:hover { background: #f39c12; }
        """)
        self.btn_quick_issue.clicked.connect(self._quick_detect_issues)
        btn_row.addWidget(self.btn_quick_issue)

        self.form_layout.addLayout(btn_row)

        self.form_layout.addStretch(1)

    def _enable_form(self, enabled: bool):
        for w in [
            self.work_type_combo, self.risk_level_combo, self.status_combo,
            self.permit_status_combo, self.work_location_edit, self.aircraft_no_edit,
            self.team_edit, self.team_leader_edit, self.description_edit,
            self.isolation_edit, self.permit_expiry_edit, self.personnel_list_widget,
            self.est_end_date, self.est_end_time, self.chk_need_client,
            self.chk_reviewed, self.pm_comments_edit, self.issues_edit,
            self.btn_save, self.btn_quick_issue, self.btn_delete
        ]:
            w.setEnabled(enabled)

    def _refresh_job_list(self):
        self.job_list.clear()
        jobs = self.db.get_risk_jobs(project_id=self.project.id, job_date=self.job_date)
        for job in jobs:
            item = QListWidgetItem()
            color = RISK_COLORS.get(job.risk_level, "#34495e")
            status_icon = {"未开工": "⏳", "进行中": "🔄", "已关闭": "✅"}.get(job.status, "•")
            review_tag = "" if job.reviewed_by_pm else "  [未审核]"
            item.setText(
                f"{status_icon} {job.work_type}\n"
                f"   {job.work_location} · {job.aircraft_no}{review_tag}"
            )
            item.setData(Qt.UserRole, job.id)
            if job.issues:
                item.setForeground(Qt.red)
            self.job_list.addItem(item)

    def _on_job_selected(self, current, previous):
        if not current:
            self._clear_form()
            self._enable_form(False)
            self.current_job = None
            return
        job_id = current.data(Qt.UserRole)
        jobs = self.db.get_risk_jobs()
        job = next((j for j in jobs if j.id == job_id), None)
        if job:
            self.current_job = job
            self._fill_form(job)
            self._enable_form(True)

    def _new_job(self):
        self.current_job = RiskJob(
            project_id=self.project.id,
            job_date=self.job_date,
            status="未开工",
            risk_level="中风险",
            permit_status="未办理",
        )
        self._clear_form()
        self._enable_form(True)
        self.work_type_combo.setFocus()
        self.job_list.clearSelection()

    def _clear_form(self):
        self.work_type_combo.setCurrentIndex(0)
        self.risk_level_combo.setCurrentIndex(1)
        self.status_combo.setCurrentIndex(0)
        self.permit_status_combo.setCurrentIndex(3)
        self.work_location_edit.clear()
        self.aircraft_no_edit.clear()
        self.team_edit.clear()
        self.team_leader_edit.clear()
        self.description_edit.clear()
        self.isolation_edit.clear()
        self.permit_expiry_edit.setDate(QDate.currentDate().addDays(7))
        self.est_end_date.setDate(QDate(self.job_date.year, self.job_date.month, self.job_date.day))
        self.est_end_time.setTime(QTime(18, 0))
        self.personnel_list_widget.clearSelection()
        self.chk_need_client.setChecked(False)
        self.chk_reviewed.setChecked(False)
        self.pm_comments_edit.clear()
        self.issues_edit.clear()

    def _fill_form(self, job: RiskJob):
        idx = self.work_type_combo.findText(job.work_type)
        if idx >= 0:
            self.work_type_combo.setCurrentIndex(idx)
        idx = self.risk_level_combo.findText(job.risk_level)
        if idx >= 0:
            self.risk_level_combo.setCurrentIndex(idx)
        idx = self.status_combo.findText(job.status)
        if idx >= 0:
            self.status_combo.setCurrentIndex(idx)
        idx = self.permit_status_combo.findText(job.permit_status)
        if idx >= 0:
            self.permit_status_combo.setCurrentIndex(idx)

        self.work_location_edit.setText(job.work_location)
        self.aircraft_no_edit.setText(job.aircraft_no)
        self.team_edit.setText(job.team)
        self.team_leader_edit.setText(job.team_leader)
        self.description_edit.setPlainText(job.description)
        self.isolation_edit.setPlainText(job.isolation_measures)
        if job.permit_expiry:
            self.permit_expiry_edit.setDate(QDate(
                job.permit_expiry.year, job.permit_expiry.month, job.permit_expiry.day))
        if job.estimated_end_time:
            self.est_end_date.setDate(QDate(
                job.estimated_end_time.year, job.estimated_end_time.month, job.estimated_end_time.day))
            self.est_end_time.setTime(QTime(
                job.estimated_end_time.hour, job.estimated_end_time.minute))

        self.personnel_list_widget.clearSelection()
        for i in range(self.personnel_list_widget.count()):
            item = self.personnel_list_widget.item(i)
            if item.data(Qt.UserRole) in job.personnel_ids:
                item.setSelected(True)

        self.chk_need_client.setChecked(job.need_client_safety_officer)
        self.chk_reviewed.setChecked(job.reviewed_by_pm)
        self.pm_comments_edit.setPlainText(job.pm_comments)
        self.issues_edit.setPlainText(job.issues)

    def _collect_form(self) -> Optional[RiskJob]:
        if not self.work_location_edit.text().strip():
            QMessageBox.warning(self, "提示", "请填写作业位置")
            return None
        if not self.team_edit.text().strip():
            QMessageBox.warning(self, "提示", "请填写作业班组")
            return None

        job = self.current_job or RiskJob()
        job.project_id = self.project.id
        job.job_date = self.job_date
        job.work_type = self.work_type_combo.currentText()
        job.risk_level = self.risk_level_combo.currentText()
        job.status = self.status_combo.currentText()
        job.permit_status = self.permit_status_combo.currentText()
        job.work_location = self.work_location_edit.text().strip()
        job.aircraft_no = self.aircraft_no_edit.text().strip()
        job.team = self.team_edit.text().strip()
        job.team_leader = self.team_leader_edit.text().strip()
        job.description = self.description_edit.toPlainText().strip()
        job.isolation_measures = self.isolation_edit.toPlainText().strip()

        pe = self.permit_expiry_edit.date()
        job.permit_expiry = date(pe.year(), pe.month(), pe.day())

        d = self.est_end_date.date()
        t = self.est_end_time.time()
        job.estimated_end_time = datetime(d.year(), d.month(), d.day(), t.hour(), t.minute())

        selected_ids = []
        for i in range(self.personnel_list_widget.count()):
            item = self.personnel_list_widget.item(i)
            if item.isSelected():
                selected_ids.append(item.data(Qt.UserRole))
        job.personnel_ids = selected_ids

        job.need_client_safety_officer = self.chk_need_client.isChecked()
        job.reviewed_by_pm = self.chk_reviewed.isChecked()
        job.pm_comments = self.pm_comments_edit.toPlainText().strip()
        job.issues = self.issues_edit.toPlainText().strip()

        return job

    def _save_job(self):
        job = self._collect_form()
        if not job:
            return
        job.id = self.db.save_risk_job(job)
        self.current_job = job
        QMessageBox.information(self, "成功", "作业信息已保存")
        self._refresh_job_list()
        self.jobs_updated.emit()

        for i in range(self.job_list.count()):
            item = self.job_list.item(i)
            if item.data(Qt.UserRole) == job.id:
                self.job_list.setCurrentItem(item)
                break

    def _quick_detect_issues(self):
        job = self._collect_form()
        if not job:
            return
        issues = []

        if job.permit_status == "已过期":
            issues.append("许可证已过期，作业暂停")
        elif job.permit_status == "即将过期":
            issues.append("许可证即将过期，需及时续办")
        elif job.permit_status == "未办理":
            issues.append("未办理作业许可证")

        today = date.today()
        if job.permit_expiry and job.permit_expiry < today:
            issues.append("许可证到期日早于今日")
        elif job.permit_expiry and (job.permit_expiry - today).days <= 3:
            issues.append(f"许可证剩余{(job.permit_expiry - today).days}天到期")

        personnel = self.db.get_personnel_by_ids(job.personnel_ids)
        for p in personnel:
            if p.certificate_expiry and p.certificate_expiry < today:
                issues.append(f"人员【{p.name}】证照已过期")
            elif p.certificate_expiry and (p.certificate_expiry - today).days <= 30:
                issues.append(f"人员【{p.name}】证照{(p.certificate_expiry - today).days}天后到期")

        if issues:
            existing = self.issues_edit.toPlainText().strip()
            text = existing + ("\n" if existing else "") + "；".join(issues)
            self.issues_edit.setPlainText(text)
            QMessageBox.information(self, "检测结果", f"发现 {len(issues)} 项问题，已填入问题栏")
        else:
            QMessageBox.information(self, "检测结果", "未发现明显问题")

    def _delete_job(self):
        if not self.current_job or not self.current_job.id:
            return
        reply = QMessageBox.question(
            self, "确认删除", "确定要删除该条风险作业记录吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_risk_job(self.current_job.id)
            self.current_job = None
            self._clear_form()
            self._enable_form(False)
            self._refresh_job_list()
            self.jobs_updated.emit()
