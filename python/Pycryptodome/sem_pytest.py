import os
import matplotlib.pyplot as plt
import timeit
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from tabulate import tabulate

# Este benchmarking mede o tempo médio de cifração e decifração do RSA
# Reaproveitando as chaves durante todas as iterações

# Geração de chaves
def generate_keys(keys):
    rsa_keys = {}
    for key_size in keys:
        rsa_keys[key_size] = RSA.generate(key_size)
    return rsa_keys

# Cifração
def benchmark_encrypt(num_executions, keys, rsa_keys):
    execution_times = {}
    for key_size in keys:
        key = rsa_keys[key_size]
        public_key = key.publickey()
        cipher_rsa = PKCS1_OAEP.new(public_key)
        message = os.urandom(190)
        total_times = []
        for _ in range(num_executions):
            start_time = timeit.default_timer()
            ciphertext = cipher_rsa.encrypt(message)
            end_time = timeit.default_timer()
            total_times.append(end_time - start_time)
        mean_time = sum(total_times) / len(total_times)
        std_deviation = (sum((x - mean_time) ** 2 for x in total_times) / len(total_times)) ** 0.5
        execution_times[key_size] = (mean_time, std_deviation)
    return execution_times

# Decifração
def benchmark_decrypt(num_executions, keys, rsa_keys):
    execution_times = {}
    for key_size in keys:
        key = rsa_keys[key_size]
        cipher_rsa = PKCS1_OAEP.new(key)
        message = os.urandom(190)
        ciphertext = cipher_rsa.encrypt(message)
        total_times = []
        for _ in range(num_executions):
            start_time = timeit.default_timer()
            plaintext = cipher_rsa.decrypt(ciphertext)
            end_time = timeit.default_timer()
            total_times.append(end_time - start_time)
        mean_time = sum(total_times) / len(total_times)
        std_deviation = (sum((x - mean_time) ** 2 for x in total_times) / len(total_times)) ** 0.5
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