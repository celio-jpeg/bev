import asyncio
import logging

import aiopg
import psycopg2
from psycopg2.extras import RealDictCursor

LATEST_BLOCK_NUM = """
SELECT max(block_num) FROM blocks
"""
LOGGER = logging.getLogger(__name__)


class Database(object):
    """Manages connection to the postgres database and makes async queries
    """

    def __init__(self, host, port, name, user, password, loop):
        self._dsn = 'dbname={} user={} password={} host={} port={}'.format(
            name, user, password, host, port)
        self._loop = loop
        self._conn = None

    async def connect(self, retries=5, initial_delay=1, backoff=2):
        """Initializes a connection to the database

        Args:
            retries (int): Number of times to retry the connection
            initial_delay (int): Number of seconds wait between reconnects
            backoff (int): Multiplies the delay after each retry
        """
        LOGGER.info('Connecting to database')

        delay = initial_delay
        for attempt in range(retries):
            try:
                self._conn = await aiopg.connect(
                    dsn=self._dsn, loop=self._loop, echo=True)
                LOGGER.info('Successfully connected to database')
                return

            except psycopg2.OperationalError:
                LOGGER.debug(
                    'Connection failed.'
                    ' Retrying connection (%s retries remaining)',
                    retries - attempt)
                await asyncio.sleep(delay)
                delay *= backoff

        self._conn = await aiopg.connect(
            dsn=self._dsn, loop=self._loop, echo=True)
        LOGGER.info('Successfully connected to database')

    def disconnect(self):
        """Closes connection to the database
        """
        self._conn.close()

    async def fetch_current_elections_resources(self, voter_id, timestamp):
        fetch_elections = """
                SELECT e.*,v.name AS "admin_name",(SELECT vote_id FROM votes WHERE voter_id='{0}'
                    AND election_id=e.election_id LIMIT 1)
                    IS NOT NULL AS "voted"
                FROM elections e JOIN voters v ON e.admin_id = v.voter_id
                AND election_id IN (SELECT election_id FROM poll_registrations WHERE voter_id='{0}' AND status='1' 
                                    AND ({2}) >= start_block_num AND ({2}) < end_block_num)
                AND start_timestamp <= {1}
                AND end_timestamp >= {1}
                AND e.status = '1'
                AND ({2}) >= e.start_block_num
                AND ({2}) < e.end_block_num
                ORDER BY start_timestamp DESC;
                """.format(voter_id, timestamp, LATEST_BLOCK_NUM)

        async with self._conn.cursor(cursor_factory=RealDictCursor) as cursor:
            await cursor.execute(fetch_elections)
            return await cursor.fetchall()

    async def fetch_past_elections_resources(self, voter_id, timestamp):
        fetch_elections = """
                SELECT e.*,v.name AS "admin_name",(SELECT vote_id FROM votes WHERE voter_id='{0}'
                    AND election_id=e.election_id LIMIT 1)
                    IS NOT NULL AS "voted"
                FROM elections e JOIN voters v ON e.admin_id = v.voter_id
                AND election_id IN (SELECT election_id FROM poll_registrations WHERE voter_id='{0}' AND status='1' 
                                    AND ({2}) >= start_block_num AND ({2}) < end_block_num)
                AND end_timestamp < {1}
                AND e.status = '1'
                AND ({2}) >= e.start_block_num
                AND ({2}) < e.end_block_num
                ORDER BY start_timestamp DESC;
                """.format(voter_id, timestamp, LATEST_BLOCK_NUM)

        async with self._conn.cursor(cursor_factory=RealDictCursor) as cursor:
            await cursor.execute(fetch_elections)
            return await cursor.fetchall()

    async def fetch_public_elections_resources(self, timestamp):
        fetch_elections = """
                SELECT *
                FROM elections
                WHERE start_timestamp <= {0}
                AND end_timestamp >= {0}
                AND status = '1'
                AND results_permission = 'PUBLIC'
                AND ({1}) >= start_block_num
                AND ({1}) < end_block_num
                ORDER BY start_timestamp DESC;
                """.format(timestamp, LATEST_BLOCK_NUM)

        async with self._conn.cursor(cursor_factory=RealDictCursor) as cursor:
            await cursor.execute(fetch_elections)
            return await cursor.fetchall()

    async def fetch_public_past_elections_resources(self, voter_id, timestamp):
        fetch_elections = """
                SELECT e.*,v.name AS "admin_name",(SELECT vote_id FROM votes WHERE voter_id='{0}'
                    AND election_id=e.election_id LIMIT 1)
                    IS NOT NULL AS "voted"
                FROM elections e JOIN voters v ON e.admin_id = v.voter_id
                WHERE e.results_permission = 'PUBLIC'
                AND e.status = '1'
                AND e.end_timestamp < {1}
                AND ({2}) >= e.start_block_num
                AND ({2}) < e.end_block_num
                ORDER BY start_timestamp DESC;
                """.format(voter_id, timestamp, LATEST_BLOCK_NUM)

        async with self._conn.cursor(cursor_factory=RealDictCursor) as cursor:
            await cursor.execute(fetch_elections)
            return await cursor.fetchall()

    async def fetch_admin_elections_resources(self, admin_id):
        fetch_elections = """
                SELECT *
                FROM elections
                WHERE admin_id = '{0}'
                AND ({1}) >= start_block_num
                AND ({1}) < end_block_num
                ORDER BY start_timestamp DESC;
                """.format(admin_id, LATEST_BLOCK_NUM)

        async with self._conn.cursor(cursor_factory=RealDictCursor) as cursor:
            await cursor.execute(fetch_elections)
            return await cursor.fetchall()

    async def fetch_admins_resources(self):
        fetch = """
            SELECT voter_id, name, type
            FROM voters
            WHERE ({0}) >= start_block_num
            AND ({0}) < end_block_num
            AND type = 'ADMIN' OR type = 'SUPERADMIN'
            ORDER BY type DESC;
        """.format(LATEST_BLOCK_NUM)

        async with self._conn.cursor(cursor_factory=RealDictCursor) as cursor:
            await cursor.execute(fetch)
            return await cursor.fetchall()

    async def fetch_voters_resources(self, voter_id=None):
        fetch = """
               SELECT voter_id
               FROM voters
               WHERE type = 'VOTER'
               AND voter_id LIKE '%{0}%'
               AND ({1}) >= start_block_num
               AND ({1}) < end_block_num
               ORDER BY type DESC;
           """.format(voter_id, LATEST_BLOCK_NUM)

        async with self._conn.cursor(cursor_factory=RealDictCursor) as cursor:
            await cursor.execute(fetch)
            return await cursor.fetchall()

    async def insert_voting_option_num_vote_resource(self,
                                                     voting_option_id,
                                                     name,
                                                     election_id):
        num_votes = 0

        insert = """
           INSERT INTO count_votes (
                    voting_option_id,
                    name,
                    election_id,
                    num_votes)
           VALUES ('{}', '{}', '{}', '{}')
           """.format(
            voting_option_id,
            name,
            election_id,
            num_votes)

        async with self._conn.cursor() as cursor:
            await cursor.execute(insert)

        self._conn.commit()

    async def update_voting_option_num_vote_resource(self,
                                                     voting_option_id,
                                                     num_votes):
        update = """
        UPDATE count_votes
        SET num_votes = '{1}'
        WHERE voting_option_id = '{0}'
        """.format(
            voting_option_id,
            num_votes)

        async with self._conn.cursor() as cursor:
            await cursor.execute(update)

        self._conn.commit()

    async def fetch_auth_resource(self, public_key=None):
        fetch = """
        SELECT * FROM auth WHERE public_key='{}'
        """.format(public_key)

        async with self._conn.cursor(cursor_factory=RealDictCursor) as cursor:
            await cursor.execute(fetch)
            return await cursor.fetchone()

    async def fetch_voter_resource(self, voter_id=None, public_key=None):
        fetch = """
        SELECT * FROM voters WHERE """ + ("""voter_id""" if voter_id else """public_key""") + """='{0}'
        AND ({1}) >= start_block_num
        AND ({1}) < end_block_num;
        """.format(voter_id if voter_id else public_key, LATEST_BLOCK_NUM)

        async with self._conn.cursor(cursor_factory=RealDictCursor) as cursor:
            await cursor.execute(fetch)
            return await cursor.fetchone()

    async def is_voter_created(self, voter_id):
        fetch = """
            SELECT voter_id
            FROM voters
            WHERE voter_id = '{0}';
        """.format(voter_id)

        async with self._conn.cursor(cursor_factory=RealDictCursor) as cursor:
            await cursor.execute(fetch)
            return await cursor.fetchone()

    async def is_superadmin_created(self):
        fetch = """
            SELECT voter_id
            FROM voters
            WHERE type='SUPERADMIN'
        """

        async with self._conn.cursor(cursor_factory=RealDictCursor) as cursor:
            await cursor.execute(fetch)
            return await cursor.fetchone()

    async def fetch_election_with_can_vote_resource(self, voter_id=None, election_id=None):
        fetch = """
                    SELECT e.*, v.name AS "admin_name", (SELECT voter_id FROM poll_registrations WHERE voter_id='{0}'
                       AND election_id='{1}' 
                       AND status='1' LIMIT 1) 
                       IS NOT NULL AS "can_vote", (SELECT vote_id FROM votes WHERE voter_id='{0}'
                        AND election_id='{1}' LIMIT 1)
                        IS NOT NULL AS "voted"
                    FROM elections e JOIN voters v ON e.admin_id = v.voter_id
                    WHERE election_id='{1}'
                    AND e.status = '1'
                    AND ({2}) >= e.start_block_num
                    AND ({2}) < e.end_block_num;
                    """.format(voter_id, election_id, LATEST_BLOCK_NUM)

        async with self._conn.cursor(cursor_factory=RealDictCursor) as cursor:
            await cursor.execute(fetch)
            return await cursor.fetchone()

    async def fetch_election_resource(self, election_id=None):
        fetch = """
                 SELECT e.*, v.name AS "admin_name"
                 FROM elections e JOIN voters v ON e.admin_id = v.voter_id
                 WHERE election_id='{0}'
                 AND ({1}) >= e.start_block_num
                 AND ({1}) < e.end_block_num;
                 """.format(election_id, LATEST_BLOCK_NUM)

        async with self._conn.cursor(cursor_factory=RealDictCursor) as cursor:
            await cursor.execute(fetch)
            return await cursor.fetchone()

    async def fetch_election_with_can_vote_resource_admin(self, voter_id=None, election_id=None):
        fetch = """
                    SELECT e.*, v.name AS "admin_name", (SELECT voter_id FROM poll_registrations WHERE voter_id='{0}'
                       AND election_id='{1}' 
                       AND status='1' LIMIT 1) 
                       IS NOT NULL AS "can_vote", (SELECT vote_id FROM votes WHERE voter_id='{0}'
                        AND election_id='{1}' LIMIT 1)
                        IS NOT NULL AS "voted"
                    FROM elections e JOIN voters v ON e.admin_id = v.voter_id
                    WHERE election_id='{1}'
                    AND ({2}) >= e.start_block_num
                    AND ({2}) < e.end_block_num;
                    """.format(voter_id, election_id, LATEST_BLOCK_NUM)

        async with self._conn.cursor(cursor_factory=RealDictCursor) as cursor:
            await cursor.execute(fetch)
            return await cursor.fetchone()

    async def fetch_number_of_votes(self, election_id=None):
        fetch = """
                    SELECT * FROM count_votes
                    WHERE election_id='{0}';
                    """.format(election_id)

        async with self._conn.cursor(cursor_factory=RealDictCursor) as cursor:
            await cursor.execute(fetch)
            return await cursor.fetchall()

    async def fetch_poll_book(self, election_id=None):
        fetch = """
                    SELECT * FROM poll_registrations
                    WHERE election_id='{0}'
                    AND status='1'
                    AND ({1}) >= start_block_num
                    AND ({1}) < end_block_num;
                    """.format(election_id, LATEST_BLOCK_NUM)

        async with self._conn.cursor(cursor_factory=RealDictCursor) as cursor:
            await cursor.execute(fetch)
            return await cursor.fetchall()

    async def fetch_poll_book_registration(self, election_id=None, voter_id=None):
        fetch = """
                       SELECT * FROM poll_registrations
                       WHERE election_id='{0}'
                       AND voter_id='{1}'
                       AND status='1'
                       AND ({2}) >= start_block_num
                       AND ({2}) < end_block_num;
                       """.format(election_id, voter_id, LATEST_BLOCK_NUM)

        async with self._conn.cursor(cursor_factory=RealDictCursor) as cursor:
            await cursor.execute(fetch)
            return await cursor.fetchone()

    async def count_poll_book(self, election_id=None):
        fetch = """
            SELECT COUNT(*)
            FROM poll_registrations
            WHERE election_id='{0}'
            AND status='1'
            AND ({1}) >= start_block_num
            AND ({1}) < end_block_num;
        """.format(election_id, LATEST_BLOCK_NUM)

        async with self._conn.cursor(cursor_factory=RealDictCursor) as cursor:
            await cursor.execute(fetch)
            return await cursor.fetchone()

    async def fetch_voting_option_resource(self, voting_option_id=None):
        fetch = """
           SELECT * FROM voting_options
           WHERE voting_option_id='{0}'
           AND status='1'
           AND ({1}) >= start_block_num
           AND ({1}) < end_block_num;
           """.format(voting_option_id, LATEST_BLOCK_NUM)

        async with self._conn.cursor(cursor_factory=RealDictCursor) as cursor:
            await cursor.execute(fetch)
            return await cursor.fetchone()

    async def fetch_voting_option_num_vote_resource(self, voting_option_id=None):
        fetch = """
              SELECT * FROM count_votes
              WHERE voting_option_id='{0}';
              """.format(voting_option_id)

        async with self._conn.cursor(cursor_factory=RealDictCursor) as cursor:
            await cursor.execute(fetch)
            return await cursor.fetchone()

    async def fetch_election_voting_options_resource(self, election_id=None):
        fetch = """
           SELECT * FROM voting_options
           WHERE election_id='{0}'
           AND status='1'
           AND ({1}) >= start_block_num
           AND ({1}) < end_block_num;
               """.format(election_id, LATEST_BLOCK_NUM)

        async with self._conn.cursor(cursor_factory=RealDictCursor) as cursor:
            await cursor.execute(fetch)
            return await cursor.fetchall()

    async def fetch_vote_resource(self, vote_id=None):
        fetch = """
           SELECT * FROM votes WHERE timestamp=(SELECT MAX(timestamp) FROM votes WHERE vote_id='{0}')
           AND ({1}) >= start_block_num
           AND ({1}) < end_block_num;
           """.format(vote_id, LATEST_BLOCK_NUM)

        async with self._conn.cursor(cursor_factory=RealDictCursor) as cursor:
            await cursor.execute(fetch)
            return await cursor.fetchone()

    async def fetch_my_vote__election_resource(self, voter_id=None, election_id=None):
        fetch = """
              SELECT * FROM votes WHERE timestamp=(SELECT MAX(timestamp) FROM votes
                                                   WHERE voter_id='{0}' AND election_id='{1}')
              AND ({2}) >= start_block_num
              AND ({2}) < end_block_num;
              """.format(voter_id, election_id, LATEST_BLOCK_NUM)

        async with self._conn.cursor(cursor_factory=RealDictCursor) as cursor:
            await cursor.execute(fetch)
            return await cursor.fetchone()

    async def create_auth_entry(self,
                                public_key,
                                encrypted_private_key,
                                hashed_password):
        insert = """
        INSERT INTO auth (
            public_key,
            encrypted_private_key,
            hashed_password
        )
        VALUES ('{}', '{}', '{}');
        """.format(
            public_key,
            encrypted_private_key.hex(),
            hashed_password.hex())

        async with self._conn.cursor() as cursor:
            await cursor.execute(insert)

        self._conn.commit()

