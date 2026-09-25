import json
import os
import time
import re
from pathlib import Path
import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai.errors import ServerError  

# ============ CONFIGURAÇÃO ============
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path) if env_path.exists() else load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Modelo principal e modelo de backup em caso de instabilidade
MODELO_PRINCIPAL = "gemini-3.5-flash-lite"
MODELO_FALLBACK = "gemini-2.5-flash"

if not GEMINI_API_KEY:
    st.error(
        "❌ Chave GEMINI_API_KEY não encontrada! Verifique o arquivo .env na raiz do projeto."
    )
    st.stop()

client = genai.Client(api_key=GEMINI_API_KEY)


# ============ GERENCIADOR DE DADOS ============
class GerenciadorDeDados:

    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.perfil_investidor = None
        self.produtos_financeiros = None
        self.historico_atendimento = None
        self.siglas_informativos = None
        self.transacoes = None

    def _ler_json(self, file_name: str) -> dict:
        """Carrega e trata exceções na leitura de arquivos JSON."""
        file_path = self.data_dir / file_name
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            st.error(f"Erro ao carregar {file_name}: {e}")
            return {}

    def _ler_csv(self, file_name: str) -> pd.DataFrame:
        """Carrega e trata exceções na leitura de arquivos CSV."""
        file_path = self.data_dir / file_name
        try:
            return pd.read_csv(file_path, encoding="utf-8")
        except Exception:
            return pd.DataFrame()

    def carregar_contexto_inicial(self) -> dict:
        """Carrega os arquivos primários necessários no início do atendimento."""
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
        """Carrega o arquivo de dúvidas/termos quando necessário."""
        if self.siglas_informativos is None:
            self.siglas_informativos = self._ler_json(
                "siglas_informativos.json"
            )
        return self.siglas_informativos

    def carregar_transacoes(self) -> pd.DataFrame:
        """Carrega o histórico de transações CSV da pasta 'data'."""
        if self.transacoes is None:
            self.transacoes = self._ler_csv("transacoes.csv")
        return self.transacoes


# ============ CARREGAR SYSTEM PROMPT DO ARQUIVO MD ============
def carregar_system_prompt(caminho_arquivo: str = "./03-prompts.md") -> str:
    """Lê as instruções e regras do assistente a partir de um arquivo Markdown."""
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


SYSTEM_PROMPT = carregar_system_prompt("./docs/03-prompts.md")

def mascarar_valores_texto(texto: str) -> str:
    """Substitui menções a valores monetários e quantias numéricas por [OCULTO]."""
    if not isinstance(texto, str):
        return texto
    # Remove 'R$ 10.000,00', 'R$10000', '10.000,00' ou sequências numéricas maiores que R$ 1.000 soltas no texto
    texto = re.sub(r'R\$\s?\d+([\.,]\d+)*', '[VALOR OCULTO]', texto)
    texto = re.sub(r'\b\d{1,3}(\.\d{3})+,\d{2}\b', '[VALOR OCULTO]', texto)
    return texto

def montar_contexto(autorizado: bool = False):
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
        # 1. Oculta dados diretos e indiretos do perfil
        renda = "[ACESSO NEGADO - Requer autorização]"
        patrimonio = "[ACESSO NEGADO - Requer autorização]"
        reserva = "[ACESSO NEGADO - Requer autorização]"
        objetivo = mascarar_valores_texto(perfil.get('objetivo_principal', 'Não informado'))
        str_historico = "[HISTÓRICO OCULTO - Requer autorização do cliente]"
        
        perfil['renda_mensal'] = "[OCULTO]"
        perfil['patrimonio_total'] = "[OCULTO]"
        perfil['reserva_emergencia_atual'] = "[OCULTO]"
        perfil['objetivo_principal'] = objetivo
        
        if 'metas' in perfil and isinstance(perfil['metas'], list):
            for meta in perfil['metas']:
                meta['valor_necessario'] = "[OCULTO - Requer autorização]"

        # 2. Oculta extratos de transações
        str_transacoes = (
            "ACESSO NEGADO/NÃO AUTORIZADO PELO CLIENTE. "
            "Você NÃO possui acesso ao extrato de transações, patrimônio, reserva ou renda. "
            "Caso precise desses dados para responder, informe o cliente que precisa da autorização dele."
        )
        
        # 3. Sanitiza o histórico de atendimentos anteriores
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

# ============ CHAMAR GEMINI COM RETRY E FALLBACK ============
def perguntar(mensagem: str, mensagens_anteriores: list, autorizado: bool) -> dict:
    contexto = montar_contexto(autorizado=autorizado)

    # Formata as mensagens do chat da sessão atual sanitizando se não houver autorização
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


# ============ INTERFACE STREAMLIT ============
st.set_page_config(
    page_title="Sumé - Educador Financeiro", page_icon="🎓", layout="centered"
)
st.title("🎓 Sumé, o Assistente e Educador Financeiro")

if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state["messages"]:
    conteudo_formatado = msg["content"].replace("$", "\\$")
    with st.chat_message(msg["role"]):
        st.markdown(conteudo_formatado)

if "autorizou_transacoes" not in st.session_state:
    st.session_state["autorizou_transacoes"] = False

TERMOS_AUTORIZACAO = ["autorizo", "pode acessar", "permito", "sim, autorizo", "consinto"]

if pergunta := st.chat_input("Sua dúvida sobre finanças..."):
    texto_lower = pergunta.lower()
    if any(termo in texto_lower for termo in TERMOS_AUTORIZACAO):
        st.session_state["autorizou_transacoes"] = True

    with st.spinner("Analisando seus dados e preparando a resposta..."):
        try:
            # Envia também o histórico de mensagens da conversa atual
            resultado = perguntar(
                mensagem=pergunta,
                mensagens_anteriores=st.session_state["messages"],
                autorizado=st.session_state["autorizou_transacoes"]
            )
            resposta_texto = resultado["resposta"]

            # Atualiza o histórico do Streamlit após a resposta do modelo
            st.session_state["messages"].append({"role": "user", "content": pergunta})
            st.session_state["messages"].append({"role": "assistant", "content": resposta_texto})
            
            with st.chat_message("user"):
                st.markdown(pergunta.replace("$", "\\$"))

            resposta_formatada = resposta_texto.replace("$", "\\$")
            with st.chat_message("assistant"):
                st.markdown(resposta_formatada)

        except Exception as err:
            st.error(f"Erro ao processar sua pergunta: {err}")

with st.sidebar:
    if st.button("🧹 Nova Conversa (Limpar Memória)"):
        st.session_state["messages"] = []
        st.session_state["autorizou_transacoes"] = False
        st.rerun()