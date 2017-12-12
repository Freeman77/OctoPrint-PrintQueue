import sqlite3
from operator import itemgetter


class PrintQueue:
    def __init__(self, db_path):
        self._status = 'stopped'
        self._db_path = db_path
        self._queue_items = []
        self._next_item = None
        self.init_db()

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value

    @property
    def next_item(self):
        self.get_queue_items()
        if len(self._queue_items) > 0:
            self._next_item = self._queue_items[0]
        else:
            self._next_item = None
        return self._next_item

    def init_db(self):
        try:
            db_conn = sqlite3.connect(self._db_path)
            cursor = db_conn.cursor()
            #Create print_queue database
            create_sql = """\
                DROP TABLE IF EXISTS print_queue;
                CREATE TABLE IF NOT EXISTS print_queue (
                    q_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    priority INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    total_copies INTEGER NOT NULL,
                    printed_copies INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT "",
                    notes TEXT DEFAULT "" 
                );
                INSERT INTO print_queue (priority, filename, total_copies, printed_copies, status, notes)
                    VALUES (1, 'bender_head_assembly_scale0.8.gcode', 3, 1, 'Ready', 'Order #111');
                INSERT INTO print_queue (priority, filename, total_copies, printed_copies, status, notes)
                    VALUES (2, 'Lock-ring-replacement.gcode', 2, 0, 'Ready', 'Order #222');
                INSERT INTO print_queue (priority, filename, total_copies, printed_copies, status, notes)
                    VALUES (3, 'testFolder/bender_head_assembly.gcode', 1, 0, 'Ready', 'Order #333');
                INSERT INTO print_queue (priority, filename, total_copies, printed_copies, status, notes)
                    VALUES (4, 'Pi3_Toothpaste_Squeezer.gcode', 4, 0, 'Ready', 'Order #444');
            """
            with db_conn:
                db_conn.executescript(create_sql)
        except Exception as e:
            print(e)
        finally:
            db_conn.close()

    def get_queue_items(self):
        try:
            db_conn = sqlite3.connect(self._db_path)
            select_sql = """\
            SELECT q_id, priority, filename, total_copies, printed_copies, status, notes
            FROM print_queue
            ORDER BY priority ASC
            """
            with db_conn:
                cursor = db_conn.cursor()
                cursor.execute(select_sql)
                all_rows = cursor.fetchall()
                self._queue_items = []
                for row in all_rows:
                    self._queue_items.append(
                        dict(q_id=row[0], priority=row[1], filename=row[2], total_copies=row[3],
                             printed_copies=row[4], status=row[5], notes=row[6]))
                self.sort_queue_items()
                return self._queue_items
        except Exception as e:
            print(e)
            return []
        finally:
            db_conn.close()

    def get_queue_item_by_id(self, q_id):
        try:
            db_conn = sqlite3.connect(self._db_path)
            select_sql = """\
            SELECT q_id, priority, filename, total_copies, printed_copies, status, notes
            FROM print_queue
            WHERE q_id = :q_id
            ORDER BY priority ASC;
            """
            with db_conn:
                cursor = db_conn.cursor()
                cursor.execute(select_sql, {'q_id': q_id})
                row = cursor.fetchone()
                if row:
                    item = dict(q_id=row[0], priority=row[1], filename=row[2], total_copies=row[3],
                                printed_copies=row[4], status=row[5], notes=row[6])
                    return item
                else:
                    return None
        except Exception as e:
            print(e)
            return None
        finally:
            db_conn.close()

    def add_queue_item(self, filename, total_copies, notes=""):
        try:
            db_conn = sqlite3.connect(self._db_path)
            insert_sql = """\
            INSERT INTO print_queue (priority, filename, total_copies, printed_copies, status, notes)
                VALUES (:priority, :filename, :total_copies, 0, 'Ready', :notes);
            """
            priority = len(self._queue_items) + 1
            with db_conn:
                cursor = db_conn.cursor()
                cursor.execute(insert_sql, {'priority': priority, 'filename': filename,
                                            'total_copies': total_copies, 'notes': notes})
                return True
        except Exception as e:
            print(e)
            return False
        finally:
            db_conn.close()

    def rem_queue_item(self, q_id):
        try:
            db_conn = sqlite3.connect(self._db_path)
            delete_sql = """\
                DELETE FROM print_queue WHERE q_id = :q_id;
                """
            item_to_remove = self.get_queue_item_by_id(q_id)
            with db_conn:
                cursor = db_conn.cursor()
                cursor.execute(delete_sql, {'q_id': q_id})
                return True
        except Exception as e:
            print(e)
            return False
        finally:
            db_conn.close()
            self._queue_items.remove(item_to_remove)
            self._sync_priorities()

    def upd_queue_item(self, q_id, total_copies, notes):
        try:
            db_conn = sqlite3.connect(self._db_path)
            insert_sql = """\
            UPDATE print_queue
            SET total_copies = :total_copies, notes = :notes
            WHERE q_id = :q_id;
            """
            with db_conn:
                cursor = db_conn.cursor()
                cursor.execute(insert_sql, {'q_id': q_id, 'total_copies': total_copies, 'notes': notes})
                return True
        except Exception as e:
            print(e)
            return False
        finally:
            db_conn.close()

    def _swap_priority(self, idx_from, idx_to):
        q_itms = self._queue_items
        q_itms[idx_from]['priority'], q_itms[idx_to]['priority'] = \
            q_itms[idx_to]['priority'], q_itms[idx_from]['priority']
        self._update_priority_in_db(q_itms[idx_from]['q_id'], q_itms[idx_from]['priority'])
        self._update_priority_in_db(q_itms[idx_to]['q_id'], q_itms[idx_to]['priority'])

    def change_priority(self, q_id, direction):
        item = self.get_queue_item_by_id(q_id)
        if item:
            try:
                idx = self._queue_items.index(item)
                if direction == "up" and idx > 0:
                    self._swap_priority(idx, idx - 1)
                    return True
                elif direction == "down" and idx < len(self._queue_items)-1:
                    self._swap_priority(idx, idx + 1)
                    return True
                else:
                    return False
            except Exception as e:
                return False
        else:
            return False

    def _update_priority_in_db(self, q_id, new_priority):
        try:
            db_conn = sqlite3.connect(self._db_path)
            update_sql = """\
                UPDATE print_queue
                SET priority = :priority
                WHERE q_id = :q_id;
                """
            with db_conn:
                cursor = db_conn.cursor()
                cursor.execute(update_sql, {'priority': new_priority, 'q_id': q_id})
                return True
        except Exception as e:
            print(e)
            return False
        finally:
            db_conn.close()

    def _sync_priorities(self):
        for idx, item in enumerate(self._queue_items):
            self._update_priority_in_db(item['q_id'], idx + 1)

    def sort_queue_items(self):
        self._queue_items.sort(key=itemgetter('priority'), reverse=False)
