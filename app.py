# filepath: /niseko_backend/niseko_backend/backend.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import json

app = Flask(__name__)
CORS(app)

def init_db():
    with sqlite3.connect("characters.db") as conn:
        conn.execute("PRAGMA foreign_keys = ON;")  # Enable foreign key support
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                highest_score INTEGER DEFAULT 0,
                data TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS cooperative_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player1_id INTEGER,
                player2_id INTEGER,
                highest_score INTEGER DEFAULT 0,
                FOREIGN KEY (player1_id) REFERENCES characters (id),
                FOREIGN KEY (player2_id) REFERENCES characters (id)
            )
        ''')
        conn.commit()

@app.route("/save_character", methods=["POST"])
def save_character():
    data = request.get_json()
    name = data.get("name")
    json_data = json.dumps(data)

    with sqlite3.connect("characters.db") as conn:
        c = conn.cursor()
        c.execute("INSERT INTO characters (name, data) VALUES (?, ?)", (name, json_data))
        conn.commit()
    print_all_characters()
    return jsonify({"status": "ok"})

@app.route("/check_character_exists", methods=["POST"])
def check_character_exists_route():
    data = request.get_json()
    name = data.get("name")

    if check_character_exists(name):
        return jsonify({"exists": True})
    else:
        return jsonify({"exists": False})
    
def check_character_exists(name):
    with sqlite3.connect("characters.db") as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM characters WHERE name = ?", (name,))
        return c.fetchone() is not None

@app.route("/get_character/<name>", methods=["GET"])
def get_character(name):
    with sqlite3.connect("characters.db") as conn:
        c = conn.cursor()
        c.execute("SELECT data FROM characters WHERE name = ?", (name,))
        result = c.fetchone()

        if result:
            return jsonify(json.loads(result[0]))
        else:
            return jsonify({"error": "Character not found"}), 404

@app.route("/get_all_characters", methods=["GET"])
def get_all_characters():
    print("Request to get all characters")
    with sqlite3.connect("characters.db") as conn:
        c = conn.cursor()
        c.execute("SELECT name, data FROM characters")
        results = c.fetchall()

        characters = []
        for name, data in results:
            characters.append({"name": name, "data": json.loads(data)})

    return jsonify(characters)

def delete_all_characters():
    with sqlite3.connect("characters.db") as conn:
        c = conn.cursor()
        c.execute("DELETE FROM characters")
        conn.commit()
        print("All characters deleted.")

def print_all_characters():
    with sqlite3.connect("characters.db") as conn:
        c = conn.cursor()
        c.execute("SELECT name, data FROM characters")
        results = c.fetchall()

        for name, data in results:
            print(f"Name: {name}, Data: {data}")

@app.route("/get_all_characters_with_highest_score", methods=["GET"])
def get_all_characters_with_highest_score():
    with sqlite3.connect("characters.db") as conn:
        c = conn.cursor()
        c.execute("SELECT name, highest_score, data FROM characters")
        results = c.fetchall()

        characters = []
        for name, highest_score, data in results:
            characters.append({"name": name, "highest_score": highest_score, "data": json.loads(data)})

    return jsonify(characters)

@app.route("/save_cooperative_players", methods=["POST"])
def save_cooperative_players():
    data = request.get_json()
    player1_name = data.get("player1_name")
    player2_name = data.get("player2_name")
    highest_score = data.get("highest_score", 0)

    with sqlite3.connect("characters.db") as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        c = conn.cursor()

        # Retrieve player IDs from the characters table
        c.execute("SELECT id FROM characters WHERE name = ?", (player1_name,))
        player1_id = c.fetchone()
        c.execute("SELECT id FROM characters WHERE name = ?", (player2_name,))
        player2_id = c.fetchone()

        if player1_id and player2_id and check_if_score_is_higher(player1_id[0], player2_id[0], highest_score):
            # If there already exists a record for these players, update it
            c.execute(
                "UPDATE cooperative_players SET highest_score = ? WHERE player1_id = ? AND player2_id = ?",
                (highest_score, player1_id[0], player2_id[0])
            )
            if c.rowcount == 0:
                # If no record was updated, insert a new one
                c.execute(
                    "INSERT INTO cooperative_players (player1_id, player2_id, highest_score) VALUES (?, ?, ?)",
                    (player1_id[0], player2_id[0], highest_score)
                )
            conn.commit()
            return jsonify({"status": "ok"})
        else:
            return jsonify({"error": "One or both players not found"}), 404

def check_if_score_is_higher(player1_id, player2_id, new_score):
    with sqlite3.connect("characters.db") as conn:
        c = conn.cursor()
        c.execute("SELECT highest_score FROM cooperative_players WHERE player1_id = ? AND player2_id = ?", (player1_id, player2_id))
        result = c.fetchone()
        if result is None:
            return True
        if result and new_score > result[0]:
            return True
        else:
            return False

@app.route("/get_cooperative_players", methods=["GET"])
def get_cooperative_players():
    with sqlite3.connect("characters.db") as conn:
        c = conn.cursor()
        c.execute("SELECT player1_name, player2_name, highest_score FROM cooperative_players")
        results = c.fetchall()

        players = []
        for player1_name, player2_name, highest_score in results:
            players.append({"player1_name": player1_name, "player2_name": player2_name, "highest_score": highest_score})

    return jsonify(players)

@app.route("/get_cooperative_players_with_details", methods=["GET"])
def get_cooperative_players_with_details():
    with sqlite3.connect("characters.db") as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        c = conn.cursor()
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
        for highest_score, player1_name, player1_data, player2_name, player2_data in results:
            players.append({
                "highest_score": highest_score,
                "player1": {"name": player1_name, "data": json.loads(player1_data)},
                "player2": {"name": player2_name, "data": json.loads(player2_data)}
            })

    return jsonify(players)

if __name__ == "__main__":
    init_db()
    print_all_characters()
    app.run(port=5000)