import pytest
from Crypto.Cipher import PKCS1_OAEP

# Benchmarking pytest - Cifracao RSA - Pycryptodome


@pytest.mark.parametrize("key_size", [2048, 4096])
@pytest.mark.parametrize("iterations", [10, 100, 1000, 10000])
def test_encrypt(benchmark, rsa_keys, message, key_size, iterations):
    private_key = rsa_keys[key_size]
    public_key = private_key.publickey()
    cipher_rsa = PKCS1_OAEP.new(public_key)

    def _encrypt():
        return cipher_rsa.encrypt(message)

    result = benchmark.pedantic(_encrypt, iterations=iterations, rounds=15)
    assert result is not None
