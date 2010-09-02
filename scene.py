import random, math

from PyQt4.QtGui import (QGraphicsLineItem, QPen, QPolygonF, QGraphicsRectItem,
                         QGraphicsPolygonItem, QGraphicsSimpleTextItem,
                         QGraphicsScene, QGraphicsItem, QMenu, QAction,
                         QActionGroup, QGraphicsSceneMouseEvent)
from PyQt4.QtCore import QPointF, QPoint, Qt, QDataStream, QVariant, QTimer, QObject, pyqtSignal, QString
from sqlalchemy import select



#scene zoom factor (deals with spring graph layout)
zoom = 40

class Vector(object):
    """Basic vector arithmetic helper."""

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __add__(self, vector):
        return Vector(self.x + vector.x, self.y + vector.y)

    def __sub__(self, vector):
        return Vector(self.x - vector.x, self.y - vector.y)

    def __mul__(self, value):
        return Vector(self.x * value, self.y * value)

    def __div__(self, value):
        return Vector(self.x / value, self.y / value)

    def __neg__(self):
        return self * -1

    def magnitude(self):
        return math.sqrt(self.x * self.x + self.y * self.y)

    def normalize(self):
        return self / self.magnitude()

    @classmethod
    def random(cls):
        return cls(random.random(), random.random())


class ArrowMediator(QObject):
    """Only used for signals because QGraphicsRect doesn't inherit from QObject."""
    clicked = pyqtSignal(QGraphicsSceneMouseEvent)


class ArrowPolygonItem(QGraphicsPolygonItem):

    @property
    def clicked(self):
        return self._mediator.clicked

    def __init__(self, parent):
        points = QPolygonF()
        self._mediator = ArrowMediator()
        for poly in (QPointF(7,0), QPointF(-7,7), QPointF(-5,2), QPointF(-11,2),
                     QPointF(-11,-2), QPointF(-5,-2), QPointF(-7,-7)):
            points.append(poly)
        QGraphicsPolygonItem.__init__(self, points, parent)
        self.setPen(Qt.darkCyan)
        self.setBrush(Qt.cyan)


    def update_position(self, point1, point2):

        rise = point2.y - point1.y
        run = point2.x - point1.x
        self.setX((run / 2) + point1.x)
        self.setY((rise / 2) + point1.y)
        tan = math.degrees(math.atan2(rise, run))
        self.setRotation(tan)

    def mousePressEvent(self, event):
        self.clicked.emit(event)
        event.ignore()


class Relation(QGraphicsLineItem):
    """ A spring represents a connection (fk) between two tables."""

    instances = []
    constant = 100.0
    length = 1.0

    def __init__(self, from_table, to_table):
        QGraphicsLineItem.__init__(self)
        self.instances.append(self)

        # from/to table connections
        self.from_table = from_table
        self.to_table = to_table
        from_table.table_move.connect(self.update_spring)
        to_table.table_move.connect(self.update_spring)

        # draw arrow
        self.arrow = ArrowPolygonItem(self)
        self.arrow.clicked.connect(self.change_settings)

        # set attributes
        pen = QPen()
        pen.setWidth(2)
        self.setPen(pen)

        self.update_spring()
        self.setZValue(-1)

        # setup configuration menu
        menu = QMenu()
        join_action = QAction('Join', menu)
        join_action.setCheckable(True)
        join_action.setChecked(True)
        outer_join_action = QAction('Outer Join', menu)
        outer_join_action.setCheckable(True)
        group = QActionGroup(menu)
        group.addAction(join_action)
        group.addAction(outer_join_action)
        menu.addAction(join_action)
        menu.addAction(outer_join_action)
        self.join_action = join_action
        self.outer_join_action = outer_join_action
        self.menu = menu

    def is_outer(self):
        return not self.join_action.isChecked()

    def change_settings(self, event):
        self.menu.popup(event.screenPos())

    def update_spring(self):
        """Update the position of the line and arrow."""
        zoom_point1 = self.from_table.point * zoom
        zoom_point2 = self.to_table.point * zoom
        self.setLine(zoom_point1.x, zoom_point1.y, zoom_point2.x, zoom_point2.y)
        self.arrow.update_position(zoom_point1, zoom_point2)

    @classmethod
    def apply_hookes_law(cls):
        for spring in cls.instances:
            d = spring.to_table.point - spring.from_table.point
            displacement = cls.length - d.magnitude()
            direction = d.normalize()

            force = direction * cls.constant * displacement * 0.5
            spring.to_table.apply_force(force)
            spring.from_table.apply_force(-force)

    @classmethod
    def clear(cls):
        cls.instances = []


class Mediator(QObject):
    """Only used for signals because QGraphicsRect doesn't inherit from QObject."""
    table_move = pyqtSignal()


class Table(QGraphicsRectItem):

    alias_dict = {}
    instances = []
    repulsion = 600.0
    damping = 0.5

    @property
    def table_move(self):
        """Mimic a signal on this class."""
        return self._mediator.table_move

    @property
    def parent(self):
        parents = (x.from_table for x in Relation.instances if x.to_table is self)
        try:
            return parents.next()
        except StopIteration:
            return None

    @property
    def child_relations(self):
        return (x for x in Relation.instances if x.from_table is self)

    def __init__(self, table, vector, mass=1.0):
        """Documentation here"""

        self.name = table.name
        self._mediator = Mediator()

        # layout widget
        x, y = vector.x, vector.y
        text = QGraphicsSimpleTextItem('{0} as {1}'.format(self.name, self.alias))
        width = text.boundingRect().width()
        QGraphicsRectItem.__init__(self, x, y, width + 10, 22)

        self.table = table.alias(self.alias)

        self.setBrush(Qt.cyan)
        self.setPen(Qt.darkCyan)

        self.width = width + 10
        self.height = 22
        self.setFlag(self.ItemIsSelectable, True)

        text.setParentItem(self)
        text.setX(x + 5)
        text.setY(y + 5)

        self.point = vector
        self.mass = mass
        self.velocity = Vector(0, 0)
        self.force = Vector(0, 0)
        self.instances.append(self)

    def apply_force(self, force):
        af = force / self.mass
        self.force = self.force + (force / self.mass)

    @classmethod
    def apply_coulombs_law(cls):
        for from_table in cls.instances:
            for to_table in cls.instances:
                if from_table is to_table:
                    continue
                d = from_table.point - to_table.point
                distance = d.magnitude() + 1.0
                direction = d.normalize()

                force = (direction * cls.repulsion) / (distance * distance * 0.5)
                from_table.apply_force(force)
                to_table.apply_force(-force)

    @classmethod
    def clear(cls):
        cls.instances = []
        cls.alias_dict = {}

    @classmethod
    def update_velocity(cls, timestep):
        for table in cls.instances:
            table.velocity = (table.velocity + table.force * timestep) * cls.damping
            table.force = Vector(0, 0)

    @classmethod
    def update_position(cls, timestep):
        for table in cls.instances:
            table.point = table.point + table.velocity * timestep
            table.setX(table.point.x)
            table.setY(table.point.y)

    def setX(self, val):
        QGraphicsRectItem.setX(self, val * zoom - (self.width / 2))
        self.table_move.emit()

    def setY(self, val):
        QGraphicsRectItem.setY(self, val * zoom - (self.height / 2))
        self.table_move.emit()

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

    # def mouseMoveEvent(self, event):
    #     pos = event.scenePos()
    #     mouse_pos = event.pos()
    #     print mouse_pos.x(), mouse_pos.y()
    #     self.point.x = pos.x() / zoom
    #     self.point.y = pos.y() / zoom
    #     self.table_move.emit()
    #     return QGraphicsRectItem.mouseMoveEvent(self, event)

    def itemChange(self, change, value):
        # print change, value
        return QGraphicsRectItem.itemChange(self, change, value)


class Scene(QGraphicsScene):

    query_changed = pyqtSignal()
    table_changed = pyqtSignal(QString)

    def __init__(self, parent=None):
        """Override scene to handle drag/drop."""
        QGraphicsScene.__init__(self, parent)
        self.selectionChanged.connect(self.on_selection_change)
        self.timer = QTimer()
        self.constraints = ''

    def addItem(self, widget):
        QGraphicsScene.addItem(self, widget)
        self.clearSelection()
        widget.setSelected(True)
        self.layout()

    def layout(self):

        # if the layout is still running, do nothing
        if self.timer.isActive():
            return
        self.timer.timeout.connect(self.run_layout)
        self.timer.start(10)

    def run_layout(self):
        points = Table.instances
        Table.apply_coulombs_law()
        Relation.apply_hookes_law()
        Table.update_velocity(0.05)
        Table.update_position(0.05)

        k = 0.0
        for point in Table.instances:
            speed = point.velocity.magnitude()
            k += speed * speed

        if k < 0.01:
            self.timer.stop()

    def dragEnterEvent(self, event):

        if len(self.selectedItems()) != 1 and \
                len(Table.instances) > 0:
            return event.ignore()
        return event.acceptProposedAction()

    def dragMoveEvent(self, event):
        return event.acceptProposedAction()

    def dropEvent(self, event):
        items = self.selectedItems()
        event.acceptProposedAction()
        data = event.mimeData().data('application/x-qabstractitemmodeldatalist')
        text = self.decode_data(data)[0][0].toString()
        table = meta.tables[str(text)]
        item = Table(table, Vector.random())
        if items:
            spring = Relation(items[0], item)
            QGraphicsScene.addItem(self, spring)
        self.addItem(item)

    def reset_scene(self):
        self.clear()
        Relation.clear()
        Table.clear()

    def get_root(self):
        """Get the root table in the scene."""
        table = Table.instances[0]
        child = table
        while 1:
            parent = child.parent
            if parent:
                child = parent
            else:
                break
        return child

    def get_columns(self):
        """Get the columns to display.

        The columns displayed are derived from the tables that are selected in
        the scene.

        """
        selected = self.selectedItems()
        col_lists = (x.table.c for x in selected)
        return [y for x in col_lists for y in x]

    def join(self, query, table):
        """Recursively join all the tables in the scene.

        This returns the joined sqlalchemy query.

        """
        for relation in table.child_relations:
            child = relation.to_table
            if relation.is_outer():
                query = query.outerjoin(child.table)
            else:
                query = query.join(child.table)
            query = self.join(query, child)
        return query

    def get_query(self):
        """Create sqlalchemy query based on the contents of the scene."""
        root = self.get_root()
        base = root.table
        cols = self.get_columns()
        query = select(cols, self.constraints, from_obj=self.join(base, root))
        return query.limit(100)

    def on_selection_change(self):
        """Run a query based on the contents of the scene.

        This only happens if it makes sense to do so.

        """
        items = self.selectedItems()
        if len(items) == 0:
            return
        elif len(items) == 1:
            name = items[0].name
            self.table_changed.emit(name)
        self.query = self.get_query()
        self.query_changed.emit()


    def decode_data(self, bytearray):
        """Handle drag/drop data."""

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

from querybrowser import meta
