import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject

class TasksView(Gtk.Box):
    def __init__(self, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12, **kwargs)
        
        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header_box.set_margin_top(24)
        header_box.set_margin_bottom(12)
        header_box.set_margin_start(24)
        header_box.set_margin_end(24)
        
        title = Gtk.Label(label="Active Tasks")
        title.add_css_class("title-2")
        title.set_halign(Gtk.Align.START)
        title.set_hexpand(True)
        
        add_btn = Gtk.Button(icon_name="list-add-symbolic")
        add_btn.add_css_class("flat")
        
        header_box.append(title)
        header_box.append(add_btn)
        self.append(header_box)
        
        # Task List
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.add_css_class("boxed-list")
        self.list_box.set_margin_start(24)
        self.list_box.set_margin_end(24)
        self.list_box.set_margin_bottom(24)
        
        self.append(self.list_box)
        
        # Populate with mock data
        self._populate_mock_tasks()

    def _populate_mock_tasks(self):
        mock_tasks = [
            ("Training Component A", "Running", "success"),
            ("Data Optimization", "Pending", "warning"),
            ("Cost Analysis", "Completed", "accent"),
        ]
        
        for name, status, color in mock_tasks:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            box.set_margin_top(12)
            box.set_margin_bottom(12)
            box.set_margin_start(12)
            box.set_margin_end(12)
            
            # Status Indicator
            indicator = Gtk.Image(icon_name="media-record-symbolic")
            indicator.add_css_class(color)
            
            # Task Name
            label = Gtk.Label(label=name)
            label.set_halign(Gtk.Align.START)
            label.set_hexpand(True)
            
            # Status badge
            status_label = Gtk.Label(label=status)
            status_label.add_css_class("dim-label")
            
            box.append(indicator)
            box.append(label)
            box.append(status_label)
            
            row.set_child(box)
            self.list_box.append(row)
