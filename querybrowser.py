
import sys

from PyQt4.QtGui import *
from PyQt4.QtCore import SIGNAL, QRectF, QObject, Qt, QDataStream, QVariant

import oursql

conn = oursql.connect(host='localhost', user='root', db='veracity')

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


class JoinList(QWidget):

    def __init__(self, scene, parent=None):
        """Initialize object."""
        QListWidget.__init__(self, parent)

        vlayout = QVBoxLayout()
        filter_layout = QHBoxLayout()

        self.edit = QLineEdit()
        self.list = QListWidget()

        filter_layout.addWidget(QLabel('Filter:'))
        filter_layout.addWidget(self.edit)

        vlayout.addLayout(filter_layout)
        vlayout.addWidget(self.list)

        self.scene = scene
        self.list.setDragEnabled(True)

        with conn.cursor() as cursor:
            cursor.execute('show tables')
            for row in cursor:
                QListWidgetItem(row[0], self.list)


        QObject.connect(self.edit, SIGNAL('textChanged(const QString &)'), self.filter)
        QObject.connect(self.list, SIGNAL('itemDoubleClicked(QListWidgetItem *)'), self.add)

        self.setLayout(vlayout)

    def filter(self, text):
        count = 0
        while count < self.list.count() - 1:
            item = self.list.item(count)
            if text and text not in item.text():
                item.setHidden(True)
            else:
                item.setHidden(False)
            count += 1

    def add(self, item):
        """Add table to the query."""
        self.scene.addItem(Table(item.text(), 0, 0))


class Scene(QGraphicsScene):
    def __init__(self, parent=None):
        """Override scene to handle drag/drop."""
        QGraphicsScene.__init__(self, parent)

    def addItem(self, widget):
        QGraphicsScene.addItem(self, widget)
        self.clearSelection()
        widget.setSelected(True)

    def dragEnterEvent(self, event):
        return event.acceptProposedAction()

    def dragMoveEvent(self, event):
        return event.acceptProposedAction()

    def dropEvent(self, event):
        event.acceptProposedAction()
        data = event.mimeData().data('application/x-qabstractitemmodeldatalist')
        text = self.decode_data(data)[0][0].toString()
        self.addItem(Table(text, 0, 0))

    def decode_data(self, bytearray):

        data = []
        item = {}

        ds = QDataStream(bytearray)
        while not ds.atEnd():

            row = ds.readInt32()
            column = ds.readInt32()

            map_items = ds.readInt32()
            for i in range(map_items):

                key = ds.readInt32()

                value = QVariant()
                ds >> value
                item[Qt.ItemDataRole(key)] = value

            data.append(item)

        return data


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

        # table widget
        table = QTableWidget(1, 1)
        table.setItem(0, 0, QTableWidgetItem('hello'))
        table.setMinimumHeight(100)

        joins = JoinList(self.scene)

        table_dock = QDockWidget('Results')
        table_dock.setWidget(table)

        query_dock = QDockWidget('Query')

        constraint_dock = QDockWidget('Constraints')

        join_dock = QDockWidget('Joins')
        join_dock.setWidget(joins)
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
        self.scene.clear()
        Table.alias_dict = {}


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
