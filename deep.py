import os
import json
import datetime
import re
import requests
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
import streamlit as st

# ----------------------------------------------
# CONSTANTES E CONFIGURAÇÕES
# ----------------------------------------------
USERS_FILE = "users.json"       # Arquivo para armazenar usuários
USER_FILES_DIR = "user_files"   # Pasta base para armazenar arquivos de cada usuário

# Administrador "principal" hard-coded (opcional).
ADMIN_LOGIN = "larsen"
ADMIN_SENHA = "31415962Isa@"

# ----------------------------------------------
# FUNÇÕES DE APOIO GERAIS
# ----------------------------------------------

def buscar_endereco_via_cep(cep: str) -> dict:
    """Tenta buscar o endereço via CEP. Se não achar, retorna dicionário vazio."""
    cep_limpo = re.sub(r'\D', '', cep)
    if not cep_limpo:
        return {}
    try:
        url = f"https://viacep.com.br/ws/{cep_limpo}/json/"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        dados = r.json()
        if "erro" in dados:
            return {}
        return {
            "logradouro": dados.get("logradouro", ""),
            "bairro": dados.get("bairro", ""),
            "localidade": dados.get("localidade", ""),
            "uf": dados.get("uf", "")
        }
    except:
        return {}

# ----------------------------------------------
# INTERFACE PRINCIPAL (STREAMLIT)
# ----------------------------------------------

def tela_receita():
    st.subheader("Gerar Receituário")

    # CEP - busca automática ou manual
    cep_digitado = st.text_input("CEP do Tutor(a) (somente números):")
    if st.button("Consultar CEP"):
        if cep_digitado.strip():
            dados_end = buscar_endereco_via_cep(cep_digitado)
            if dados_end:
                st.session_state.end_busca = dados_end
                st.success(f"Endereço encontrado: {dados_end.get('logradouro')}, {dados_end.get('bairro')}, {dados_end.get('localidade')}-{dados_end.get('uf')}")
            else:
                st.warning("CEP não encontrado. Preencha manualmente.")
                st.session_state.end_busca = {}

    dados_cep = st.session_state.get("end_busca", {})

    if dados_cep:
        logradouro = dados_cep.get("logradouro", "")
        bairro = dados_cep.get("bairro", "")
        cidade = dados_cep.get("localidade", "")
        uf = dados_cep.get("uf", "")
    else:
        logradouro = st.text_input("Logradouro (Rua):")
        bairro = st.text_input("Bairro:")
        cidade = st.text_input("Cidade:")
        uf = st.text_input("UF:")

    numero = st.text_input("Número:")
    complemento = st.text_input("Complemento (opcional):")

    # Montamos o endereço formatado
    endereco_formatado = f"{logradouro}, {numero}, {bairro}, {cidade}-{uf}"
    if complemento:
        endereco_formatado += f" (Compl.: {complemento})"
    if cep_digitado:
        endereco_formatado += f" - CEP: {cep_digitado}"

    # Exibir o endereço final
    st.write("Endereço Final:", endereco_formatado)

# ----------------------------------------------
# INICIALIZAÇÃO
# ----------------------------------------------
if __name__ == "__main__":
    # Cria pasta para arquivos de usuários, se não existir
    if not os.path.exists(USER_FILES_DIR):
        os.makedirs(USER_FILES_DIR)

    tela_receita()
