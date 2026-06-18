from datetime import date, datetime
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QBrush
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGroupBox, QFrame, QScrollArea, QGridLayout, QSizePolicy,
    QMessageBox, QDialog, QDialogButtonBox, QLineEdit, QTextEdit,
    QDateEdit, QCheckBox, QFormLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMenu, QButtonGroup
)

from app.db.database import Database
from app.models.schemas import (
    ContractProject, RiskJob, JOB_STATUSES, Personnel, FollowUp
)
from app.utils.exporter import DailyReportExporter


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
    def __init__(self, job: RiskJob, personnel: List[Personnel], db: Database,
                 is_overdue_closed: bool = False, on_update=None):
        super().__init__()
        self.job = job
        self.personnel = personnel
        self.db = db
        self.is_overdue_closed = is_overdue_closed
        self.on_update = on_update
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
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

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

        self._fu_btn = QPushButton()
        self._fu_btn.setFlat(True)
        self._fu_btn.setCursor(Qt.PointingHandCursor)
        self._fu_btn.clicked.connect(self._open_follow_ups)
        self._refresh_fu_btn_text()
        header.addWidget(self._fu_btn)

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

        self._fu_preview_area = None
        self._render_fu_preview(layout)

    def _refresh_fu_btn_text(self):
        fus = self.db.get_follow_ups_by_job(self.job.id or 0)
        pending = sum(1 for f in fus if not f.confirmed)
        self._fu_btn.setText(f"📎 跟进链 {len(fus)}"
                             + (f"（待确认{pending}）" if pending else ""))
        self._fu_btn.setStyleSheet("""
            QPushButton {
                background: #ecf0f1; color: #34495e;
                padding: 3px 10px; border-radius: 4px;
                font-size: 11px; font-weight: bold;
                border: 1px solid #bdc3c7;
            }
            QPushButton:hover { background: #d5dbdb; }
        """)

    def _render_fu_preview(self, parent_layout: QVBoxLayout):
        fus = self.db.get_follow_ups_by_job(self.job.id or 0)
        if not fus:
            return

        if self._fu_preview_area:
            self._fu_preview_area.deleteLater()
            self._fu_preview_area = None

        box = QFrame()
        self._fu_preview_area = box
        box.setStyleSheet("""
            QFrame {
                background: #fafbfc;
                border: 1px dashed #95a5a6;
                border-radius: 5px;
                margin-top: 4px;
            }
        """)
        bl = QVBoxLayout(box)
        bl.setContentsMargins(6, 4, 6, 6)
        bl.setSpacing(3)

        title_lbl = QLabel(f"📎 跟进链（共 {len(fus)} 条）")
        title_lbl.setStyleSheet("font-size: 11px; color: #7f8c8d; font-weight: bold;")
        bl.addWidget(title_lbl)

        for i, fu in enumerate(fus[-3:], 1):
            tag = "✅" if fu.confirmed else "⏳"
            time_str = fu.follow_time.strftime("%m-%d %H:%M") if fu.follow_time else "-"
            text = f"{tag} <b>[{time_str}]</b> {fu.owner or '-'}：{fu.action or '-'}"
            if fu.result:
                text += f" → {fu.result}"
            if fu.confirmed and fu.confirmed_by:
                text += f" <span style='color:#27ae60'>（{fu.confirmed_by}确认）</span>"
            lbl = QLabel(text)
            lbl.setTextFormat(Qt.RichText)
            lbl.setStyleSheet("font-size: 10px; color: #34495e; padding: 2px 3px;")
            lbl.setWordWrap(True)
            bl.addWidget(lbl)

        if len(fus) > 3:
            more = QLabel(f"... 还有 {len(fus) - 3} 条，点击【跟进链】查看完整")
            more.setStyleSheet("font-size: 10px; color: #95a5a6;")
            bl.addWidget(more)

        parent_layout.addWidget(box)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        act_fu = menu.addAction("📎 查看/添加跟进")
        act_refresh = menu.addAction("🔄 刷新卡片")
        chosen = menu.exec(self.mapToGlobal(pos))
        if chosen == act_fu:
            self._open_follow_ups()
        elif chosen == act_refresh:
            if self.on_update:
                self.on_update()

    def _open_follow_ups(self):
        dlg = FollowUpDialog(self.db, self.job, self)
        if dlg.exec() == QDialog.Accepted:
            self._refresh_fu_btn_text()
            if self.on_update:
                self.on_update()


class DailyReportWindow(QWidget):
    def __init__(self, db: Database, project: ContractProject, job_date: date):
        super().__init__()
        self.db = db
        self.project = project
        self.job_date = job_date
        self._filter_mode = "all"  # all / client / overdue / ontime
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle(f"现场风险日报 - {self.project.name} ({self.job_date.isoformat()})")
        self.setMinimumSize(1300, 800)
        self.setStyleSheet("background: #f5f6fa;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self._build_header(layout)
        self._build_filter_bar(layout)
        self._build_summary(layout)
        self._build_coordination(layout)
        self._build_kanban(layout)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_detail = QPushButton("📋 闭环明细")
        self.btn_detail.setMinimumHeight(38)
        self.btn_detail.setMinimumWidth(130)
        self.btn_detail.setStyleSheet("""
            QPushButton {
                background: #d35400; color: white; font-weight: bold;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background: #e67e22; }
        """)
        self.btn_detail.clicked.connect(self._open_closed_loop_detail)
        btn_row.addWidget(self.btn_detail)

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

        self.btn_export_pdf = QPushButton("📄 导出 PDF")
        self.btn_export_pdf.setMinimumHeight(38)
        self.btn_export_pdf.setMinimumWidth(130)
        self.btn_export_pdf.setStyleSheet("""
            QPushButton {
                background: #c0392b; color: white; font-weight: bold;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background: #e74c3c; }
        """)
        self.btn_export_pdf.clicked.connect(self._on_export_pdf)
        btn_row.addWidget(self.btn_export_pdf)

        self.btn_export_excel = QPushButton("📊 导出 Excel")
        self.btn_export_excel.setMinimumHeight(38)
        self.btn_export_excel.setMinimumWidth(130)
        self.btn_export_excel.setStyleSheet("""
            QPushButton {
                background: #27ae60; color: white; font-weight: bold;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background: #2ecc71; }
        """)
        self.btn_export_excel.clicked.connect(self._on_export_excel)
        btn_row.addWidget(self.btn_export_excel)

        layout.addLayout(btn_row)

        self._refresh()

    def _build_filter_bar(self, parent_layout: QVBoxLayout):
        bar = QFrame()
        bar.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #bdc3c7;
                border-radius: 6px;
            }
        """)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(10, 8, 10, 8)
        bl.setSpacing(10)

        title = QLabel("🔍 快速筛选：")
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #34495e;")
        bl.addWidget(title)

        self.filter_group = QButtonGroup(self)
        self.filter_group.setExclusive(True)

        filters = [
            ("all", "📋 全部", "#34495e"),
            ("client", "👤 客户安全员", "#8e44ad"),
            ("overdue", "🚨 超时未关闭", "#e74c3c"),
            ("ontime", "🟢 按时关闭", "#27ae60"),
        ]
        for key, label, color in filters:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(30)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: #f8f9fa;
                    color: {color};
                    border: 1px solid #bdc3c7;
                    border-radius: 5px;
                    padding: 4px 12px;
                    font-size: 12px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ background: #e9ecef; }}
                QPushButton:checked {{
                    background: {color};
                    color: white;
                    border: 1px solid {color};
                }}
            """)
            btn.clicked.connect(lambda _=False, k=key: self._set_filter(k))
            self.filter_group.addButton(btn)
            bl.addWidget(btn)
            if key == "all":
                btn.setChecked(True)

        bl.addStretch(1)

        self.filter_tip = QLabel("显示全部风险卡片")
        self.filter_tip.setStyleSheet("font-size: 11px; color: #7f8c8d;")
        bl.addWidget(self.filter_tip)

        parent_layout.addWidget(bar)

    def _set_filter(self, mode: str):
        self._filter_mode = mode
        tips = {
            "all": "显示全部风险卡片",
            "client": "只显示【需客户安全员到场】的未关闭卡片",
            "overdue": "只显示【超时未关闭】的进行中卡片",
            "ontime": "只显示【按时关闭】的已关闭卡片",
        }
        self.filter_tip.setText(tips.get(mode, ""))
        self._refresh()

    def _match_filter(self, job: RiskJob) -> bool:
        if self._filter_mode == "all":
            return True
        if self._filter_mode == "client":
            return job.need_client_safety_officer and job.status != "已关闭"
        if self._filter_mode == "overdue":
            if job.status != "进行中":
                return False
            return job.estimated_end_time is not None and job.estimated_end_time < datetime.now()
        if self._filter_mode == "ontime":
            if job.status != "已关闭":
                return False
            return not self.db.is_overdue_closed(job)
        return True

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

            if not self._match_filter(job):
                continue

            personnel = self.db.get_personnel_by_ids(job.personnel_ids)
            is_overdue_closed = self.db.is_overdue_closed(job)
            card = RiskCard(job, personnel, self.db, is_overdue_closed, self._refresh)
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
            if self._filter_mode == "all":
                self.count_labels[status].setText(str(counts.get(status, 0)))
            else:
                col_layout = self.cards_layouts[status]
                visible = col_layout.count() - 1
                self.count_labels[status].setText(str(visible))

    def _on_export_pdf(self):
        jobs = self.db.get_risk_jobs(project_id=self.project.id, job_date=self.job_date)
        exporter = DailyReportExporter(self.db, self.project, self.job_date, jobs, self)
        exporter.export_pdf()

    def _on_export_excel(self):
        jobs = self.db.get_risk_jobs(project_id=self.project.id, job_date=self.job_date)
        exporter = DailyReportExporter(self.db, self.project, self.job_date, jobs, self)
        exporter.export_excel()

    def _open_closed_loop_detail(self):
        jobs = self.db.get_risk_jobs(project_id=self.project.id, job_date=self.job_date)
        dlg = ClosedLoopDetailWindow(self.db, self.project, self.job_date, jobs, self)
        dlg.exec()

    def _on_print(self):
        QMessageBox.information(self, "提示", "请使用「导出 PDF」或「导出 Excel」功能保存日报。")


class FollowUpDialog(QDialog):
    """跟进记录管理对话框"""

    def __init__(self, db: Database, job: RiskJob, parent=None):
        super().__init__(parent)
        self.db = db
        self.job = job
        self.setWindowTitle(f"跟进链管理 - {job.work_type}")
        self.setMinimumSize(760, 520)
        self.setStyleSheet("background: #f5f6fa;")
        self._init_ui()
        self._refresh_table()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        header = QLabel(f"作业：<b>{self.job.work_type}</b> · "
                        f"{self.job.work_location or '-'} · {self.job.aircraft_no or '-'}")
        header.setTextFormat(Qt.RichText)
        header.setStyleSheet("font-size: 13px; color: #34495e; padding: 6px;")
        layout.addWidget(header)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["选", "时间", "跟进人", "跟进动作", "复查日期", "复查结果", "闭环确认", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background: white; border: 1px solid #bdc3c7;
                gridline-color: #ecf0f1; font-size: 11px;
            }
            QHeaderView::section {
                background: #34495e; color: white; padding: 5px;
                font-weight: bold; border: none;
            }
        """)
        layout.addWidget(self.table, 1)

        form_box = QGroupBox("➕ 新增跟进记录")
        form_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold; font-size: 13px; color: #2c3e50;
                border: 1px solid #2980b9; border-radius: 6px;
                margin-top: 8px; padding: 10px 10px 10px 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; color: #2980b9; }
        """)
        form = QFormLayout(form_box)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(6)

        self.edit_owner = QLineEdit()
        self.edit_owner.setPlaceholderText("例如：安全工程师 刘工")
        self.edit_action = QTextEdit()
        self.edit_action.setPlaceholderText("跟进动作（做了什么，复核/补充措施等）")
        self.edit_action.setMinimumHeight(50)
        self.edit_review = QDateEdit()
        self.edit_review.setCalendarPopup(True)
        self.edit_review.setDisplayFormat("yyyy-MM-dd")
        from datetime import date as _date
        self.edit_review.setDate(_date.today())
        self.edit_result = QLineEdit()
        self.edit_result.setPlaceholderText("复查结果描述")
        self.chk_confirmed = QCheckBox("已闭环确认")
        self.edit_confirmer = QLineEdit()
        self.edit_confirmer.setPlaceholderText("确认人（项目经理/安全员等）")
        self.edit_confirmer.setEnabled(False)
        self.chk_confirmed.toggled.connect(self.edit_confirmer.setEnabled)

        form.addRow("跟进人", self.edit_owner)
        form.addRow("跟进动作", self.edit_action)
        form.addRow("复查日期", self.edit_review)
        form.addRow("复查结果", self.edit_result)
        fl = QHBoxLayout()
        fl.addWidget(self.chk_confirmed)
        fl.addWidget(QLabel("  确认人："))
        fl.addWidget(self.edit_confirmer)
        form.addRow("闭环确认", fl)

        layout.addWidget(form_box)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        btn_add = QPushButton("💾 保存新增")
        btn_add.setMinimumHeight(36)
        btn_add.setMinimumWidth(120)
        btn_add.setStyleSheet("""
            QPushButton { background: #2980b9; color: white; font-weight: bold;
                          border: none; border-radius: 6px; }
            QPushButton:hover { background: #3498db; }
        """)
        btn_add.clicked.connect(self._add_record)
        btn_row.addWidget(btn_add)

        btn_batch = QPushButton("✅ 批量确认选中")
        btn_batch.setMinimumHeight(36)
        btn_batch.setMinimumWidth(140)
        btn_batch.setStyleSheet("""
            QPushButton { background: #8e44ad; color: white; font-weight: bold;
                          border: none; border-radius: 6px; }
            QPushButton:hover { background: #9b59b6; }
            QPushButton:disabled { background: #95a5a6; }
        """)
        btn_batch.clicked.connect(self._batch_confirm)
        btn_row.addWidget(btn_batch)
        self.btn_batch_confirm = btn_batch

        btn_sel_pending = QPushButton("选待确认")
        btn_sel_pending.setMinimumHeight(36)
        btn_sel_pending.setMinimumWidth(90)
        btn_sel_pending.setStyleSheet("""
            QPushButton { background: #7f8c8d; color: white; font-weight: bold;
                          border: none; border-radius: 6px; }
            QPushButton:hover { background: #95a5a6; }
        """)
        btn_sel_pending.clicked.connect(self._select_all_pending)
        btn_row.addWidget(btn_sel_pending)

        btn_box = QDialogButtonBox(QDialogButtonBox.Close)
        btn_close = btn_box.button(QDialogButtonBox.Close)
        btn_close.setText("✅ 完成")
        btn_close.setMinimumHeight(36)
        btn_close.setMinimumWidth(100)
        btn_close.setStyleSheet("""
            QPushButton { background: #27ae60; color: white; font-weight: bold;
                          border: none; border-radius: 6px; }
            QPushButton:hover { background: #2ecc71; }
        """)
        btn_box.rejected.connect(self.accept)
        btn_box.accepted.connect(self.accept)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _refresh_table(self):
        fus = self.db.get_follow_ups_by_job(self.job.id or 0)
        self.table.setRowCount(len(fus))
        self._current_fus = fus
        for r, fu in enumerate(fus):
            chk = QCheckBox()
            chk.setEnabled(not fu.confirmed)
            chk.setStyleSheet("QCheckBox { margin-left: 8px; }")
            self.table.setCellWidget(r, 0, chk)
            self.table.setItem(r, 1, QTableWidgetItem(
                fu.follow_time.strftime("%Y-%m-%d %H:%M") if fu.follow_time else "-"))
            self.table.setItem(r, 2, QTableWidgetItem(fu.owner or "-"))
            self.table.setItem(r, 3, QTableWidgetItem(fu.action or "-"))
            self.table.setItem(r, 4, QTableWidgetItem(
                fu.review_date.isoformat() if fu.review_date else "-"))
            self.table.setItem(r, 5, QTableWidgetItem(fu.result or "-"))
            if fu.confirmed:
                text = f"✅ {fu.confirmed_by or '-'}"
                if fu.confirmed_at:
                    text += f"\n{fu.confirmed_at.strftime('%m-%d %H:%M')}"
                item = QTableWidgetItem(text)
                item.setBackground(QBrush(QColor("#d5f5e3")))
                item.setForeground(QBrush(QColor("#1e8449")))
            else:
                item = QTableWidgetItem("⏳ 待确认")
                item.setBackground(QBrush(QColor("#fef9e7")))
            self.table.setItem(r, 6, item)

            btn_del = QPushButton("🗑 删除")
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setStyleSheet("""
                QPushButton { background: #fadbd8; color: #c0392b;
                              border: 1px solid #e6b0aa; border-radius: 3px;
                              padding: 2px 8px; font-size: 10px; }
                QPushButton:hover { background: #f1948a; color: white; }
            """)
            btn_del.clicked.connect(lambda _=False, fid=fu.id: self._delete_record(fid))
            self.table.setCellWidget(r, 7, btn_del)
            self.table.setRowHeight(r, 46)

    def _add_record(self):
        owner = self.edit_owner.text().strip()
        action = self.edit_action.toPlainText().strip()
        if not owner or not action:
            QMessageBox.warning(self, "提示", "请填写「跟进人」和「跟进动作」")
            return
        fu = FollowUp(
            job_id=self.job.id,
            follow_time=datetime.now(),
            owner=owner,
            action=action,
            review_date=self.edit_review.date().toPython(),
            result=self.edit_result.text().strip(),
            confirmed=self.chk_confirmed.isChecked(),
            confirmed_by=self.edit_confirmer.text().strip() if self.chk_confirmed.isChecked() else "",
            confirmed_at=datetime.now() if self.chk_confirmed.isChecked() and self.edit_confirmer.text().strip() else None,
        )
        self.db.save_follow_up(fu)

        self.edit_owner.clear()
        self.edit_action.clear()
        self.edit_result.clear()
        self.chk_confirmed.setChecked(False)
        self.edit_confirmer.clear()
        self._refresh_table()

    def _delete_record(self, fid: int):
        if QMessageBox.question(self, "确认", "确认删除此条跟进记录？") == QMessageBox.Yes:
            self.db.delete_follow_up(fid)
            self._refresh_table()

    def _select_all_pending(self):
        fus = getattr(self, "_current_fus", [])
        for r, fu in enumerate(fus):
            chk = self.table.cellWidget(r, 0)
            if chk and chk.isEnabled():
                chk.setChecked(True)

    def _batch_confirm(self):
        fus = getattr(self, "_current_fus", [])
        selected_ids = []
        for r, fu in enumerate(fus):
            chk = self.table.cellWidget(r, 0)
            if chk and chk.isChecked() and not fu.confirmed:
                selected_ids.append(fu.id)
        if not selected_ids:
            QMessageBox.information(self, "提示", "请勾选至少一条待确认的跟进记录")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"批量确认跟进记录（共 {len(selected_ids)} 条）")
        dlg.setMinimumWidth(460)
        dlg.setStyleSheet("background: #f5f6fa;")
        v = QVBoxLayout(dlg)
        v.setSpacing(10)

        tip = QLabel(f"将把选中的 {len(selected_ids)} 条待确认跟进标记为已确认闭环")
        tip.setStyleSheet("color: #2c3e50; font-weight: bold; padding: 4px;")
        v.addWidget(tip)

        form = QFormLayout()
        form.setSpacing(8)
        e_confirmer = QLineEdit()
        e_confirmer.setPlaceholderText("例如：项目经理")
        e_remark = QTextEdit()
        e_remark.setPlaceholderText("确认说明（批量填写结果，例如「复盘会现场确认闭环」），留空则保留原结果")
        e_remark.setMinimumHeight(70)
        form.addRow("确认人：", e_confirmer)
        form.addRow("确认说明：", e_remark)
        v.addLayout(form)

        btn_bar = QHBoxLayout()
        btn_bar.addStretch(1)
        btn_ok = QPushButton("💾 批量保存")
        btn_ok.setMinimumHeight(36)
        btn_ok.setStyleSheet("""
            QPushButton { background: #27ae60; color: white; font-weight: bold;
                          border: none; border-radius: 6px; padding: 0 18px; }
            QPushButton:hover { background: #2ecc71; }
        """)
        btn_cancel = QPushButton("取消")
        btn_cancel.setMinimumHeight(36)
        btn_cancel.setStyleSheet("""
            QPushButton { background: #95a5a6; color: white; font-weight: bold;
                          border: none; border-radius: 6px; padding: 0 16px; }
            QPushButton:hover { background: #7f8c8d; }
        """)
        btn_bar.addWidget(btn_cancel)
        btn_bar.addWidget(btn_ok)
        v.addLayout(btn_bar)

        def do_save():
            confirmer = e_confirmer.text().strip()
            remark = e_remark.toPlainText().strip()
            if not confirmer:
                QMessageBox.warning(dlg, "提示", "请填写「确认人」")
                return
            cnt = 0
            for fid in selected_ids:
                all_fus = self.db.get_follow_ups_by_job(self.job.id or 0)
                fu = next((f for f in all_fus if f.id == fid), None)
                if not fu or fu.confirmed:
                    continue
                fu.confirmed = True
                fu.confirmed_by = confirmer
                fu.confirmed_at = datetime.now()
                if remark:
                    fu.result = remark if not fu.result else fu.result + "；" + remark
                self.db.save_follow_up(fu)
                cnt += 1
            QMessageBox.information(dlg, "成功", f"已批量确认 {cnt} 条跟进记录")
            dlg.accept()

        btn_ok.clicked.connect(do_save)
        btn_cancel.clicked.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:
            self._refresh_table()


class ClosedLoopDetailWindow(QDialog):
    """按风险作业查看的闭环明细页 —— 复盘会逐条过用"""

    def __init__(self, db: Database, project: ContractProject, job_date: date,
                 jobs: List[RiskJob], parent=None):
        super().__init__(parent)
        self.db = db
        self.project = project
        self.job_date = job_date
        self.all_jobs = jobs
        self.current_job_id: Optional[int] = None
        self.setWindowTitle(f"闭环明细复盘 - {project.name} ({job_date.isoformat()})")
        self.setMinimumSize(1200, 780)
        self.setStyleSheet("background: #f5f6fa;")
        self._init_ui()
        self._reload_jobs()
        if self.all_jobs:
            self._select_job(self.all_jobs[0].id)

    def _init_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # 左侧：作业列表
        left = QFrame()
        left.setFixedWidth(320)
        left.setStyleSheet("""
            QFrame { background: white; border: 1px solid #bdc3c7; border-radius: 6px; }
        """)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(8, 8, 8, 8)
        lv.setSpacing(6)

        head = QVBoxLayout()
        h1 = QLabel("📚 风险作业列表")
        h1.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        head.addWidget(h1)
        h2 = QLabel(f"共 {len(self.all_jobs)} 条，点击左侧查看明细")
        h2.setStyleSheet("font-size: 11px; color: #7f8c8d;")
        head.addWidget(h2)

        # 状态筛选
        filter_row = QHBoxLayout()
        self.filter_group = QButtonGroup(self)
        self.filter_group.setExclusive(True)
        for key, label in [("all", "全部"), ("doing", "进行中"),
                           ("closed", "已关闭"), ("issue", "有问题"),
                           ("pending_fu", "待确认跟进")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setMinimumHeight(26)
            btn.setStyleSheet("""
                QPushButton {
                    background: #f8f9fa; color: #34495e;
                    border: 1px solid #bdc3c7; border-radius: 4px;
                    padding: 2px 6px; font-size: 10px; font-weight: bold;
                }
                QPushButton:hover { background: #e9ecef; }
                QPushButton:checked { background: #2980b9; color: white; border: 1px solid #2980b9; }
            """)
            btn.clicked.connect(lambda _=False, k=key: self._apply_filter(k))
            self.filter_group.addButton(btn)
            filter_row.addWidget(btn)
            if key == "all":
                btn.setChecked(True)
        head.addLayout(filter_row)
        lv.addLayout(head)

        self.job_list = QListWidget()
        self.job_list.setStyleSheet("""
            QListWidget {
                background: white; border: none; font-size: 12px; outline: none;
            }
            QListWidget::item {
                padding: 7px 8px; margin: 2px 2px; border-radius: 4px;
                border-left: 3px solid #bdc3c7;
            }
            QListWidget::item:selected {
                background: #eaf2f8; border-left: 3px solid #2980b9; color: #2c3e50;
            }
        """)
        self.job_list.currentItemChanged.connect(self._on_job_selected)
        lv.addWidget(self.job_list, 1)

        stat_lbl = QLabel("💡 选中作业后可在右侧查看跟进链和批量确认")
        stat_lbl.setStyleSheet("color: #7f8c8d; font-size: 10px; padding: 2px;")
        stat_lbl.setWordWrap(True)
        lv.addWidget(stat_lbl)

        root.addWidget(left)

        # 右侧：作业详情
        right = QFrame()
        right.setStyleSheet("background: white; border: 1px solid #bdc3c7; border-radius: 6px;")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(14, 14, 14, 14)
        rv.setSpacing(10)

        self.right_title = QLabel("（请在左侧选择作业）")
        self.right_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        rv.addWidget(self.right_title)

        self.right_sub = QLabel("")
        self.right_sub.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        rv.addWidget(self.right_sub)

        self.right_tags = QHBoxLayout()
        rv.addLayout(self.right_tags)

        # 基本信息 + 跟进的分组
        self.detail_stack = QWidget()
        rv.addWidget(self.detail_stack, 1)

        detail_v = QVBoxLayout(self.detail_stack)
        detail_v.setContentsMargins(0, 0, 0, 0)
        detail_v.setSpacing(8)

        info_box = QGroupBox("🔧 基本信息 / 问题 / 关闭")
        info_box.setStyleSheet("""
            QGroupBox { font-weight: bold; color: #2c3e50; border: 1px solid #bdc3c7;
                        border-radius: 5px; margin-top: 8px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)
        self.info_form = QFormLayout(info_box)
        self.info_form.setHorizontalSpacing(16)
        self.info_form.setVerticalSpacing(6)
        detail_v.addWidget(info_box)

        follow_box = QGroupBox("📎 跟进记录链（可多选后批量确认）")
        follow_box.setStyleSheet("""
            QGroupBox { font-weight: bold; color: #2c3e50; border: 1px solid #8e44ad;
                        border-radius: 5px; margin-top: 8px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #8e44ad; }
        """)
        fb_v = QVBoxLayout(follow_box)
        fb_v.setSpacing(6)

        tool_row = QHBoxLayout()
        self.btn_select_pending = QPushButton("🔘 全选待确认")
        self.btn_select_pending.setMinimumHeight(30)
        self.btn_select_pending.setStyleSheet("""
            QPushButton { background: #7f8c8d; color: white; font-weight: bold;
                          border: none; border-radius: 4px; padding: 0 10px; font-size: 11px; }
            QPushButton:hover { background: #95a5a6; }
        """)
        self.btn_select_pending.clicked.connect(self._sel_all_pending_fus)
        tool_row.addWidget(self.btn_select_pending)

        self.btn_batch_confirm = QPushButton("✅ 批量标记闭环")
        self.btn_batch_confirm.setMinimumHeight(30)
        self.btn_batch_confirm.setStyleSheet("""
            QPushButton { background: #8e44ad; color: white; font-weight: bold;
                          border: none; border-radius: 4px; padding: 0 14px; font-size: 11px; }
            QPushButton:hover { background: #9b59b6; }
        """)
        self.btn_batch_confirm.clicked.connect(self._batch_confirm_fus)
        tool_row.addWidget(self.btn_batch_confirm)

        self.btn_new_fu = QPushButton("➕ 新增跟进")
        self.btn_new_fu.setMinimumHeight(30)
        self.btn_new_fu.setStyleSheet("""
            QPushButton { background: #2980b9; color: white; font-weight: bold;
                          border: none; border-radius: 4px; padding: 0 12px; font-size: 11px; }
            QPushButton:hover { background: #3498db; }
        """)
        self.btn_new_fu.clicked.connect(self._new_follow_up)
        tool_row.addWidget(self.btn_new_fu)

        tool_row.addStretch(1)
        self.lbl_fu_summary = QLabel("")
        self.lbl_fu_summary.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        tool_row.addWidget(self.lbl_fu_summary)
        fb_v.addLayout(tool_row)

        self.fu_table = QTableWidget(0, 8)
        self.fu_table.setHorizontalHeaderLabels(
            ["选", "时间", "跟进人", "跟进动作", "复查日期", "复查结果", "闭环确认", "操作"])
        self.fu_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.fu_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.fu_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.fu_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.fu_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.fu_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.fu_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.fu_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.fu_table.setAlternatingRowColors(True)
        self.fu_table.setStyleSheet("""
            QTableWidget { background: white; border: 1px solid #bdc3c7; gridline-color: #ecf0f1; font-size: 11px; }
            QHeaderView::section { background: #34495e; color: white; padding: 5px; font-weight: bold; border: none; }
        """)
        fb_v.addWidget(self.fu_table, 1)

        detail_v.addWidget(follow_box, 1)

        root.addWidget(right, 1)

        # 底部按钮
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        btn_close = QPushButton("✔ 关闭")
        btn_close.setMinimumHeight(36)
        btn_close.setMinimumWidth(110)
        btn_close.setStyleSheet("""
            QPushButton { background: #27ae60; color: white; font-weight: bold;
                          border: none; border-radius: 6px; }
            QPushButton:hover { background: #2ecc71; }
        """)
        btn_close.clicked.connect(self.accept)
        bottom.addWidget(btn_close)
        rv.addLayout(bottom)

    # ---- 作业列表 & 筛选 ----
    def _reload_jobs(self):
        self.all_jobs = self.db.get_risk_jobs(project_id=self.project.id, job_date=self.job_date)
        self._apply_filter(getattr(self, "_current_filter", "all"))

    def _apply_filter(self, key: str):
        self._current_filter = key
        now = datetime.now()
        filtered = list(self.all_jobs)
        if key == "doing":
            filtered = [j for j in filtered if j.status == "进行中"]
        elif key == "closed":
            filtered = [j for j in filtered if j.status == "已关闭"]
        elif key == "issue":
            filtered = [j for j in filtered if j.issues]
        elif key == "pending_fu":
            result = []
            for j in filtered:
                fus = self.db.get_follow_ups_by_job(j.id or 0)
                if any(not f.confirmed for f in fus):
                    result.append(j)
            filtered = result

        self.job_list.clear()
        for j in filtered:
            pending = 0
            for f in self.db.get_follow_ups_by_job(j.id or 0):
                if not f.confirmed:
                    pending += 1
            status_color = {"未开工": "#2980b9", "进行中": "#e67e22", "已关闭": "#27ae60"}.get(j.status, "#7f8c8d")
            level_color = RISK_COLORS.get(j.risk_level, "#34495e")
            mark = ""
            if j.issues:
                mark += " 🚨"
            if pending:
                mark += f" ⏳×{pending}"
            if j.need_client_safety_officer and j.status != "已关闭":
                mark += " 👤"

            title = f"{j.work_type} · {j.work_location or '-'}"
            sub = f"[{j.risk_level}] {j.status} | 负责人：{j.team_leader or '-'}{mark}"
            item = QListWidgetItem()
            item.setData(Qt.UserRole, j.id)
            self.job_list.addItem(item)

            w = QWidget()
            wv = QVBoxLayout(w)
            wv.setContentsMargins(4, 3, 4, 3)
            wv.setSpacing(2)
            t1 = QHBoxLayout()
            l1 = QLabel(title)
            l1.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 12px;")
            t1.addWidget(l1)
            t1.addStretch(1)
            tag1 = QLabel(f"●{j.risk_level}")
            tag1.setStyleSheet(f"color: {level_color}; font-weight: bold; font-size: 11px;")
            t1.addWidget(tag1)
            wv.addLayout(t1)
            l2 = QLabel(sub)
            l2.setStyleSheet(f"color: {status_color}; font-size: 10px;")
            wv.addWidget(l2)
            item.setSizeHint(w.sizeHint())
            self.job_list.setItemWidget(item, w)

    def _on_job_selected(self, cur, prev):
        if cur is None:
            return
        jid = cur.data(Qt.UserRole)
        self._select_job(jid)

    def _select_job(self, job_id: int):
        self.current_job_id = job_id
        job = next((j for j in self.all_jobs if j.id == job_id), None)
        if not job:
            return
        # 左侧列表同步选中
        for i in range(self.job_list.count()):
            it = self.job_list.item(i)
            if it.data(Qt.UserRole) == job_id:
                self.job_list.setCurrentItem(it)
                break

        # 渲染标题
        status_color = {"未开工": "#2980b9", "进行中": "#e67e22", "已关闭": "#27ae60"}.get(job.status, "#7f8c8d")
        self.right_title.setText(f"{job.work_type}")
        self.right_sub.setText(
            f"位置：{job.work_location or '-'}　|　机型：{job.aircraft_no or '-'}　|　"
            f"班组：{job.team or '-'} / {job.team_leader or '-'}　|　许可证：{job.permit_status}"
        )
        # 清空旧标签
        while self.right_tags.count():
            item = self.right_tags.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        def add_tag(text, bg, fg="white"):
            l = QLabel(text)
            l.setStyleSheet(f"background: {bg}; color: {fg}; padding: 3px 10px; "
                            f"border-radius: 10px; font-size: 11px; font-weight: bold;")
            self.right_tags.addWidget(l)

        add_tag(job.status, status_color)
        add_tag(job.risk_level, RISK_COLORS.get(job.risk_level, "#34495e"))
        if job.need_client_safety_officer:
            add_tag("👤 客户安全员", "#8e44ad")
        if job.issues:
            add_tag("🚨 有问题", "#c0392b")
        if job.status == "已关闭":
            if self.db.is_overdue_closed(job):
                add_tag("🔴 超时关闭", "#c0392b")
            else:
                add_tag("🟢 按时关闭", "#27ae60")
        fus = self.db.get_follow_ups_by_job(job.id or 0)
        pending = sum(1 for f in fus if not f.confirmed)
        if pending > 0:
            add_tag(f"⏳ 待确认 ×{pending}", "#f39c12")
        self.right_tags.addStretch(1)

        # 信息表单
        while self.info_form.count():
            it = self.info_form.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        def add_row(label, value, value_color=None):
            lb = QLabel(label + "：")
            lb.setStyleSheet("color: #7f8c8d; font-size: 12px;")
            v = QLabel(str(value) if value else "—")
            v.setWordWrap(True)
            v.setStyleSheet(f"color: {value_color or '#2c3e50'}; font-size: 12px; font-weight: bold;")
            self.info_form.addRow(lb, v)

        add_row("作业位置", job.work_location)
        add_row("机型/机号", job.aircraft_no)
        add_row("风险描述", job.description)
        add_row("隔离措施", job.isolation_measures)
        issue_color = "#c0392b" if job.issues else None
        add_row("⚠️ 问题提示", job.issues, issue_color)
        pm_color = "#2980b9" if job.pm_comments else None
        add_row("项目经理意见", job.pm_comments, pm_color)
        add_row("许可证状态", job.permit_status, "#d35400" if job.permit_status in ("已过期", "即将过期") else None)
        add_row("许可证到期", job.permit_expiry.isoformat() if job.permit_expiry else None)
        est_str = job.estimated_end_time.strftime("%Y-%m-%d %H:%M") if job.estimated_end_time else None
        add_row("预计结束", est_str)
        if job.status == "已关闭":
            act_str = job.actual_end_time.strftime("%Y-%m-%d %H:%M") if job.actual_end_time else None
            c_color = "#c0392b" if self.db.is_overdue_closed(job) else "#27ae60"
            add_row("实际结束", act_str, c_color)
        cr_color = "#c0392b" if job.close_remark and "超时" in job.close_remark else None
        add_row("🚪 关闭说明", job.close_remark, cr_color)
        personnel_names = "、".join(p.name for p in self.db.get_personnel_by_ids(job.personnel_ids))
        add_row("参与人员", personnel_names)
        add_row("审核状态", "✅ 已审核" if job.reviewed_by_pm else "⏳ 待项目经理审核",
                "#27ae60" if job.reviewed_by_pm else "#e67e22")

        self._reload_fu_table()

    # ---- 跟进表格 ----
    def _reload_fu_table(self):
        if not self.current_job_id:
            return
        fus = self.db.get_follow_ups_by_job(self.current_job_id)
        self._current_fus = fus
        self.fu_table.setRowCount(len(fus))
        pending = 0
        for r, fu in enumerate(fus):
            if not fu.confirmed:
                pending += 1
            chk = QCheckBox()
            chk.setEnabled(not fu.confirmed)
            chk.setStyleSheet("QCheckBox { margin-left: 8px; }")
            self.fu_table.setCellWidget(r, 0, chk)
            self.fu_table.setItem(r, 1, QTableWidgetItem(
                fu.follow_time.strftime("%Y-%m-%d %H:%M") if fu.follow_time else "-"))
            self.fu_table.setItem(r, 2, QTableWidgetItem(fu.owner or "-"))
            self.fu_table.setItem(r, 3, QTableWidgetItem(fu.action or "-"))
            self.fu_table.setItem(r, 4, QTableWidgetItem(
                fu.review_date.isoformat() if fu.review_date else "-"))
            self.fu_table.setItem(r, 5, QTableWidgetItem(fu.result or "-"))
            if fu.confirmed:
                text = f"✅ {fu.confirmed_by or '-'}"
                if fu.confirmed_at:
                    text += f"\n{fu.confirmed_at.strftime('%m-%d %H:%M')}"
                item = QTableWidgetItem(text)
                item.setBackground(QBrush(QColor("#d5f5e3")))
                item.setForeground(QBrush(QColor("#1e8449")))
            else:
                item = QTableWidgetItem("⏳ 待确认")
                item.setBackground(QBrush(QColor("#fef9e7")))
            self.fu_table.setItem(r, 6, item)

            btn_del = QPushButton("🗑")
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setStyleSheet("""
                QPushButton { background: #fadbd8; color: #c0392b;
                              border: 1px solid #e6b0aa; border-radius: 3px;
                              padding: 2px 8px; font-size: 10px; }
                QPushButton:hover { background: #f1948a; color: white; }
            """)
            btn_del.clicked.connect(lambda _=False, fid=fu.id: self._delete_fu(fid))
            self.fu_table.setCellWidget(r, 7, btn_del)
            self.fu_table.setRowHeight(r, 40)

        self.lbl_fu_summary.setText(f"共 {len(fus)} 条跟进，待确认 {pending} 条")

    def _sel_all_pending_fus(self):
        fus = getattr(self, "_current_fus", [])
        for r, fu in enumerate(fus):
            chk = self.fu_table.cellWidget(r, 0)
            if chk and chk.isEnabled():
                chk.setChecked(True)

    def _batch_confirm_fus(self):
        fus = getattr(self, "_current_fus", [])
        selected_ids = []
        for r, fu in enumerate(fus):
            chk = self.fu_table.cellWidget(r, 0)
            if chk and chk.isChecked() and not fu.confirmed:
                selected_ids.append(fu.id)
        if not selected_ids:
            QMessageBox.information(self, "提示", "请勾选至少一条待确认的跟进")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"批量确认跟进（共 {len(selected_ids)} 条）")
        dlg.setMinimumWidth(460)
        dlg.setStyleSheet("background: #f5f6fa;")
        v = QVBoxLayout(dlg); v.setSpacing(10)
        tip = QLabel(f"为选中的 {len(selected_ids)} 条记录填写确认信息")
        tip.setStyleSheet("font-weight: bold; color: #2c3e50; padding: 4px;")
        v.addWidget(tip)
        form = QFormLayout(); form.setSpacing(8)
        e_confirmer = QLineEdit()
        e_confirmer.setPlaceholderText("例如：项目经理 / 客户安全员")
        e_remark = QTextEdit()
        e_remark.setPlaceholderText("确认说明（例如「6.18 协调会确认闭环」），留空则沿用原结果")
        e_remark.setMinimumHeight(70)
        form.addRow("确认人：", e_confirmer)
        form.addRow("确认说明：", e_remark)
        v.addLayout(form)

        bar = QHBoxLayout(); bar.addStretch(1)
        b_ok = QPushButton("💾 批量保存")
        b_ok.setMinimumHeight(36)
        b_ok.setStyleSheet("QPushButton { background:#27ae60; color:white; font-weight:bold;"
                           "border:none; border-radius:6px; padding:0 18px; }"
                           "QPushButton:hover { background:#2ecc71; }")
        b_cancel = QPushButton("取消")
        b_cancel.setMinimumHeight(36)
        b_cancel.setStyleSheet("QPushButton { background:#95a5a6; color:white; font-weight:bold;"
                               "border:none; border-radius:6px; padding:0 16px; }"
                               "QPushButton:hover { background:#7f8c8d; }")
        bar.addWidget(b_cancel); bar.addWidget(b_ok)
        v.addLayout(bar)

        def save():
            confirmer = e_confirmer.text().strip()
            remark = e_remark.toPlainText().strip()
            if not confirmer:
                QMessageBox.warning(dlg, "提示", "请填写确认人")
                return
            cnt = 0
            for fid in selected_ids:
                all_fus = self.db.get_follow_ups_by_job(self.current_job_id)
                fu = next((f for f in all_fus if f.id == fid), None)
                if not fu or fu.confirmed:
                    continue
                fu.confirmed = True
                fu.confirmed_by = confirmer
                fu.confirmed_at = datetime.now()
                if remark:
                    fu.result = remark if not fu.result else fu.result + "；" + remark
                self.db.save_follow_up(fu)
                cnt += 1
            QMessageBox.information(dlg, "成功", f"已批量确认 {cnt} 条跟进")
            dlg.accept()

        b_ok.clicked.connect(save)
        b_cancel.clicked.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:
            self._reload_fu_table()
            self._reload_jobs()
            # 重新渲染当前作业
            self._select_job(self.current_job_id)

    def _delete_fu(self, fid: int):
        if QMessageBox.question(self, "确认", "删除这条跟进记录？") == QMessageBox.Yes:
            self.db.delete_follow_up(fid)
            self._reload_fu_table()

    def _new_follow_up(self):
        if not self.current_job_id:
            return
        job = next((j for j in self.all_jobs if j.id == self.current_job_id), None)
        if not job:
            return
        dlg = FollowUpDialog(self.db, job, self)
        if dlg.exec() == QDialog.Accepted:
            self._reload_fu_table()
            self._reload_jobs()
            self._select_job(self.current_job_id)
