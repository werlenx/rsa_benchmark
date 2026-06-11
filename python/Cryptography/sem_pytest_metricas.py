import gc
import math
import os
import time
import tracemalloc
from typing import Callable, Iterable

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from tabulate import tabulate


# Benchmarking RSA sem pytest, com metricas de tempo, CPU e memoria.
# A cifracao e a decifracao reaproveitam as chaves durante as iteracoes.

KEY_SIZES = (2048, 4096)
OPERATION_ITERATIONS = (10, 100, 1000, 10000)
MESSAGE_SIZE_BYTES = 190
ENCRYPT_DECRYPT_WARMUP_ROUNDS = 3
KEYGEN_WARMUP_ROUNDS = 1
BYTES_PER_KIB = 1024


def oaep_padding() -> padding.OAEP:
    return padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None,
    )


def generate_keys(
    key_sizes: Iterable[int],
) -> dict[int, tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]]:
    rsa_keys = {}
    for key_size in key_sizes:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
        public_key = private_key.public_key()
        rsa_keys[key_size] = (private_key, public_key)
    return rsa_keys


def new_stats() -> dict[str, float]:
    return {
        "count": 0.0,
        "total": 0.0,
        "mean": 0.0,
        "m2": 0.0,
        "min": math.inf,
        "max": 0.0,
    }


def add_sample(stats: dict[str, float], value: float) -> None:
    stats["count"] += 1
    stats["total"] += value

    delta = value - stats["mean"]
    stats["mean"] += delta / stats["count"]
    delta2 = value - stats["mean"]
    stats["m2"] += delta * delta2

    if value < stats["min"]:
        stats["min"] = value
    if value > stats["max"]:
        stats["max"] = value


def std_deviation(stats: dict[str, float]) -> float:
    if stats["count"] == 0:
        return 0.0
    return math.sqrt(stats["m2"] / stats["count"])


def warmup(operation: Callable[[], object], rounds: int) -> None:
    gc.collect()
    for _ in range(rounds):
        operation()
    gc.collect()


def benchmark_operation(
    operation_name: str,
    key_size: int,
    iterations: int,
    operation: Callable[[], object],
    warmup_rounds: int,
) -> list[object]:
    warmup(operation, warmup_rounds)

    wall_stats = new_stats()
    cpu_stats = new_stats()
    was_gc_enabled = gc.isenabled()

    gc.collect()
    if was_gc_enabled:
        gc.disable()

    tracemalloc.start()
    tracemalloc.reset_peak()

    last_result = None
    try:
        for _ in range(iterations):
            wall_start = time.perf_counter()
            cpu_start = time.process_time()

            last_result = operation()

            add_sample(cpu_stats, time.process_time() - cpu_start)
            add_sample(wall_stats, time.perf_counter() - wall_start)
    finally:
        memory_current_bytes, memory_peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        if was_gc_enabled:
            gc.enable()
        gc.collect()

    # Mantem uma referencia ate aqui para que a ultima operacao conte na memoria.
    if last_result is None:
        raise RuntimeError("A operacao medida nao retornou resultado.")

    cpu_percent = (
        (cpu_stats["total"] / wall_stats["total"]) * 100
        if wall_stats["total"]
        else 0.0
    )

    return [
        operation_name,
        key_size,
        iterations,
        wall_stats["mean"],
        std_deviation(wall_stats),
        wall_stats["min"],
        wall_stats["max"],
        wall_stats["total"],
        cpu_stats["mean"],
        std_deviation(cpu_stats),
        cpu_stats["total"],
        cpu_percent,
        memory_peak_bytes / BYTES_PER_KIB,
        memory_current_bytes / BYTES_PER_KIB,
    ]


def make_keygen_operation(key_size: int) -> Callable[[], rsa.RSAPrivateKey]:
    def keygen() -> rsa.RSAPrivateKey:
        return rsa.generate_private_key(public_exponent=65537, key_size=key_size)

    return keygen


def make_encrypt_operation(public_key: rsa.RSAPublicKey, message: bytes) -> Callable[[], bytes]:
    def encrypt() -> bytes:
        return public_key.encrypt(message, oaep_padding())

    return encrypt


def make_decrypt_operation(
    private_key: rsa.RSAPrivateKey,
    public_key: rsa.RSAPublicKey,
    message: bytes,
) -> Callable[[], bytes]:
    ciphertext = public_key.encrypt(message, oaep_padding())

    def decrypt() -> bytes:
        return private_key.decrypt(ciphertext, oaep_padding())

    return decrypt


def run_benchmarks() -> list[list[object]]:
    results = []
    rsa_keys = generate_keys(KEY_SIZES)
    message = os.urandom(MESSAGE_SIZE_BYTES)

    for iterations in OPERATION_ITERATIONS:
        for key_size in KEY_SIZES:
            private_key, public_key = rsa_keys[key_size]

            results.append(
                benchmark_operation(
                    operation_name="gerar_chaves",
                    key_size=key_size,
                    iterations=iterations,
                    operation=make_keygen_operation(key_size),
                    warmup_rounds=KEYGEN_WARMUP_ROUNDS,
                )
            )

            results.append(
                benchmark_operation(
                    operation_name="cifrar",
                    key_size=key_size,
                    iterations=iterations,
                    operation=make_encrypt_operation(public_key, message),
                    warmup_rounds=ENCRYPT_DECRYPT_WARMUP_ROUNDS,
                )
            )

            results.append(
                benchmark_operation(
                    operation_name="decifrar",
                    key_size=key_size,
                    iterations=iterations,
                    operation=make_decrypt_operation(private_key, public_key, message),
                    warmup_rounds=ENCRYPT_DECRYPT_WARMUP_ROUNDS,
                )
            )

    print(
        "Configuracao: "
        f"chaves={KEY_SIZES}, "
        f"iteracoes={OPERATION_ITERATIONS}"
    )
    print()

    return results


def main() -> None:
    headers = [
        "Operacao",
        "Chave",
        "Iteracoes",
        "Wall medio (s)",
        "Wall desvio (s)",
        "Wall min (s)",
        "Wall max (s)",
        "Wall total (s)",
        "CPU medio (s)",
        "CPU desvio (s)",
        "CPU total (s)",
        "CPU processo (%)",
        "Pico mem Python (KiB)",
        "Mem Python atual (KiB)",
    ]
    print(tabulate(run_benchmarks(), headers=headers, floatfmt=".6f"))


if __name__ == "__main__":
    main()
