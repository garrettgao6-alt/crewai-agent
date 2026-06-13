import subscription_store


def test_load_and_save_usage_records_current_period_events(tmp_path):
    original_db_path = subscription_store.DB_PATH
    subscription_store.DB_PATH = tmp_path / "users.db"
    try:
        with subscription_store.get_connection() as connection:
            connection.execute("CREATE TABLE users (id INTEGER PRIMARY KEY)")
            connection.execute("INSERT INTO users (id) VALUES (1)")

        initial_usage = subscription_store.load_usage(1)
        assert initial_usage["current_document_count"] == 0
        assert initial_usage["current_request_count"] == 0
        assert initial_usage["events"] == []

        updated_usage = subscription_store.save_usage(1, docs=2, api_calls=3)

        assert updated_usage["current_document_count"] == 2
        assert updated_usage["current_request_count"] == 3
        assert [
            (event["event_type"], event["amount"])
            for event in updated_usage["events"]
        ] == [("documents", 2), ("api_requests", 3)]
    finally:
        subscription_store.DB_PATH = original_db_path
