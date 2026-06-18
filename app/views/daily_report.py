from datetime import date, datetime
from typing import List

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QBrush
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGroupBox, QFrame, QScrollArea, QGridLayout, QSizePolicy,
    QMessageBox
)

from app.db.database import Database
from app.models.schemas import (
    ContractProject, RiskJob, JOB_STATUSES, Personnel
)


RISK_COLORS = {
    "低风险": "#27ae60",
    "中风险": "#f39c12",
    "高风险": "#e67e22",
    "极高风险": "#c0392b",
}

STATUS_COLORS = {
    "未开工": "#95a5a6",
    "进行中": "#3498db",
    "已关闭": "#27ae60",
}


class RiskCard(QFrame):
    def __init__(self, job: RiskJob, personnel: List[Personnel],
                 is_overdue_closed: bool = False):
        super().__init__()
        self.job = job
        self.personnel = personnel
        self.is_overdue_closed = is_overdue_closed
        self._build()

    def _build(self):
        has_issue = bool(self.job.issues)
        border_color = "#e74c3c" if has_issue else "#bdc3c7"
        border_width = 3 if has_issue else 1

        self.setStyleSheet(f"""
            QFrame {{
                background: white;
                border: {border_width}px solid {border_color};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        risk_color = RISK_COLORS.get(self.job.risk_level, "#34495e")
        risk_label = QLabel(f"● {self.job.risk_level}")
        risk_label.setStyleSheet(f"""
            color: {risk_color}; font-weight: bold; font-size: 13px;
        """)
        header.addWidget(risk_label)

        if self.job.need_client_safety_officer:
            client_tag = QLabel("👤 客户安全员")
            client_tag.setStyleSheet("""
                background: #8e44ad; color: white; padding: 2px 8px;
                border-radius: 4px; font-size: 11px; font-weight: bold;
            """)
            header.addWidget(client_tag)

        if has_issue:
            issue_tag = QLabel("⚠ 有问题")
            issue_tag.setStyleSheet("""
                background: #e74c3c; color: white; padding: 2px 8px;
                border-radius: 4px; font-size: 11px; font-weight: bold;
            """)
            header.addWidget(issue_tag)

        header.addStretch(1)

        if not self.job.reviewed_by_pm:
            review_tag = QLabel("待审核")
            review_tag.setStyleSheet("""
                background: #e67e22; color: white; padding: 2px 8px;
                border-radius: 4px; font-size: 11px; font-weight: bold;
            """)
            header.addWidget(review_tag)

        layout.addLayout(header)

        title = QLabel(self.job.work_type)
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)

        subtitle = QLabel(f"{self.job.work_location} · {self.job.aircraft_no}")
        subtitle.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        layout.addWidget(subtitle)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet("color: #ecf0f1;")
        layout.addWidget(sep1)

        info_grid = QGridLayout()
        info_grid.setHorizontalSpacing(12)
        info_grid.setVerticalSpacing(4)

        def add_info(row, label, value, value_color=None):
            lab = QLabel(f"{label}：")
            lab.setStyleSheet("font-size: 11px; color: #95a5a6;")
            val = QLabel(str(value) if value else "-")
            vc = value_color or "#2c3e50"
            val.setStyleSheet(f"font-size: 11px; color: {vc}; font-weight: bold;")
            val.setWordWrap(True)
            info_grid.addWidget(lab, row, 0)
            info_grid.addWidget(val, row, 1)

        permit_color = None
        if self.job.permit_status == "已过期":
            permit_color = "#e74c3c"
        elif self.job.permit_status == "即将过期":
            permit_color = "#e67e22"
        elif self.job.permit_status == "未办理":
            permit_color = "#95a5a6"

        row = 0
        add_info(row, "班组/负责人", f"{self.job.team} · {self.job.team_leader}"); row += 1
        add_info(row, "许可证", self.job.permit_status, permit_color); row += 1
        if self.job.permit_expiry:
            add_info(row, "许可到期", self.job.permit_expiry.isoformat(), permit_color); row += 1
        est_end_str = "-"
        if self.job.estimated_end_time:
            est_end_str = self.job.estimated_end_time.strftime("%m-%d %H:%M")
        add_info(row, "预计关闭", est_end_str); row += 1

        if self.job.status == "已关闭":
            actual_str = self.job.actual_end_time.strftime("%m-%d %H:%M") if self.job.actual_end_time else "未填"
            close_color = "#c0392b" if self.is_overdue_closed else "#27ae60"
            add_info(row, "实际关闭", actual_str, close_color); row += 1
            close_tag = "🔴 超时关闭" if self.is_overdue_closed else "🟢 按时关闭"
            add_info(row, "关闭结果", close_tag, close_color); row += 1

        if self.personnel:
            names = "、".join(p.name for p in self.personnel)
            names_lbl = QLabel(f"人员：{names}")
            names_lbl.setStyleSheet("font-size: 11px; color: #2c3e50;")
            names_lbl.setWordWrap(True)
            info_grid.addWidget(names_lbl, row, 0, 1, 2)

        layout.addLayout(info_grid)

        if self.job.isolation_measures:
            sep2 = QFrame()
            sep2.setFrameShape(QFrame.HLine)
            sep2.setStyleSheet("color: #ecf0f1;")
            layout.addWidget(sep2)
            iso_lbl = QLabel(f"🔒 {self.job.isolation_measures}")
            iso_lbl.setStyleSheet("font-size: 11px; color: #34495e;")
            iso_lbl.setWordWrap(True)
            layout.addWidget(iso_lbl)

        if has_issue:
            sep3 = QFrame()
            sep3.setFrameShape(QFrame.HLine)
            sep3.setStyleSheet("color: #e74c3c;")
            layout.addWidget(sep3)
            issue_lbl = QLabel(f"🚨 {self.job.issues}")
            issue_lbl.setStyleSheet("font-size: 11px; color: #c0392b; font-weight: bold;")
            issue_lbl.setWordWrap(True)
            layout.addWidget(issue_lbl)

        if self.job.status == "已关闭" and self.job.close_remark:
            sep_close = QFrame()
            sep_close.setFrameShape(QFrame.HLine)
            close_color = "#c0392b" if self.is_overdue_closed else "#27ae60"
            sep_close.setStyleSheet(f"color: {close_color};")
            layout.addWidget(sep_close)
            close_lbl = QLabel(f"🚪 {self.job.close_remark}")
            close_lbl.setStyleSheet(f"font-size: 11px; color: {close_color}; font-weight: bold;")
            close_lbl.setWordWrap(True)
            layout.addWidget(close_lbl)

        if self.job.pm_comments:
            sep4 = QFrame()
            sep4.setFrameShape(QFrame.HLine)
            sep4.setStyleSheet("color: #2980b9;")
            layout.addWidget(sep4)
            pm_lbl = QLabel(f"📋 PM：{self.job.pm_comments}")
            pm_lbl.setStyleSheet("font-size: 11px; color: #2980b9;")
            pm_lbl.setWordWrap(True)
            layout.addWidget(pm_lbl)


class DailyReportWindow(QWidget):
    def __init__(self, db: Database, project: ContractProject, job_date: date):
        super().__init__()
        self.db = db
        self.project = project
        self.job_date = job_date
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle(f"现场风险日报 - {self.project.name} ({self.job_date.isoformat()})")
        self.setMinimumSize(1300, 800)
        self.setStyleSheet("background: #f5f6fa;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self._build_header(layout)
        self._build_summary(layout)
        self._build_coordination(layout)
        self._build_kanban(layout)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_refresh = QPushButton("🔄 刷新数据")
        self.btn_refresh.setMinimumHeight(38)
        self.btn_refresh.setMinimumWidth(130)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background: #2980b9; color: white; font-weight: bold;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background: #3498db; }
        """)
        self.btn_refresh.clicked.connect(self._refresh)
        btn_row.addWidget(self.btn_refresh)

        self.btn_print = QPushButton("📄 打印/导出")
        self.btn_print.setMinimumHeight(38)
        self.btn_print.setMinimumWidth(130)
        self.btn_print.setStyleSheet("""
            QPushButton {
                background: #7f8c8d; color: white; font-weight: bold;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background: #95a5a6; }
        """)
        self.btn_print.clicked.connect(self._on_print)
        btn_row.addWidget(self.btn_print)

        layout.addLayout(btn_row)

        self._refresh()

    def _build_header(self, layout: QVBoxLayout):
        header = QHBoxLayout()

        left = QVBoxLayout()
        title = QLabel("民航维修现场风险日报")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        left.addWidget(title)

        subtitle = QLabel(
            f"承包商：{self.project.name}（合同号：{self.project.contract_no}）"
        )
        subtitle.setStyleSheet("font-size: 13px; color: #7f8c8d; margin-top: 2px;")
        left.addWidget(subtitle)
        header.addLayout(left)
        header.addStretch(1)

        right = QVBoxLayout()
        right.setAlignment(Qt.AlignRight)
        date_lbl = QLabel(f"日报日期：{self.job_date.isoformat()}")
        date_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #2980b9;")
        right.addWidget(date_lbl)
        gen_lbl = QLabel(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
        gen_lbl.setStyleSheet("font-size: 11px; color: #95a5a6;")
        right.addWidget(gen_lbl)
        header.addLayout(right)

        layout.addLayout(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #bdc3c7;")
        layout.addWidget(sep)

    def _build_summary(self, layout: QVBoxLayout):
        self.summary_layout = QHBoxLayout()
        self.summary_layout.setSpacing(12)

        self.card_total = self._make_summary_card("风险作业总数", "0", "#34495e")
        self.card_pending = self._make_summary_card("未开工", "0", "#95a5a6")
        self.card_doing = self._make_summary_card("进行中", "0", "#3498db")
        self.card_closed = self._make_summary_card("已关闭", "0", "#27ae60")
        self.card_issues = self._make_summary_card("⚠ 存在问题", "0", "#e74c3c", highlight=True)

        self.summary_layout.addWidget(self.card_total)
        self.summary_layout.addWidget(self.card_pending)
        self.summary_layout.addWidget(self.card_doing)
        self.summary_layout.addWidget(self.card_closed)
        self.summary_layout.addWidget(self.card_issues)

        layout.addLayout(self.summary_layout)

    def _make_summary_card(self, label: str, value: str, color: str, highlight: bool = False) -> QFrame:
        card = QFrame()
        border_color = "#e74c3c" if highlight else "#bdc3c7"
        border_width = 2 if highlight else 1
        card.setStyleSheet(f"""
            QFrame {{
                background: white;
                border: {border_width}px solid {border_color};
                border-radius: 8px; padding: 12px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(4)
        v_lbl = QLabel(value)
        v_lbl.setAlignment(Qt.AlignCenter)
        v_lbl.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {color};")
        l_lbl = QLabel(label)
        l_lbl.setAlignment(Qt.AlignCenter)
        l_lbl.setStyleSheet(f"font-size: 12px; color: {color};")
        layout.addWidget(v_lbl)
        layout.addWidget(l_lbl)
        return card

    def _update_summary_card(self, card: QFrame, value: str):
        labels = card.findChildren(QLabel)
        if labels:
            labels[0].setText(value)

    def _build_coordination(self, layout: QVBoxLayout):
        box = QGroupBox("协调会摘要（项目经理重点关注）")
        box.setStyleSheet("""
            QGroupBox {
                font-weight: bold; font-size: 14px;
                border: 2px solid #8e44ad; border-radius: 8px;
                margin-top: 8px; padding: 14px 12px 10px 12px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #8e44ad; }
        """)
        box_layout = QHBoxLayout(box)
        box_layout.setSpacing(10)

        self.coord_client_col = self._make_coord_column("👤 需客户安全员到场", "#8e44ad")
        self.coord_close_col = self._make_coord_column("⏰ 预计今天关闭", "#2980b9")
        self.coord_overdue_col = self._make_coord_column("🚨 超时未关闭", "#e74c3c")

        box_layout.addWidget(self.coord_client_col, 1)
        box_layout.addWidget(self.coord_close_col, 1)
        box_layout.addWidget(self.coord_overdue_col, 1)

        layout.addWidget(box)

    def _make_coord_column(self, title: str, color: str) -> QFrame:
        col = QFrame()
        col.setStyleSheet(f"""
            QFrame {{
                background: #fafafa;
                border: 1px solid #ecf0f1;
                border-top: 3px solid {color};
                border-radius: 6px;
            }}
        """)
        v = QVBoxLayout(col)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(4)
        t = QLabel(title)
        t.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {color};")
        v.addWidget(t)

        content = QVBoxLayout()
        content.setSpacing(3)
        content.addStretch(1)
        v.addLayout(content, 1)
        setattr(col, "_content_layout", content)

        count_lbl = QLabel("共 0 项")
        count_lbl.setStyleSheet(f"font-size: 11px; color: {color}; font-weight: bold;")
        v.addWidget(count_lbl)
        setattr(col, "_count_label", count_lbl)
        return col

    def _fill_coord_column(self, col: QFrame, jobs: list, color: str):
        cl = getattr(col, "_content_layout")
        while cl.count() > 1:
            it = cl.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()
        for job in jobs:
            est_str = job.estimated_end_time.strftime("%H:%M") if job.estimated_end_time else "-"
            risk_color = RISK_COLORS.get(job.risk_level, "#34495e")
            lbl = QLabel(
                f"<span style='color:{risk_color}'>●</span> <b>{job.work_type}</b><br>"
                f"<span style='color:#7f8c8d'>{job.work_location} · {job.aircraft_no}</span><br>"
                f"<span style='color:{color}'>预计 {est_str} · {job.team_leader}</span>"
            )
            lbl.setTextFormat(Qt.RichText)
            lbl.setStyleSheet("font-size: 11px; padding: 4px 5px; background: white; border-radius: 3px;")
            lbl.setWordWrap(True)
            cl.insertWidget(cl.count() - 1, lbl)
        getattr(col, "_count_label").setText(f"共 {len(jobs)} 项")

    def _build_kanban(self, layout: QVBoxLayout):
        kanban_container = QWidget()
        kanban_layout = QHBoxLayout(kanban_container)
        kanban_layout.setContentsMargins(0, 0, 0, 0)
        kanban_layout.setSpacing(12)

        self.column_widgets = {}
        for status in JOB_STATUSES:
            col = self._make_kanban_column(status)
            kanban_layout.addWidget(col, 1)
            self.column_widgets[status] = col

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(kanban_container)
        layout.addWidget(scroll, 1)

    def _make_kanban_column(self, status: str) -> QFrame:
        col = QFrame()
        color = STATUS_COLORS.get(status, "#7f8c8d")
        col.setStyleSheet(f"""
            QFrame {{
                background: white;
                border: 1px solid #bdc3c7;
                border-top: 4px solid {color};
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(col)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel(status)
        title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {color};")
        header.addWidget(title)
        header.addStretch(1)

        self.count_labels = getattr(self, "count_labels", {})
        count_lbl = QLabel("0")
        count_lbl.setStyleSheet(f"""
            background: {color}; color: white; padding: 2px 10px;
            border-radius: 10px; font-weight: bold; font-size: 12px;
        """)
        self.count_labels[status] = count_lbl
        header.addWidget(count_lbl)
        layout.addLayout(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #ecf0f1;")
        layout.addWidget(sep)

        self.cards_layouts = getattr(self, "cards_layouts", {})
        cards_layout = QVBoxLayout()
        cards_layout.setSpacing(8)
        cards_layout.addStretch(1)
        self.cards_layouts[status] = cards_layout
        layout.addLayout(cards_layout, 1)

        return col

    def _clear_cards(self):
        for status in JOB_STATUSES:
            layout = self.cards_layouts[status]
            while layout.count() > 1:
                item = layout.takeAt(0)
                w = item.widget()
                if w:
                    w.deleteLater()

    def _refresh(self):
        self._clear_cards()
        jobs = self.db.get_risk_jobs(project_id=self.project.id, job_date=self.job_date)

        client_jobs = []
        close_today_jobs = []
        overdue_jobs = []
        now = datetime.now()

        total = len(jobs)
        counts = {s: 0 for s in JOB_STATUSES}
        issue_count = 0

        for job in jobs:
            counts[job.status] = counts.get(job.status, 0) + 1
            if job.issues:
                issue_count += 1

            if job.need_client_safety_officer and job.status != "已关闭":
                client_jobs.append(job)

            if job.status == "进行中" and job.estimated_end_time:
                if job.estimated_end_time.date() == self.job_date:
                    close_today_jobs.append(job)
                if job.estimated_end_time < now:
                    overdue_jobs.append(job)

            personnel = self.db.get_personnel_by_ids(job.personnel_ids)
            is_overdue_closed = self.db.is_overdue_closed(job)
            card = RiskCard(job, personnel, is_overdue_closed)
            layout = self.cards_layouts.get(job.status)
            if layout:
                layout.insertWidget(layout.count() - 1, card)

        self._fill_coord_column(self.coord_client_col, client_jobs, "#8e44ad")
        self._fill_coord_column(self.coord_close_col, close_today_jobs, "#2980b9")
        self._fill_coord_column(self.coord_overdue_col, overdue_jobs, "#e74c3c")

        self._update_summary_card(self.card_total, str(total))
        self._update_summary_card(self.card_pending, str(counts.get("未开工", 0)))
        self._update_summary_card(self.card_doing, str(counts.get("进行中", 0)))
        self._update_summary_card(self.card_closed, str(counts.get("已关闭", 0)))
        self._update_summary_card(self.card_issues, str(issue_count))

        for status in JOB_STATUSES:
            self.count_labels[status].setText(str(counts.get(status, 0)))

    def _on_print(self):
        QMessageBox.information(self, "提示", "可使用系统截图工具将此看板保存或打印。\n"
                                              "后续版本将支持PDF导出。")
