import sys
from PySide6.QtWidgets import QApplication

from app.db.database import Database
from app.views.project_selection import ProjectSelectionWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("民航维修现场风险日报系统")

    db = Database()
    db.init_db()
    db.ensure_demo_data()

    window = ProjectSelectionWindow(db)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
