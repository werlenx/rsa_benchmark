import pytest
import os
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

# Benchmarking pytest - Decifração RSA - Pycryptodome

# Configuração das chaves RSA
@pytest.fixture
def rsa_keys():
    keys = [2048, 4096]
    rsa_keys = {}
    for key_size in keys:
        rsa_keys[key_size] = RSA.generate(key_size)
    return rsa_keys

# Teste de decifração
@pytest.mark.parametrize("key_size", [2048, 4096])
@pytest.mark.parametrize("iterations", [10, 100, 1000, 10000])
def test_decrypt(benchmark, rsa_keys, key_size, iterations):
    private_key = rsa_keys[key_size]
    public_key = private_key.publickey()
    message = os.urandom(190)
    cipher_rsa = PKCS1_OAEP.new(private_key)
    ciphertext = cipher_rsa.encrypt(message)

    cipher_rsa = PKCS1_OAEP.new(private_key)

    def _decrypt():
        return cipher_rsa.decrypt(ciphertext)

    result = benchmark.pedantic(_decrypt, iterations=iterations, rounds=15)
    assert result is not None