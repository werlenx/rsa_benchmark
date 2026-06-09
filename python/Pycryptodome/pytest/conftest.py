import os

import pytest
from Crypto.PublicKey import RSA

# Fixtures compartilhadas para todos os benchmarks RSA - Pycryptodome


@pytest.fixture
def rsa_keys():
    """Gera pares de chaves RSA para os tamanhos parametrizados.
    Executado como setup, NAO e medido no benchmark."""
    keys = [2048, 4096]
    rsa_keys = {}
    for key_size in keys:
        rsa_keys[key_size] = RSA.generate(key_size)
    return rsa_keys


@pytest.fixture
def message():
    """Mensagem fixa de 190 bytes para cifracao/decifracao."""
    return os.urandom(190)
