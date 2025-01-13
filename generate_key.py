from cryptography.fernet import Fernet

# Schlüssel generieren
key = Fernet.generate_key()
print(key.decode())