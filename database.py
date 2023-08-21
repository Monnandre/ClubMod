import sqlite3
from datetime import datetime, timezone

class DatabaseQuery:
    def __init__(self):
        self.conn = sqlite3.connect('clubs.db')
        self.cursor = self.conn.cursor()

        self.setup()

    def setup(self):
        # Create the 'clubs' table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS clubs (
                club_id TEXT NOT NULL
            )
        ''')

        # Create the 'members' table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS members (
                member_id TEXT NOT NULL,
                club_id TEXT NOT NULL,
                joins INTEGER,
                join_date TEXT NOT NULL,
                in_club INTEGER,
                tickets_played_all INTEGER,
                trophies_gained_all INTEGER,
                tickets_played_week INTEGER,
                tickets_week_id INTEGER,
                trophies_gained_week INTEGER,
                tickets_played_today INTEGER,
                tickets_day_id INTEGER,
                trophies_gained_today INTEGER,
                last_checked_combat TEXT NOT NULL,
                FOREIGN KEY (club_id) REFERENCES clubs (club_id)
            )
        ''')
        self.conn.commit()

    def is_club_in_database(self, club_id):
        # Check if the club already exists in the clubs table
        self.cursor.execute('''
            SELECT club_id
            FROM clubs
            WHERE club_id = ?
        ''', (club_id,))

        existing_club = self.cursor.fetchone()
        return existing_club

    def register_club(self, club_id):
        # Register the club only if it doesn't exist
        self.cursor.execute('''
            INSERT INTO clubs (club_id)
            VALUES (?)
        ''', (club_id,))
        self.conn.commit()

    def clear_club(self, club_id):
        # Delete club's members first
        self.cursor.execute('''
            DELETE FROM members
            WHERE club_id = ?
        ''', (club_id,))

        # Delete the club itself
        self.cursor.execute('''
            DELETE FROM clubs
            WHERE club_id = ?
        ''', (club_id,))

        self.conn.commit()

    def get_all_club_ids(self):
        self.cursor.execute('''
            SELECT club_id
            FROM clubs
        ''')

        club_ids = self.cursor.fetchall()
        return [club_id[0] for club_id in club_ids]

    def register_member(self, club_id, member_id):
        joins = 1
        # Check if the member already exists in the members table
        self.cursor.execute('''
            SELECT joins
            FROM members
            WHERE club_id = ? AND member_id = ?
        ''', (club_id, member_id))

        existing_member = self.cursor.fetchone()

        if existing_member:
            current_joins = existing_member[0]
            updated_joins = current_joins + 1
            joins = updated_joins
            self.cursor.execute('''
                UPDATE members
                SET joins = ?, join_date = ?, in_club = 1
                WHERE club_id = ? AND member_id = ?
            ''', (updated_joins, self.get_current_date_utc(), club_id, member_id))
        else:
            self.cursor.execute('''
                INSERT INTO members (club_id, member_id, joins, join_date, in_club, tickets_played_all, tickets_played_week, tickets_week_id, tickets_played_today, tickets_day_id, last_checked_combat, trophies_gained_all, trophies_gained_week, trophies_gained_today)
                VALUES (?, ?, 1, ?, 1, 0, 0, 0, 0, 0, "0", 0, 0, 0)
            ''', (club_id, member_id, self.get_current_date_utc()))

        self.conn.commit()
        return joins

    def retrive_club_members(self, club_id):
        self.cursor.execute('''
            SELECT member_id
            FROM members
            WHERE club_id = ? AND in_club = 1
        ''', (club_id,))

        return [member[0] for member in self.cursor.fetchall()]

    def get_all_clubs_members(self):
        self.cursor.execute('''
            SELECT member_id
            FROM members
            WHERE in_club = 1
        ''')

        return [member[0] for member in self.cursor.fetchall()]

    def retrive_member_join_infos(self, member_id):
        self.cursor.execute('''
            SELECT joins, join_date, in_club
            FROM members
            WHERE member_id = ?
        ''', (member_id,))

        return self.cursor.fetchone()

    def retrive_member_ligue_infos(self, member_id):
        self.cursor.execute('''
            SELECT in_club, tickets_played_all, tickets_played_week, tickets_week_id, tickets_played_today, tickets_day_id, last_checked_combat
            FROM members
            WHERE member_id = ?
        ''', (member_id,))

        return self.cursor.fetchone()

    def update_member_ligue_infos(self, member_id, tickets_played_all, tickets_played_week, tickets_week_id, tickets_played_today, tickets_day_id, last_checked_combat):
        self.cursor.execute('''
            UPDATE members
            SET tickets_played_all = ?, tickets_played_week = ?, tickets_week_id = ?, tickets_played_today = ?, tickets_day_id = ?, last_checked_combat = ?
            WHERE member_id = ?
        ''', (tickets_played_all, tickets_played_week, tickets_week_id, tickets_played_today, tickets_day_id, last_checked_combat, member_id))
        self.conn.commit()

    def on_member_quit(self, club_id, member_id):
        self.cursor.execute('''
            UPDATE members
            SET in_club = 0
            WHERE club_id = ? AND member_id = ?
        ''', (club_id, member_id))
        self.conn.commit()

    def get_current_date_utc(self):
        utc_datetime = datetime.now(timezone.utc)
        return utc_datetime.strftime('%Y-%m-%d')

if __name__ == "__main__":
    db = DatabaseQuery()
    db.clear_club("j0rv0ppg")