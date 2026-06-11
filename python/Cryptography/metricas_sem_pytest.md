# Metricas do benchmark sem pytest

Este documento descreve as metricas adicionadas em `sem_pytest_metricas.py` e o que elas agregam ao benchmark RSA com a biblioteca `cryptography`.

## Objetivo

O benchmark original sem pytest media tempo medio e desvio padrao para cifracao e decifracao. A versao com metricas mantem essa ideia e acrescenta:

- tempo de parede por operacao, com media, desvio padrao, minimo, maximo e total;
- tempo de CPU por operacao, com media, desvio padrao e total;
- percentual de CPU consumido pelo processo durante a janela medida;
- pico de memoria Python observado por `tracemalloc`;
- memoria Python ainda alocada ao fim da janela medida.

A geracao de chaves fica fora da janela medida, como no `sem_pytest.py` original. Assim, o experimento continua comparando apenas cifracao e decifracao nas mesmas rodadas de `10`, `100`, `1000` e `10000` iteracoes.

## Metricas de tempo

### Wall time

O wall time e medido com `time.perf_counter()`. Ele representa o tempo observado no relogio de alta resolucao do sistema.

O que agrega:

- mostra a latencia percebida por quem executa a operacao;
- preserva as metricas originais de tempo medio e desvio padrao;
- permite comparar o custo observado de `cifrar` e `decifrar`;
- evidencia variacao entre execucoes por meio de minimo, maximo e desvio padrao.

### CPU time

O CPU time e medido com `time.process_time()`. Ele contabiliza o tempo de CPU consumido pelo proprio processo Python.

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
- em cenarios com multiplas threads nativas, o valor pode passar de 100%, pois `process_time()` soma CPU consumida pelo processo.

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

## Decisoes para reduzir interferencia

### Warmup antes da medicao

Cada operacao executa rodadas de aquecimento antes da janela medida.

Por que:

- reduz impacto de inicializacoes tardias;
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

### GC durante a janela medida

Antes da medicao, o benchmark executa `gc.collect()`. Durante a janela medida, o coletor ciclico fica desabilitado com `gc.disable()` e depois volta ao estado anterior.

Por que:

- evita que uma coleta ciclica ocorra no meio de uma operacao e distorca tempo, CPU e memoria;
- preserva o comportamento normal do processo depois da rodada;
- mantem a medicao simples sem adicionar uma infraestrutura grande ao script.

## O que foi simplificado

O benchmark usa parametros fixos no proprio arquivo, porque o objetivo e comparar sempre o mesmo conjunto de chaves e iteracoes. Para este projeto, configuracao externa nao acrescenta valor e deixa a execucao menos direta.

Foram removidos:

- fallback manual para ausencia de `tabulate`, porque `tabulate` e requisito do projeto;
- medicao separada de geracao de chave, porque o benchmark base trata isso como setup;
- leitura de RSS por `/proc/self/statm`, porque e especifica de Linux e aumenta a complexidade;
- calibracao de overhead dos temporizadores, porque o ganho e pequeno para este nivel de benchmark;
- coluna de espera externa, porque a coluna `CPU processo (%)` ja ajuda a interpretar interferencias externas.

Os parametros agora ficam explicitos no topo do arquivo:

```python
KEY_SIZES = (2048, 4096)
OPERATION_ITERATIONS = (10, 100, 1000, 10000)
```

## Como executar

Execucao padrao:

```bash
python3 Cryptography/sem_pytest_metricas.py
```

Para uma rodada menor, altere temporariamente as constantes no topo de `sem_pytest_metricas.py`.

## Leitura dos resultados

Use `Wall medio` e `Wall desvio` para comparar latencia observada. Use `CPU medio`, `CPU total` e `CPU processo (%)` para comparar custo computacional com menor impacto de escalonamento externo. Use `Pico mem Python` e `Mem Python atual` para entender alocacoes temporarias e memoria retida dentro do que `tracemalloc` consegue rastrear.
