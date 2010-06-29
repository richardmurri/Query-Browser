from PyQt4.QtGui import (QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QLabel,
                         QCheckBox, QListWidget, QListWidgetItem)
from PyQt4.QtCore import pyqtSignal


class Filter(QWidget):
    """Abstract base class for filters."""
    filter_changed = pyqtSignal()


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
        text = self.edit.text()
        if text is None:
            return False
        return text not in list_item


class FkFilter(Filter):
    """Handle filtering of a list by matching foreign keys of the input."""

    def __init__(self):
        """Create qt widget and attach handlers."""
        QWidget.__init__(self)

        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        self.checkbox = QCheckBox()
        self.edit = QLineEdit()
        self.label = QLabel('Fk Filter:')
        hbox.addWidget(self.checkbox)
        hbox.addWidget(self.label)
        hbox.addWidget(self.edit)
        self.setLayout(hbox)
        self.edit.setDisabled(True)
        self.label.setDisabled(True)

        # when the text is changed, run the filter
        self.edit.textChanged.connect(self.filter_changed)
        self.checkbox.stateChanged.connect(self.set_disabled)

    def filter_item(self, list_item):
        """Filter an item if it isn't a foreign key of the input."""
        text = self.edit.text()
        if self.checkbox.isChecked():
            return text not in list_item
        else:
            return False

    def set_disabled(self, enabled):
        """Disable/Enable the filter."""
        self.edit.setDisabled(not enabled)
        self.label.setDisabled(not enabled)
        self.filter_changed.emit()


class JoinList(QWidget):
    """The join list includes a list of possible tables to join.

    The point is to filter down to the smallest amount possible for what you
    want to join.  This makes creating the joins easier.

    """

    def __init__(self, items):
        """Initialize object."""
        QWidget.__init__(self)

        # create list
        self.list = QListWidget()
        self.list.setDragEnabled(True)

        # add filters
        text_filter = TextFilter()
        fk_filter = FkFilter()

        self.list_filter = ListFilter(self.list, [text_filter, fk_filter])

        # set vertical layout
        vlayout = QVBoxLayout()
        vlayout.addWidget(text_filter)
        vlayout.addWidget(self.list)
        vlayout.addWidget(fk_filter)

        for item in reversed(sorted(items)):
            self.list.insertItem(0, item)

        self.setLayout(vlayout)

