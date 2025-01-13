from cryptography.fernet import Fernet

# Generierten Schlüssel verwenden
key = b'3AjVoBuGvF35d9xrwK95_MKHKPOk9rjEJuczZawkK-E='  # Ersetzen Sie diesen durch Ihren Schlüssel
f = Fernet(key)

# Originaldatei lesen
with open("content_file.txt", "rb") as file:
    original_data = file.read()

# Datei verschlüsseln und speichern
encrypted_data = f.encrypt(original_data)
with open("content_file.txt.encrypted", "wb") as encrypted_file:
    encrypted_file.write(encrypted_data)