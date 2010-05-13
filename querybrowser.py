
import sys

from PyQt4.QtGui import *
from PyQt4.QtCore import SIGNAL, QRectF, QObject, Qt



class Table(QGraphicsRectItem):

    alias_dict = {}

    def __init__(self, name, x, y):
        """Documentation here"""
        self.name = str(name)

        # layout widget
        text = QGraphicsSimpleTextItem('{0} as {1}'.format(name, self.alias))
        width = text.boundingRect().width()
        QGraphicsRectItem.__init__(self, x, y, width + 10, 22)
        self.setFlag(self.ItemIsMovable, True)
        self.setFlag(self.ItemIsSelectable, True)

        text.setParentItem(self)
        text.setX(x + 5)
        text.setY(y + 5)

    @property
    def alias(self):
        if not hasattr(self, '_alias'):
            letters = ''.join(x[0] for x in self.name.split('_'))
            self._alias = letters
            self.alias_dict.setdefault(letters, 0)
            num = self.alias_dict.get(letters, None)
            if num:
                self._alias += str(num)
            self.alias_dict[letters] += 1
        return self._alias

    @property
    def joins(self):
        return ['party_role', 'party_group', 'person']

    def mousePressEvent(self, event):
        print 'click'



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
        self.scene = QGraphicsScene()
        graph = QGraphicsView(self.scene)

        # table widget
        table = QTableWidget(1, 1)
        table.setItem(0, 0, QTableWidgetItem('hello'))
        table.setMinimumHeight(100)

        table_dock = QDockWidget('Results')
        table_dock.setWidget(table)

        query_dock = QDockWidget('Query')

        constraint_dock = QDockWidget('Constraints')

        join_dock = QDockWidget('Joins')
        # join_dock.setMinimumWidth(170)

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
        table, ok = QInputDialog.getText(self, 'Table Name', 'Table Name')
        if not ok:
            return

        #clear settings
        self.scene.clear()
        Table.alias_dict = {}

        self.scene.addItem(Table(table, 0, 0))
        self.scene.addItem(Table('testing_table', 100, 0))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
