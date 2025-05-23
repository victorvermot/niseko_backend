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
                    name TEXT UNIQUE,
                    highest_score INTEGER DEFAULT 0,
                    data JSONB
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS cooperative_players (
                    id SERIAL PRIMARY KEY,
                    player1_id INTEGER REFERENCES characters(id),
                    player2_id INTEGER REFERENCES characters(id),
                    highest_score INTEGER DEFAULT 0
                )
            ''')
            conn.commit()

@app.route("/save_character", methods=["POST"])
def save_character():
    data = request.get_json()
    name = data.get("name")
    json_data = json.dumps(data)

    with get_db_connection() as conn:
        with conn.cursor() as c:
            c.execute("INSERT INTO characters (name, data) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING", (name, json_data))
            conn.commit()
    print_all_characters()
    return jsonify({"status": "ok"})

@app.route("/check_character_exists", methods=["POST"])
def check_character_exists_route():
    data = request.get_json()
    name = data.get("name")
    return jsonify({"exists": check_character_exists(name)})

def check_character_exists(name):
    with get_db_connection() as conn:
        with conn.cursor() as c:
            c.execute("SELECT 1 FROM characters WHERE name = %s", (name,))
            return c.fetchone() is not None

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
            c.execute("SELECT name, data FROM characters")
            results = c.fetchall()
            characters = [{"name": name, "data": data} for name, data in results]
    return jsonify(characters)

def delete_all_characters():
    with get_db_connection() as conn:
        with conn.cursor() as c:
            c.execute("DELETE FROM characters")
            conn.commit()
            print("All characters deleted.")

def print_all_characters():
    with get_db_connection() as conn:
        with conn.cursor() as c:
            c.execute("SELECT name, data FROM characters")
            results = c.fetchall()
            for name, data in results:
                print(f"Name: {name}, Data: {data}")

@app.route("/get_all_characters_with_highest_score", methods=["GET"])
def get_all_characters_with_highest_score():
    with get_db_connection() as conn:
        with conn.cursor() as c:
            c.execute("SELECT name, highest_score, data FROM characters")
            results = c.fetchall()
            characters = [{"name": name, "highest_score": score, "data": data} for name, score, data in results]
    return jsonify(characters)

@app.route("/save_cooperative_players", methods=["POST"])
def save_cooperative_players():
    data = request.get_json()
    player1_name = data.get("player1_name")
    player2_name = data.get("player2_name")
    highest_score = data.get("highest_score", 0)

    with get_db_connection() as conn:
        with conn.cursor() as c:
            c.execute("SELECT id FROM characters WHERE name = %s", (player1_name,))
            player1_id = c.fetchone()
            c.execute("SELECT id FROM characters WHERE name = %s", (player2_name,))
            player2_id = c.fetchone()

            if player1_id and player2_id and check_if_score_is_higher(player1_id[0], player2_id[0], highest_score):
                c.execute("""
                    UPDATE cooperative_players 
                    SET highest_score = %s 
                    WHERE player1_id = %s AND player2_id = %s
                """, (highest_score, player1_id[0], player2_id[0]))

                if c.rowcount == 0:
                    c.execute("""
                        INSERT INTO cooperative_players (player1_id, player2_id, highest_score)
                        VALUES (%s, %s, %s)
                    """, (player1_id[0], player2_id[0], highest_score))

                conn.commit()
                return jsonify({"status": "ok"})
            else:
                return jsonify({"error": "One or both players not found"}), 404

def check_if_score_is_higher(player1_id, player2_id, new_score):
    with get_db_connection() as conn:
        with conn.cursor() as c:
            c.execute("SELECT highest_score FROM cooperative_players WHERE player1_id = %s AND player2_id = %s", (player1_id, player2_id))
            result = c.fetchone()
            return result is None or (result and new_score > result[0])

@app.route("/get_cooperative_players_with_details", methods=["GET"])
def get_cooperative_players_with_details():
    with get_db_connection() as conn:
        with conn.cursor() as c:
            c.execute('''
                SELECT 
                    cp.highest_score,
                    c1.name AS player1_name,
                    c1.data AS player1_data,
                    c2.name AS player2_name,
                    c2.data AS player2_data
                FROM cooperative_players cp
                JOIN characters c1 ON cp.player1_id = c1.id
                JOIN characters c2 ON cp.player2_id = c2.id
            ''')
            results = c.fetchall()

            players = []
            for score, p1_name, p1_data, p2_name, p2_data in results:
                players.append({
                    "highest_score": score,
                    "player1": {"name": p1_name, "data": p1_data},
                    "player2": {"name": p2_name, "data": p2_data}
                })
    return jsonify(players)


with app.app_context():
    try:
        init_db()
        print("✅ Database initialized.")
    except Exception as e:
        print(f"⚠️ Database init failed: {e}")