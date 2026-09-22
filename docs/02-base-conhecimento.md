# Base de Conhecimento

## Dados Utilizados

| Arquivo | Formato | Para que serve |
|---------|---------|---------------------|
| `historico_atendimento.csv` | CSV | Contextualizar interações anteriores |
| `perfil_investidor.json` | JSON | Personalizar explicações e informativos de investimentos |
| `produtos_financeiros.json` | JSON | Sugerir produtos adequados ao perfil |
| `silgas_informativos.json` | JSON | Informativo das siglas e cálculo de rentabilidade |
| `transacoes.csv` | CSV | Analisar padrão de gastos do cliente |

---

## Adaptações nos Dados

> Você modificou ou expandiu os dados mockados? Descreva aqui.

 - Expandi os dados de produtos financeiros, há mais possibilidades de investimentos, e um breve informativo da rentabilidade de cada investimento. Além do risco, agora existe a recomendação para o perfil também 
 - Expandi as transações (geradas pelo copilot) para 1 ano
 - Adicionei um json sobre o que cada sigla quer dizer e como é tirada a rentabilidade de forma sucinta

---

## Estratégia de Integração

### Como os dados são carregados?
> Descreva como seu agente acessa a base de conhecimento.

Carrega os dados de perfil_investido.json, produtos_financeiros.json e historico_atendimento.json assim que o usuário pede informações sobre investimentos, se surgir dúvidas sobre o investimento, carrega siglas_informativos.json, assim como transacoes.csv se vier com dúvidas sobre qual investimento seria adequado:
```python
import json
from pathlib import Path
import pandas as pd


class GerenciadorDeDados:

    def __init__(self, data_dir: str = "data"):
        # Define o caminho do diretório 'data' como relativo ao arquivo do projeto
        self.data_dir = Path(data_dir)

        # Dados principais (carregados no início da consulta)
        self.perfil_investidor = None
        self.produtos_financeiros = None
        self.historico_atendimento = None

        # Dados complementares (carregados sob demanda)
        self.siglas_informativos = None
        self.transacoes = None

    def _ler_json(self, file_name: str) -> dict:
        """Carrega e trata exceções na leitura de arquivos JSON contidos na pasta 'data'."""
        file_path = self.data_dir / file_name
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(
                f"Erro: O arquivo '{file_name}' não foi encontrado na pasta '{self.data_dir}'."
            )
            return {}
        except json.JSONDecodeError:
            print(
                f"Erro: O arquivo '{file_name}' não contém um JSON válido."
            )
            return {}

    def carregar_contexto_inicial(self) -> dict:
        """Carrega os arquivos primários necessários no início do atendimento."""
        self.perfil_investidor = self._ler_json("perfil_investidor.json")
        self.produtos_financeiros = self._ler_json("produtos_financeiros.json")
        self.historico_atendimento = self._ler_json(
            "historico_atendimento.json"
        )

        return {
            "perfil": self.perfil_investidor,
            "produtos": self.produtos_financeiros,
            "historico": self.historico_atendimento,
        }

    def carregar_siglas_informativos(self) -> dict:
        """Carrega o arquivo de dúvidas/termos quando necessário."""
        if self.siglas_informativos is None:
            self.siglas_informativos = self._ler_json(
                "siglas_informativos.json"
            )
        return self.siglas_informativos

    def carregar_transacoes(self) -> pd.DataFrame:
        """Carrega o histórico de transações CSV da pasta 'data'."""
        file_path = self.data_dir / "transacoes.csv"
        try:
            if self.transacoes is None:
                self.transacoes = pd.read_csv(file_path, encoding="utf-8")
            return self.transacoes
        except FileNotFoundError:
            print(
                f"Erro: O arquivo 'transacoes.csv' não foi encontrado na pasta '{self.data_dir}'."
            )
            return pd.DataFrame()


# Exemplo de execução do fluxo
if __name__ == "__main__":
    # Inicializa o gerenciador configurado para a pasta 'data'
    gerenciador = GerenciadorDeDados(data_dir="data")

    # 1. Carregamento primário ao pedir informações de investimentos
    contexto_cliente = gerenciador.carregar_contexto_inicial()

    # 2. Carregamento sob demanda: Dúvidas sobre termos/siglas
    duvida_conceito = True
    if duvida_conceito:
        glossario = gerenciador.carregar_siglas_informativos()

    # 3. Carregamento sob demanda: Análise de transações passadas
    duvida_adequacao = True
    if duvida_adequacao:
        historico_transacoes = gerenciador.carregar_transacoes()
```

### Como os dados são usados no prompt?
> Os dados vão no system prompt? São consultados dinamicamente?

 - Diretrizes Estáticas (System Prompt): 
 Contém a persona do agente (educado, claro e didático), as instruções de conduta, as regras do modo analogia e os guardrails rígidos (proibição de alucinar dados e obrigatoriedade de informar caso um ativo não exista na base).

 - Contexto Primário Injetado Dinamicamente: 
 Assim que o cliente inicia a consulta de investimentos, a aplicação lê `perfil_investidor.json`, `produtos_financeiros.json` e `historico_atendimento.json` e injeta essas estruturas no trecho de User Context do prompt para que o modelo processe o saldo, suitability e o catálogo de ativos.

 - Consulta Sob Demanda (RAG / Carregamento sob Condição):
Se a mensagem do cliente contiver dúvidas sobre termos conceituais (ex: "O que é CDI?", "O que significa Liquidez?"), o arquivo `siglas_informativos.json` é lido e anexado dinamicamente ao prompt.

Se o cliente pedir sugestões personalizadas sobre adequação ao seu histórico de gastos, o DataFrame de `transacoes.csv` é sumarizado e anexado ao contexto antes da geração da resposta.

---

## Exemplo de Contexto Montado

> Mostre um exemplo de como os dados são formatados para o agente.

O exemplo abaixo se baseia nos dados originais da base de conhecimento, sintetizado como as informações serão utilizada pelo agente.

```text
DADOS DO CLIENTE:
 - nome: João Silva
 - Perfil: Moderado
 - Objetivo: Construir reserva de emergência
 - Reserva atual: 10000.00
 - Reserva recomendada: 3 a 4x o total de sáidas recorrentes do resumo de gastos

RESUMO DE GASTOS: 
 - Entradas (Salário):
    R$ 5.000,00 por mês

 - Saídas recorrentes (fixas todo mês):
    - Aluguel: R$ 1.200,00/mês
    - Supermercado: ~R$ 500,00/mês
    - Conta de Luz: ~R$ 200,00/mês
    - Academia: R$ 99,00/mês
    - Combustível: ~R$ 275,00/mês
    - Farmácia: ~R$ 120,00/mês
    - Uber: ~R$ 70,00/mês
    - Lazer/Assinaturas: ~R$ 100,00/mês (Netflix, Spotify, Cinema, etc.)
    *- TOTAL: ~R$ 3.764,00/mês* 

INVESTIMENTOS DISPONÍVES:
 - Tesouro Selic (risco baixo), Aporte mínimo de R$ 30.00, rendimento de 100% da taxa Selic
 - CDB Liquidez Diária (risco baixo), Aporte mínimo de R$ 100.00, rendimento de 102% do CDI
 - LCI/LCA (risco baixo), Aporte mínimo de R$ 1000.00, rendimento de 95% do CDI
 - Fundo Multimercado (risco medio), Aporte mínimo de R$ 500.00, rendimento de CDI + 2%
 - Fundo de Ações (risco alto), Aporte mínimo de R$ 100.00, rendimento de Variável
 - Debêntures Incentivadas (risco medio), Aporte mínimo de R$ 1000.00, rendimento de IPCA + 5%

INFORMATIVOS DOS INVESTIMENTOS E SIGLAS:
 - nome: CDI
      - definição: Certificado de Depósito Interbancário, taxa média dos empréstimos entre bancos.
      - rendimento: Varia conforme a taxa Selic, acompanhando de perto os juros básicos da economia.
 - nome: CDB
      - definicao: Certificado de Depósito Bancário, título emitido por bancos para captar recursos.
      - rendimento: Pode ser prefixado, pós-fixado (atrelado ao CDI) ou híbrido (CDI + IPCA).
 - nome: Selic
      - definicao: Taxa básica de juros da economia brasileira, definida pelo Banco Central.
      - rendimento: Alterada pelo Copom para controlar inflação e estimular ou frear a economia.
 - nome: IPCA
      - definicao: Índice Nacional de Preços ao Consumidor Amplo, indicador oficial da inflação.
      - rendimento: Oscila conforme a variação dos preços de bens e serviços consumidos pelas famílias.
 - nome: ETF
      - definicao: Exchange Traded Fund, fundo negociado em bolsa que replica índices de mercado.
      - rendimento: Varia conforme o desempenho do índice que acompanha (Ibovespa, S&P500, criptoativos).
 - nome: Cripto
      - definicao: Ativos digitais descentralizados, como Bitcoin e Ethereum.
      - rendimento: Oscilam de acordo com oferta e demanda global, sem lastro em indicadores econômicos tradicionais.
```
