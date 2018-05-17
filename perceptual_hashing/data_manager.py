#!/usr/bin/env python
import sqlite3


################################################################################
class VideoDistance:
    ############################################################################
    def __init__(self, a, b, method, distance):
        self.a = a
        self.b = b
        self.method = method
        self.distance = distance
        return

    def __eq__(self, other):
        return (self.a == other.a and
                self.b == other.b and
                self.method == other.method and
                self.distance == other.distance)

    def __repr__(self):
        return 'VideoDistance({}, {}, {}, {})'.format(self.a,
                                                      self.b,
                                                      self.method,
                                                      self.distance)

    def __str__(self):
        return repr(self)


################################################################################
class Hash:
    ############################################################################
    def __init__(self, method, value, method_id=None):
        self._id = method_id
        self._name = method
        self._value = value
        return

    ############################################################################
    @property
    def id(self):
        return self._id

    ############################################################################
    @property
    def method(self):
        return self._name

    ############################################################################
    @property
    def value(self):
        return self._value

    ############################################################################
    def __repr__(self):
        return 'Hash(\'{}\', \'{}\', {})'.format(self._name, self._value,
                                                 self._id)

    ############################################################################
    def __str__(self):
        return repr(self)

    ############################################################################
    def __eq__(self, other):
        if isinstance(other, Hash):
            return self._name == other._name and self._value == other._value
        else:
            return self._value == other


################################################################################
class Video:
    ############################################################################
    def __init__(self, name, fmt, video_id=None, hash_values=None):
        self._id = video_id
        self._name = name
        self._fmt = fmt
        self._hash_values = hash_values
        return

    ############################################################################
    @property
    def id(self):
        return self._id

    ############################################################################
    @property
    def name(self):
        return self._name

    ############################################################################
    @property
    def format(self):
        return self._fmt

    ############################################################################
    @property
    def hash_values(self):
        if self._hash_values is None:
            self._hash_values = {}
        return self._hash_values

    ############################################################################
    def __hash__(self):
        return hash((self._id, self._name, self._fmt,
                    hash(tuple(self._hash_values.keys()))))

    ############################################################################
    def __repr__(self):
        return 'Video({}, {}, video_id={}, hash_value={})'.format(
                self._name, self._fmt, self._id, self._hash_values)

    ############################################################################
    def __str__(self):
        return '{}.{}: {}'.format(self._name, self._fmt, self._hash_values)

    ############################################################################
    def __eq__(self, other):
        return (self._id == other._id
                and self._name == other._name
                and self._fmt == other._fmt
                and self._hash_values == other._hash_values)

    ############################################################################
    def __lt__(self, other):
        return (self._name < other._name
                or (self._name == other._name and self._fmt < other._fmt))


################################################################################
class VideoSet:
    ############################################################################
    def __init__(self, set_id=None, videos=None):
        self._id = set_id
        self._videos = videos
        return

    ############################################################################
    @property
    def videos(self):
        return set(self._videos)

    ############################################################################
    @property
    def id(self):
        return self._id

    ############################################################################
    def __eq__(self, other):
        return self._id == other._id and self._videos == other._videos

    ############################################################################
    def __repr__(self):
        return 'VideoSet({}, {})'.format(self.id, str(self.videos))

    ############################################################################
    def __str__(self):
        return repr(self)


################################################################################
class DAO:
    ############################################################################
    def __init__(self, connection):
        self._c = connection
        return


################################################################################
class HashDAO(DAO):
    ############################################################################
    def get_hash_method_by_name(self, hash_method_name, commit=True):
        c = self._c.cursor()
        c.execute('''
            SELECT id
            FROM hash_methods
            WHERE name = ?
            ''', [hash_method_name])
        hash_method_id = c.fetchone()
        if hash_method_id is None:
            c.execute('''
                INSERT INTO hash_methods (name)
                VALUES (?)
                ''', [hash_method_name])
            c.execute('''
                SELECT id
                FROM hash_methods
                ORDER BY id DESC
                LIMIT 1
                ''')
            hash_method_id = c.fetchone()
            if commit:
                self._c.commit()
        return hash_method_id[0]

    ############################################################################
    def get_video_hashes(self, video_id):
        get_hashes_sql = '''
            SELECT h.name, ch.hash_value, h.id
            FROM computed_hashes ch
            INNER JOIN hash_methods h
            ON ch.hash_method_id = h.id
            LEFT JOIN video_info v
            ON v.id = ch.video_id
            WHERE v.id = ?
            '''
        c = self._c.cursor()
        c.execute(get_hashes_sql, [video_id])
        return {v[0]: Hash(*v) for v in c.fetchall()}

    ############################################################################
    def get_method_accuracy(self, method_id):
        getsql = '''
            SELECT accuracy
            ,threshold
            ,true_positives
            ,true_negatives
            ,false_positives
            ,false_negatives
            FROM hash_methods
            WHERE id = ?
        '''

        c = self._c.cursor()
        c.execute(getsql, [method_id])
        v = c.fetchone()
        if v is not None:
            return dict(zip(['accuracy', 'threshold', 'true_positives',
                             'true_negatives', 'false_positives',
                             'false_negatives'], v))
        return None

    ############################################################################
    def set_method_accuracy(self, method_id, details, force=False):
        best = self.get_method_accuracy(method_id)
        if (best is not None and best['accuracy'] is not None
                and best['accuracy'] > details['accuracy']
                and not force):
            return

        updatesql = '''
            UPDATE hash_methods
            SET accuracy = ?
            ,threshold = ?
            ,true_positives = ?
            ,true_negatives = ?
            ,false_positives = ?
            ,false_negatives = ?
            WHERE id = ?
        '''

        c = self._c.cursor()
        c.execute(updatesql, [details['accuracy'], details['threshold'],
                              details['true_positives'],
                              details['true_negatives'],
                              details['false_positives'],
                              details['false_negatives'],
                              method_id])
        self._c.commit()
        return

    ############################################################################
    def add_video_hashes(self, video, old_video, commit=True):
        insert_video_hash_sql = '''
            INSERT INTO computed_hashes (video_id, hash_method_id, hash_value)
            VALUES (?,?,?)
            '''

        update_video_hash_sql = '''
            UPDATE computed_hashes
            SET hash_value = ?
            WHERE hash_method_id = ? AND video_id = ?
            '''

        if video.id is None:
            raise RuntimeError('video must be in db')

        if old_video is None:
            old_video = Video('none', 'none')

        new_hash_upserts = []
        for hash_method, hash_value in video.hash_values.items():
            if hash_method not in old_video.hash_values:
                new_hash_upserts.append((insert_video_hash_sql,
                                         hash_method, hash_value))
            elif hash_value != old_video.hash_values[hash_method]:
                new_hash_upserts.append((update_video_hash_sql,
                                         hash_method, hash_value))

        c = self._c.cursor()
        for q, hash_method, hash_value in new_hash_upserts:
            hash_id = hash_value.id
            if hash_id is None:
                hash_id = self.get_hash_method_by_name(hash_method, False)
            c.execute(q, [video.id, hash_id, str(hash_value.value)])

        if commit:
            self._c.commit()
        hash_values = {}
        hash_values.update(old_video.hash_values)
        hash_values.update(video.hash_values)

        return Video(video.name, video.format,
                     video_id=video.id, hash_values=hash_values)


################################################################################
class VideoDAO(DAO):
    ############################################################################
    def __init__(self, connection, hashdao):
        super().__init__(connection)
        self._hashdao = hashdao
        return

    ############################################################################
    def _video(self, row):
        if row is not None:
            video_id, video_name, fmt = row
            hashes = self._hashdao.get_video_hashes(video_id)
            return Video(video_name, fmt, video_id=video_id, hash_values=hashes)
        return None

    ############################################################################
    def _video_id(self, video):
        if video.id is not None:
            return video.id
        else:
            v = self.videos_by_name(video.name, video.format)
            if v and len(v) == 1 and v[0].id:
                return v[0].id
        raise RuntimeError("Cannot find video id")

    ############################################################################
    def video_by_id(self, video_id):
        if video_id is None:
            return None
        get_video_by_id_sql = '''
            SELECT v.id, v.video_name, v.format
            FROM video_info v
            WHERE v.id = ?
            '''
        c = self._c.cursor()
        c.execute(get_video_by_id_sql, [video_id])
        return self._video(c.fetchone())

    ############################################################################
    def all_videos(self):
        sql = '''
        SELECT id
        FROM video_info
        '''
        c = self._c.cursor()
        c.execute(sql)

        return [self.video_by_id(v[0]) for v in c.fetchall()]

    ############################################################################
    def videos_by_name(self, video_name, fmt=None):
        search = [video_name]
        get_video_by_name_sql = '''
            SELECT v.id, v.video_name, v.format
            FROM video_info v
            WHERE v.video_name = ?
            '''

        if fmt is not None:
            get_video_by_name_sql += '''
            AND v.format = ?
            '''
            search.append(fmt)

        c = self._c.cursor()
        c.execute(get_video_by_name_sql, search)
        return [self._video(v) for v in c.fetchall()]

    ############################################################################
    def video_by_name_and_format(self, video_name, fmt):
        videos = self.videos_by_name(video_name, fmt)
        if videos is not None and len(videos) > 0:
            return videos[0]
        return None

    ############################################################################
    def add_video_hashes(self, video, commit=True):
        if video.id is None:
            return self.add_video(video, commit)
        old_video = self.video_by_id(video.id)
        return self._hashdao.add_video_hashes(video, old_video, commit)

    ############################################################################
    def add_video_if_new(self, video, commit=True):
        if video.id is not None:
            return video
        v = self.video_by_name_and_format(video.name, video.format)
        if v is not None:
            return v
        return self.add_video(video, commit)

    ############################################################################
    def add_video(self, video, commit=True):
        add_video_info_sql = '''
            INSERT INTO video_info (video_name, format)
            VALUES (?,?)
            '''
        c = self._c.cursor()
        c.execute(add_video_info_sql, [video.name, video.format])
        v = self.videos_by_name(video.name, video.format)[0]
        old_video = self.video_by_id(video.id)
        self._hashdao.add_video_hashes(v, old_video, commit=False)

        if commit:
            self._c.commit()
        return self.video_by_id(v.id)


################################################################################
class VideoSetDAO(DAO):
    ############################################################################
    def __init__(self, connection, video_dao):
        super().__init__(connection)
        self._video_dao = video_dao
        return

    ############################################################################
    def get_video_set_by_video_id(self, video):
        if video.id is None:
            return None

        video_set_from_video_name_sql = '''
            SELECT set_id
            FROM video_set_memberships s
            INNER JOIN video_info v
            ON v.id = s.video_id
            WHERE v.id = ?
            '''
        cur = self._c.cursor()
        cur.execute(video_set_from_video_name_sql, [video.id])
        set_id = cur.fetchone()
        if set_id is not None:
            return self.get_video_set_by_id(set_id[0])
        return None

    ############################################################################
    def get_video_all_sets(self):
        sql = '''
        SELECT id
        FROM video_sets
        '''
        c = self._c.cursor()
        c.execute(sql)

        return [self.get_video_set_by_id(v[0]) for v in c.fetchall()]

    ############################################################################
    def get_video_set(self, video):
        if video.id is not None:
            return self.get_video_set_by_video_id(video)

        video_set_from_video_name_sql = '''
            SELECT set_id
            FROM video_set_memberships s
            INNER JOIN video_info v
            ON v.id = s.video_id
            WHERE v.video_name = ?
            AND v.video_fmt = ?
            '''
        cur = self._c.cursor()
        cur.execute(video_set_from_video_name_sql, [video.name, video.format])
        set_id = cur.fetchone()
        if set_id is not None:
            return self.get_video_set_by_id(set_id[0])
        return None

    ############################################################################
    def get_video_set_by_id(self, set_id):
        video_set_sql = '''
            SELECT v.id
            FROM video_set_memberships sm
            LEFT JOIN video_info v
            ON v.id = sm.video_id
            INNER JOIN video_sets s
            ON s.id = sm.set_id
            WHERE s.id = ?
            '''
        cur = self._c.cursor()
        cur.execute(video_set_sql, [set_id])
        videos = [self._video_dao.video_by_id(r[0]) for r in cur.fetchall()]
        return VideoSet(set_id, set(videos))

    ############################################################################
    def create_video_set(self, commit=True):
        c = self._c.cursor()
        c.execute('''
        INSERT INTO video_sets (number_of_videos)
        VALUES (0)
        ''')
        c.execute('''
        SELECT id
        FROM video_sets
        ORDER BY id DESC
        LIMIT 1
        ''')

        set_id = c.fetchone()[0]
        v = VideoSet(set_id=set_id, videos=set([]))
        if commit:
            self._c.commit()
        return v

    ############################################################################
    def add_video_to_set(self, video, video_set=None, commit=True):
        if video.id is None:
            video = self._video_dao.add_video(video)

        if video_set is None:
            video_set = self.get_video_set(video)

        if video_set is None:
            video_set = self.create_video_set(False)

        if video in video_set.videos:
            return video_set

        c = self._c.cursor()
        c.execute('''INSERT INTO video_set_memberships (set_id, video_id)
                     VALUES (?,?)
                  ''', [video_set.id, video.id])

        if commit:
            self._c.commit()
        return VideoSet(video_set.id, video_set.videos.union(set([video])))


################################################################################
class VideoDistanceDAO(DAO):
    ############################################################################
    def add_distance(self, distance, commit=True):
        rmsql = '''
        DELETE FROM video_distances
        WHERE a = ? AND b = ? AND method = ?
        '''
        sql = '''
        INSERT INTO video_distances (a, b, method, distance)
        VALUES (?,?,?,?)
        '''
        c = self._c.cursor()
        c.execute(rmsql, [distance.a.id, distance.b.id, distance.method])
        c.execute(sql, [distance.a.id, distance.b.id,
                        distance.method, distance.distance])
        if commit:
            self._c.commit()
        return

    ############################################################################
    def get_distance(self, method, video1, video2):
        sql = '''
        SELECT distance
        FROM video_distances
        WHERE a = ? AND b = ? AND method = ?
        '''
        c = self._c.cursor()
        c.execute(sql, [video1.id, video2.id, method])
        v = c.fetchone()
        if v is not None:
            return VideoDistance(video1, video2, method, v[0])
        c.execute(sql, [video2.id, video1.id, method])
        v = c.fetchone()
        if v is not None:
            return VideoDistance(video2, video1, method, v[0])
        return None


################################################################################
class VideoDataManager:
    ############################################################################
    def __init__(self, path='videohash.db'):
        self.path = path
        self.conn = sqlite3.connect(path)
        self._create_schema()
        return

    ############################################################################
    @property
    def hash_dao(self):
        return HashDAO(self.conn)

    ############################################################################
    @property
    def video_dao(self):
        return VideoDAO(self.conn, self.hash_dao)

    ############################################################################
    @property
    def videoset_dao(self):
        return VideoSetDAO(self.conn, self.video_dao)

    ############################################################################
    @property
    def distance_dao(self):
        return VideoDistanceDAO(self.conn)

    ############################################################################
    def _create_schema(self):
        c = self.conn
        c.execute('''
        PRAGMA foreign_keys = ON
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS video_info
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_name TEXT NOT NULL,
            format VARCHAR(5) NOT NULL,
            date_added DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(video_name, format)
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS video_distances
        (
            a INTEGER NOT NULL,
            b INTEGER NOT NULL,
            method INTEGER NOT NULL,
            distance INTEGER(8) NOT NULL,
            date_added DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (a, b, method)
            FOREIGN KEY (a) REFERENCES video_info(id) ON DELETE CASCADE,
            FOREIGN KEY (b) REFERENCES video_info(id) ON DELETE CASCADE,
            FOREIGN KEY (method) REFERENCES hash_methods(id) ON DELETE CASCADE,
            CHECK (a != b)
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS video_sets
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number_of_videos INTEGER NOT NULL
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS video_set_memberships
        (
            set_id INTEGER(8) NOT NULL,
            video_id INTEGER(8) NOT NULL,
            PRIMARY KEY(set_id, video_id)
            FOREIGN KEY(video_id) REFERENCES video_info(id) ON DELETE CASCADE,
            FOREIGN KEY(set_id) REFERENCES video_sets(id) ON DELETE CASCADE
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS hash_methods
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            accuracy REAL,
            threshold REAL,
            true_positives INTEGER,
            true_negatives INTEGER,
            false_positives INTEGER,
            false_negatives INTEGER
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS computed_hashes
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id INTEGER(8) NOT NULL,
            hash_method_id INTEGER NOT NULL,
            hash_value TEXT,
            UNIQUE(video_id, hash_method_id),
            FOREIGN KEY(video_id) REFERENCES video_info(id) ON DELETE CASCADE,
            FOREIGN KEY (hash_method_id) REFERENCES hash_methods(id)
                ON DELETE CASCADE
        )
        ''')

        c.commit()
        return
