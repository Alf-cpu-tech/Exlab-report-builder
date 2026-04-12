from database import execute_db, query_db


# DATASET OPERATIONS

def create_dataset(user_id, filename, status="uploaded", metadata=None):
    return execute_db("""
        INSERT INTO dataset (user_id, filename, status, metadata)
        VALUES (?, ?, ?, ?)
    """, (user_id, filename, status, metadata))


def get_dataset(dataset_id):
    return query_db("""
        SELECT * FROM dataset WHERE id = ?
    """, (dataset_id,), one=True)

# PROCESSED OPERATIONS

def create_processed(dataset_id, json_data):
    return execute_db("""
        INSERT INTO processed (dataset_id, json_data)
        VALUES (?, ?)
    """, (dataset_id, json_data))


def get_processed(processed_id):
    return query_db("""
        SELECT * FROM processed WHERE id = ?
    """, (processed_id,), one=True)