# Metricas do benchmark sem pytest

Este documento descreve as metricas adicionadas em `sem_pytest_metricas.py`, por que cada decisao de medicao foi tomada e o que cada metrica agrega ao benchmark RSA com a biblioteca `cryptography`.

## Objetivo

O benchmark original sem pytest media tempo medio e desvio padrao para cifracao e decifracao. A nova copia mantem essas metricas e acrescenta:

- tempo de parede por operacao, com media, desvio padrao, minimo, maximo e total;
- tempo de CPU por operacao, com media, desvio padrao e total;
- percentual de CPU consumido pelo processo durante a janela medida;
- percentual de espera externa estimada;
- pico de memoria Python observado por `tracemalloc`;
- memoria Python ainda alocada ao fim da janela medida;
- variacao de RSS do processo.

A copia tambem mede `gerar_chave`, alem de `cifrar` e `decifrar`, porque a geracao de chaves e uma parte importante do custo real de uso de RSA e ja aparece no conjunto de testes com pytest.

## Metricas de tempo

### Wall time

O wall time e medido com `time.perf_counter_ns()`. Ele representa o tempo observado no relogio de alta resolucao do sistema.

O que agrega:

- mostra a latencia percebida por quem executa a operacao;
- preserva as metricas originais de tempo medio e desvio padrao;
- permite comparar o custo observado de `gerar_chave`, `cifrar` e `decifrar`;
- evidencia variacao entre execucoes por meio de minimo, maximo e desvio padrao.

### CPU time

O CPU time e medido com `time.process_time_ns()`. Ele contabiliza o tempo de CPU consumido pelo proprio processo Python.

O que agrega:

- reduz o impacto de interferencia de outros processos na metrica principal de consumo computacional;
- separa custo real de processamento de atrasos causados por escalonamento do sistema operacional;
- ajuda a identificar se uma operacao e CPU-bound.

### CPU do processo (%)

O percentual de CPU do processo e calculado como:

```text
CPU total / wall total * 100
```

O que agrega:

- valores proximos de 100% indicam que o processo ficou ocupado em CPU durante quase toda a janela medida;
- valores muito abaixo de 100% sugerem espera, preempcao pelo sistema operacional ou outro tipo de ruido externo;
- em cenarios com multiplas threads nativas, o valor pode passar de 100%, pois `process_time_ns()` soma CPU consumida pelo processo.

### Espera externa (%)

A espera externa estimada e calculada como:

```text
max(0, wall total - CPU total) / wall total * 100
```

O que agrega:

- funciona como um indicador de interferencia residual;
- ajuda a decidir se uma rodada deve ser repetida em um ambiente mais silencioso;
- evita mascarar ruido descartando resultados automaticamente.

## Metricas de memoria

### Pico de memoria Python

O pico de memoria Python e medido com `tracemalloc.get_traced_memory()`, iniciado depois do setup e antes da janela medida.

O que agrega:

- mede alocacoes rastreadas pelo interpretador Python durante a operacao;
- evita incluir custo de setup, como geracao de chaves reaproveitadas para cifracao e decifracao;
- captura picos temporarios de objetos Python, mesmo quando eles sao liberados antes do fim da medicao.

Limitacao:

- `tracemalloc` nao mede toda memoria nativa usada por OpenSSL ou pela biblioteca `cryptography`.

### Memoria Python atual

E a memoria Python rastreada que continua alocada ao fim da janela medida.

O que agrega:

- ajuda a diferenciar alocacao temporaria de memoria retida;
- pode indicar crescimento acumulado quando comparada entre rodadas.

### Delta RSS

O RSS e lido de `/proc/self/statm` antes e depois da janela medida. Ele representa paginas residentes do processo no sistema operacional.

O que agrega:

- inclui memoria do processo como um todo, inclusive partes nativas que `tracemalloc` nao rastreia;
- ajuda a detectar crescimento de memoria fora do heap Python;
- complementa o pico Python com uma visao do sistema operacional.

Limitacoes:

- o RSS pode nao cair imediatamente quando objetos sao liberados, porque o alocador pode manter memoria reservada;
- o delta antes/depois pode perder picos muito curtos;
- esta leitura depende de Linux por usar `/proc/self/statm`.

## Decisoes para reduzir interferencia

### GC pausado durante a janela medida

Antes de cada janela medida, o benchmark executa `gc.collect()`. Durante a janela medida, o coletor ciclico fica desabilitado com `gc.disable()`. Depois da coleta das metricas, o estado anterior do GC e restaurado e uma nova coleta e feita fora da medicao.

Por que:

- evita que uma coleta ciclica ocorra no meio de uma operacao e distorca tempo, CPU e memoria;
- mantem a limpeza fora da janela medida;
- preserva o comportamento normal do processo apos cada rodada.

Observacao:

- desabilitar o GC ciclico nao desativa contagem de referencias do CPython. Objetos comuns ainda podem ser liberados normalmente quando perdem a ultima referencia.

### Warmup antes da medicao

Cada operacao executa rodadas de aquecimento antes da janela medida.

Por que:

- reduz impacto de inicializacoes preguiçosas;
- aquece caminhos de codigo usados pela biblioteca;
- diminui ruido de alocacoes iniciais que nao representam a operacao em regime.

### Setup fora da janela medida

Para cifracao e decifracao, as chaves sao geradas antes da medicao e reaproveitadas. Para decifracao, o ciphertext tambem e preparado antes da janela medida.

Por que:

- isola o custo da operacao que esta sendo medida;
- mantem compatibilidade com o benchmark original, que reaproveitava chaves;
- evita misturar custo de geracao de chave com custo de cifrar ou decifrar.

### Sem I/O dentro da janela medida

O benchmark nao imprime, nao grava arquivos e nao gera mensagens aleatorias dentro das iteracoes medidas de cifracao e decifracao.

Por que:

- I/O e chamadas ao sistema podem introduzir latencia externa;
- a metrica fica mais focada no custo criptografico.

### Calibracao do overhead dos temporizadores

Antes das medicoes, o script mede o menor custo observado de uma janela vazia com os mesmos temporizadores e subtrai esse overhead de cada iteracao.

Por que:

- reduz o peso das chamadas a `perf_counter_ns()` e `process_time_ns()`;
- e especialmente util para operacoes rapidas, como cifracao com chave menor;
- usar o menor overhead observado evita descontar ruido externo como se fosse custo fixo.

### Interferencia de terceiros processos

Nao e possivel garantir, a partir de um script Python comum, que outros processos do sistema operacional nao concorram por CPU. Por isso, o benchmark toma duas decisoes complementares:

- usa CPU time para medir o consumo do proprio processo;
- reporta espera externa para sinalizar quando o wall time ficou maior que o CPU time.

Com isso, o benchmark nao promete eliminar todo ruido externo, mas torna esse ruido visivel e reduz sua influencia na interpretacao principal.

## Como executar

Execucao padrao:

```bash
python3 Cryptography/sem_pytest_metricas.py
```

Para uma rodada menor, util em validacao rapida:

```bash
RSA_BENCHMARK_ITERATIONS=10 RSA_BENCHMARK_KEYGEN_ITERATIONS=2 python3 Cryptography/sem_pytest_metricas.py
```

Variaveis disponiveis:

- `RSA_BENCHMARK_KEY_SIZES`: tamanhos de chave separados por virgula. Padrao: `2048,4096`;
- `RSA_BENCHMARK_ITERATIONS`: iteracoes de cifracao e decifracao separadas por virgula. Padrao: `10,100,1000,10000`;
- `RSA_BENCHMARK_KEYGEN_ITERATIONS`: iteracoes de geracao de chave. Padrao: `15`;
- `RSA_BENCHMARK_TIMER_OVERHEAD_SAMPLES`: amostras usadas para calibrar overhead dos temporizadores. Padrao: `1000`.

## Leitura dos resultados

Use `Wall medio` e `Wall desvio` para comparar latencia observada. Use `CPU medio` e `CPU total` para comparar custo computacional com menor impacto de escalonamento externo. Use `Espera externa (%)` para identificar rodadas contaminadas por concorrencia do sistema. Use `Pico mem Python`, `Mem Python atual` e `Delta RSS` em conjunto para entender alocacoes temporarias, memoria retida e crescimento do processo no nivel do sistema operacional.
