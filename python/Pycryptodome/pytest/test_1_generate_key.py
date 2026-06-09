import pytest
from Crypto.PublicKey import RSA

# Benchmarking pytest - Geracao de chaves RSA - Pycryptodome


@pytest.mark.parametrize("key_size", [2048, 4096])
def test_key_generation(benchmark, key_size):
    def generate_key():
        return RSA.generate(key_size)

    result = benchmark.pedantic(generate_key, rounds=15)
    assert result is not None
