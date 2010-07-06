
import sys

from PyQt4.QtGui import *
from PyQt4.QtCore import (SIGNAL, QObject, Qt, QDataStream, QVariant, QTimer,
                          QPointF, pyqtSignal)
from sqlalchemy import create_engine, MetaData, select

from joinlist import JoinList
from scene import Scene

engine = create_engine('mysql://root@localhost/veracity', pool_recycle=3600)
meta = MetaData()
meta.reflect(bind=engine)


class MainWindow(QMainWindow):

    def __init__(self):
        QMainWindow.__init__(self)

        # menu
        filemenu = self.menuBar().addMenu('&File')
        newquery = filemenu.addAction('&New Query')
        quit_ = filemenu.addAction('&Quit')
        QObject.connect(newquery, SIGNAL('triggered()'), self.newquery)
        QObject.connect(quit_, SIGNAL('triggered()'), sys.exit)

        # graphics view
        self.scene = Scene()
        graph = QGraphicsView(self.scene)
        QObject.connect(self.scene, SIGNAL('selectionChanged()'), self.on_add)

        # table dock
        self.table = QTableWidget(1, 1)
        self.table.setMinimumHeight(100)
        table_dock = QDockWidget('Results')
        table_dock.setWidget(self.table)

        # query dock
        query_dock = QDockWidget('Query')
        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        query_dock.setWidget(self.text_edit)

        # constraint dock
        constraint_dock = QDockWidget('Constraints')
        self.constraints = QPlainTextEdit()
        constraint_dock.setWidget(self.constraints)

        # join dock
        items = (QListWidgetItem(x) for x in meta.tables.keys())
        self.joins = JoinList(items, meta)
        join_dock = QDockWidget('Joins')
        join_dock.setWidget(self.joins)

        self.addDockWidget(Qt.BottomDockWidgetArea, table_dock)
        self.addDockWidget(Qt.BottomDockWidgetArea, query_dock)
        self.addDockWidget(Qt.BottomDockWidgetArea, constraint_dock)
        self.tabifyDockWidget(table_dock, query_dock)
        self.tabifyDockWidget(query_dock, constraint_dock)
        table_dock.raise_()
        self.addDockWidget(Qt.LeftDockWidgetArea, join_dock)

        self.setCentralWidget(graph)


    def newquery(self):
        """Click File->New Query"""
        self.scene.clear()
        Table.alias_dict = {}

    def join(self, query, table):
        for child in table.children:
            query = query.join(child.table)
            query = self.join(query, child)
        return query
    def query(self, table):

        selected = self.scene.selectedItems()
        if len(selected) == 0:
            return

        col_lists = (x.table.c for x in selected)
        cols = [y for x in col_lists for y in x]

        parent = selected[0]
        while parent:
            found = parent
            parent = getattr(parent, 'base_table', None)

        base = found.table

        constraints = self.constraints.toPlainText() or ''

        # query = select(cols, constraints, from_obj=base)
        query = select(cols, constraints, from_obj=self.join(base, found))
        query = query.limit(100)

        results = engine.execute(query)
        keys = results.keys()
        self.table.clear()
        self.table.setColumnCount(len(keys))
        self.table.setRowCount(0)

        cols_set = False
        row = -1
        for row, result in enumerate(results):
            self.table.setRowCount(row + 1)
            for column, data in enumerate(result):
                self.table.setItem(row, column, QTableWidgetItem(str(data)))

        if not cols_set:
            self.table.setHorizontalHeaderLabels(list(keys))

        self.text_edit.setPlainText(str(query))

    def on_add(self):
        items = self.scene.selectedItems()
        if len(items) == 0:
            return
        name = items[0].name

        table = meta.tables[name]
        self.query(table)
        self.joins.set_table(name)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
