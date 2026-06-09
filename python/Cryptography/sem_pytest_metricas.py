import gc
import math
import os
import resource
import sys
import time
import tracemalloc
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

try:
    from tabulate import tabulate
except ModuleNotFoundError:
    tabulate = None


# Benchmarking RSA sem pytest, com metricas de tempo, CPU e memoria.
# A cifracao e a decifracao reaproveitam as chaves durante as iteracoes.

DEFAULT_KEY_SIZES = (2048, 4096)
DEFAULT_OPERATION_ITERATIONS = (10, 100, 1000, 10000)
DEFAULT_KEY_GENERATION_ITERATIONS = 15
MESSAGE_SIZE_BYTES = 190
ENCRYPT_DECRYPT_WARMUP_ROUNDS = 3
KEY_GENERATION_WARMUP_ROUNDS = 1
TIMER_OVERHEAD_SAMPLES = 1_000

NANOSECONDS_PER_SECOND = 1_000_000_000
BYTES_PER_KIB = 1024


@dataclass
class RunningStats:
    count: int = 0
    total_ns: int = 0
    mean_ns: float = 0.0
    m2_ns: float = 0.0
    min_ns: Optional[int] = None
    max_ns: Optional[int] = None

    def add(self, value_ns: int) -> None:
        self.count += 1
        self.total_ns += value_ns

        delta = value_ns - self.mean_ns
        self.mean_ns += delta / self.count
        delta2 = value_ns - self.mean_ns
        self.m2_ns += delta * delta2

        if self.min_ns is None or value_ns < self.min_ns:
            self.min_ns = value_ns
        if self.max_ns is None or value_ns > self.max_ns:
            self.max_ns = value_ns

    @property
    def mean_s(self) -> float:
        return self.mean_ns / NANOSECONDS_PER_SECOND if self.count else 0.0

    @property
    def std_s(self) -> float:
        if self.count == 0:
            return 0.0
        return math.sqrt(self.m2_ns / self.count) / NANOSECONDS_PER_SECOND

    @property
    def total_s(self) -> float:
        return self.total_ns / NANOSECONDS_PER_SECOND

    @property
    def min_s(self) -> float:
        return (self.min_ns or 0) / NANOSECONDS_PER_SECOND

    @property
    def max_s(self) -> float:
        return (self.max_ns or 0) / NANOSECONDS_PER_SECOND


@dataclass
class BenchmarkResult:
    operation: str
    key_size: int
    iterations: int
    wall: RunningStats
    cpu: RunningStats
    python_memory_peak_bytes: int
    python_memory_current_bytes: int
    rss_delta_bytes: Optional[int]
    external_wait_percent: float

    @property
    def process_cpu_percent(self) -> float:
        if self.wall.total_ns == 0:
            return 0.0
        return (self.cpu.total_ns / self.wall.total_ns) * 100


def parse_int_list(env_name: str, default_values: Iterable[int]) -> List[int]:
    raw_value = os.getenv(env_name)
    if not raw_value:
        return list(default_values)

    try:
        values = [int(value.strip()) for value in raw_value.split(",") if value.strip()]
    except ValueError as exc:
        raise ValueError(f"{env_name} deve conter apenas inteiros separados por virgula.") from exc

    if not values or any(value <= 0 for value in values):
        raise ValueError(f"{env_name} deve conter ao menos um inteiro positivo.")

    return values


def parse_positive_int(env_name: str, default_value: int) -> int:
    raw_value = os.getenv(env_name)
    if not raw_value:
        return default_value

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{env_name} deve ser um inteiro positivo.") from exc

    if value <= 0:
        raise ValueError(f"{env_name} deve ser um inteiro positivo.")

    return value


def oaep_padding() -> padding.OAEP:
    return padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None,
    )


def generate_keys(key_sizes: Iterable[int]) -> Dict[int, Tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]]:
    rsa_keys = {}
    for key_size in key_sizes:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
        public_key = private_key.public_key()
        rsa_keys[key_size] = (private_key, public_key)
    return rsa_keys


def current_rss_bytes() -> Optional[int]:
    try:
        with open("/proc/self/statm", "r", encoding="utf-8") as statm_file:
            fields = statm_file.readline().split()
        if len(fields) < 2:
            return None
        return int(fields[1]) * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError):
        return None


def max_rss_bytes() -> int:
    max_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return max_rss
    return max_rss * BYTES_PER_KIB


def calibrate_timer_overhead(samples: int) -> Tuple[int, int]:
    wall_overhead_ns: Optional[int] = None
    cpu_overhead_ns: Optional[int] = None

    was_gc_enabled = gc.isenabled()
    gc.collect()
    gc.disable()
    try:
        for _ in range(samples):
            wall_start_ns = time.perf_counter_ns()
            cpu_start_ns = time.process_time_ns()
            cpu_end_ns = time.process_time_ns()
            wall_end_ns = time.perf_counter_ns()

            wall_delta_ns = wall_end_ns - wall_start_ns
            cpu_delta_ns = cpu_end_ns - cpu_start_ns

            if wall_overhead_ns is None or wall_delta_ns < wall_overhead_ns:
                wall_overhead_ns = wall_delta_ns
            if cpu_overhead_ns is None or cpu_delta_ns < cpu_overhead_ns:
                cpu_overhead_ns = cpu_delta_ns
    finally:
        if was_gc_enabled:
            gc.enable()
        gc.collect()

    return wall_overhead_ns or 0, cpu_overhead_ns or 0


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
    timer_overhead_ns: Tuple[int, int],
) -> BenchmarkResult:
    warmup(operation, warmup_rounds)

    wall_timer_overhead_ns, cpu_timer_overhead_ns = timer_overhead_ns
    wall_stats = RunningStats()
    cpu_stats = RunningStats()
    was_gc_enabled = gc.isenabled()

    gc.collect()
    rss_before_bytes = current_rss_bytes()

    if was_gc_enabled:
        gc.disable()

    tracemalloc.start()
    tracemalloc.reset_peak()

    last_result = None
    try:
        for _ in range(iterations):
            wall_start_ns = time.perf_counter_ns()
            cpu_start_ns = time.process_time_ns()

            last_result = operation()

            cpu_end_ns = time.process_time_ns()
            wall_end_ns = time.perf_counter_ns()

            wall_delta_ns = max(0, wall_end_ns - wall_start_ns - wall_timer_overhead_ns)
            cpu_delta_ns = max(0, cpu_end_ns - cpu_start_ns - cpu_timer_overhead_ns)

            wall_stats.add(wall_delta_ns)
            cpu_stats.add(cpu_delta_ns)
    finally:
        python_memory_current_bytes, python_memory_peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        if was_gc_enabled:
            gc.enable()

        rss_after_bytes = current_rss_bytes()
        gc.collect()

    # Mantem uma referencia ate aqui para que o resultado da ultima operacao
    # nao seja liberado antes da coleta de memoria corrente.
    if last_result is None:
        raise RuntimeError("A operacao medida nao retornou resultado.")

    rss_delta_bytes = None
    if rss_before_bytes is not None and rss_after_bytes is not None:
        rss_delta_bytes = rss_after_bytes - rss_before_bytes

    external_wait_ns = max(0, wall_stats.total_ns - cpu_stats.total_ns)
    external_wait_percent = 0.0
    if wall_stats.total_ns:
        external_wait_percent = (external_wait_ns / wall_stats.total_ns) * 100

    return BenchmarkResult(
        operation=operation_name,
        key_size=key_size,
        iterations=iterations,
        wall=wall_stats,
        cpu=cpu_stats,
        python_memory_peak_bytes=python_memory_peak_bytes,
        python_memory_current_bytes=python_memory_current_bytes,
        rss_delta_bytes=rss_delta_bytes,
        external_wait_percent=external_wait_percent,
    )


def make_key_generation_operation(key_size: int) -> Callable[[], rsa.RSAPrivateKey]:
    def generate_key() -> rsa.RSAPrivateKey:
        return rsa.generate_private_key(public_exponent=65537, key_size=key_size)

    return generate_key


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


def bytes_to_kib(value_bytes: Optional[int]) -> object:
    if value_bytes is None:
        return "N/D"
    return value_bytes / BYTES_PER_KIB


def results_to_table(results: Iterable[BenchmarkResult]) -> List[List[object]]:
    table_rows = []
    for result in results:
        table_rows.append(
            [
                result.operation,
                result.key_size,
                result.iterations,
                result.wall.mean_s,
                result.wall.std_s,
                result.wall.min_s,
                result.wall.max_s,
                result.wall.total_s,
                result.cpu.mean_s,
                result.cpu.std_s,
                result.cpu.total_s,
                result.process_cpu_percent,
                result.external_wait_percent,
                bytes_to_kib(result.python_memory_peak_bytes),
                bytes_to_kib(result.python_memory_current_bytes),
                bytes_to_kib(result.rss_delta_bytes),
            ]
        )
    return table_rows


def format_cell(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def render_table(rows: List[List[object]], headers: List[str]) -> str:
    if tabulate is not None:
        return tabulate(rows, headers=headers, floatfmt=".6f")

    formatted_rows = [[format_cell(value) for value in row] for row in rows]
    widths = [
        max(len(header), *(len(row[index]) for row in formatted_rows))
        for index, header in enumerate(headers)
    ]

    header_line = "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers))
    separator_line = "  ".join("-" * width for width in widths)
    body_lines = [
        "  ".join(value.rjust(widths[index]) for index, value in enumerate(row))
        for row in formatted_rows
    ]

    return "\n".join([header_line, separator_line, *body_lines])


def run_benchmarks() -> List[BenchmarkResult]:
    key_sizes = parse_int_list("RSA_BENCHMARK_KEY_SIZES", DEFAULT_KEY_SIZES)
    operation_iterations = parse_int_list("RSA_BENCHMARK_ITERATIONS", DEFAULT_OPERATION_ITERATIONS)
    key_generation_iterations = parse_positive_int(
        "RSA_BENCHMARK_KEYGEN_ITERATIONS",
        DEFAULT_KEY_GENERATION_ITERATIONS,
    )
    timer_overhead_samples = parse_positive_int(
        "RSA_BENCHMARK_TIMER_OVERHEAD_SAMPLES",
        TIMER_OVERHEAD_SAMPLES,
    )

    timer_overhead_ns = calibrate_timer_overhead(timer_overhead_samples)
    results: List[BenchmarkResult] = []

    for key_size in key_sizes:
        results.append(
            benchmark_operation(
                operation_name="gerar_chave",
                key_size=key_size,
                iterations=key_generation_iterations,
                operation=make_key_generation_operation(key_size),
                warmup_rounds=KEY_GENERATION_WARMUP_ROUNDS,
                timer_overhead_ns=timer_overhead_ns,
            )
        )

    rsa_keys = generate_keys(key_sizes)
    message = os.urandom(MESSAGE_SIZE_BYTES)

    for iterations in operation_iterations:
        for key_size in key_sizes:
            private_key, public_key = rsa_keys[key_size]

            results.append(
                benchmark_operation(
                    operation_name="cifrar",
                    key_size=key_size,
                    iterations=iterations,
                    operation=make_encrypt_operation(public_key, message),
                    warmup_rounds=ENCRYPT_DECRYPT_WARMUP_ROUNDS,
                    timer_overhead_ns=timer_overhead_ns,
                )
            )

            results.append(
                benchmark_operation(
                    operation_name="decifrar",
                    key_size=key_size,
                    iterations=iterations,
                    operation=make_decrypt_operation(private_key, public_key, message),
                    warmup_rounds=ENCRYPT_DECRYPT_WARMUP_ROUNDS,
                    timer_overhead_ns=timer_overhead_ns,
                )
            )

    wall_overhead_ns, cpu_overhead_ns = timer_overhead_ns
    print(
        "Configuracao: "
        f"chaves={key_sizes}, "
        f"iteracoes_cifrar_decifrar={operation_iterations}, "
        f"iteracoes_gerar_chave={key_generation_iterations}"
    )
    print(
        "Overhead estimado por medicao: "
        f"wall={wall_overhead_ns} ns, cpu={cpu_overhead_ns} ns"
    )
    print(f"Pico RSS do processo ao final: {max_rss_bytes() / BYTES_PER_KIB:.2f} KiB")
    print()

    return results


def main() -> None:
    results = run_benchmarks()
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
        "Espera externa (%)",
        "Pico mem Python (KiB)",
        "Mem Python atual (KiB)",
        "Delta RSS (KiB)",
    ]
    print(render_table(results_to_table(results), headers=headers))


if __name__ == "__main__":
    main()
