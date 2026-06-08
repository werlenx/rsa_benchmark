import os
import timeit
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from tabulate import tabulate

# Este benchmarking mede o tempo médio de cifração e decifração do RSA
# Reaproveitando as chaves durante todas as iterações

# Geração das chaves
def generate_keys(keys):
    rsa_keys = {}
    for key_size in keys:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
        public_key = private_key.public_key()
        rsa_keys[key_size] = (private_key, public_key)
    return rsa_keys

# Cifração
def benchmark_encrypt(num_executions, keys, rsa_keys):
    execution_times = {}
    for key_size in keys:
        private_key, public_key = rsa_keys[key_size]
        message = os.urandom(190)

        total_times = [timeit.timeit(lambda: public_key.encrypt(message, padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )), number=1) for _ in range(num_executions)]

        mean_time = sum(total_times) / num_executions
        std_deviation = (sum((x - mean_time) ** 2 for x in total_times) / num_executions) ** 0.5
        execution_times[key_size] = (mean_time, std_deviation)

    return execution_times

# Decifração
def benchmark_decrypt(num_executions, keys, rsa_keys):
    execution_times = {}
    for key_size in keys:
        private_key, public_key = rsa_keys[key_size]
        message = os.urandom(190)
        ciphertext = public_key.encrypt(
            message,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        total_times = [timeit.timeit(lambda: private_key.decrypt(ciphertext, padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )), number=1) for _ in range(num_executions)]

        mean_time = sum(total_times) / num_executions
        std_deviation = (sum((x - mean_time) ** 2 for x in total_times) / num_executions) ** 0.5
        execution_times[key_size] = (mean_time, std_deviation)

    return execution_times

# Valores de iterações e chaves
iterations = [10, 100, 1000, 10000]
keys = [2048, 4096]

rsa_keys = generate_keys(keys)

# Criar tabela com os dados
table_data = []
for num_executions in iterations:
    encrypt_execution_times = benchmark_encrypt(num_executions, keys, rsa_keys)
    decrypt_execution_times = benchmark_decrypt(num_executions, keys, rsa_keys)
    for key_size in keys:
        encrypt_mean, encrypt_std = encrypt_execution_times[key_size]
        decrypt_mean, decrypt_std = decrypt_execution_times[key_size]
        table_data.append([key_size, num_executions, encrypt_mean, encrypt_std, decrypt_mean, decrypt_std])

headers = ["Tamanho da Chave", "Número de Iterações", "Tempo Médio Cifração", "Desvio Padrão Cifração",
           "Tempo Médio Decifração", "Desvio Padrão Decifração"]

print(tabulate(table_data, headers=headers, floatfmt=".6f"))