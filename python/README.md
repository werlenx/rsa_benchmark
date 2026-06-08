# WTICG-SBSeg
Este repositório apresenta os códigos desenvolvidos no trabalho "Avaliação de diferentes implementações do sistema de criptografia RSA", submetido ao XVIII Workshop de Trabalhos de Iniciação Científica e de Graduação (WTICG) do Simpósio Brasileiro em Segurança da Informação e de Sistemas Computacionais.

## Informações Principais

### Título do Trabalho:
Avaliação de diferentes implementações do sistema de criptografia RSA

### Resumo do trabalho:
  Com o aumento do fluxo de informações entre diferentes dispositivos, os sistemas de criptografia tornaram-se essenciais para garantir a confidencialidade e a integridade dos dados. O algoritmo RSA se destaca como uma opção eficaz para prover essas garantias. Este trabalho apresenta uma pesquisa em andamento que avalia implementações do RSA, considerando distintas linguagens e bibliotecas criptográficas. Os resultados preliminares, obtidos em um único ambiente de programação, já revelam diferenças significativas no tempo médio de execução de cada processo de criptografia.

## Sumário
- [Introdução](#introdução)
- [Instalação](#instalação)
- [Organização](#organização)
- [Uso](#uso)
- [Resultados](#resultados)

## Introdução
Os experimentos iniciais foram conduzidos na linguagem de programação Python, com uso de duas bibliotecas criptográficas, [Cryptography](https://cryptography.io/) e [Pycryptodome](https://pycryptodome.readthedocs.io/). São considerados dois tamanhos de chaves, `2048` e `4096` bits, e um conjunto de iterações `[10, 100, 1000, 10000]`. Os testes foram repetidos `5` vezes, a maior parte em dias distintos.

No que tange ao microbenchmarking, utiliza-se o pytest para a medição de tempo médio. Além disso, apresenta-se uma versão que não sem o uso de versão específica de microbenchmarking.

## Instalação

Para começar, certifique-se de ter a versão mais recente do Python instalada em sua máquina. Recomenda-se realizar os testes em uma distribuição Linux.

Em seguida, instale as bibliotecas necessárias usando o seguinte comando:

```bash
pip install cryptography pycryptodome matplotlib tabulate pytest pytest-benchmark
```
## Organização
O código está dividido em duas pastas, [Cryptography](https://github.com/anacarlaquallio/WTICG-SBSeg/tree/main/Cryptography) e [Pycryptodome](https://github.com/anacarlaquallio/WTICG-SBSeg/tree/main/Pycryptodome). Nas duas pastas, tem-se a organização:

- **`api.py`**: 
  Este arquivo apresenta uma implementação do RSA com base na documentação da biblioteca, sendo a base para as implementações de microbenchmarking.

- **`sem_pytest.py`**: 
  Este arquivo apresenta o código desenvolvido para a medição do tempo médio dos processos de cifração e decifração, considerando as chaves `[2048, 4096]` e o conjunto de iterações `[10, 100, 1000, 10000]`, sem a utilização de uma ferramenta específica de microbenchmarking.

- **`pytest`**: 
  Esta pasta contém os códigos que utilizam o pytest como ferramenta de microbenchmarking. Os arquivos incluídos são:

  - **`Geral`**: Benchmarking do processo de criptografia.
  - **`Geracao`**: Benchmarking do processo de geração das chaves.
  - **`Cifracao`**: Benchmarking do processo de cifração.
  - **`Decifracao`**: Benchmarking do processo de decifração.

## Uso
### Sem uso do pytest
Os códigos **`geral.py`** e **`memoria.py`** podem ser executados com o comando:

```bash
python3 nome_arquivo.py
```

### Com o pytest
Os códigos que utilizam o pytest podem ser executados da forma:

```bash
pytest --benchmark-save=nome_arquivo
```

Além da apresentação dos resultados no terminal, será salvo um arquivo no formato `JSON` com os dados obtidos e informações sobre o ambiente de execução. Para converter esse arquivo para formato `CSV`, você pode utilizar o script em Python abaixo.

```python
import json
import csv

# Carregar os dados do arquivo JSON
with open('0005_teste05-geral.json') as json_file:
    data = json.load(json_file)

# Extrair os benchmarks
benchmarks = data['benchmarks']

# Especificar o nome do arquivo CSV
csv_file = '0005_teste05-geral-pycrypto.csv'

# Criar e escrever o arquivo CSV
with open(csv_file, mode='w', newline='') as file:
    writer = csv.writer(file)
    
    # Escrever o cabeçalho
    header = ['Name', 'Min (s)', 'Max (s)', 'Mean (s)', 'StdDev (s)', 'Median (s)', 'IQR (s)', 'Outliers', 'OPS (Kops/s)', 'Rounds', 'Iterations']
    writer.writerow(header)
    
    # Escrever os dados
    for benchmark in benchmarks:
        name = benchmark['name']
        stats = benchmark['stats']
        writer.writerow([
            name,
            '{:.15f}'.format(stats['min']),  # Formatando os números para terem 6 casas decimais
            '{:.15f}'.format(stats['max']),
            '{:.15f}'.format(stats['mean']),
            '{:.15f}'.format(stats['stddev']),
            '{:.15f}'.format(stats['median']),
            '{:.15f}'.format(stats['iqr']),
            stats['outliers'],
            '{:.15f}'.format(stats['ops']),
            stats['rounds'],
            stats['iterations']
        ])

print(f'Dados salvos em {csv_file}')
```

Para a execução, é preciso instalar as bibliotecas por meio do comando:
```bash
pip install json csv
```

## Resultados
Os dados obtidos por meio de 5 repetições do experimento podem ser visualizados [nesta planilha](https://docs.google.com/spreadsheets/d/1iL2zPLjMAbF1erl2esZhUujT43B-jvYXtMeDLPTdb-A/edit?usp=sharing).