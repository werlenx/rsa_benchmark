import pytest
from Crypto.Cipher import PKCS1_OAEP

# Benchmarking pytest - Decifracao RSA - Pycryptodome


@pytest.mark.parametrize("key_size", [2048, 4096])
@pytest.mark.parametrize("iterations", [10, 100, 1000, 10000])
def test_decrypt(benchmark, rsa_keys, message, key_size, iterations):
    private_key = rsa_keys[key_size]
    public_key = private_key.publickey()
    encrypt_cipher = PKCS1_OAEP.new(public_key)
    decrypt_cipher = PKCS1_OAEP.new(private_key)
    ciphertext = encrypt_cipher.encrypt(message)

    def _decrypt():
        return decrypt_cipher.decrypt(ciphertext)

    result = benchmark.pedantic(_decrypt, iterations=iterations, rounds=15)
    assert result is not None
