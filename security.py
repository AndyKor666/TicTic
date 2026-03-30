from cryptography.fernet import Fernet
import config

cipher = Fernet(config.FERNET_KEY)

def encrypt_msg(msg):
    return cipher.encrypt(msg.encode()).decode()

def decrypt_msg(raw_msg):
    return cipher.decrypt(raw_msg.encode()).decode()