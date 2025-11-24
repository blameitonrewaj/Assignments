import random
import threading
import time
import paho.mqtt.client as mqtt

BROKER = "broker.emqx.io"   
PORT = 1883

TOPIC = "Guessing Game"    

nickname = input("Enter your nickname: ").strip() or "player"
is_host_input = input("Are you the host? (y/n): ").strip().lower()
is_host = is_host_input == "y"

secret_number = None
game_over = False

if is_host:
    while True:
        try:
            val = int(input("Enter the secret number (1–50): ").strip())
            if 1 <= val <= 50:
                secret_number = val
                break
            else:
                print("Please enter a number between 1 and 50.")
        except ValueError:
            print("Please enter a valid integer.")
    print("[HOST] Secret number set. Other players can start guessing.")
else:
    print("Waiting for the host to start the game...")


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("Connected to broker.")
        client.subscribe(TOPIC)
        client.publish(TOPIC, f"SYSTEM|{nickname} joined the game.")
    else:
        print("Connection failed with code", rc)


def on_message(client, userdata, msg):
    global game_over, secret_number
    payload = msg.payload.decode("utf-8")

    parts = payload.split("|", 2)
    if len(parts) < 2:
        print(payload)
        return

    msg_type = parts[0]
    sender = parts[1]
    data = parts[2] if len(parts) == 3 else ""


    if sender == nickname and msg_type != "SYSTEM":
        print(f"(echo) {payload}")
        return

    if msg_type == "SYSTEM":
        print(f"[SYSTEM] {sender} {data}")
    elif msg_type == "CHAT":
        print(f"[CHAT] {sender}: {data}")
    elif msg_type == "GUESS":

    
        print(f"[GUESS] {sender} guessed {data}")
        if is_host and not game_over:
            try:
                guess = int(data)
            except ValueError:
                return
            if guess < secret_number:
                client.publish(TOPIC, f"RESULT|HOST|{sender}'s guess {guess} is too LOW.")
            elif guess > secret_number:
                client.publish(TOPIC, f"RESULT|HOST|{sender}'s guess {guess} is too HIGH.")
            else:
                game_over = True
                client.publish(TOPIC, f"RESULT|HOST|{sender} guessed CORRECT! Number was {secret_number}.")
                client.publish(TOPIC, "SYSTEM|GAME|Game over.")
    elif msg_type == "RESULT":
        print(f"[RESULT] {data}")

def input_loop(client):
    global game_over
    print("Commands:")
    print("  /guess N   -> make a guess (integer)")
    print("  /say text  -> send chat message")
    print("  /quit      -> leave game")
    while not game_over:
        try:
            line = input("> ").strip()
        except EOFError:
            break

        if not line:
            continue

        if line.startswith("/guess"):
            parts = line.split()
            if len(parts) != 2:
                print("Usage: /guess N")
                continue
            client.publish(TOPIC, f"GUESS|{nickname}|{parts[1]}")
        elif line.startswith("/say"):
            text = line[4:].strip()
            if text:
                client.publish(TOPIC, f"CHAT|{nickname}|{text}")
        elif line.startswith("/quit"):
            client.publish(TOPIC, f"SYSTEM|{nickname}|left the game.")
            game_over = True
            break
        else:
            print("Unknown command. Use /guess, /say, or /quit.")

def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"Connecting to {BROKER}:{PORT}...")
    try:
        client.connect(BROKER, PORT, keepalive=60)
    except Exception as e:
        print("Initial connect failed:", e)
        print("Try another broker (e.g., broker.emqx.io or broker.hivemq.com) or another network.")
        return

    client.loop_start()
    try:
        input_loop(client)
    finally:
        time.sleep(1)
        client.loop_stop()
        client.disconnect()
        print("Disconnected.")


if __name__ == "__main__":
    main()