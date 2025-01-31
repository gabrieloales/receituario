import os
import json
import datetime
import re
import base64
import requests
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
import streamlit as st

# Configurações
USERS_FILE = "users.json"
USER_FILES_DIR = "user_files"
ADMIN_LOGIN = "larsen"
ADMIN_SENHA = "31415962Isa@"

def carregar_usuarios():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return {}

def verificar_login(login, senha):
    if login == ADMIN_LOGIN and senha == ADMIN_SENHA:
        return {"login": login, "is_admin": True}
    usuarios = carregar_usuarios()
    user_data = usuarios.get(login)
    if user_data and user_data.get("password") == senha:
        return {"login": login, "is_admin": user_data.get("is_admin", False)}
    return None

def gerar_pdf_receita(nome_pdf, paciente, tutor, cpf, especie_raca, pelagem, peso, idade, sexo, chip, lista_medicamentos, instrucoes_uso, data_receita):
    largura, altura = A4
    c = canvas.Canvas(nome_pdf, pagesize=A4)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(largura / 2, altura - 2 * cm, "Receituário Veterinário")
    c.setFont("Helvetica", 10)
    c.drawString(2 * cm, altura - 4 * cm, f"Paciente: {paciente}")
    c.drawString(2 * cm, altura - 5 * cm, f"Tutor: {tutor}")
    c.drawString(2 * cm, altura - 6 * cm, f"CPF: {cpf}")
    c.drawString(2 * cm, altura - 7 * cm, f"Espécie - Raça: {especie_raca}")
    c.drawString(2 * cm, altura - 8 * cm, f"Pelagem: {pelagem}")
    c.drawString(2 * cm, altura - 9 * cm, f"Peso: {peso}")
    c.drawString(2 * cm, altura - 10 * cm, f"Idade: {idade}")
    c.drawString(2 * cm, altura - 11 * cm, f"Sexo: {sexo}")
    c.drawString(2 * cm, altura - 12 * cm, f"Chip: {chip}")
    y = altura - 14 * cm
    for i, med in enumerate(lista_medicamentos, start=1):
        c.drawString(2 * cm, y, f"{i}) {med['quantidade']} - {med['nome']}")
        y -= 1 * cm
    c.drawString(2 * cm, y - 2 * cm, "Instruções de Uso:")
    for linha in instrucoes_uso.split("\n"):
        c.drawString(2 * cm, y - 3 * cm, linha)
        y -= 0.7 * cm
    c.showPage()
    c.save()

def main():
    st.title("Gerador de Receituário Veterinário")
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    if "usuario_logado" not in st.session_state:
        st.session_state.usuario_logado = None
    if not st.session_state.autenticado:
        login = st.text_input("Login:")
        senha = st.text_input("Senha:", type="password")
        if st.button("Entrar"):
            user_info = verificar_login(login, senha)
            if user_info:
                st.session_state.autenticado = True
                st.session_state.usuario_logado = user_info
                st.experimental_rerun()
            else:
                st.error("Login ou senha incorretos.")
        return
    if st.button("Sair", key="logout"):
        st.session_state.autenticado = False
        st.session_state.usuario_logado = None
        st.experimental_rerun()
    st.subheader("Gerar Receita")
    paciente = st.text_input("Nome do Paciente:")
    tutor = st.text_input("Nome do Tutor:")
    cpf = st.text_input("CPF do Tutor:")
    especie_raca = st.text_input("Espécie - Raça:")
    pelagem = st.text_input("Pelagem:")
    peso = st.text_input("Peso:")
    idade = st.text_input("Idade:")
    sexo = st.radio("Sexo:", ["Macho", "Fêmea"])
    chip = st.text_input("Número do Chip:")
    lista_medicamentos = []
    qtd_med = st.text_input("Quantidade do Medicamento:")
    nome_med = st.text_input("Nome do Medicamento:")
    if st.button("Adicionar Medicamento"):
        if qtd_med and nome_med:
            lista_medicamentos.append({"quantidade": qtd_med, "nome": nome_med})
            st.success("Medicamento adicionado!")
    instrucoes_uso = st.text_area("Instruções de Uso:")
    if st.button("Gerar Receita"):
        nome_pdf = "receita_veterinaria.pdf"
        gerar_pdf_receita(nome_pdf, paciente, tutor, cpf, especie_raca, pelagem, peso, idade, sexo, chip, lista_medicamentos, instrucoes_uso, datetime.datetime.now().strftime("%d/%m/%Y"))
        with open(nome_pdf, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        st.markdown(f'<a href="data:application/pdf;base64,{b64}" download="{nome_pdf}">Baixar Receita</a>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
