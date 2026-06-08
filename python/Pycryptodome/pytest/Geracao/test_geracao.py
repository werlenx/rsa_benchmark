import pytest
from Crypto.PublicKey import RSA

# Benchmarking pytest - Geração de chaves RSA - Pycryptodome

# Teste de geração de chaves RSA
@pytest.mark.parametrize("key_size", [2048, 4096])
def test_key_generation(benchmark, key_size):
    def generate_key():
        return RSA.generate(key_size)
    
    # Mede o tempo necessário para gerar a chave
    result = benchmark.pedantic(generate_key, rounds=15)
    
    # Verifica se a chave foi gerada corretamente
    assert result is not None
