import psycopg2
import json
import random

def get_db_connection():
    return psycopg2.connect(
        dbname="niseko",
        user="victor",
        password="victor",
        host="localhost",
        port="5432"
    )

def generate_character(name):
    return {
        "name": name,
        "hair_style": random.randint(0, 3),
        "hat_style": random.randint(0, 3),
        "body_style": random.randint(0, 3),
        "face_style": random.randint(0, 3),
        "skin_color": random.randint(0, 3)
    }

def insert_character(data):
    json_data = json.dumps(data)
    name = data["name"]
    with get_db_connection() as conn:
        with conn.cursor() as c:
            # Make sure the table has a 'name' column (your current app assumes that but init_db doesn't create it)
            c.execute("INSERT INTO characters (name, data) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING", (name, json_data))
            conn.commit()

def main():
    names = ["Alice", "Bob", "Charlie", "Diana", "Eli"]
    for name in names:
        character = generate_character(name)
        insert_character(character)
        print(f"Inserted: {character}")

if __name__ == "__main__":
    main()
