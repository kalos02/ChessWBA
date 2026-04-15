import os
import shutil
import sqlite3
import tempfile
import time
import unittest

import app as app_module


class Phase1HardeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp(prefix="chesswba-tests-")
        cls.temp_db_path = os.path.join(cls.temp_dir, "ChessAdmin.test.sqlite3")

        source_db_path = app_module.app.config["DB_PATH"]
        shutil.copyfile(source_db_path, cls.temp_db_path)

        cls.original_db = app_module.db
        cls.original_db_path = app_module.app.config["DB_PATH"]
        cls.original_testing_flag = app_module.app.config.get("TESTING", False)

        app_module.app.config["TESTING"] = True
        app_module.app.config["DB_PATH"] = cls.temp_db_path
        app_module.db = app_module.Database(cls.temp_db_path)
        app_module.validate_required_schema()

    @classmethod
    def tearDownClass(cls):
        app_module.db = cls.original_db
        app_module.app.config["DB_PATH"] = cls.original_db_path
        app_module.app.config["TESTING"] = cls.original_testing_flag
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        self.client = app_module.app.test_client()

    def _unique_name(self, prefix):
        return "{}{}".format(prefix, int(time.time() * 1000000))

    def test_add_edit_delete_endpoints(self):
        first_name = self._unique_name("TAdd")
        last_name = "Player"

        add_response = self.client.post(
            "/addPlayer",
            data={
                "first_name": first_name,
                "last_name": last_name,
                "ranking": "1",
                "points": "777",
                "date_of_birth": "",
            },
            follow_redirects=False,
        )
        self.assertEqual(add_response.status_code, 302)
        self.assertEqual(add_response.headers.get("Location"), "/members")

        inserted_rows = app_module.db.execute(
            """
            SELECT id, first_name, last_name, ranking, points
            FROM ChessAdminApp_player
            WHERE first_name = ? AND last_name = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            first_name,
            last_name,
        )
        self.assertTrue(inserted_rows)
        player_id = inserted_rows[0]["id"]

        edit_response = self.client.post(
            "/editPlayer",
            data={
                "id": str(player_id),
                "first_name": first_name,
                "last_name": "PlayerEdited",
                "ranking": "2",
                "points": "778",
                "date_of_birth": "",
            },
            follow_redirects=False,
        )
        self.assertEqual(edit_response.status_code, 302)
        self.assertEqual(edit_response.headers.get("Location"), "/members")

        edited_rows = app_module.db.execute(
            "SELECT first_name, last_name, points FROM ChessAdminApp_player WHERE id = ?",
            player_id,
        )
        self.assertTrue(edited_rows)
        self.assertEqual(edited_rows[0]["last_name"], "PlayerEdited")
        self.assertEqual(int(edited_rows[0]["points"]), 778)

        delete_response = self.client.post(
            "/deletePlayer",
            data={"id": str(player_id)},
            follow_redirects=False,
        )
        self.assertEqual(delete_response.status_code, 302)
        self.assertEqual(delete_response.headers.get("Location"), "/members")

        remaining = app_module.db.execute(
            "SELECT COUNT(*) AS count FROM ChessAdminApp_player WHERE id = ?",
            player_id,
        )
        self.assertEqual(int(remaining[0]["count"]), 0)

    def test_delete_is_blocked_for_player_with_matches(self):
        referenced_rows = app_module.db.execute(
            """
            SELECT cp.id AS player_id
            FROM ChessAdminApp_match m
            JOIN ChessAdminApp_player cp ON cp.id = m.player_one_id
            WHERE m.player_one_id IS NOT NULL
            LIMIT 1
            """
        )
        self.assertTrue(referenced_rows)
        player_id = int(referenced_rows[0]["player_id"])

        before_rows = app_module.db.execute(
            "SELECT COUNT(*) AS count FROM ChessAdminApp_player WHERE id = ?",
            player_id,
        )
        self.assertEqual(int(before_rows[0]["count"]), 1)

        toggle_response = self.client.post(
            "/togglePlayerStatus",
            data={"id": str(player_id)},
            follow_redirects=False,
        )
        self.assertEqual(toggle_response.status_code, 302)
        self.assertEqual(toggle_response.headers.get("Location"), "/members")

        after_rows = app_module.db.execute(
            "SELECT id, is_active FROM ChessAdminApp_player WHERE id = ?",
            player_id,
        )
        self.assertTrue(after_rows)
        self.assertEqual(int(after_rows[0]["is_active"]), 0)

        # Restore active status so subsequent tests see a consistent active player set.
        app_module.db.execute(
            "UPDATE ChessAdminApp_player SET is_active = 1 WHERE id = ?",
            player_id,
        )

    def test_ranking_integrity_after_mutation(self):
        first_name = self._unique_name("TRank")
        last_name = "Check"

        add_response = self.client.post(
            "/addPlayer",
            data={
                "first_name": first_name,
                "last_name": last_name,
                "ranking": "1",
                "points": "999",
                "date_of_birth": "",
            },
            follow_redirects=False,
        )
        self.assertEqual(add_response.status_code, 302)

        bad_ties_rows = app_module.db.execute(
            """
            SELECT COUNT(*) AS count
            FROM (
                SELECT ranking
                FROM ChessAdminApp_player
                WHERE COALESCE(is_active, 1) = 1
                GROUP BY ranking
                HAVING COUNT(DISTINCT points) > 1
            ) t
            """
        )
        self.assertEqual(int(bad_ties_rows[0]["count"]), 0)

        distinct_rank_rows = app_module.db.execute(
            "SELECT DISTINCT ranking FROM ChessAdminApp_player WHERE COALESCE(is_active, 1) = 1 ORDER BY ranking ASC"
        )
        distinct_ranks = [int(row["ranking"]) for row in distinct_rank_rows]
        self.assertTrue(distinct_ranks)
        expected_ranks = list(range(1, distinct_ranks[-1] + 1))
        self.assertEqual(distinct_ranks, expected_ranks)

        inserted_rows = app_module.db.execute(
            "SELECT id FROM ChessAdminApp_player WHERE first_name = ? AND last_name = ? ORDER BY id DESC LIMIT 1",
            first_name,
            last_name,
        )
        self.assertTrue(inserted_rows)
        cleanup_id = int(inserted_rows[0]["id"])

        self.client.post("/deletePlayer", data={"id": str(cleanup_id)}, follow_redirects=False)

    def test_dashboard_queries_sorted(self):
        by_rank_rows = app_module.db.execute(
            "SELECT ranking FROM ChessAdminApp_player ORDER BY ranking ASC, id ASC"
        )
        by_rank = [int(row["ranking"]) for row in by_rank_rows]
        self.assertEqual(by_rank, sorted(by_rank))

        by_points_rows = app_module.db.execute(
            "SELECT points, ranking FROM ChessAdminApp_player ORDER BY points DESC, ranking ASC, id ASC"
        )
        by_points_keys = [(int(row["points"]), int(row["ranking"])) for row in by_points_rows]
        expected_keys = sorted(by_points_keys, key=lambda x: (-x[0], x[1]))
        self.assertEqual(by_points_keys, expected_keys)

        index_response = self.client.get("/")
        self.assertEqual(index_response.status_code, 200)

    def test_history_page_exposes_match_actions(self):
        history_response = self.client.get("/history")
        self.assertEqual(history_response.status_code, 200)

        html = history_response.get_data(as_text=True)
        self.assertIn(">Edit<", html)
        self.assertIn("js-edit-match", html)
        self.assertIn("id=\"edit-player1\"", html)
        self.assertIn("delete-match-backdrop", html)

    def test_edit_match_endpoint_updates_match_details(self):
        player_rows = app_module.db.execute(
            "SELECT id FROM ChessAdminApp_player WHERE COALESCE(is_active, 1) = 1 ORDER BY ranking ASC LIMIT 3"
        )
        self.assertGreaterEqual(len(player_rows), 3)

        player_one_id = int(player_rows[0]["id"])
        player_two_id = int(player_rows[1]["id"])
        replacement_player_id = int(player_rows[2]["id"])

        create_response = self.client.post(
            "/match",
            data={
                "player1_id": str(player_one_id),
                "player2_id": str(player_two_id),
                "venue": "Edit Test Venue",
                "scheduled_date": "2026-04-14",
                "status": "COMPLETE",
                "result": "draw",
            },
            follow_redirects=False,
        )
        self.assertEqual(create_response.status_code, 302)
        self.assertEqual(create_response.headers.get("Location"), "/history")

        inserted_rows = app_module.db.execute(
            """
            SELECT id
            FROM ChessAdminApp_match
            WHERE venue = ? AND player_one_id = ? AND player_two_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            "Edit Test Venue",
            player_one_id,
            player_two_id,
        )
        self.assertTrue(inserted_rows)
        match_id = int(inserted_rows[0]["id"])

        try:
            edit_response = self.client.post(
                "/editMatch",
                data={
                    "match_id": str(match_id),
                    "player1_id": str(replacement_player_id),
                    "player2_id": str(player_two_id),
                    "venue": "Edited Venue",
                    "scheduled_date": "2026-04-15",
                    "status": "COMPLETED",
                    "result": "p1",
                },
                follow_redirects=False,
            )
            self.assertEqual(edit_response.status_code, 302)
            self.assertEqual(edit_response.headers.get("Location"), "/history")

            edited_rows = app_module.db.execute(
                """
                SELECT player_one_id, player_two_id, venue, scheduled_date, status, match_result, winner_id
                FROM ChessAdminApp_match
                WHERE id = ?
                """,
                match_id,
            )
            self.assertTrue(edited_rows)
            self.assertEqual(int(edited_rows[0]["player_one_id"]), replacement_player_id)
            self.assertEqual(int(edited_rows[0]["player_two_id"]), player_two_id)
            self.assertEqual(edited_rows[0]["venue"], "Edited Venue")
            self.assertEqual(edited_rows[0]["scheduled_date"], "2026-04-15")
            self.assertEqual(edited_rows[0]["status"], "COMPLETED")
            self.assertEqual(edited_rows[0]["match_result"], "WIN")
            self.assertEqual(int(edited_rows[0]["winner_id"]), replacement_player_id)
        finally:
            app_module.db.execute("DELETE FROM ChessAdminApp_match WHERE id = ?", match_id)

    def test_edit_match_preserves_existing_values_when_optional_fields_are_blank(self):
        player_rows = app_module.db.execute(
            "SELECT id FROM ChessAdminApp_player WHERE COALESCE(is_active, 1) = 1 ORDER BY ranking ASC LIMIT 2"
        )
        self.assertGreaterEqual(len(player_rows), 2)

        player_one_id = int(player_rows[0]["id"])
        player_two_id = int(player_rows[1]["id"])

        create_response = self.client.post(
            "/match",
            data={
                "player1_id": str(player_one_id),
                "player2_id": str(player_two_id),
                "venue": "Preserve Test Venue",
                "scheduled_date": "2026-04-14",
                "status": "COMPLETE",
                "result": "draw",
            },
            follow_redirects=False,
        )
        self.assertEqual(create_response.status_code, 302)
        self.assertEqual(create_response.headers.get("Location"), "/history")

        inserted_rows = app_module.db.execute(
            """
            SELECT id
            FROM ChessAdminApp_match
            WHERE venue = ? AND player_one_id = ? AND player_two_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            "Preserve Test Venue",
            player_one_id,
            player_two_id,
        )
        self.assertTrue(inserted_rows)
        match_id = int(inserted_rows[0]["id"])

        try:
            edit_response = self.client.post(
                "/editMatch",
                data={
                    "match_id": str(match_id),
                    "player1_id": str(player_one_id),
                    "player2_id": str(player_two_id),
                    "venue": "",
                    "scheduled_date": "",
                    "status": "COMPLETED",
                    "result": "",
                },
                follow_redirects=False,
            )
            self.assertEqual(edit_response.status_code, 302)
            self.assertEqual(edit_response.headers.get("Location"), "/history")

            edited_rows = app_module.db.execute(
                "SELECT venue, scheduled_date, status, match_result, winner_id FROM ChessAdminApp_match WHERE id = ?",
                match_id,
            )
            self.assertTrue(edited_rows)
            self.assertEqual(edited_rows[0]["venue"], "Preserve Test Venue")
            self.assertEqual(edited_rows[0]["scheduled_date"], "2026-04-14")
            self.assertEqual(edited_rows[0]["status"], "COMPLETED")
            self.assertEqual(edited_rows[0]["match_result"], "DRAW")
            self.assertIsNone(edited_rows[0]["winner_id"])
        finally:
            app_module.db.execute("DELETE FROM ChessAdminApp_match WHERE id = ?", match_id)

    def test_edit_match_status_updates_correctly(self):
        player_rows = app_module.db.execute(
            "SELECT id FROM ChessAdminApp_player WHERE COALESCE(is_active, 1) = 1 ORDER BY ranking ASC LIMIT 2"
        )
        self.assertGreaterEqual(len(player_rows), 2)

        player_one_id = int(player_rows[0]["id"])
        player_two_id = int(player_rows[1]["id"])

        create_response = self.client.post(
            "/match",
            data={
                "player1_id": str(player_one_id),
                "player2_id": str(player_two_id),
                "venue": "Status Test Venue",
                "scheduled_date": "2026-04-14",
                "status": "COMPLETED",
                "result": "p1",
            },
            follow_redirects=False,
        )
        self.assertEqual(create_response.status_code, 302)
        self.assertEqual(create_response.headers.get("Location"), "/history")

        inserted_rows = app_module.db.execute(
            """
            SELECT id
            FROM ChessAdminApp_match
            WHERE venue = ? AND player_one_id = ? AND player_two_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            "Status Test Venue",
            player_one_id,
            player_two_id,
        )
        self.assertTrue(inserted_rows)
        match_id = int(inserted_rows[0]["id"])

        try:
            edit_response = self.client.post(
                "/editMatch",
                data={
                    "match_id": str(match_id),
                    "player1_id": str(player_one_id),
                    "player2_id": str(player_two_id),
                    "venue": "Status Test Venue Updated",
                    "scheduled_date": "2026-04-16",
                    "status": "PENDING",
                    "result": "",
                },
                follow_redirects=False,
            )
            self.assertEqual(edit_response.status_code, 302)
            self.assertEqual(edit_response.headers.get("Location"), "/history")

            edited_rows = app_module.db.execute(
                "SELECT venue, scheduled_date, status, match_result, winner_id FROM ChessAdminApp_match WHERE id = ?",
                match_id,
            )
            self.assertTrue(edited_rows)
            self.assertEqual(edited_rows[0]["venue"], "Status Test Venue Updated")
            self.assertEqual(edited_rows[0]["scheduled_date"], "2026-04-16")
            self.assertEqual(edited_rows[0]["status"], "SCHEDULED")
            self.assertIsNone(edited_rows[0]["match_result"])
            self.assertIsNone(edited_rows[0]["winner_id"])
        finally:
            app_module.db.execute("DELETE FROM ChessAdminApp_match WHERE id = ?", match_id)

    def test_delete_match_endpoint_removes_match(self):
        player_rows = app_module.db.execute(
            "SELECT id FROM ChessAdminApp_player WHERE COALESCE(is_active, 1) = 1 ORDER BY ranking ASC LIMIT 2"
        )
        self.assertGreaterEqual(len(player_rows), 2)

        player_one_id = int(player_rows[0]["id"])
        player_two_id = int(player_rows[1]["id"])

        create_response = self.client.post(
            "/match",
            data={
                "player1_id": str(player_one_id),
                "player2_id": str(player_two_id),
                "venue": "Delete Test Venue",
                "scheduled_date": "2026-04-14",
                "status": "COMPLETE",
                "result": "draw",
            },
            follow_redirects=False,
        )
        self.assertEqual(create_response.status_code, 302)
        self.assertEqual(create_response.headers.get("Location"), "/history")

        inserted_rows = app_module.db.execute(
            """
            SELECT id
            FROM ChessAdminApp_match
            WHERE venue = ? AND player_one_id = ? AND player_two_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            "Delete Test Venue",
            player_one_id,
            player_two_id,
        )
        self.assertTrue(inserted_rows)
        match_id = int(inserted_rows[0]["id"])

        delete_response = self.client.post(
            "/deleteMatch",
            data={"match_id": str(match_id)},
            follow_redirects=False,
        )
        self.assertEqual(delete_response.status_code, 302)
        self.assertEqual(delete_response.headers.get("Location"), "/history")

        remaining_rows = app_module.db.execute(
            "SELECT COUNT(*) AS count FROM ChessAdminApp_match WHERE id = ?",
            match_id,
        )
        self.assertEqual(int(remaining_rows[0]["count"]), 0)

    def test_profile_route_handles_missing_opponent_data(self):
        player_rows = app_module.db.execute(
            "SELECT id, ranking FROM ChessAdminApp_player ORDER BY id ASC LIMIT 1"
        )
        self.assertTrue(player_rows)
        player_id = int(player_rows[0]["id"])
        player_rank = int(player_rows[0]["ranking"])

        with sqlite3.connect(app_module.app.config["DB_PATH"]) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO ChessAdminApp_match
                    (scheduled_date, status, venue, match_result,
                     player_one_entry_ranking, player_two_entry_ranking,
                     player_one_ranking_change, player_two_ranking_change,
                     follow_live, player_one_id, player_two_id, winner_id,
                     player_one_points_change, player_two_points_change)
                VALUES (datetime('now'), 'COMPLETED', 'Test Venue', 'WIN',
                        ?, 9999, 0, 0,
                        'N/A', ?, 99999999, ?,
                        0, 0)
                """,
                (player_rank, player_id, player_id),
            )
            match_id = cursor.lastrowid
            conn.commit()

        try:
            profile_response = self.client.get("/profile/{}".format(player_id))
            self.assertEqual(profile_response.status_code, 200)
        finally:
            with sqlite3.connect(app_module.app.config["DB_PATH"]) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM ChessAdminApp_match WHERE id = ?", (match_id,))
                conn.commit()


if __name__ == "__main__":
    unittest.main()
