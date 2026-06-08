from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Cipher import PKCS1_OAEP

# Esse código baseia-se na documentação da biblioteca Pycryptodome
# Disponível em: https://pycryptodome.readthedocs.io/en/latest/
# Com base nesse código, o processo de microbenchmarking foi gerado

# Geração de chaves
key = RSA.generate(2048)
private_key = key.export_key().decode("utf-8")
file_out = open("private.pem", "wb")
file_out.write(private_key.encode("utf-8"))
file_out.close()

public_key = key.publickey().export_key().decode("utf-8")
file_out = open("receiver.pem", "wb")
file_out.write(public_key.encode("utf-8"))
file_out.close()

# Exemplo de mensagem
data = "I met aliens in UFO. Here is the map.".encode("utf-8")
file_out = open("encrypted_data.bin", "wb")

recipient_key = RSA.import_key(open("receiver.pem").read())
session_key = get_random_bytes(16)

# Encript
cipher_rsa = PKCS1_OAEP.new(recipient_key)
enc_session_key = cipher_rsa.encrypt(session_key)

# Decrypt
private_key = RSA.import_key(open("private.pem").read())  # Carregue a chave privada corretamente
cipher_rsa = PKCS1_OAEP.new(private_key)
session_key = cipher_rsa.decrypt(enc_session_key)

# Visualizar as chaves geradas
print("Chave privada:")
print(private_key)
print("\nChave pública:")
print(public_key)