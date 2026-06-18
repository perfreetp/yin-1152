from datetime import date
from typing import Optional

from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGroupBox, QListWidget, QListWidgetItem, QLineEdit, QComboBox,
    QDateEdit, QFormLayout, QMessageBox, QSplitter, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView
)

from app.db.database import Database
from app.models.schemas import (
    Personnel, PersonnelQualification, WORK_TYPES
)


STATUS_COLORS = {
    "有效": "#27ae60",
    "即将过期": "#e67e22",
    "已过期": "#c0392b",
    "无资质": "#95a5a6",
}


class PersonnelQualificationWindow(QWidget):
    personnel_updated = Signal()

    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.current_personnel: Optional[Personnel] = None
        self.all_qual_map = self.db.get_all_qualifications()
        self._init_ui()
        self._refresh_personnel_list()

    def _init_ui(self):
        self.setWindowTitle("人员资质管理")
        self.setMinimumSize(1100, 680)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        title = QLabel("人员资质管理")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)

        hint = QLabel("维护作业人员信息及其可承担的作业类型资质。资质到期前30天标黄，已过期标红。")
        hint.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #bdc3c7; width: 2px; }")

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 10, 0)

        list_title = QLabel("作业人员")
        list_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        left_layout.addWidget(list_title)

        self.personnel_list = QListWidget()
        self.personnel_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #bdc3c7; border-radius: 6px;
                background: white; padding: 4px;
            }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #ecf0f1; }
            QListWidget::item:selected { background: #e8f4fc; }
        """)
        self.personnel_list.currentItemChanged.connect(self._on_personnel_selected)
        left_layout.addWidget(self.personnel_list, 1)

        btn_row = QHBoxLayout()
        self.btn_new_person = QPushButton("新增人员")
        self.btn_new_person.setStyleSheet("""
            QPushButton { background: #2980b9; color: white; padding: 6px;
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #3498db; }
        """)
        self.btn_new_person.clicked.connect(self._new_personnel)
        btn_row.addWidget(self.btn_new_person)

        self.btn_del_person = QPushButton("删除人员")
        self.btn_del_person.setStyleSheet("""
            QPushButton { background: #e74c3c; color: white; padding: 6px;
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #ec7063; }
            QPushButton:disabled { background: #95a5a6; }
        """)
        self.btn_del_person.clicked.connect(self._delete_personnel)
        btn_row.addWidget(self.btn_del_person)
        left_layout.addLayout(btn_row)

        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(10)

        info_box = QGroupBox("人员基本信息")
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

        self.name_edit = QLineEdit()
        self.emp_edit = QLineEdit()
        self.team_edit = QLineEdit()
        self.position_edit = QLineEdit()
        self.cert_no_edit = QLineEdit()
        self.cert_expiry_edit = QDateEdit()
        self.cert_expiry_edit.setCalendarPopup(True)
        self.cert_expiry_edit.setDisplayFormat("yyyy-MM-dd")
        self.cert_expiry_edit.setSpecialValueText("无")
        self.cert_expiry_edit.setDate(QDate.currentDate())

        info_form.addRow("姓名：", self.name_edit)
        info_form.addRow("工号：", self.emp_edit)
        info_form.addRow("班组：", self.team_edit)
        info_form.addRow("岗位：", self.position_edit)
        info_form.addRow("上岗证号：", self.cert_no_edit)
        info_form.addRow("上岗证到期：", self.cert_expiry_edit)

        self.btn_save_person = QPushButton("保存人员信息")
        self.btn_save_person.setMinimumHeight(34)
        self.btn_save_person.setStyleSheet("""
            QPushButton { background: #27ae60; color: white; font-weight: bold;
                          border: none; border-radius: 6px; }
            QPushButton:hover { background: #2ecc71; }
            QPushButton:disabled { background: #95a5a6; }
        """)
        self.btn_save_person.clicked.connect(self._save_personnel)
        info_form.addRow(self.btn_save_person)

        right_layout.addWidget(info_box)

        qual_box = QGroupBox("作业类型资质")
        qual_box.setStyleSheet(info_box.styleSheet())
        qual_layout = QVBoxLayout(qual_box)

        qual_hint = QLabel("为该人员添加可承担的作业类型及对应资质证号、有效期：")
        qual_hint.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        qual_layout.addWidget(qual_hint)

        add_row = QHBoxLayout()
        self.qual_work_type = QComboBox()
        for wt in WORK_TYPES:
            self.qual_work_type.addItem(wt)
        self.qual_cert_no = QLineEdit()
        self.qual_cert_no.setPlaceholderText("资质证号")
        self.qual_expiry = QDateEdit()
        self.qual_expiry.setCalendarPopup(True)
        self.qual_expiry.setDisplayFormat("yyyy-MM-dd")
        self.qual_expiry.setDate(QDate.currentDate().addDays(180))

        add_row.addWidget(self.qual_work_type, 2)
        add_row.addWidget(self.qual_cert_no, 2)
        add_row.addWidget(self.qual_expiry, 2)

        self.btn_add_qual = QPushButton("添加资质")
        self.btn_add_qual.setMinimumHeight(32)
        self.btn_add_qual.setStyleSheet("""
            QPushButton { background: #8e44ad; color: white; font-weight: bold;
                          border: none; border-radius: 4px; padding: 0 14px; }
            QPushButton:hover { background: #9b59b6; }
            QPushButton:disabled { background: #95a5a6; }
        """)
        self.btn_add_qual.clicked.connect(self._add_qualification)
        add_row.addWidget(self.btn_add_qual)
        qual_layout.addLayout(add_row)

        self.qual_table = QTableWidget(0, 4)
        self.qual_table.setHorizontalHeaderLabels(["作业类型", "资质证号", "到期日", "状态"])
        self.qual_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.qual_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.qual_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.qual_table.setStyleSheet("""
            QTableWidget { border: 1px solid #bdc3c7; border-radius: 4px; background: white; }
            QHeaderView::section { background: #ecf0f1; font-weight: bold; padding: 6px; }
        """)
        qual_layout.addWidget(self.qual_table, 1)

        del_row = QHBoxLayout()
        del_row.addStretch(1)
        self.btn_del_qual = QPushButton("删除选中资质")
        self.btn_del_qual.setMinimumHeight(32)
        self.btn_del_qual.setStyleSheet("""
            QPushButton { background: #e74c3c; color: white; font-weight: bold;
                          border: none; border-radius: 4px; padding: 0 14px; }
            QPushButton:hover { background: #ec7063; }
            QPushButton:disabled { background: #95a5a6; }
        """)
        self.btn_del_qual.clicked.connect(self._delete_qualification)
        del_row.addWidget(self.btn_del_qual)
        qual_layout.addLayout(del_row)

        right_layout.addWidget(qual_box, 1)

        splitter.addWidget(right)
        splitter.setSizes([320, 780])
        layout.addWidget(splitter, 1)

        self._enable_person_form(False)
        self._enable_qual_form(False)

    def _enable_person_form(self, enabled: bool):
        for w in [self.name_edit, self.emp_edit, self.team_edit, self.position_edit,
                  self.cert_no_edit, self.cert_expiry_edit, self.btn_save_person,
                  self.btn_del_person]:
            w.setEnabled(enabled)

    def _enable_qual_form(self, enabled: bool):
        for w in [self.qual_work_type, self.qual_cert_no, self.qual_expiry,
                  self.btn_add_qual, self.qual_table, self.btn_del_qual]:
            w.setEnabled(enabled)

    def _refresh_personnel_list(self):
        self.all_qual_map = self.db.get_all_qualifications()
        self.personnel_list.clear()
        personnel = self.db.get_all_personnel()
        today = date.today()
        for p in personnel:
            quals = self.all_qual_map.get(p.id, [])
            expired_cnt = sum(1 for q in quals if q.expiry_date and q.expiry_date < today)
            if p.certificate_expiry and p.certificate_expiry < today:
                expired_cnt += 1
            warn = f"  ⚠{expired_cnt}项过期" if expired_cnt else ""
            item = QListWidgetItem(f"{p.name}（{p.team}）{warn}")
            item.setData(Qt.UserRole, p.id)
            if expired_cnt:
                item.setForeground(QColor("#c0392b"))
            self.personnel_list.addItem(item)

    def _on_personnel_selected(self, current, previous):
        if not current:
            self.current_personnel = None
            self._clear_person_form()
            self._enable_person_form(False)
            self._enable_qual_form(False)
            self.qual_table.setRowCount(0)
            return
        pid = current.data(Qt.UserRole)
        personnel = self.db.get_all_personnel()
        p = next((x for x in personnel if x.id == pid), None)
        if p:
            self.current_personnel = p
            self._fill_person_form(p)
            self._refresh_qual_table(p)
            self._enable_person_form(True)
            self._enable_qual_form(True)

    def _clear_person_form(self):
        self.name_edit.clear()
        self.emp_edit.clear()
        self.team_edit.clear()
        self.position_edit.clear()
        self.cert_no_edit.clear()
        self.cert_expiry_edit.setDate(QDate.currentDate())

    def _fill_person_form(self, p: Personnel):
        self.name_edit.setText(p.name)
        self.emp_edit.setText(p.employee_id)
        self.team_edit.setText(p.team)
        self.position_edit.setText(p.position)
        self.cert_no_edit.setText(p.certificate_no)
        if p.certificate_expiry:
            self.cert_expiry_edit.setDate(QDate(
                p.certificate_expiry.year, p.certificate_expiry.month, p.certificate_expiry.day))
        else:
            self.cert_expiry_edit.setDate(self.cert_expiry_edit.minimumDate())

    def _new_personnel(self):
        self.current_personnel = Personnel()
        self._clear_person_form()
        self._enable_person_form(True)
        self._enable_qual_form(False)
        self.qual_table.setRowCount(0)
        self.personnel_list.clearSelection()
        self.name_edit.setFocus()

    def _save_personnel(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "提示", "请填写姓名")
            return
        p = self.current_personnel or Personnel()
        p.name = self.name_edit.text().strip()
        p.employee_id = self.emp_edit.text().strip()
        p.team = self.team_edit.text().strip()
        p.position = self.position_edit.text().strip()
        p.certificate_no = self.cert_no_edit.text().strip()
        qd = self.cert_expiry_edit.date()
        if self.cert_expiry_edit.date() == self.cert_expiry_edit.minimumDate():
            p.certificate_expiry = None
        else:
            p.certificate_expiry = date(qd.year(), qd.month(), qd.day())
        p.id = self.db.save_personnel(p)
        self.current_personnel = p
        QMessageBox.information(self, "成功", "人员信息已保存")
        self._refresh_personnel_list()
        self.personnel_updated.emit()

        for i in range(self.personnel_list.count()):
            item = self.personnel_list.item(i)
            if item.data(Qt.UserRole) == p.id:
                self.personnel_list.setCurrentItem(item)
                break

    def _delete_personnel(self):
        if not self.current_personnel or not self.current_personnel.id:
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定删除人员【{self.current_personnel.name}】及其全部资质吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_personnel(self.current_personnel.id)
            self.current_personnel = None
            self._clear_person_form()
            self._enable_person_form(False)
            self._enable_qual_form(False)
            self.qual_table.setRowCount(0)
            self._refresh_personnel_list()
            self.personnel_updated.emit()

    def _refresh_qual_table(self, p: Personnel):
        quals = self.db.get_qualifications_by_personnel(p.id)
        self.qual_table.setRowCount(0)
        today = date.today()
        for q in quals:
            row = self.qual_table.rowCount()
            self.qual_table.insertRow(row)
            self.qual_table.setItem(row, 0, QTableWidgetItem(q.work_type))
            self.qual_table.setItem(row, 1, QTableWidgetItem(q.certificate_no))
            exp_str = q.expiry_date.isoformat() if q.expiry_date else "长期"
            self.qual_table.setItem(row, 2, QTableWidgetItem(exp_str))

            if q.expiry_date:
                days = (q.expiry_date - today).days
                if days < 0:
                    status_text, color = "已过期", "#c0392b"
                elif days <= 30:
                    status_text, color = f"即将过期({days}天)", "#e67e22"
                else:
                    status_text, color = "有效", "#27ae60"
            else:
                status_text, color = "有效", "#27ae60"

            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(QColor(color))
            status_item.setData(Qt.UserRole, q.id)
            self.qual_table.setItem(row, 3, status_item)

    def _add_qualification(self):
        if not self.current_personnel or not self.current_personnel.id:
            QMessageBox.warning(self, "提示", "请先保存人员信息")
            return
        work_type = self.qual_work_type.currentText()
        existing = self.db.get_qualifications_by_personnel(self.current_personnel.id)
        if any(q.work_type == work_type for q in existing):
            QMessageBox.warning(self, "提示", f"该人员已有【{work_type}】资质，请勿重复添加")
            return
        qd = self.qual_expiry.date()
        q = PersonnelQualification(
            personnel_id=self.current_personnel.id,
            work_type=work_type,
            certificate_no=self.qual_cert_no.text().strip(),
            expiry_date=date(qd.year(), qd.month(), qd.day())
        )
        self.db.save_qualification(q)
        self.qual_cert_no.clear()
        self.qual_expiry.setDate(QDate.currentDate().addDays(180))
        self._refresh_qual_table(self.current_personnel)
        self._refresh_personnel_list()
        self.personnel_updated.emit()

    def _delete_qualification(self):
        row = self.qual_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选中一行资质")
            return
        status_item = self.qual_table.item(row, 3)
        qual_id = status_item.data(Qt.UserRole)
        reply = QMessageBox.question(
            self, "确认删除", "确定删除该条资质吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_qualification(qual_id)
            if self.current_personnel:
                self._refresh_qual_table(self.current_personnel)
            self._refresh_personnel_list()
            self.personnel_updated.emit()
