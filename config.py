import hashlib

HOST = '127.0.0.1'
PORT = 4000

USERS_FILE = "users.json"
FERNET_KEY = b'cKxnXOaYyO63E3hkXoAKU_NFzCE1Fl6FDS5tfAavVO8='

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()