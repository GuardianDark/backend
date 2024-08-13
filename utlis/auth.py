import secrets
from cryptography.fernet import Fernet


def generate_auth_token():
    key = Fernet.generate_key() 
    f = Fernet(key) 
    token = secrets.token_urlsafe(32)
    encrypted_token = f.encrypt(token.encode()).decode() 
    return encrypted_token, key.decode()


def decrypt_auth_token(encrypted_token, key):
    f = Fernet(key.encode())
    decrypted_token = f.decrypt(encrypted_token.encode()).decode() 
    return decrypted_token