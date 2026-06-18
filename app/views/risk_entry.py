from datetime import date, datetime
from typing import Optional, List

from PySide6.QtCore import Qt, QDate, QTime, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QLabel, QComboBox, QDateEdit, QTimeEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QGroupBox, QListWidget, QListWidgetItem,
    QLineEdit, QTextEdit, QCheckBox, QMessageBox, QFormLayout,
    QFrame, QScrollArea, QSplitter, QDialog, QDialogButtonBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)

from app.db.database import Database
from app.models.schemas import (
    ContractProject, RiskJob, Personnel, PersonnelQualification,
    WORK_TYPES, RISK_LEVELS, JOB_STATUSES, PERMIT_STATUSES
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
        self.personnel_list_widget.setMaximumHeight(140)
        self.personnel_list_widget.setStyleSheet("""
            QListWidget { border: 1px solid #bdc3c7; border-radius: 4px; }
            QListWidget::item { padding: 4px 6px; border-bottom: 1px solid #ecf0f1; }
        """)
        self._refresh_personnel_list()

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

        self.personnel_match_label = QLabel("选择作业类型后将显示人员资质匹配情况")
        self.personnel_match_label.setStyleSheet("font-size: 11px; color: #7f8c8d; padding: 2px 0;")
        self.personnel_match_label.setWordWrap(True)
        safety_form.addRow(self.personnel_match_label)
        safety_form.addRow("参与人员：", self.personnel_list_widget)
        safety_form.addRow("预计结束时间：", est_end_widget)
        self.form_layout.addWidget(safety_box)

        self.work_type_combo.currentIndexChanged.connect(self._update_personnel_match_marks)

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

        self.close_info_label = QLabel("")
        self.close_info_label.setWordWrap(True)
        self.close_info_label.setStyleSheet("font-size: 12px; padding: 4px 0;")
        review_layout.addWidget(self.close_info_label)

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

        self.btn_quick_issue = QPushButton("🔍 现场审核助手")
        self.btn_quick_issue.setMinimumHeight(40)
        self.btn_quick_issue.setMinimumWidth(160)
        self.btn_quick_issue.setStyleSheet("""
            QPushButton {
                background: #e67e22; color: white; font-weight: bold;
                border: none; border-radius: 6px; font-size: 13px;
            }
            QPushButton:hover { background: #f39c12; }
        """)
        self.btn_quick_issue.clicked.connect(self._open_audit_assistant)
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

        self._refresh_personnel_list()
        for i in range(self.personnel_list_widget.count()):
            item = self.personnel_list_widget.item(i)
            if item.data(Qt.UserRole) in job.personnel_ids:
                item.setSelected(True)

        self.chk_need_client.setChecked(job.need_client_safety_officer)
        self.chk_reviewed.setChecked(job.reviewed_by_pm)
        self.pm_comments_edit.setPlainText(job.pm_comments)
        self.issues_edit.setPlainText(job.issues)
        self._update_close_info(job)

    def _update_close_info(self, job: RiskJob):
        if job.status != "已关闭":
            self.close_info_label.setText("")
            self.close_info_label.setStyleSheet("font-size: 12px; padding: 4px 0;")
            return
        actual_str = job.actual_end_time.strftime("%m-%d %H:%M") if job.actual_end_time else "未填写"
        est_str = job.estimated_end_time.strftime("%m-%d %H:%M") if job.estimated_end_time else "无"
        overdue = self.db.is_overdue_closed(job)
        if overdue:
            over_hours = (job.actual_end_time - job.estimated_end_time).total_seconds() / 3600
            tag = f"🔴 超时关闭（超时 {over_hours:.1f} 小时）"
            color = "#c0392b"
        else:
            tag = "🟢 按时关闭"
            color = "#27ae60"
        remark = job.close_remark or "无"
        self.close_info_label.setText(
            f"🚪 已关闭 | 实际结束：{actual_str} | 预计：{est_str} | {tag}\n关闭说明：{remark}"
        )
        self.close_info_label.setStyleSheet(
            f"font-size: 12px; padding: 6px 8px; color: {color}; font-weight: bold; "
            f"background: {'#fdecea' if overdue else '#eafaf1'}; border-radius: 4px;"
        )

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
        old_status = self.current_job.status if (self.current_job and self.current_job.id) else None
        job = self._collect_form()
        if not job:
            return

        if job.status == "已关闭" and old_status != "已关闭":
            dlg = CloseJobDialog(self.job_date, job.estimated_end_time, self)
            if dlg.exec() != QDialog.Accepted:
                return
            d = dlg.actual_date.date()
            t = dlg.actual_time.time()
            job.actual_end_time = datetime(d.year(), d.month(), d.day(), t.hour(), t.minute())
            remark = dlg.remark_edit.toPlainText().strip()
            if job.estimated_end_time and job.actual_end_time > job.estimated_end_time:
                over_hours = (job.actual_end_time - job.estimated_end_time).total_seconds() / 3600
                tag = f"【超时关闭·超时{over_hours:.1f}小时】"
            else:
                tag = "【按时关闭】"
            job.close_remark = tag + (remark if remark else "")

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

    def _refresh_personnel_list(self):
        self.all_personnel = self.db.get_all_personnel()
        self.personnel_list_widget.clear()
        work_type = self.work_type_combo.currentText() if self.work_type_combo else ""
        today = date.today()
        for p in self.all_personnel:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, p.id)
            self._apply_personnel_match_mark(item, p, work_type, today)
            self.personnel_list_widget.addItem(item)
        self._update_match_summary()

    def _apply_personnel_match_mark(self, item, p, work_type, today):
        expiry_str = p.certificate_expiry.isoformat() if p.certificate_expiry else "无"
        if work_type:
            chk = self.db.check_qualification(p.id, work_type)
            status = chk["status"]
            if status == "无资质":
                tag, color = "❌无资质", "#c0392b"
            elif status == "已过期":
                tag, color = "⚠证过期", "#c0392b"
            elif status == "即将过期":
                days = (chk["expiry_date"] - today).days
                tag, color = f"⚠临期{days}天", "#e67e22"
            else:
                tag, color = "✓匹配", "#27ae60"
        else:
            tag, color = "", "#2c3e50"
        item.setText(f"{p.name}（{p.team}）{tag}  上岗证：{expiry_str}")
        item.setForeground(QColor(color))

    def _update_personnel_match_marks(self):
        work_type = self.work_type_combo.currentText()
        today = date.today()
        for i in range(self.personnel_list_widget.count()):
            item = self.personnel_list_widget.item(i)
            pid = item.data(Qt.UserRole)
            p = next((x for x in self.all_personnel if x.id == pid), None)
            if p:
                selected = item.isSelected()
                self._apply_personnel_match_mark(item, p, work_type, today)
                if selected:
                    item.setSelected(True)
        self._update_match_summary()

    def _update_match_summary(self):
        work_type = self.work_type_combo.currentText()
        if not work_type:
            self.personnel_match_label.setText("选择作业类型后将显示人员资质匹配情况")
            return
        match = no_qual = warn = 0
        for i in range(self.personnel_list_widget.count()):
            item = self.personnel_list_widget.item(i)
            pid = item.data(Qt.UserRole)
            chk = self.db.check_qualification(pid, work_type)
            s = chk["status"]
            if s == "无资质":
                no_qual += 1
            elif s in ("已过期", "即将过期"):
                warn += 1
            else:
                match += 1
        self.personnel_match_label.setText(
            f"当前作业类型【{work_type}】：✓匹配 {match} 人 · 无资质 {no_qual} 人 · 证过期/临期 {warn} 人"
        )

    def _open_audit_assistant(self):
        job = self._collect_form()
        if not job:
            return
        issues = self.db.detect_job_issues(job)
        dlg = AuditAssistantDialog(job, issues, self)
        if dlg.exec() == QDialog.Accepted and dlg.issues_text.strip():
            existing = self.issues_edit.toPlainText().strip()
            new_text = dlg.issues_text.strip()
            combined = existing + ("\n" if existing else "") + new_text
            self.issues_edit.setPlainText(combined)
            QMessageBox.information(self, "已写入", "审核问题已写入问题栏，请记得保存作业信息。")

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


class CloseJobDialog(QDialog):
    def __init__(self, job_date: date, estimated_end_time, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关闭作业")
        self.setMinimumWidth(420)
        self._build(job_date, estimated_end_time)

    def _build(self, job_date, estimated_end_time):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("🚪 确认关闭作业")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)

        est_str = estimated_end_time.strftime("%Y-%m-%d %H:%M") if estimated_end_time else "未设置"
        est_lbl = QLabel(f"预计结束时间：{est_str}")
        est_lbl.setStyleSheet("font-size: 13px; color: #7f8c8d;")
        layout.addWidget(est_lbl)

        form = QFormLayout()
        form.setSpacing(8)

        self.actual_date = QDateEdit()
        self.actual_date.setCalendarPopup(True)
        self.actual_date.setDisplayFormat("yyyy-MM-dd")
        self.actual_date.setDate(QDate(job_date.year, job_date.month, job_date.day))

        self.actual_time = QTimeEdit()
        self.actual_time.setDisplayFormat("HH:mm")
        self.actual_time.setTime(QTime.currentTime())

        if estimated_end_time:
            self.actual_date.setDate(QDate(
                estimated_end_time.year, estimated_end_time.month, estimated_end_time.day))
            self.actual_time.setTime(QTime(
                estimated_end_time.hour, estimated_end_time.minute))

        time_row = QHBoxLayout()
        time_row.addWidget(self.actual_date)
        time_row.addWidget(self.actual_time)
        time_widget = QWidget()
        time_widget.setLayout(time_row)
        form.addRow("实际结束时间：", time_widget)

        self.remark_edit = QTextEdit()
        self.remark_edit.setMaximumHeight(80)
        self.remark_edit.setPlaceholderText("关闭说明，如：作业按时完成、外观检查合格等")
        form.addRow("关闭说明：", self.remark_edit)

        layout.addLayout(form)

        self.overdue_hint = QLabel("")
        self.overdue_hint.setWordWrap(True)
        self.overdue_hint.setStyleSheet("font-size: 12px; padding: 4px 0;")
        layout.addWidget(self.overdue_hint)

        self.actual_date.dateChanged.connect(self._update_overdue_hint)
        self.actual_time.timeChanged.connect(self._update_overdue_hint)
        self._estimated_end_time = estimated_end_time
        self._update_overdue_hint()

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("确认关闭")
        btns.button(QDialogButtonBox.Cancel).setText("取消")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _update_overdue_hint(self):
        if not self._estimated_end_time:
            self.overdue_hint.setText("（未设置预计结束时间，无法判断是否超时）")
            self.overdue_hint.setStyleSheet("font-size: 12px; color: #7f8c8d; padding: 4px 0;")
            return
        d = self.actual_date.date()
        t = self.actual_time.time()
        actual = datetime(d.year(), d.month(), d.day(), t.hour(), t.minute())
        if actual > self._estimated_end_time:
            over_hours = (actual - self._estimated_end_time).total_seconds() / 3600
            self.overdue_hint.setText(f"🔴 将标记为超时关闭（超时 {over_hours:.1f} 小时）")
            self.overdue_hint.setStyleSheet("font-size: 12px; color: #c0392b; padding: 4px 0; font-weight: bold;")
        else:
            self.overdue_hint.setText("🟢 将标记为按时关闭")
            self.overdue_hint.setStyleSheet("font-size: 12px; color: #27ae60; padding: 4px 0; font-weight: bold;")


class AuditAssistantDialog(QDialog):
    def __init__(self, job: RiskJob, issues, parent=None):
        super().__init__(parent)
        self.setWindowTitle("现场审核助手")
        self.setMinimumSize(680, 480)
        self.issues_text = ""
        self._build(job, issues)

    def _build(self, job, issues):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("🔍 现场审核助手")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)

        summary = QLabel(
            f"作业类型：{job.work_type} · 位置：{job.work_location or '-'} · "
            f"参与人员：{len(job.personnel_ids)} 人"
        )
        summary.setStyleSheet("font-size: 13px; color: #7f8c8d;")
        summary.setWordWrap(True)
        layout.addWidget(summary)

        if issues:
            table = QTableWidget(len(issues), 4)
            table.setHorizontalHeaderLabels(["类别", "对象", "问题描述", "选择"])
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
            table.setStyleSheet("""
                QTableWidget { border: 1px solid #bdc3c7; border-radius: 4px; background: white; }
                QHeaderView::section { background: #ecf0f1; font-weight: bold; padding: 6px; }
            """)
            type_colors = {
                "资质不匹配": "#c0392b",
                "证照过期": "#c0392b",
                "上岗证过期": "#c0392b",
                "许可证过期": "#c0392b",
                "许可证已过期": "#c0392b",
                "超时未关闭": "#e67e22",
                "证照即将过期": "#e67e22",
                "上岗证即将过期": "#e67e22",
                "许可证即将过期": "#e67e22",
                "许可证临期": "#e67e22",
                "未办理许可证": "#e67e22",
            }
            for i, issue in enumerate(issues):
                obj = issue.personnel_name if issue.personnel_name else "作业整体"
                type_item = QTableWidgetItem(issue.issue_type)
                color = type_colors.get(issue.issue_type, "#34495e")
                type_item.setForeground(QColor(color))
                table.setItem(i, 0, type_item)
                table.setItem(i, 1, QTableWidgetItem(obj))
                table.setItem(i, 2, QTableWidgetItem(issue.detail))
                chk_item = QTableWidgetItem()
                chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                chk_item.setCheckState(Qt.Checked)
                table.setItem(i, 3, chk_item)
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self._table = table
            self._issues = issues
            layout.addWidget(table, 1)

            hint = QLabel("已勾选的问题将写入作业的「问题」栏。可取消勾选不需要记录的项。")
            hint.setStyleSheet("font-size: 11px; color: #7f8c8d;")
            layout.addWidget(hint)
        else:
            ok_lbl = QLabel("✅ 未发现问题\n\n当前作业的人员资质、许可证、证照有效期均符合要求。")
            ok_lbl.setStyleSheet("font-size: 15px; color: #27ae60; padding: 30px;")
            ok_lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(ok_lbl)
            self._table = None
            self._issues = []

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("写入问题栏")
        btns.button(QDialogButtonBox.Cancel).setText("关闭")
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_accept(self):
        if self._table:
            selected = []
            for i, issue in enumerate(self._issues):
                chk = self._table.item(i, 3)
                if chk and chk.checkState() == Qt.Checked:
                    obj = issue.personnel_name if issue.personnel_name else ""
                    prefix = f"【{issue.issue_type}】" + (f"{obj}：" if obj else "：")
                    selected.append(prefix + issue.detail)
            self.issues_text = "\n".join(selected)
        self.accept()
