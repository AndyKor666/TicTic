import hashlib

HOST = '127.0.0.1'
PORT = 4001
FERNET_KEY = b'cKxnXOaYyO63E3hkXoAKU_NFzCE1Fl6FDS5tfAavVO8='

DB_CONF = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=DESKTOP-DOGCDD4\\SQLEXPRESS;"
    "DATABASE=AuthSystemDB;"
    "Trusted_Connection=yes"
)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()