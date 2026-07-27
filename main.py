"""Simple review retrieval helper for the review bot.

This module connects to the database and returns stored reviews for a given
matriculation number.
"""

import os

import psycopg2
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from psycopg2.extras import RealDictCursor

from functions.review import process_reviews

# Load environment variables so the database URI is available.
load_dotenv()

app = Flask(__name__)

DB_URI = os.environ.get("DB_URI")

# Keep one database connection for the helper module.
_conn = psycopg2.connect(DB_URI, cursor_factory=RealDictCursor)

def get_conn():
    """Return a reusable psycopg2 connection and reconnect when needed."""
    global _conn
    if _conn is None or _conn.closed:
        # Create a fresh connection if the existing one is missing or closed.
        _conn = psycopg2.connect(DB_URI, cursor_factory=RealDictCursor)
    return _conn

def get_reviews(matric_no: str, conn):
    """Fetch all review texts associated with a specific matriculation number."""
    with conn:
        with conn.cursor() as cur:
            # Query the reviews table for the requested student.
            cur.execute(
                """
                SELECT review_data FROM reviews
                WHERE matric_no=%s
                """,
                (matric_no,),
            )
            data = cur.fetchall()

    # Return just the review text values as a clean list.
    return [review["review_data"] for review in data]


# Example of how this could be exposed as an API endpoint in the future.
@app.route("/api/reviews", methods=['POST'])
async def get_reviews_api():
    # Use the async review processing pipeline instead of a direct DB query.
    matric_no = request.get_json()['matric_no']
    merged_reviews = await process_reviews(matric_no, get_conn())
    return {"reviews": merged_reviews}

@app.route("/home", methods=['GET'])
def home():
    return jsonify({"status":"succes", "message": "Welcome home"})

if __name__ == '__main__':
    app.run(debug=True)
# Print a sample result when the file is run directly.
# print(get_reviews("24CG036163"))