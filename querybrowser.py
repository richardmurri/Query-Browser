
import sys, random, math, time

from PyQt4.QtGui import *
from PyQt4.QtCore import (SIGNAL, QObject, Qt, QDataStream, QVariant, QTimer,
                          QPointF)
from sqlalchemy import create_engine, MetaData, select

engine = create_engine('mysql://root@localhost/veracity', pool_recycle=3600)
meta = MetaData()
meta.reflect(bind=engine)

zoom = 40

class Vector(object):
    """Basic vector arithmetic helper."""

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def add(self, vector):
        return Vector(self.x + vector.x, self.y + vector.y)

    def subtract(self, vector):
        return Vector(self.x - vector.x, self.y - vector.y)

    def multiply(self, value):
        return Vector(self.x * value, self.y * value)

    def divide(self, value):
        return Vector(self.x / value, self.y / value)

    def magnitude(self):
        return math.sqrt(self.x * self.x + self.y * self.y)

    def normalize(self):
        return self.divide(self.magnitude())

    @classmethod
    def random(cls):
        return cls(random.random(), random.random())


class Spring(QGraphicsLineItem):
    instances = []
    constant = 100.0
    length = 1.0

    def __init__(self, table1, table2):
        self.table1 = table1
        self.table2 = table2
        table1.springs.append(self)
        table2.springs.append(self)
        self.instances.append(self)

        QGraphicsLineItem.__init__(self)

        pen = QPen()
        pen.setWidth(2)

        points = QPolygonF()
        for poly in (QPointF(7,0), QPointF(-7,7), QPointF(-5,2), QPointF(-11,2),
                     QPointF(-11,-2), QPointF(-5,-2), QPointF(-7,-7)):
            points.append(poly)

        self.arrow = QGraphicsPolygonItem(points, self)
        self.arrow.setBrush(Qt.cyan)
        self.arrow.setPen(Qt.darkCyan)

        self.setPen(pen)
        self.update_spring()
        self.setZValue(-1)

    def update_spring(self):
        point1 = self.table1.point
        point2 = self.table2.point

        x1 = point1.x * zoom
        y1 = point1.y * zoom
        x2 = point2.x * zoom
        y2 = point2.y * zoom
        self.setLine(x1, y1, x2, y2)

        rise = y2 - y1
        run = x2 - x1
        self.arrow.setX((run / 2)+ x1)
        self.arrow.setY((rise / 2)+ y1)

        tan = math.degrees(math.atan2(rise, run))
        self.arrow.setRotation(tan)




    @classmethod
    def apply_hookes_law(cls):
        for spring in cls.instances:
            d = spring.table2.point.subtract(spring.table1.point)
            displacement = spring.length - d.magnitude()
            direction = d.normalize()

            spring.table1.apply_force(direction.multiply(spring.constant * displacement * -0.5))
            spring.table2.apply_force(direction.multiply(spring.constant * displacement * 0.5))


timer = QTimer()
def start():

    if timer.isActive():
        return

    def run1():
        points = Table.instances
        Table.apply_coulombs_law()
        Spring.apply_hookes_law()
        Table.update_velocity(0.05)
        Table.update_position(0.05)

        k = 0.0
        for point in Table.instances:
            speed = point.velocity.magnitude()
            k += speed * speed

        print k
        if k < 0.01:
            timer.stop()

    QObject.connect(timer, SIGNAL('timeout()'), run1)
    timer.start(10)


class Table(QGraphicsRectItem):

    alias_dict = {}
    instances = []
    repulsion = 600.0
    damping = 0.5

    def __init__(self, name, vector, mass=1.0):
        """Documentation here"""
        self.name = str(name)

        # layout widget
        x, y = vector.x, vector.y
        text = QGraphicsSimpleTextItem('{0} as {1}'.format(name, self.alias))
        width = text.boundingRect().width()
        QGraphicsRectItem.__init__(self, x, y, width + 10, 22)

        self.setBrush(Qt.cyan)
        self.setPen(Qt.darkCyan)


        self.width = width + 10
        self.height = 22
        self.setFlag(self.ItemIsMovable, True)
        self.setFlag(self.ItemIsSelectable, True)

        text.setParentItem(self)
        text.setX(x + 5)
        text.setY(y + 5)

        self.point = vector
        self.mass = mass
        self.velocity = Vector(0, 0)
        self.force = Vector(0, 0)
        self.instances.append(self)
        self.springs = []

    def apply_force(self, force):
        af = force.divide(self.mass)
        self.force = self.force.add(force.divide(self.mass))

    @classmethod
    def apply_coulombs_law(cls):
        for table1 in cls.instances:
            for table2 in cls.instances:
                if table1 is table2:
                    continue
                d = table1.point.subtract(table2.point)
                distance = d.magnitude() + 1.0
                direction = d.normalize()

                af = direction.multiply(cls.repulsion)
                af2 = af.divide(distance * distance * 0.5)

                table1.apply_force(direction.multiply(cls.repulsion).divide(distance * distance * 0.5))
                table2.apply_force(direction.multiply(cls.repulsion).divide(distance * distance * -0.5))

    @classmethod
    def update_velocity(cls, timestep):
        for table in cls.instances:
            table.velocity = table.velocity.add(table.force.multiply(timestep)).multiply(cls.damping)
            table.force = Vector(0, 0)

    @classmethod
    def update_position(cls, timestep):
        for table in cls.instances:
            table.point = table.point.add(table.velocity.multiply(timestep))
            table.setX(table.point.x)
            table.setY(table.point.y)

    def update_springs(self):
        for spring in self.springs:
            spring.update_spring()

    def setX(self, val):
        QGraphicsRectItem.setX(self, val * zoom - (self.width / 2))
        self.update_springs()

    def setY(self, val):
        QGraphicsRectItem.setY(self, val * zoom - (self.height / 2))
        self.update_springs()

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

    def mousePressEvent(self, event):
        print 'click'


class JoinList(QWidget):

    def __init__(self, scene, parent=None):
        """Initialize object."""
        QWidget.__init__(self, parent)

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

        for table in sorted(meta.tables.keys()):
            QListWidgetItem(table, self.list)

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
        self.scene.addItem(Table(item.text(), Vector.random()))


class Scene(QGraphicsScene):


    def __init__(self, parent=None):
        """Override scene to handle drag/drop."""
        QGraphicsScene.__init__(self, parent)

    def addItem(self, widget):
        QGraphicsScene.addItem(self, widget)
        self.clearSelection()
        widget.setSelected(True)
        start()

    def dragEnterEvent(self, event):
        return event.acceptProposedAction()

    def dragMoveEvent(self, event):
        return event.acceptProposedAction()

    def dropEvent(self, event):
        event.acceptProposedAction()
        data = event.mimeData().data('application/x-qabstractitemmodeldatalist')
        text = self.decode_data(data)[0][0].toString()
        item = Table(text, Vector.random())
        items = self.selectedItems()
        if items:
            spring = Spring(items[0], item)
            QGraphicsScene.addItem(self, spring)
        self.addItem(item)

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

        # join dock
        joins = JoinList(self.scene)
        join_dock = QDockWidget('Joins')
        join_dock.setWidget(joins)

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

    def query(self, table):

        # set results
        query = select([table]).limit(100)
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

        connects_to = (fk.column.table.name for fk in table.foreign_keys)
        connected_to = (t.name for t in meta.tables.itervalues()
                        for fk in t.foreign_keys if fk.column.table is table)
        fks = set()
        fks.update(connects_to)
        fks.update(connected_to)
        fks = list(fks)
        fks.sort()
        print fks


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
