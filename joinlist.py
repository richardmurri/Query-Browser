from PySide.QtGui import (QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QLabel,
                         QCheckBox, QListWidget, QListWidgetItem)
from PySide.QtCore import Signal


class Filter(QWidget):
    """Abstract base class for filters."""
    filter_changed = Signal()


class ListFilter(object):
    """Handle filtering a list from multiple filters.

    Each filter needs to inherit from Filter.  Whenever the changed signal is
    sent the filter will refilter the entire list.

    """

    def __init__(self, list_component, filters):
        """Filtering of a list component."""
        self.list = list_component
        self.filters = filters
        for f in filters:
            f.filter_changed.connect(self.filter)

    def filter(self):
        """Filter the configured list."""
        count = 0
        while count < self.list.count():
            item = self.list.item(count)
            text = item.text()

            # ask the filters if this item should be filtered
            visible = True
            for f in self.filters:
                visible = visible and not f.filter_item(text)

            item.setHidden(not visible)
            count += 1


class TextFilter(Filter):
    """Handle filtering of a list by matching subsequence."""

    def __init__(self):
        """Create qt widget and attach handlers."""
        QWidget.__init__(self)
        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit()
        self.label = QLabel('Filter:')
        hbox.addWidget(self.label)
        hbox.addWidget(self.edit)
        self.setLayout(hbox)
        self.edit.textChanged.connect(self.filter_changed)

    def filter_item(self, list_item):
        """Filter an item if it doesn't include a subsequence of the text."""
        text = str(self.edit.text())
        if text is '':
            return False
        return text not in str(list_item)


class FkFilter(QWidget):
    """Handle filtering of a list by matching foreign keys of the input."""

    filter_changed = Signal()

    def __init__(self, meta):
        """Create qt widget and attach handlers."""
        QWidget.__init__(self)

        self.meta = meta

        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        self.checkbox = QCheckBox()
        self.edit = QLineEdit()
        self.label = QLabel('Fk Filter:')
        hbox.addWidget(self.checkbox)
        hbox.addWidget(self.label)
        hbox.addWidget(self.edit)
        self.setLayout(hbox)
        self.checkbox.setChecked(True)
        # self.checkbox.setTristate(True)

        # when the text is changed, run the filter
        self.edit.textChanged.connect(self.filter_changed)
        self.edit.textChanged.connect(self.reset)
        self.checkbox.stateChanged.connect(self.filter_changed)

    def reset(self):
        if hasattr(self, '_fks'):
            del self._fks
        self.filter_changed.emit()

    def filter_item(self, list_item):
        """Filter an item if it isn't a foreign key of the input."""
        if self.checkbox.isChecked():
            return str(list_item) not in self.fks()
        else:
            return False

    def fks(self):
        if not hasattr(self, '_fks'):
            name = str(self.edit.text())
            table = self.meta.tables.get(name)
            if table is not None:
                connects_to = (fk.column.table.name for fk in table.foreign_keys)
                connected_to = (t.name for t in self.meta.tables.itervalues()
                                for fk in t.foreign_keys if fk.column.table is table)
                fks = set()
                fks.update(connects_to)
                fks.update(connected_to)
                self._fks = fks
            else:
                self._fks = set(self.meta.tables.keys())
        return self._fks


class JoinList(QWidget):
    """The join list includes a list of possible tables to join.

    The point is to filter down to the smallest amount possible for what you
    want to join.  This makes creating the joins easier.

    """

    def __init__(self, items, meta):
        """Initialize object."""
        QWidget.__init__(self)

        # create list
        self.list = QListWidget()
        self.list.setDragEnabled(True)

        # add filters
        self.text_filter = TextFilter()
        self.fk_filter = FkFilter(meta)

        self.list_filter = ListFilter(self.list, [self.text_filter, self.fk_filter])

        # # set vertical layout
        vlayout = QVBoxLayout()
        vlayout.addWidget(self.text_filter)
        vlayout.addWidget(self.list)
        vlayout.addWidget(self.fk_filter)

        for item in reversed([QListWidgetItem(x) for x in sorted(items)]):
            self.list.insertItem(0, item)

        self.setLayout(vlayout)

    def set_table(self, table):
        self.text_filter.edit.setText('')
        self.fk_filter.edit.setText(str(table))

