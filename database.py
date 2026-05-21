"""
database.py: Database management module for LaTeX exercises.
Handles all database operations including CRUD operations and hierarchical topic management.
"""
import sqlite3
from datetime import datetime
from typing import List, Dict, Tuple, Optional

import os
from pathlib import Path

class DatabaseManager:
    """Manages database operations for exercises and metadata."""
    
    def __init__(self, db_path: str = "exercises.db"):
        """
        Initialise the database manager.

        Parameters
        ----------
        db_path : str
            Either a bare filename (e.g. ``"exercises.db"`` – the default) or
            a full absolute path (e.g. ``r"C:\\Users\\X\\mydb.db"``).

            * **Bare filename** – the file is placed inside
              ``%APPDATA%\\YasmeenTex\\`` (created automatically if needed).
            * **Absolute path** – used verbatim; the parent directory is
              created if it does not exist yet.
        """
        if os.path.isabs(db_path):
            # Caller supplied a full path – respect it and ensure the
            # parent directory exists.
            self.db_path = db_path
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        else:
            # Bare filename → store inside %APPDATA%\YasmeenTex\
            appdata_dir = os.getenv('APPDATA')
            if appdata_dir:
                app_folder = Path(appdata_dir) / "YasmeenTex"
                app_folder.mkdir(parents=True, exist_ok=True)
                self.db_path = str(app_folder / db_path)
            else:
                # Fallback to current working directory
                self.db_path = db_path

        self.conn = None
        self.init_db()
    
    def init_db(self):
        """Initialize database connection and create tables if they don't exist."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()
        self._populate_default_topics()
    
    def _create_tables(self):
        """Create necessary tables for exercises and metadata."""
        cursor = self.conn.cursor()
        
        # Main exercises table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keycode TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                latex TEXT NOT NULL,
                solution TEXT,
                creation_date TEXT DEFAULT CURRENT_TIMESTAMP,
                level TEXT
            )
        """)
        
        # Hierarchical topics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                parent_id INTEGER,
                order_index INTEGER DEFAULT 0,
                FOREIGN KEY (parent_id) REFERENCES topics(id) ON DELETE CASCADE,
                UNIQUE(name, parent_id)
            )
        """)
        
        # Exercise-topic mapping (many-to-many)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exercise_topics (
                exercise_id INTEGER NOT NULL,
                topic_id INTEGER NOT NULL,
                PRIMARY KEY (exercise_id, topic_id),
                FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE,
                FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
            )
        """)
        
        # Metadata/keywords table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exercise_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes for better search performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_exercises_keycode 
            ON exercises(keycode)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_exercises_name 
            ON exercises(name)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_exercises_level 
            ON exercises(level)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_keywords_keyword 
            ON keywords(keyword)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_topics_parent 
            ON topics(parent_id)
        """)
        
        self.conn.commit()
    
    def _populate_default_topics(self):
        """Populate default topic hierarchy if topics table is empty."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM topics")
        if cursor.fetchone()[0] > 0:
            return  # Topics already exist
        
        # Define default topic hierarchy
        topics_hierarchy = {
            "Analysis": {
                "Real Analysis": ["Sequences and Series", "Limits and Continuity", 
                                 "Differentiation", "Integration", "Measure Theory"],
                "Complex Analysis": ["Analytic Functions", "Complex Integration", 
                                    "Cauchy's Theorem", "Series Expansions", "Residue Theory"],
                "Functional Analysis": ["Normed Spaces", "Banach and Hilbert Spaces", 
                                       "Linear Operators", "Spectral Theory"],
                "Topology (Analysis)": ["Metric Spaces", "Continuity & Compactness", "Connectedness"]
            },
            "Algebra": {
                "Linear Algebra": ["Vector Spaces", "Linear Transformations", 
                                  "Eigenvalues & Eigenvectors", "Inner Product Spaces"],
                "Abstract Algebra": ["Groups", "Rings", "Fields", "Modules", "Galois Theory"],
                "Commutative Algebra": ["Ideals & Quotients", "Noetherian Rings", "Localization"]
            },
            "Geometry": {
                "Euclidean Geometry": ["Lines, Angles, Triangles", "Circles & Conics"],
                "Differential Geometry": ["Curves and Surfaces", "Riemannian Geometry", "Geodesics"],
                "Algebraic Geometry": ["Affine & Projective Varieties", "Schemes and Morphisms", 
                                      "Intersection Theory"],
                "Topology (Geometry)": ["Manifolds", "Homotopy & Homology"]
            },
            "Number Theory": {
                "Elementary Number Theory": ["Divisibility & Primes", "Modular Arithmetic", 
                                           "Diophantine Equations"],
                "Analytic Number Theory": ["Prime Number Theorem", "Riemann Zeta Function"],
                "Algebraic Number Theory": ["Number Fields", "Ideals & Class Groups", 
                                           "Units and Factorization"]
            },
            "Probability & Statistics": {
                "Probability Theory": ["Probability Spaces", "Random Variables", 
                                      "Expectation & Variance", "Law of Large Numbers & CLT"],
                "Statistics": ["Descriptive Statistics", "Inferential Statistics", 
                              "Regression & Correlation"],
                "Stochastic Processes": ["Markov Chains", "Brownian Motion", "Poisson Processes"]
            },
            "Applied Mathematics": {
                "Differential Equations": ["Ordinary Differential Equations", 
                                          "Partial Differential Equations", "Dynamical Systems"],
                "Numerical Analysis": ["Numerical Linear Algebra", "Interpolation & Approximation", 
                                      "Numerical Solutions to ODEs & PDEs"],
                "Optimization": ["Linear Programming", "Nonlinear Optimization", "Variational Methods"],
                "Mathematical Modelling": ["Population Models", "Fluid Dynamics", "Economic Models"]
            },
            "Logic & Foundations": {
                "Set Theory": ["Cardinality", "Ordinals", "Axiomatic Set Theory"],
                "Mathematical Logic": ["Propositional & Predicate Logic", "Proof Theory", "Model Theory"],
                "Category Theory": ["Objects & Morphisms", "Functors & Natural Transformations", 
                                   "Limits & Colimits"]
            }
        }
        
        # Insert topics
        order = 0
        for main_topic, subtopics in topics_hierarchy.items():
            cursor.execute("INSERT INTO topics (name, parent_id, order_index) VALUES (?, NULL, ?)", 
                          (main_topic, order))
            main_id = cursor.lastrowid
            order += 1
            
            sub_order = 0
            for subtopic, subsubtopics in subtopics.items():
                cursor.execute("INSERT INTO topics (name, parent_id, order_index) VALUES (?, ?, ?)", 
                              (subtopic, main_id, sub_order))
                sub_id = cursor.lastrowid
                sub_order += 1
                
                subsub_order = 0
                for subsubtopic in subsubtopics:
                    cursor.execute("INSERT INTO topics (name, parent_id, order_index) VALUES (?, ?, ?)", 
                                  (subsubtopic, sub_id, subsub_order))
                    subsub_order += 1
        
        self.conn.commit()
    
    def generate_keycode(self) -> str:
        """Generate unique keycode in format EX-YYYYMMDD.HHMMSS.F"""
        now = datetime.now()
        base_keycode = now.strftime("EX-%Y%m%d.%H%M%S")
        
        # Add fractional seconds to ensure uniqueness
        microsecond = now.microsecond // 100000  # Single digit
        keycode = f"{base_keycode}.{microsecond}"
        
        # Ensure uniqueness
        cursor = self.conn.cursor()
        counter = 0
        test_keycode = keycode
        while True:
            cursor.execute("SELECT id FROM exercises WHERE keycode = ?", (test_keycode,))
            if not cursor.fetchone():
                return test_keycode
            counter += 1
            test_keycode = f"{keycode}_{counter}"
    
    def add_exercise(self, name: str, latex: str, solution: str = None, 
                    level: str = None, topic_ids: List[int] = None, 
                    keywords: List[str] = None) -> Tuple[int, str]:
        """
        Add a new exercise to the database.
        
        Returns:
            Tuple of (exercise_id, keycode)
        """
        cursor = self.conn.cursor()
        
        keycode = self.generate_keycode()
        
        cursor.execute("""
            INSERT INTO exercises (keycode, name, latex, solution, level, creation_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (keycode, name, latex, solution, level, datetime.now().isoformat()))
        
        exercise_id = cursor.lastrowid
        
        # Add topic associations
        if topic_ids:
            for topic_id in topic_ids:
                cursor.execute("""
                    INSERT INTO exercise_topics (exercise_id, topic_id)
                    VALUES (?, ?)
                """, (exercise_id, topic_id))
        
        # Add keywords
        if keywords:
            for keyword in keywords:
                cursor.execute("""
                    INSERT INTO keywords (exercise_id, keyword)
                    VALUES (?, ?)
                """, (exercise_id, keyword.strip().lower()))
        
        self.conn.commit()
        return exercise_id, keycode
    
    def update_exercise(self, exercise_id: int, name: str = None, latex: str = None, 
                       solution: str = None, level: str = None, topic_ids: List[int] = None,
                       keywords: List[str] = None):
        """Update an existing exercise."""
        cursor = self.conn.cursor()
        
        # Build dynamic update query
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if latex is not None:
            updates.append("latex = ?")
            params.append(latex)
        if solution is not None:
            updates.append("solution = ?")
            params.append(solution)
        if level is not None:
            updates.append("level = ?")
            params.append(level)
        
        if updates:
            params.append(exercise_id)
            query = f"UPDATE exercises SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
        
        # Update topic associations
        if topic_ids is not None:
            cursor.execute("DELETE FROM exercise_topics WHERE exercise_id = ?", (exercise_id,))
            for topic_id in topic_ids:
                cursor.execute("""
                    INSERT INTO exercise_topics (exercise_id, topic_id)
                    VALUES (?, ?)
                """, (exercise_id, topic_id))
        
        # Update keywords
        if keywords is not None:
            cursor.execute("DELETE FROM keywords WHERE exercise_id = ?", (exercise_id,))
            for keyword in keywords:
                cursor.execute("""
                    INSERT INTO keywords (exercise_id, keyword)
                    VALUES (?, ?)
                """, (exercise_id, keyword.strip().lower()))
        
        self.conn.commit()
    
    def delete_exercise(self, exercise_id: int):
        """Delete an exercise and its associated data."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM exercises WHERE id = ?", (exercise_id,))
        self.conn.commit()
    
    def get_exercise(self, exercise_id: int) -> Optional[Tuple]:
        """Get a single exercise by ID."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, keycode, name, latex, solution, creation_date, level
            FROM exercises WHERE id = ?
        """, (exercise_id,))
        return cursor.fetchone()
    
    def get_keywords(self, exercise_id: int) -> List[str]:
        """Get all keywords for an exercise."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT keyword FROM keywords WHERE exercise_id = ?
        """, (exercise_id,))
        return [row[0] for row in cursor.fetchall()]
    
    def get_exercise_topics(self, exercise_id: int) -> List[int]:
        """Get all topic IDs for an exercise."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT topic_id FROM exercise_topics WHERE exercise_id = ?
        """, (exercise_id,))
        return [row[0] for row in cursor.fetchall()]
    
    def get_topic_tree(self) -> List[Dict]:
        """Get complete topic hierarchy as nested dictionaries."""
        cursor = self.conn.cursor()
        
        def get_children(parent_id):
            cursor.execute("""
                SELECT id, name, order_index FROM topics 
                WHERE parent_id {} 
                ORDER BY order_index, name
            """.format("IS NULL" if parent_id is None else f"= {parent_id}"))
            
            children = []
            for topic_id, name, order_idx in cursor.fetchall():
                # Count exercises in this topic
                cursor.execute("""
                    SELECT COUNT(*) FROM exercise_topics WHERE topic_id = ?
                """, (topic_id,))
                count = cursor.fetchone()[0]
                
                child = {
                    'id': topic_id,
                    'name': name,
                    'order_index': order_idx,
                    'exercise_count': count,
                    'children': get_children(topic_id)
                }
                children.append(child)
            
            return children
        
        return get_children(None)
    
    def get_exercises_by_topic(self, topic_id: int) -> List[Tuple]:
        """Get all exercises for a specific topic."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT e.id, e.keycode, e.name, e.level, e.creation_date
            FROM exercises e
            JOIN exercise_topics et ON e.id = et.exercise_id
            WHERE et.topic_id = ?
            ORDER BY e.creation_date DESC
        """, (topic_id,))
        return cursor.fetchall()
    
    def search_exercises(self, query: str = "", level: str = None, 
                        topic_ids: List[int] = None) -> List[Tuple]:
        """
        Search exercises by name, keywords, level, or topics.
        
        Returns:
            List of tuples: (id, keycode, name, level, creation_date)
        """
        cursor = self.conn.cursor()
        
        sql = """
            SELECT DISTINCT e.id, e.keycode, e.name, e.level, e.creation_date
            FROM exercises e
            LEFT JOIN keywords k ON e.id = k.exercise_id
            LEFT JOIN exercise_topics et ON e.id = et.exercise_id
            WHERE 1=1
        """
        params = []
        
        if query:
            sql += """ AND (
                LOWER(e.name) LIKE ? OR 
                LOWER(e.latex) LIKE ? OR
                LOWER(e.keycode) LIKE ? OR
                LOWER(k.keyword) LIKE ?
            )"""
            search_term = f"%{query.lower()}%"
            params.extend([search_term, search_term, search_term, search_term])
        
        if level:
            sql += " AND e.level = ?"
            params.append(level)
        
        if topic_ids:
            placeholders = ','.join('?' * len(topic_ids))
            sql += f" AND et.topic_id IN ({placeholders})"
            params.extend(topic_ids)
        
        sql += " ORDER BY e.creation_date DESC"
        
        cursor.execute(sql, params)
        return cursor.fetchall()
    
    def get_all_levels(self) -> List[str]:
        """Get list of all unique levels in the database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT level FROM exercises WHERE level IS NOT NULL ORDER BY level")
        return [row[0] for row in cursor.fetchall()]
    
    def get_topic_path(self, topic_id: int) -> List[str]:
        """Get full path of topic names from root to specified topic."""
        cursor = self.conn.cursor()
        path = []
        
        current_id = topic_id
        while current_id is not None:
            cursor.execute("SELECT name, parent_id FROM topics WHERE id = ?", (current_id,))
            result = cursor.fetchone()
            if not result:
                break
            name, parent_id = result
            path.insert(0, name)
            current_id = parent_id
        
        return path
    
    def get_statistics(self) -> Dict:
        """Get database statistics."""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM exercises")
        total_exercises = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM exercises WHERE solution IS NOT NULL AND solution != ''")
        with_solutions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM topics WHERE parent_id IS NULL")
        main_topics = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM topics")
        total_topics = cursor.fetchone()[0]
        
        stats = {
            'total_exercises': total_exercises,
            'with_solutions': with_solutions,
            'without_solutions': total_exercises - with_solutions,
            'main_topics': main_topics,
            'total_topics': total_topics,
            'levels': self.get_all_levels()
        }
        
        return stats
        
    def add_topic(self, name: str, parent_id: Optional[int] = None) -> int:
        """Add a new topic."""
        cursor = self.conn.cursor()
        
        # Get the next order_index
        if parent_id is None:
            cursor.execute("SELECT COALESCE(MAX(order_index), -1) + 1 FROM topics WHERE parent_id IS NULL")
        else:
            cursor.execute("SELECT COALESCE(MAX(order_index), -1) + 1 FROM topics WHERE parent_id = ?", (parent_id,))
        
        order_index = cursor.fetchone()[0]
        
        cursor.execute("""
            INSERT INTO topics (name, parent_id, order_index)
            VALUES (?, ?, ?)
        """, (name, parent_id, order_index))
        
        self.conn.commit()
        return cursor.lastrowid

    def rename_topic(self, topic_id: int, new_name: str):
        """Rename a topic."""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE topics SET name = ? WHERE id = ?", (new_name, topic_id))
        self.conn.commit()

    def delete_topic(self, topic_id: int):
        """Delete a topic and all its children."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
        self.conn.commit()

    def get_topic_info(self, topic_id: int) -> Optional[Tuple]:
        """Get topic information (id, name, parent_id, order_index)."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, name, parent_id, order_index 
            FROM topics 
            WHERE id = ?
        """, (topic_id,))
        return cursor.fetchone()

    def change_topic_parent(self, topic_id: int, new_parent_id: Optional[int]):
        """Change the parent of a topic."""
        cursor = self.conn.cursor()
        
        # Get the next order_index for the new parent
        if new_parent_id is None:
            cursor.execute("SELECT COALESCE(MAX(order_index), -1) + 1 FROM topics WHERE parent_id IS NULL")
        else:
            cursor.execute("SELECT COALESCE(MAX(order_index), -1) + 1 FROM topics WHERE parent_id = ?", (new_parent_id,))
        
        new_order_index = cursor.fetchone()[0]
        
        cursor.execute("""
            UPDATE topics 
            SET parent_id = ?, order_index = ? 
            WHERE id = ?
        """, (new_parent_id, new_order_index, topic_id))
        
        self.conn.commit()
        
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            
    def move_topic_up(self, topic_id: int):
        """Move a topic up in the order."""
        cursor = self.conn.cursor()
        
        # Get current topic info
        cursor.execute("SELECT parent_id, order_index FROM topics WHERE id = ?", (topic_id,))
        result = cursor.fetchone()
        if not result:
            return False
        parent_id, current_order = result
        
        if current_order == 0:  # Already at the top
            return False
        
        # Find the previous topic
        cursor.execute("""
            SELECT id, order_index FROM topics 
            WHERE parent_id IS ? AND order_index < ? 
            ORDER BY order_index DESC LIMIT 1
        """, (parent_id, current_order))
        prev_topic = cursor.fetchone()
        
        if prev_topic:
            prev_id, prev_order = prev_topic
            # Swap order indices
            cursor.execute("UPDATE topics SET order_index = ? WHERE id = ?", (prev_order, topic_id))
            cursor.execute("UPDATE topics SET order_index = ? WHERE id = ?", (current_order, prev_id))
            self.conn.commit()
            return True
        return False

    def move_topic_down(self, topic_id: int):
        """Move a topic down in the order."""
        cursor = self.conn.cursor()
        
        # Get current topic info
        cursor.execute("SELECT parent_id, order_index FROM topics WHERE id = ?", (topic_id,))
        result = cursor.fetchone()
        if not result:
            return False
        parent_id, current_order = result
        
        # Find the maximum order for this parent
        cursor.execute("SELECT MAX(order_index) FROM topics WHERE parent_id IS ?", (parent_id,))
        max_order = cursor.fetchone()[0] or 0
        
        if current_order >= max_order:  # Already at the bottom
            return False
        
        # Find the next topic
        cursor.execute("""
            SELECT id, order_index FROM topics 
            WHERE parent_id IS ? AND order_index > ? 
            ORDER BY order_index ASC LIMIT 1
        """, (parent_id, current_order))
        next_topic = cursor.fetchone()
        
        if next_topic:
            next_id, next_order = next_topic
            # Swap order indices
            cursor.execute("UPDATE topics SET order_index = ? WHERE id = ?", (next_order, topic_id))
            cursor.execute("UPDATE topics SET order_index = ? WHERE id = ?", (current_order, next_id))
            self.conn.commit()
            return True
        return False
