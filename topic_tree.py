"""
topic_tree.py: Custom topic tree widget for LaTeX Exercise Viewer.
"""
from PyQt5.QtWidgets import QTreeWidget, QMessageBox, QInputDialog, QMenu, QTreeWidgetItem, QDialog
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QKeySequence

class TopicTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.setup_context_menu()
        self.installEventFilter(self)
        
    def setup_context_menu(self):
        """Setup context menu for topic tree."""
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_topic_context_menu)
        
    def update_language(self):
        """Update topic tree language."""
        self.setHeaderLabel(self.tr("topics"))
        
    def tr(self, text):
        """Get translation for text."""
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'tr'):
            return self.main_window.tr(text)
        return text
        
    def dropEvent(self, event):
        """Handle drop events and update database."""
        # Get the dragged item
        dragged_item = self.currentItem()
        if not dragged_item:
            return
            
        # Store the original structure for backup
        original_structure = self.get_current_tree_structure()
        try:
            # Let the default drop handling occur first
            super().dropEvent(event)
            # Now update the database to match the new structure
            self.update_database_from_tree()
        except Exception as e:
            # Restore original structure on error
            QMessageBox.critical(self, self.tr("error"), f"{self.tr('failed_to_move_topic')}:\n{str(e)}")
            self.load_topic_tree()  # Reload from database

    def show_topic_context_menu(self, position):
        """Show context menu for topic tree."""
        item = self.itemAt(position)
        menu = QMenu(self)
        menu.setToolTipsVisible(True)
        
        # Add Main Topic option (always available)
        add_main_topic_action = menu.addAction("➕ " + self.tr("add_main_topic"))
        add_main_topic_action.setToolTip(self.tr("add_main_topic_tooltip"))
        add_main_topic_action.triggered.connect(self.add_root_topic)
        
        # If a specific topic is clicked, show topic-specific options
        if item and item.data(0, Qt.UserRole):
            topic_id = item.data(0, Qt.UserRole)
            topic_name = item.text(0)
            if " [" in topic_name:
                topic_name = topic_name.split(" [")[0]
                
            menu.addSeparator()
            
            # Add Child Topic
            add_child_action = menu.addAction("📁 " + self.tr("add_child_topic"))
            add_child_action.setToolTip(self.tr("add_child_topic_tooltip").format(topic_name))
            add_child_action.triggered.connect(lambda: self.add_child_topic(topic_id))
            
            # Movement options
            movement_menu = QMenu("↕️ " + self.tr("move_topic"), self)
            
            # Move Up
            move_up_action = movement_menu.addAction("↑ " + self.tr("move_up"))
            move_up_action.setShortcut(QKeySequence("Ctrl+Up"))
            move_up_action.setToolTip(self.tr("move_up_tooltip"))
            move_up_action.triggered.connect(lambda: self.move_topic_up(topic_id))
            
            # Move Down
            move_down_action = movement_menu.addAction("↓ " + self.tr("move_down"))
            move_down_action.setShortcut(QKeySequence("Ctrl+Down"))
            move_down_action.setToolTip(self.tr("move_down_tooltip"))
            move_down_action.triggered.connect(lambda: self.move_topic_down(topic_id))
            
            movement_menu.addSeparator()
            
            # Promote (move left/make parent)
            promote_action = movement_menu.addAction("← " + self.tr("promote"))
            promote_action.setShortcut(QKeySequence("Ctrl+Left"))
            promote_action.setToolTip(self.tr("promote_tooltip"))
            promote_action.triggered.connect(lambda: self.promote_topic(topic_id, item))
            
            # Demote (move right/make child)
            demote_action = movement_menu.addAction("→ " + self.tr("demote"))
            demote_action.setShortcut(QKeySequence("Ctrl+Right"))
            demote_action.setToolTip(self.tr("demote_tooltip"))
            demote_action.triggered.connect(lambda: self.demote_topic(topic_id, item))
            
            menu.addMenu(movement_menu)
            menu.addSeparator()
            
            # Rename Topic
            rename_action = menu.addAction("✏️ " + self.tr("rename_topic"))
            rename_action.setToolTip(self.tr("rename_topic_tooltip").format(topic_name))
            rename_action.triggered.connect(lambda: self.rename_topic(topic_id, item))
            
            # Delete Topic
            delete_action = menu.addAction("🗑️ " + self.tr("delete_topic"))
            delete_action.setToolTip(self.tr("delete_topic_tooltip").format(topic_name))
            delete_action.triggered.connect(lambda: self.delete_topic(topic_id, item))
            
        menu.exec_(self.viewport().mapToGlobal(position))

    # def add_root_topic(self):
        # """Add a new root topic."""
        # topic_name, ok = QInputDialog.getText(
            # self, 
            # self.tr("add_main_topic"), 
            # self.tr("enter_main_topic_name"),
            # text=""
        # )
        # if ok and topic_name.strip():
            # try:
                # # Check if topic already exists
                # existing_topics = self.main_window.db.get_topic_tree()
                # for topic in existing_topics:
                    # if topic['name'].lower() == topic_name.strip().lower():
                        # QMessageBox.warning(
                            # self, 
                            # self.tr("topic_exists"), 
                            # self.tr("topic_already_exists").format(topic_name)
                        # )
                        # return
                # self.main_window.db.add_topic(topic_name.strip(), None)
                # self.load_topic_tree()
                # QMessageBox.information(self, self.tr("success"), self.tr("main_topic_added_success"))
                # # Auto-expand to show the new topic
                # if hasattr(self.main_window, 'tree_widget_container'):
                    # self.main_window.tree_widget_container.show()
                    # if not self.main_window.tree_visible:
                        # self.main_window.toggle_tree_panel()  # Show tree if it was hidden
            # except Exception as e:
                # QMessageBox.critical(self, self.tr("error"), f"{self.tr('failed_to_add_topic')}:\n{str(e)}")

    # def add_child_topic(self, parent_topic_id):
        # """Add a new child topic."""
        # topic_name, ok = QInputDialog.getText(
            # self, 
            # self.tr("add_child_topic"), 
            # self.tr("enter_child_topic_name")
        # )
        # if ok and topic_name.strip():
            # try:
                # self.main_window.db.add_topic(topic_name.strip(), parent_topic_id)
                # self.load_topic_tree()
                # QMessageBox.information(self, self.tr("success"), self.tr("child_topic_added_success"))
            # except Exception as e:
                # QMessageBox.critical(self, self.tr("error"), f"{self.tr('failed_to_add_topic')}:\n{str(e)}")

    # def rename_topic(self, topic_id, tree_item):
        # """Rename a topic."""
        # current_name = tree_item.text(0)
        # # Remove exercise count from display name if present
        # if " [" in current_name:
            # current_name = current_name.split(" [")[0]
        # new_name, ok = QInputDialog.getText(
            # self, 
            # self.tr("rename_topic"), 
            # self.tr("enter_new_topic_name"),
            # text=current_name
        # )
        # if ok and new_name.strip():
            # try:
                # self.main_window.db.rename_topic(topic_id, new_name.strip())
                # self.load_topic_tree()
                # QMessageBox.information(self, self.tr("success"), self.tr("topic_renamed_success"))
            # except Exception as e:
                # QMessageBox.critical(self, self.tr("error"), f"{self.tr('failed_to_rename_topic')}:\n{str(e)}")


    def add_root_topic(self):
        """Add a new root topic."""
        dialog = QInputDialog(self)
        dialog.setWindowTitle(self.tr("add_main_topic"))
        dialog.setLabelText(self.tr("enter_main_topic_name"))
        dialog.setTextValue("")

        # ✅ Use self.tr() for OK / Cancel
        dialog.setOkButtonText(self.tr("ok"))
        dialog.setCancelButtonText(self.tr("cancel"))

        if dialog.exec_() == QDialog.Accepted:
            topic_name = dialog.textValue()
            if topic_name.strip():
                try:
                    existing_topics = self.main_window.db.get_topic_tree()
                    for topic in existing_topics:
                        if topic['name'].lower() == topic_name.strip().lower():
                            QMessageBox.warning(
                                self,
                                self.tr("topic_exists"),
                                self.tr("topic_already_exists").format(topic_name)
                            )
                            return
                    self.main_window.db.add_topic(topic_name.strip(), None)
                    self.load_topic_tree()
                    QMessageBox.information(self, self.tr("success"), self.tr("main_topic_added_success"))
                    if hasattr(self.main_window, 'tree_widget_container'):
                        self.main_window.tree_widget_container.show()
                        if not self.main_window.tree_visible:
                            self.main_window.toggle_tree_panel()
                except Exception as e:
                    QMessageBox.critical(self, self.tr("error"), f"{self.tr('failed_to_add_topic')}:\n{str(e)}")


    def add_child_topic(self, parent_topic_id):
        """Add a new child topic."""
        dialog = QInputDialog(self)
        dialog.setWindowTitle(self.tr("add_child_topic"))
        dialog.setLabelText(self.tr("enter_child_topic_name"))

        # ✅ Use self.tr() for OK / Cancel
        dialog.setOkButtonText(self.tr("ok"))
        dialog.setCancelButtonText(self.tr("cancel"))

        if dialog.exec_() == QDialog.Accepted:
            topic_name = dialog.textValue()
            if topic_name.strip():
                try:
                    self.main_window.db.add_topic(topic_name.strip(), parent_topic_id)
                    self.load_topic_tree()
                    QMessageBox.information(self, self.tr("success"), self.tr("child_topic_added_success"))
                except Exception as e:
                    QMessageBox.critical(self, self.tr("error"), f"{self.tr('failed_to_add_topic')}:\n{str(e)}")


    def rename_topic(self, topic_id, tree_item):
        """Rename a topic."""
        current_name = tree_item.text(0)
        if " [" in current_name:
            current_name = current_name.split(" [")[0]

        dialog = QInputDialog(self)
        dialog.setWindowTitle(self.tr("rename_topic"))
        dialog.setLabelText(self.tr("enter_new_topic_name"))
        dialog.setTextValue(current_name)

        # ✅ Use self.tr() for OK / Cancel
        dialog.setOkButtonText(self.tr("ok"))
        dialog.setCancelButtonText(self.tr("cancel"))

        if dialog.exec_() == QDialog.Accepted:
            new_name = dialog.textValue()
            if new_name.strip():
                try:
                    self.main_window.db.rename_topic(topic_id, new_name.strip())
                    self.load_topic_tree()
                    QMessageBox.information(self, self.tr("success"), self.tr("topic_renamed_success"))
                except Exception as e:
                    QMessageBox.critical(self, self.tr("error"), f"{self.tr('failed_to_rename_topic')}:\n{str(e)}")
                
                
                
                

    def delete_topic(self, topic_id, tree_item):
        """Delete a topic after confirmation."""
        topic_name = tree_item.text(0)
        if " [" in topic_name:
            topic_name = topic_name.split(" [")[0]
            
        # Check if topic has exercises
        exercises = self.main_window.db.get_exercises_by_topic(topic_id)
        exercise_count = len(exercises)
        
        if exercise_count > 0:
            reply = QMessageBox.warning(
                self,
                self.tr("confirm_topic_deletion"),
                self.tr("topic_has_exercises_warning").format(
                    topic_name=topic_name, 
                    exercise_count=exercise_count
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
        else:
            reply = QMessageBox.question(
                self,
                self.tr("confirm_topic_deletion"),
                self.tr("confirm_topic_delete").format(topic_name),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
        if reply == QMessageBox.Yes:
            try:
                self.main_window.db.delete_topic(topic_id)
                self.load_topic_tree()
                QMessageBox.information(self, self.tr("success"), self.tr("topic_deleted_success"))
            except Exception as e:
                QMessageBox.critical(self, self.tr("error"), f"{self.tr('failed_to_delete_topic')}:\n{str(e)}")
                
    def eventFilter(self, obj, event):
        """Handle keyboard events for topic movement."""
        from PyQt5.QtCore import QEvent
        
        if obj == self and event.type() == QEvent.KeyPress:
            if event.modifiers() == Qt.ControlModifier:
                current_item = self.currentItem()
                
                if current_item and current_item.data(0, Qt.UserRole):
                    topic_id = current_item.data(0, Qt.UserRole)
                    
                    if event.key() == Qt.Key_Up:
                        self.move_topic_up(topic_id)
                        return True
                    elif event.key() == Qt.Key_Down:
                        self.move_topic_down(topic_id)
                        return True
                    elif event.key() == Qt.Key_Left:
                        self.promote_topic(topic_id, current_item)
                        return True
                    elif event.key() == Qt.Key_Right:
                        self.demote_topic(topic_id, current_item)
                        return True
        
        return super().eventFilter(obj, event)
    
    def move_topic_up(self, topic_id: int):
        """Move topic up in the order."""
        try:
            if self.main_window.db.move_topic_up(topic_id):
                # Force a complete reload of the tree
                self.load_topic_tree()
                # Find and select the moved topic
                self.select_topic_in_tree(topic_id)
                self.main_window.statusBar().showMessage(self.tr("topic_moved_up"))
            else:
                self.main_window.statusBar().showMessage(self.tr("topic_already_top"))
        except Exception as e:
            QMessageBox.critical(self, self.tr("error"), f"{self.tr('failed_to_move_topic')}:\n{str(e)}")

    def move_topic_down(self, topic_id: int):
        """Move topic down in the order."""
        try:
            if self.main_window.db.move_topic_down(topic_id):
                # Force a complete reload of the tree
                self.load_topic_tree()
                # Find and select the moved topic
                self.select_topic_in_tree(topic_id)
                self.main_window.statusBar().showMessage(self.tr("topic_moved_down"))
            else:
                self.main_window.statusBar().showMessage(self.tr("topic_already_bottom"))
        except Exception as e:
            QMessageBox.critical(self, self.tr("error"), f"{self.tr('failed_to_move_topic')}:\n{str(e)}")

    def promote_topic(self, topic_id: int, tree_item):
        """Promote a topic to a higher level (move left)."""
        try:
            # Get current parent
            topic_info = self.main_window.db.get_topic_info(topic_id)
            if not topic_info or topic_info[2] is None:  # Already a root topic
                QMessageBox.information(self, self.tr("cannot_promote"), self.tr("already_highest_level"))
                return
                
            current_parent_id = topic_info[2]
            # Get grandparent (parent of current parent)
            parent_info = self.main_window.db.get_topic_info(current_parent_id)
            grandparent_id = parent_info[2] if parent_info else None
            
            # Move topic to grandparent level
            self.main_window.db.change_topic_parent(topic_id, grandparent_id)
            # Force reload and reselect
            self.load_topic_tree()
            self.select_topic_in_tree(topic_id)
            self.main_window.statusBar().showMessage(self.tr("topic_promoted"))
        except Exception as e:
            QMessageBox.critical(self, self.tr("error"), f"{self.tr('failed_to_promote_topic')}:\n{str(e)}")

    def demote_topic(self, topic_id: int, tree_item):
        """Demote a topic to a lower level (move right)."""
        try:
            # Get the previous sibling to become parent
            parent_item = tree_item.parent()
            if not parent_item:
                QMessageBox.information(self, self.tr("cannot_demote"), self.tr("root_cannot_demote"))
                return
                
            current_index = parent_item.indexOfChild(tree_item)
            if current_index == 0:
                QMessageBox.information(self, self.tr("cannot_demote"), self.tr("no_previous_sibling"))
                return
                
            # Get the previous sibling
            previous_sibling = parent_item.child(current_index - 1)
            previous_sibling_id = previous_sibling.data(0, Qt.UserRole)
            
            # Move topic to be child of previous sibling
            self.main_window.db.change_topic_parent(topic_id, previous_sibling_id)
            # Force reload and reselect
            self.load_topic_tree()
            self.select_topic_in_tree(topic_id)
            self.main_window.statusBar().showMessage(self.tr("topic_demoted"))
        except Exception as e:
            QMessageBox.critical(self, self.tr("error"), f"{self.tr('failed_to_demote_topic')}:\n{str(e)}")

    def select_topic_in_tree(self, topic_id: int):
        """Select a topic in the tree by its ID."""
        def find_topic_item(item, target_id):
            if not item:
                return None
            if item.data(0, Qt.UserRole) == target_id:
                return item
            for i in range(item.childCount()):
                found = find_topic_item(item.child(i), target_id)
                if found:
                    return found
            return None
            
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            found_item = find_topic_item(item, topic_id)
            if found_item:
                self.setCurrentItem(found_item)
                found_item.setExpanded(True)
                return

    def get_current_tree_structure(self):
        """Get the current tree structure as a dictionary for backup."""
        structure = {}
        def get_item_structure(item):
            if not item:
                return None
            topic_id = item.data(0, Qt.UserRole)
            children = []
            for i in range(item.childCount()):
                children.append(get_item_structure(item.child(i)))
            return {
                'id': topic_id,
                'text': item.text(0),
                'children': children
            }
            
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            structure[i] = get_item_structure(item)
        return structure

    def update_database_from_tree(self):
        """Update database to match the current tree widget structure."""
        try:
            # First, collect all the changes
            changes = []
            def collect_changes(item, parent_id=None, order=0):
                if not item:
                    return
                topic_id = item.data(0, Qt.UserRole)
                if topic_id:
                    changes.append({
                        'id': topic_id,
                        'parent_id': parent_id,
                        'order_index': order
                    })
                # Process children
                for i in range(item.childCount()):
                    child = item.child(i)
                    collect_changes(child, topic_id, i)
                    
            # Collect changes from all top-level items
            for i in range(self.topLevelItemCount()):
                item = self.topLevelItem(i)
                collect_changes(item, None, i)
                
            # Apply changes to database in a transaction
            cursor = self.main_window.db.conn.cursor()
            # First reset all orders to avoid conflicts
            cursor.execute("UPDATE topics SET order_index = -1")
            # Apply each change
            for change in changes:
                cursor.execute("""
                    UPDATE topics 
                    SET parent_id = ?, order_index = ? 
                    WHERE id = ?
                """, (change['parent_id'], change['order_index'], change['id']))
            self.main_window.db.conn.commit()
            # Reload to ensure UI matches database
            self.load_topic_tree()
            self.main_window.statusBar().showMessage(self.tr("topic_structure_updated"))
        except Exception as e:
            self.main_window.db.conn.rollback()
            raise Exception(f"{self.tr('failed_to_update_database')}: {str(e)}")

    def load_topic_tree(self):
        """Load and display the topic tree."""
        self.clear()
        tree_data = self.main_window.db.get_topic_tree()
        
        def add_tree_items(parent_item, topics):
            for topic in topics:
                count_text = f" [{topic['exercise_count']}]" if topic['exercise_count'] > 0 else ""
                item = QTreeWidgetItem([f"{topic['name']}{count_text}"])
                item.setData(0, Qt.UserRole, topic['id'])
                if parent_item:
                    parent_item.addChild(item)
                else:
                    self.addTopLevelItem(item)
                if topic['children']:
                    add_tree_items(item, topic['children'])
                    
        add_tree_items(None, tree_data)
        self.expandAll()

    def on_topic_selected(self, item, column):
        """Handle topic selection from tree."""
        topic_id = item.data(0, Qt.UserRole)
        if topic_id is None:
            return
            
        # Get exercises for this topic
        exercises = self.main_window.db.get_exercises_by_topic(topic_id)
        if not exercises:
            self.main_window.clear_views()
            topic_path = " > ".join(self.main_window.db.get_topic_path(topic_id))
            self.main_window.statusBar().showMessage(f"{self.tr('topic')}: {topic_path} ({self.tr('no_exercises')})")
            return
            
        # Load first exercise
        if exercises:
            ex_id = exercises[0][0]
            self.main_window.load_exercise(ex_id)
            topic_path = " > ".join(self.main_window.db.get_topic_path(topic_id))
            self.main_window.statusBar().showMessage(f"{self.tr('topic')}: {topic_path} | {len(exercises)} {self.tr('exercises_count')}")