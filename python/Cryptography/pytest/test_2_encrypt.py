import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

# Benchmarking pytest - Cifração RSA - Cryptography

@pytest.mark.parametrize("key_size", [2048, 4096])
@pytest.mark.parametrize("iterations", [10, 100, 1000, 10000])
def test_encrypt(benchmark, rsa_keys, message, key_size, iterations):
    private_key, public_key = rsa_keys[key_size]
    
    def _encrypt():
        return public_key.encrypt(message, padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        ))
    
    result = benchmark.pedantic(_encrypt, iterations=iterations, rounds=15)
    assert result is not None
