from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import os
import json

app = Flask(__name__)
CORS(app)

def get_db_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'], sslmode='require')

def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as c:
            c.execute('''
                CREATE TABLE IF NOT EXISTS characters (
                    id SERIAL PRIMARY KEY,
                    data JSONB
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS cooperative_players (
                    id SERIAL PRIMARY KEY,
                    player1_id INTEGER REFERENCES characters(id),
                    player2_id INTEGER REFERENCES characters(id),
                    highest_score INTEGER DEFAULT 0,
                    UNIQUE (player1_id, player2_id)
                )
            ''')
            conn.commit()

@app.route("/save_character", methods=["POST"])
def save_character():
    data = request.get_json()
    json_data = json.dumps(data)

    with get_db_connection() as conn:
        with conn.cursor() as c:
            c.execute("INSERT INTO characters (data) VALUES (%s) RETURNING id", (json_data,))
            character_id = c.fetchone()[0]
            conn.commit()
    return jsonify({"status": "ok", "character_id": character_id})

@app.route("/get_character/<name>", methods=["GET"])
def get_character(name):
    with get_db_connection() as conn:
        with conn.cursor() as c:
            c.execute("SELECT data FROM characters WHERE name = %s", (name,))
            result = c.fetchone()
            if result:
                return jsonify(result[0])
            else:
                return jsonify({"error": "Character not found"}), 404

@app.route("/get_all_characters", methods=["GET"])
def get_all_characters():
    with get_db_connection() as conn:
        with conn.cursor() as c:
            c.execute("SELECT data FROM characters")
            results = c.fetchall()
            characters = [{"data": data} for data in results]
    return jsonify(characters)

def print_all_characters():
    with get_db_connection() as conn:
        with conn.cursor() as c:
            c.execute("SELECT name, data FROM characters")
            results = c.fetchall()
            for name, data in results:
                print(f"Name: {name}, Data: {data}")

@app.route("/save_cooperative_players", methods=["POST"])
def save_cooperative_players():
    data = request.get_json()
    player1_id = data.get("player1_id")
    player2_id = data.get("player2_id")
    new_score = data.get("highest_score")
    if not player1_id or not player2_id or new_score is None:
        return jsonify({"error": "Invalid input"}), 400
    if player1_id == player2_id:
        return jsonify({"error": "Players cannot be the same"}), 400
    if not check_if_score_is_higher(player1_id, player2_id, new_score):
        return jsonify({"error": "New score is not higher than the existing score"}), 400
    with get_db_connection() as conn:
        with conn.cursor() as c:
            c.execute("""
                INSERT INTO cooperative_players (player1_id, player2_id, highest_score)
                VALUES (%s, %s, %s)
                ON CONFLICT (player1_id, player2_id) DO UPDATE SET highest_score = GREATEST(cooperative_players.highest_score, EXCLUDED.highest_score)
            """, (player1_id, player2_id, new_score))
            conn.commit()
    return jsonify({"status": "ok"})

def check_if_score_is_higher(player1_id, player2_id, new_score):
    with get_db_connection() as conn:
        with conn.cursor() as c:
            c.execute("SELECT highest_score FROM cooperative_players WHERE player1_id = %s AND player2_id = %s", (player1_id, player2_id))
            result = c.fetchone()
            return result is None or (result and new_score > result[0])

@app.route("/get_top_three_cooperative_players", methods=["GET"])
def get_top_three_cooperative_players():
    with get_db_connection() as conn:
        with conn.cursor() as c:
            c.execute('''
                SELECT 
                    cp.highest_score,
                    c1.data AS player1_data,
                    c2.data AS player2_data
                FROM cooperative_players cp
                JOIN characters c1 ON cp.player1_id = c1.id
                JOIN characters c2 ON cp.player2_id = c2.id
                ORDER BY cp.highest_score DESC
                LIMIT 3
            ''')
            results = c.fetchall()
            players = []
            for score, p1_name, p1_data, p2_name, p2_data in results:
                players.append({
                    "highest_score": score,
                    "player1": {
                        "name": p1_name,
                        "data": p1_data
                    },
                    "player2": {
                        "name": p2_name,
                        "data": p2_data
                    }
                })
            return jsonify(players)

with app.app_context():
    try:
        init_db()
        print("✅ Database initialized.")
    except Exception as e:
        print(f"⚠️ Database init failed: {e}")