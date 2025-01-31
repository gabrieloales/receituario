import os
import json
import datetime
import re
import base64
import requests
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import streamlit as st

# ----------------------------------------------
# CONSTANTES E CONFIGURAÇÕES
# ----------------------------------------------
USER_FILES_DIR = "user_files"   # Pasta base para armazenar arquivos de cada usuário

# ----------------------------------------------
# FUNÇÃO PARA GERAR O PDF
# ----------------------------------------------
def gerar_pdf_receita(
    nome_pdf,
    paciente="",
    tutor="",
    cpf="",
    lista_medicamentos=None,
    instrucoes_uso="",
    nome_vet=None,
    crmv=None
):
    """
    Gera um PDF de receita veterinária.
    """
    if lista_medicamentos is None:
        lista_medicamentos = []
    
    largura, altura = A4
    c = canvas.Canvas(nome_pdf, pagesize=A4)
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, altura - 100, "Receituário Veterinário")
    c.setFont("Helvetica", 12)
    c.drawString(100, altura - 130, f"Paciente: {paciente}")
    c.drawString(100, altura - 150, f"Tutor: {tutor}")
    c.drawString(100, altura - 170, f"CPF: {cpf}")
    
    y_meds = altura - 200
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, y_meds, "Medicamentos:")
    c.setFont("Helvetica", 11)
    y_meds -= 20
    for i, med in enumerate(lista_medicamentos, start=1):
        c.drawString(100, y_meds, f"{i}) {med['quantidade']} - {med['nome']}")
        y_meds -= 20
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, y_meds - 20, "Instruções de Uso:")
    c.setFont("Helvetica", 11)
    y_meds -= 40
    for linha in instrucoes_uso.split("\n"):
        c.drawString(100, y_meds, linha)
        y_meds -= 20
    
    c.setFont("Helvetica", 11)
    c.drawString(100, y_meds - 40, f"Veterinário(a): {nome_vet}")
    c.drawString(100, y_meds - 60, f"CRMV: {crmv}")
    
    c.showPage()
    c.save()
    return nome_pdf

# ----------------------------------------------
# STREAMLIT INTERFACE
# ----------------------------------------------
def main():
    st.title("Gerador de Receituário Veterinário")
    
    paciente = st.text_input("Nome do Paciente:")
    tutor = st.text_input("Nome do Tutor(a):")
    cpf = st.text_input("CPF do Tutor(a):")
    
    qtd_med = st.text_input("Quantidade do Medicamento:")
    nome_med = st.text_input("Nome do Medicamento:")
    
    if "lista_medicamentos" not in st.session_state:
        st.session_state.lista_medicamentos = []
    
    if st.button("Adicionar Medicamento"):
        if qtd_med and nome_med:
            st.session_state.lista_medicamentos.append({"quantidade": qtd_med, "nome": nome_med})
            st.success("Medicamento adicionado!")
        else:
            st.warning("Informe quantidade e nome do medicamento.")
    
    st.write("Medicamentos Adicionados:")
    for i, med in enumerate(st.session_state.lista_medicamentos, start=1):
        st.write(f"{i}) {med['quantidade']} - {med['nome']}")
    
    instrucoes_uso = st.text_area("Digite as instruções de uso:")
    nome_vet = st.text_input("Nome do Veterinário(a):")
    crmv = st.text_input("CRMV:")
    
    if st.button("Gerar Receita"):
        nome_arquivo = f"{paciente.replace(' ', '_')}-{cpf.replace('.', '').replace('-', '')}.pdf"
        pdf_path = gerar_pdf_receita(
            nome_pdf=nome_arquivo,
            paciente=paciente,
            tutor=tutor,
            cpf=cpf,
            lista_medicamentos=st.session_state.lista_medicamentos,
            instrucoes_uso=instrucoes_uso,
            nome_vet=nome_vet,
            crmv=crmv
        )
        
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="Baixar Receita",
                data=f,
                file_name=nome_arquivo,
                mime="application/pdf"
            )

if __name__ == "__main__":
    main()
