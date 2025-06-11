import psycopg2
import random

def get_db_connection():
    return psycopg2.connect(
        dbname="niseko",
        user="victor",
        password="victor",
        host="localhost",
        port="5432"
    )

def get_all_character_ids():
    with get_db_connection() as conn:
        with conn.cursor() as c:
            c.execute("SELECT id FROM characters")
            results = c.fetchall()
            return [row[0] for row in results]

def insert_cooperative_players(player1_id, player2_id, highest_score):
    with get_db_connection() as conn:
        with conn.cursor() as c:
            # Insert only if pair doesn't already exist
            c.execute("""
                INSERT INTO cooperative_players (player1_id, player2_id, highest_score)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (player1_id, player2_id, highest_score))
            conn.commit()

def main():
    character_ids = get_all_character_ids()
    print(f"Found {len(character_ids)} characters.")

    # Shuffle IDs for random pairing
    random.shuffle(character_ids)

    # Take pairs of 2
    num_pairs = min(len(character_ids) // 2, 10)  # Max 10 pairs, or fewer if not enough characters

    for i in range(num_pairs):
        player1_id = character_ids[i * 2]
        player2_id = character_ids[i * 2 + 1]

        if player1_id == player2_id:
            continue  # Skip self-pairing, should not happen with shuffle

        highest_score = random.randint(10, 1000)

        insert_cooperative_players(player1_id, player2_id, highest_score)
        print(f"Inserted pair: {player1_id} & {player2_id} with score {highest_score}")

if __name__ == "__main__":
    main()
