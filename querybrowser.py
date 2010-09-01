
import sys

from PyQt4.QtGui import *
from PyQt4.QtCore import Qt
from sqlalchemy import create_engine, MetaData

from joinlist import JoinList
from scene import Scene

engine = create_engine('mysql://root@localhost/veracity', pool_recycle=3600)
meta = MetaData()
meta.reflect(bind=engine)


class MainWindow(QMainWindow):
    """The main application window."""

    def __init__(self):
        """Initialize."""
        QMainWindow.__init__(self)

        # graphics view
        self.scene = Scene()
        graph = QGraphicsView(self.scene)
        self.scene.query_changed.connect(self.query_change)
        self.scene.table_changed.connect(self.table_change)

        # table dock
        result_dock = QDockWidget('Results')
        self.result_table = QTableWidget(1, 1)
        self.result_table.setMinimumHeight(100)
        result_dock.setWidget(self.result_table)

        # query dock
        query_dock = QDockWidget('Query')
        self.query_view = QPlainTextEdit()
        self.query_view.setReadOnly(True)
        query_dock.setWidget(self.query_view)

        # constraint dock
        constraint_dock = QDockWidget('Constraints')
        self.constraints = QPlainTextEdit()
        constraint_dock.setWidget(self.constraints)
        self.constraints.textChanged.connect(self.set_constraints)

        # joins dock
        join_dock = QDockWidget('Joins')
        items = meta.tables.keys()
        self.joins = JoinList(items, meta)
        join_dock.setWidget(self.joins)

        # menu
        filemenu = self.menuBar().addMenu('&File')
        newquery = QAction('&New Query', filemenu)
        quit_ = QAction('&Quit', filemenu)
        filemenu.addAction(newquery)
        filemenu.addAction(quit_)
        newquery.triggered.connect(self.scene.reset_scene)
        quit_.triggered.connect(sys.exit)

        # layout
        self.addDockWidget(Qt.BottomDockWidgetArea, result_dock)
        self.addDockWidget(Qt.BottomDockWidgetArea, query_dock)
        self.addDockWidget(Qt.BottomDockWidgetArea, constraint_dock)
        self.tabifyDockWidget(result_dock, query_dock)
        self.tabifyDockWidget(query_dock, constraint_dock)
        result_dock.raise_()
        self.addDockWidget(Qt.LeftDockWidgetArea, join_dock)
        self.setCentralWidget(graph)

    def table_change(self, name):
        """When the table changes, set the filters."""
        self.joins.set_table(name)

    def query_change(self):
        """When the query changes, run the query and show results.

        This will clear the table and then add the results.  It also adds the
        query string to the query view.

        """
        query = self.scene.query

        self.query_view.setPlainText(str(query))

        results = engine.execute(query)
        keys = results.keys()
        self.result_table.clear()
        self.result_table.setColumnCount(len(keys))
        self.result_table.setRowCount(0)

        cols_set = False
        row = -1
        for row, result in enumerate(results):
            self.result_table.setRowCount(row + 1)
            for column, data in enumerate(result):
                self.result_table.setItem(row, column,
                                          QTableWidgetItem(str(data)))

        if not cols_set:
            self.result_table.setHorizontalHeaderLabels(list(keys))

    def set_constraints(self):
        """Update the query constraints when the constraint text changes."""
        self.scene.constraints = self.constraints.toPlainText() or ''


# Run the application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
