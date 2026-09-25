# Base de Conhecimento

## Dados Utilizados

| Arquivo | Formato | Para que serve |
|---------|---------|---------------------|
| `historico_atendimento.json` / `historico_atendimento.csv` | JSON / CSV | Contextualizar interações anteriores e histórico de suporte do cliente |
| `perfil_investidor.json` | JSON | Personalizar explicações, validar suitability, metas e informações do perfil |
| `produtos_financeiros.json` | JSON | Sugerir catálogo de produtos de investimento adequados ao perfil |
| `siglas_informativos.json` | JSON | Consultar conceitos, termos técnicos (CDI, Selic, IPCA) e regras de rentabilidade |
| `transacoes.csv` | CSV | Analisar extrato, padrões de receita/despesas e apoiar recomendações de reserva |
| `03-prompts.md` / `docs/03-prompts.md` | Markdown | Fornecer as diretrizes estáticas (System Prompt), persona e regras de conduta do assistente |

---

## Adaptações e Regras de Segurança dos Dados

- **Mascaramento e Privacidade de Dados (Guardrails de LGPD):** 
  Implementada a função `mascarar_valores_texto()` utilizando expressões regulares (`re.sub`). Quando o usuário não autoriza o acesso aos seus dados financeiros sensíveis, valores monetários (ex: salários, patrimônio, limites e despesas) são substituídos pela tag `[VALOR OCULTO]` ou `[ACESSO NEGADO]`.
- **Controle Dinâmico de Autorização (Opt-In):**
  O sistema monitora o chat em busca de termos de autorização (ex.: `"autorizo"`, `"permito"`, `"pode acessar"`). Enquanto o consentimento não for detectado, o extrato de transações e detalhes financeiros são omitidos ou sanitizados.
- **Formatação de Dados Híbrida:**
  O suporte ao histórico de atendimento foi expandido para aceitar tanto arquivos `.csv` quanto `.json`, garantindo resiliência no carregamento.

---

## Estrutura do Código e Explicação das Funções (`app.py`)

### 1. Gerenciador de Dados (`GerenciadorDeDados`)

Classe responsável por centralizar a leitura e o acesso aos arquivos físicos localizados na pasta `./data`.

```python
class GerenciadorDeDados:

    def __init__(self, data_dir: str = "./data"):
        """Inicializa a classe definindo o diretório padrão e atributos de cache dos dados."""
        self.data_dir = Path(data_dir)
        self.perfil_investidor = None
        self.produtos_financeiros = None
        self.historico_atendimento = None
        self.siglas_informativos = None
        self.transacoes = None

    def _ler_json(self, file_name: str) -> dict:
        """Método privado com tratamento de exceções (FileNotFoundError e JSONDecodeError) 
        para leitura segura de arquivos JSON."""
        file_path = self.data_dir / file_name
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            st.error(f"Erro ao carregar {file_name}: {e}")
            return {}

    def _ler_csv(self, file_name: str) -> pd.DataFrame:
        """Método privado para leitura de tabelas CSV utilizando pandas, retornando um 
        DataFrame vazio em caso de erro."""
        file_path = self.data_dir / file_name
        try:
            return pd.read_csv(file_path, encoding="utf-8")
        except Exception:
            return pd.DataFrame()

    def carregar_contexto_inicial(self) -> dict:
        """Carrega os dados primários (Perfil, Produtos e Histórico de Atendimento) 
        necessários na inicialização da conversa."""
        self.perfil_investidor = self._ler_json("perfil_investidor.json")
        self.produtos_financeiros = self._ler_json("produtos_financeiros.json")

        file_path_hist = self.data_dir / "historico_atendimento.csv"
        if file_path_hist.exists():
            self.historico_atendimento = self._ler_csv(
                "historico_atendimento.csv"
            )
        else:
            self.historico_atendimento = self._ler_json(
                "historico_atendimento.json"
            )

        return {
            "perfil": self.perfil_investidor,
            "produtos": self.produtos_financeiros,
            "historico": self.historico_atendimento,
        }

    def carregar_siglas_informativos(self) -> dict:
        """Carrega sob demanda o dicionário de siglas e informativos conceituais."""
        if self.siglas_informativos is None:
            self.siglas_informativos = self._ler_json(
                "siglas_informativos.json"
            )
        return self.siglas_informativos

    def carregar_transacoes(self) -> pd.DataFrame:
        """Carrega sob demanda a tabela de transações do cliente."""
        if self.transacoes is None:
            self.transacoes = self._ler_csv("transacoes.csv")
        return self.transacoes

```

---

### 2. Carregamento do Prompt do Sistema (`carregar_system_prompt`)

Lê e carrega as instruções da persona "Sumé" registradas no arquivo Markdown externo (`03-prompts.md`).

```python
def carregar_system_prompt(caminho_arquivo: str = "./03-prompts.md") -> str:
    """Carrega as diretrizes do assistente a partir do arquivo .md. 
    Caso o arquivo não exista no caminho informado, busca em locais alternativos 
    ou ativa um prompt de fallback padrão."""
    caminho = Path(caminho_arquivo)

    if not caminho.exists():
        caminho = Path(__file__).resolve().parent / "03-prompts.md"

    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        st.warning(
            f"⚠️ Arquivo '{caminho_arquivo}' não encontrado! Usando prompt padrão."
        )
        return "Você é o Sumé, um assistente e educador financeiro amigável e didático."

```

---

### 3. Mascaramento e Sanitização de Dados (`mascarar_valores_texto`)

Garante que nenhuma menção explícita a quantias monetárias seja exposta ao modelo sem consentimento do usuário.

```python
def mascarar_valores_texto(texto: str) -> str:
    """Aplica Expressões Regulares (Regex) para identificar formatos numéricos 
    e cifrões (ex.: R$ 10.000,00 ou 1.000,00) e os substitui por '[VALOR OCULTO]'."""
    if not isinstance(texto, str):
        return texto
    texto = re.sub(r'R\$\s?\d+([\.,]\d+)*', '[VALOR OCULTO]', texto)
    texto = re.sub(r'\b\d{1,3}(\.\d{3})+,\d{2}\b', '[VALOR OCULTO]', texto)
    return texto

```

---

### 4. Montagem Dinâmica de Contexto (`montar_contexto`)

Constrói o bloco de contexto que será fornecido ao LLM, ajustando a visibilidade das informações financeiras de acordo com o parâmetro `autorizado`.

```python
def montar_contexto(autorizado: bool = False):
    """Instancia o GerenciadorDeDados e formata a string de contexto.
    - Se autorizado == True: Inclui renda, patrimônio, reserva, histórico e tabela de transações na íntegra.
    - Se autorizado == False: Mascara os valores financeiros do perfil, oculta extratos e sanitiza o histórico prévio."""
    gerenciador = GerenciadorDeDados(data_dir="./data")
    dados_iniciais = gerenciador.carregar_contexto_inicial()
    
    perfil = json.loads(json.dumps(dados_iniciais.get("perfil", {})))
    produtos = dados_iniciais.get("produtos", {})
    historico = dados_iniciais.get("historico", pd.DataFrame())

    if autorizado:
        renda = f"R$ {perfil.get('renda_mensal', 0.0):,.2f}"
        patrimonio = f"R$ {perfil.get('patrimonio_total', 0.0):,.2f}"
        reserva = f"R$ {perfil.get('reserva_emergencia_atual', 0.0):,.2f}"
        objetivo = perfil.get('objetivo_principal', 'Não informado')
        
        transacoes = gerenciador.carregar_transacoes()
        str_transacoes = (
            transacoes.to_string(index=False)
            if not transacoes.empty
            else "Nenhuma transação registrada."
        )
        
        str_historico = (
            historico.to_string(index=False)
            if isinstance(historico, pd.DataFrame)
            else json.dumps(historico, indent=2, ensure_ascii=False)
        )
    else:
        # Oculta informações financeiras diretas e indiretas
        renda = "[ACESSO NEGADO - Requer autorização]"
        patrimonio = "[ACESSO NEGADO - Requer autorização]"
        reserva = "[ACESSO NEGADO - Requer autorização]"
        objetivo = mascarar_valores_texto(perfil.get('objetivo_principal', 'Não informado'))
        
        perfil['renda_mensal'] = "[OCULTO]"
        perfil['patrimonio_total'] = "[OCULTO]"
        perfil['reserva_emergencia_atual'] = "[OCULTO]"
        perfil['objetivo_principal'] = objetivo
        
        if 'metas' in perfil and isinstance(perfil['metas'], list):
            for meta in perfil['metas']:
                meta['valor_necessario'] = "[OCULTO - Requer autorização]"

        str_transacoes = (
            "ACESSO NEGADO/NÃO AUTORIZADO PELO CLIENTE. "
            "Você NÃO possui acesso ao extrato de transações, patrimônio, reserva ou renda. "
            "Caso precise desses dados para responder, informe o cliente que precisa da autorização dele."
        )
        
        # Sanitiza atendimentos anteriores
        if isinstance(historico, pd.DataFrame):
            historico_sanitizado = historico.copy()
            for col in historico_sanitizado.columns:
                historico_sanitizado[col] = historico_sanitizado[col].astype(str).apply(mascarar_valores_texto)
            str_historico = historico_sanitizado.to_string(index=False)
        else:
            str_historico_raw = json.dumps(historico, indent=2, ensure_ascii=False)
            str_historico = mascarar_valores_texto(str_historico_raw)

    contexto = f"""
CLIENTE: {perfil.get('nome', 'Não informado')}, {perfil.get('idade', 'N/A')} anos, perfil {perfil.get('perfil_investidor', 'Não identificado')}
RENDA MENSAL: {renda}
OBJETIVO: {objetivo}
PATRIMÔNIO: {patrimonio} | RESERVA: {reserva}

DETALHES DO PERFIL:
{json.dumps(perfil, indent=2, ensure_ascii=False)}

TRANSAÇÕES RECENTES:
{str_transacoes}

ATENDIMENTOS ANTERIORES:
{str_historico}

PRODUTOS DISPONÍVEIS:
{json.dumps(produtos, indent=2, ensure_ascii=False)}
"""
    return contexto

```

---

### 5. Invocação da LLM com Retry e Fallback (`perguntar`)

Gere a resposta do assistente acionando a API do Google Gemini com mecânica de redundância de modelos (Fallback).

```python
def perguntar(mensagem: str, mensagens_anteriores: list, autorizado: bool) -> dict:
    """
    1. Prepara a string do contexto com base no estado de autorização.
    2. Formata o histórico do chat da sessão corrente (sanitizando o histórico se não autorizado).
    3. Une SYSTEM_PROMPT + CONTEXTO + HISTÓRICO DA CONVERSA + PERGUNTA ATUAL.
    4. Executa a requisição tentando primeiro o MODELO_PRINCIPAL; em caso de falha, aciona o MODELO_FALLBACK.
    5. Retorna um dicionário contendo a resposta e métricas de tempo de execução.
    """
    contexto = montar_contexto(autorizado=autorizado)

    historico_chat_sessao = ""
    for msg in mensagens_anteriores:
        role = "Cliente" if msg["role"] == "user" else "Assistente"
        conteudo = msg["content"]
        if not autorizado:
            conteudo = mascarar_valores_texto(conteudo)
        historico_chat_sessao += f"\n{role}: {conteudo}"

    prompt_completo = f"""
{SYSTEM_PROMPT}

CONTEXTO DO USUÁRIO LOGADO:
{contexto}

HISTÓRICO DA CONVERSA ATUAL:
{historico_chat_sessao}

Pergunta Atual do Cliente: {mensagem}
"""
    inicio = time.time()
    modelos_para_tentar = [MODELO_PRINCIPAL, MODELO_FALLBACK]

    response = None
    ultimo_erro = None

    for modelo in modelos_para_tentar:
        try:
            response = client.models.generate_content(
                model=modelo, contents=prompt_completo
            )
            break
        except Exception as e:
            ultimo_erro = e
            time.sleep(1)
            continue

    if response is None:
        raise Exception(f"Erro ao consultar modelo: {ultimo_erro}")

    tempo_execucao = round(time.time() - inicio, 2)
    return {
        "resposta": response.text,
        "metricas": {"tempo_segundos": tempo_execucao},
    }

```

---

### 6. Camada de Interface do Usuário (`Streamlit`)

Gerencia a renderização do chat, controle de estado do consentimento e interações do usuário na interface web.

```python
# Configuração da página e títulos
st.set_page_config(
    page_title="Sumé - Educador Financeiro", page_icon="🎓", layout="centered"
)
st.title("🎓 Sumé, o Assistente e Educador Financeiro")

# Inicialização da memória de mensagens da sessão
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Exibição do histórico de mensagens no chat
for msg in st.session_state["messages"]:
    # Trata o caractere '$' para evitar problemas com parsing de equações no LaTeX do Streamlit
    conteudo_formatado = msg["content"].replace("$", "\\$")
    with st.chat_message(msg["role"]):
        st.markdown(conteudo_formatado)

# Inicialização do estado de autorização
if "autorizou_transacoes" not in st.session_state:
    st.session_state["autorizou_transacoes"] = False

TERMOS_AUTORIZACAO = ["autorizo", "pode acessar", "permito", "sim, autorizo", "consinto"]

# Captura do input do usuário
if pergunta := st.chat_input("Sua dúvida sobre finanças..."):
    texto_lower = pergunta.lower()
    
    # Verifica se a mensagem contém gatilhos de consentimento
    if any(termo in texto_lower for termo in TERMOS_AUTORIZACAO):
        st.session_state["autorizou_transacoes"] = True

    with st.spinner("Analisando seus dados e preparando a resposta..."):
        try:
            # Invoca a função perguntar com a pergunta, histórico e permissão atual
            resultado = perguntar(
                mensagem=pergunta,
                mensagens_anteriores=st.session_state["messages"],
                autorizado=st.session_state["autorizou_transacoes"]
            )
            resposta_texto = resultado["resposta"]

            # Atualiza a memória de mensagens da sessão
            st.session_state["messages"].append({"role": "user", "content": pergunta})
            st.session_state["messages"].append({"role": "assistant", "content": resposta_texto})
            
            # Exibe as novas mensagens na tela
            with st.chat_message("user"):
                st.markdown(pergunta.replace("$", "\\$"))

            resposta_formatada = resposta_texto.replace("$", "\\$")
            with st.chat_message("assistant"):
                st.markdown(resposta_formatada)

        except Exception as err:
            st.error(f"Erro ao processar sua pergunta: {err}")

# Barra lateral com funcionalidade para resetar o estado e memória da sessão
with st.sidebar:
    if st.button("🧹 Nova Conversa (Limpar Memória)"):
        st.session_state["messages"] = []
        st.session_state["autorizou_transacoes"] = False
        st.rerun()

```

### Como os dados são usados no prompt?

* **Diretrizes Estáticas (System Prompt):**
Define a persona do assistente de investimentos (didático, cortês e objetivo), instruções de conduta, guardrails rígidos (proibição de inventar produtos/dados inexistentes na base) e suporte ao modo analogia.
* **Contexto Primário Injetado Dinamicamente:**
Ao iniciar uma sessão de orientação, o método `carregar_contexto_inicial()` fornece `perfil_investidor.json`, `produtos_financeiros.json` e `historico_atendimento.json`, injetando diretamente o perfil do cliente, saldo, histórico de conversas anteriores e a lista de produtos disponíveis.
* **Consulta Sob Demanda (RAG / Carregamento sob Condição):**
* **Dúvidas conceituais:** Caso a interação envolva perguntas sobre termos técnicos ou siglas (ex.: "O que é CDI?"), invoca-se `carregar_siglas_informativos()`.
* **Análise orçamentária:** Se o usuário solicitar recomendações com base no seu padrão de gastos ou cálculo de reserva de emergência, invoca-se `carregar_transacoes()` para ler e sumarizar os dados do arquivo `transacoes.csv`.



---

## Exemplo de Contexto Montado

```text
DADOS DO CLIENTE:
 - Nome: João Silva
 - Perfil: Moderado
 - Objetivo: Construir reserva de emergência
 - Reserva atual: R$ 10.000,00
 - Reserva recomendada: 3x a 6x o total de saídas recorrentes

RESUMO DE GASTOS: 
 - Entradas (Salário): R$ 5.000,00/mês
 - Saídas recorrentes (fixas todo mês):
    - Aluguel: R$ 1.200,00/mês
    - Supermercado: ~R$ 500,00/mês
    - Conta de Luz: ~R$ 200,00/mês
    - Academia: R$ 99,00/mês
    - Combustível: ~R$ 275,00/mês
    - Farmácia: ~R$ 120,00/mês
    - Uber: ~R$ 70,00/mês
    - Lazer/Assinaturas: ~R$ 100,00/mês
    - TOTAL: ~R$ 3.764,00/mês

INVESTIMENTOS DISPONÍVEIS:
 - Tesouro Selic (risco baixo), Aporte mínimo de R$ 30,00, rendimento de 100% da taxa Selic
 - CDB Liquidez Diária (risco baixo), Aporte mínimo de R$ 100,00, rendimento de 102% do CDI
 - LCI/LCA (risco baixo), Aporte mínimo de R$ 1.000,00, rendimento de 95% do CDI
 - Fundo Multimercado (risco médio), Aporte mínimo de R$ 500,00, rendimento de CDI + 2%
 - Fundo de Ações (risco alto), Aporte mínimo de R$ 100,00, rendimento Variável
 - Debêntures Incentivadas (risco médio), Aporte mínimo de R$ 1.000,00, rendimento de IPCA + 5%

INFORMATIVOS DOS INVESTIMENTOS E SIGLAS:
 - CDI: Certificado de Depósito Interbancário, taxa média dos empréstimos entre bancos. Acompanha de perto a taxa Selic.
 - CDB: Certificado de Depósito Bancário, título emitido por bancos para captar recursos. Pode ser pré, pós (CDI) ou híbrido.
 - Selic: Taxa básica de juros da economia brasileira, definida pelo Banco Central.
 - IPCA: Índice Nacional de Preços ao Consumidor Amplo, indicador oficial da inflação no Brasil.
 - ETF: Exchange Traded Fund, fundo negociado em bolsa que replica índices de mercado (ex.: Ibovespa).
 - Cripto: Ativos digitais descentralizados (ex.: Bitcoin), com rentabilidade dependente de oferta e demanda global.

```