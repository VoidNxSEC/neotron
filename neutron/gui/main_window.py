import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

from neutron.gui.tasks_view import TasksView

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.set_default_size(800, 600)
        self.set_title("Neutron")
        
        # Main Layout
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        # Header Bar
        header = Adw.HeaderBar()
        content.append(header)
        
        # Main View (using Adw.StatusPage for a nice empty state or container)
        # For now, we'll put our TasksView directly in a scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        
        tasks_view = TasksView()
        scrolled.set_child(tasks_view)
        
        content.append(scrolled)
        
        self.set_content(content)
