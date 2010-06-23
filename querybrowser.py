
import sys, random, math, time

from PyQt4.QtGui import *
from PyQt4.QtCore import SIGNAL, QRectF, QObject, Qt, QDataStream, QVariant, QTimer

import oursql

conn = oursql.connect(host='localhost', user='root', db='veracity')

class Vector(object):
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

class Spring(object):
    springs = []

    def __init__(self, point1, point2, length=1.0, constant=500.0):
        self.point1 = point1
        self.point2 = point2
        self.length = length
        self.constant = constant
        self.springs.append(self)

    @classmethod
    def apply_hookes_law(cls):
        for spring in cls.springs:
            d = spring.point2.point.subtract(spring.point1.point)
            displacement = spring.length - d.magnitude()
            direction = d.normalize()

            spring.point1.apply_force(direction.multiply(spring.constant * displacement * -0.5))
            spring.point2.apply_force(direction.multiply(spring.constant * displacement * 0.5))


timer = QTimer()
def start():

    if timer.isActive():
        return

    def run1():
        points = Table.points
        Table.apply_coulombs_law()
        Spring.apply_hookes_law()
        Table.update_velocity(0.05)
        Table.update_position(0.05)

        k = 0.0
        for point in Table.points:
            speed = point.velocity.magnitude()
            k += speed * speed

        print k
        if k < 0.01:
            timer.stop()

    QObject.connect(timer, SIGNAL('timeout()'), run1)
    timer.start(10)


class Table(QGraphicsRectItem):

    alias_dict = {}
    points = []
    repulsion = 100.0
    damping = 0.5
    zoom = 40

    def __init__(self, name, vector, mass=1.0):
        """Documentation here"""
        self.name = str(name)

        # layout widget
        x, y = vector.x, vector.y
        text = QGraphicsSimpleTextItem('{0} as {1}'.format(name, self.alias))
        width = text.boundingRect().width()
        QGraphicsRectItem.__init__(self, x, y, width + 10, 22)
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
        self.points.append(self)

    def apply_force(self, force):
        af = force.divide(self.mass)
        self.force = self.force.add(force.divide(self.mass))

    @classmethod
    def apply_coulombs_law(cls):
        for point1 in cls.points:
            for point2 in cls.points:
                if point1 is not point2:
                    d = point1.point.subtract(point2.point)
                    distance = d.magnitude() + 1.0
                    direction = d.normalize()

                    af = direction.multiply(cls.repulsion)
                    af2 = af.divide(distance * distance * 0.5)

                    point1.apply_force(direction.multiply(cls.repulsion).divide(distance * distance * 0.5))
                    point2.apply_force(direction.multiply(cls.repulsion).divide(distance * distance * -0.5))

    @classmethod
    def update_velocity(cls, timestep):
        for point in cls.points:
            point.velocity = point.velocity.add(point.force.multiply(timestep)).multiply(cls.damping)
            point.force = Vector(0, 0)

    @classmethod
    def update_position(cls, timestep):
        for point in cls.points:
            point.point = point.point.add(point.velocity.multiply(timestep))
            point.setX(point.point.x)
            point.setY(point.point.y)

    def setX(self, val):
        QGraphicsRectItem.setX(self, val * self.zoom - self.width / 2)
        items = self.collidingItems(Qt.IntersectsItemShape)
        items = (x for x in items if not isinstance(x, QGraphicsSimpleTextItem))

    def setY(self, val):
        QGraphicsRectItem.setY(self, val * self.zoom - self.height / 2)

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
            Spring(items[0], item)
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
