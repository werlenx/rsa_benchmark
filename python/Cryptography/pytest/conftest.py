import os
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

# Fixtures compartilhadas para todos os benchmarks RSA - Cryptography

@pytest.fixture
def rsa_keys():
    """Gera pares de chaves RSA para os tamanhos parametrizados.
    Executado como setup, NÃO é medido no benchmark."""
    keys = [2048, 4096]
    rsa_keys = {}
    for key_size in keys:
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=key_size
        )
        public_key = private_key.public_key()
        rsa_keys[key_size] = (private_key, public_key)
    return rsa_keys

@pytest.fixture
def message():
    """Mensagem fixa de 190 bytes para cifração/decifração."""
    return os.urandom(190)
