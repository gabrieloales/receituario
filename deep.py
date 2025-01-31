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

# Função para formatar CPF
def formatar_cpf(cpf_str: str) -> str:
    digits = re.sub(r'\D', '', cpf_str)
    if len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    return cpf_str

# Função para buscar endereço via CEP
def buscar_endereco_via_cep(cep: str) -> dict:
    try:
        url = f"https://viacep.com.br/ws/{cep}/json/"
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
    except Exception as e:
        st.warning(f"Erro ao buscar CEP: {e}")
        return {}

# Função para gerar o PDF
def gerar_pdf_receita(
        nome_pdf="receita_veterinaria.pdf",
        tipo_farmacia="FARMÁCIA VETERINÁRIA",
        paciente="",
        tutor="",
        cpf="",
        rg="",
        endereco_formatado="",
        especie_raca="",
        pelagem="",
        peso="",
        idade="",
        sexo="",
        chip="",
        lista_medicamentos=None,
        instrucoes_uso="",
        data_receita=None
):
    if lista_medicamentos is None:
        lista_medicamentos = []
    if not data_receita:
        data_receita = datetime.datetime.now().strftime("%d/%m/%Y")

    largura, altura = A4
    c = canvas.Canvas(nome_pdf, pagesize=A4)

    # Configurações de fonte
    font_label = "Helvetica-Bold"
    font_value = "Helvetica"
    font_label_size = 9
    font_value_size = 9
    font_title_size = 13

    # Margens
    margem_esquerda = 2 * cm
    margem_direita = 2 * cm
    largura_util = largura - margem_esquerda - margem_direita

    # Título
    y_titulo = altura - 4 * cm
    c.setFont(font_label, font_title_size)
    c.drawCentredString(largura / 2, y_titulo, tipo_farmacia.upper())

    # Dados do Paciente
    y_left = y_titulo - 1 * cm
    left_fields = [
        ("PACIENTE: ", paciente),
        ("ESPÉCIE - RAÇA: ", especie_raca),
        ("PELAGEM: ", pelagem),
        ("SEXO: ", sexo),
        ("IDADE: ", idade),
        ("PESO: ", peso),
        ("CHIP: ", chip)
    ]
    c.setFont(font_label, font_label_size)
    for label, valor in left_fields:
        c.drawString(margem_esquerda, y_left, label)
        offset = c.stringWidth(label, font_label, font_label_size)
        c.setFont(font_value, font_value_size)
        c.drawString(margem_esquerda + offset, y_left, valor)
        c.setFont(font_label, font_label_size)
        y_left -= 0.7 * cm

    # Dados do Tutor
    y_right = y_titulo - 1 * cm
    right_fields = [
        ("TUTOR(A): ", tutor),
        ("CPF: ", formatar_cpf(cpf))
    ]
    if rg:
        right_fields.append(("RG: ", rg))
    if endereco_formatado:
        right_fields.append(("ENDEREÇO: ", endereco_formatado))

    c.setFont(font_label, font_label_size)
    for label, valor in right_fields:
        c.drawString(margem_esquerda + largura_util / 2, y_right, label)
        offset = c.stringWidth(label, font_label, font_label_size)
        c.setFont(font_value, font_value_size)
        c.drawString(margem_esquerda + largura_util / 2 + offset, y_right, valor)
        c.setFont(font_label, font_label_size)
        y_right -= 0.7 * cm

    # Medicamentos
    y_med = y_left - 1 * cm
    c.setFont(font_label, 10)
    for i, med in enumerate(lista_medicamentos, start=1):
        texto_med = f"{i}) QTD: {med.get('quantidade', '')} - MEDICAMENTO: {med.get('nome', '')}"
        c.drawString(margem_esquerda, y_med, texto_med)
        y_med -= 0.7 * cm

    # Instruções de Uso
    y_inst = y_med - 1 * cm
    c.setFont(font_label, 10)
    c.drawString(margem_esquerda, y_inst, "INSTRUÇÕES DE USO: ")
    y_inst -= 0.7 * cm
    c.setFont(font_value, font_value_size)
    for linha in instrucoes_uso.split("\n"):
        c.drawString(margem_esquerda, y_inst, linha)
        y_inst -= 0.7 * cm

    # Rodapé
    y_rodape = 2 * cm
    c.setFont(font_value, 10)
    c.drawString(margem_esquerda, y_rodape, f"Data: {data_receita}")
    c.drawString(margem_esquerda, y_rodape - 0.7 * cm, "Assinatura: ___________________________")

    c.save()
    st.success(f"PDF gerado com sucesso: {nome_pdf}")

# Interface do Streamlit
def main():
    st.title("Gerador de Receituário Veterinário")

    st.subheader("Dados do Paciente")
    paciente = st.text_input("Nome do Paciente:")
    especie_raca = st.text_input("Espécie - Raça:")
    pelagem = st.text_input("Pelagem:")
    peso = st.text_input("Peso:")
    idade = st.text_input("Idade:")
    sexo = st.radio("Sexo:", ("Macho", "Fêmea"))
    chip = st.text_input("Número do Chip (se houver):")

    st.subheader("Dados do Tutor")
    tutor = st.text_input("Nome do Tutor(a):")
    cpf = st.text_input("CPF do Tutor(a):")
    rg = st.text_input("RG do Tutor(a) (opcional):")
    cep = st.text_input("CEP do Tutor(a):")
    endereco = buscar_endereco_via_cep(cep)
    endereco_formatado = f"{endereco.get('logradouro', '')}, {endereco.get('bairro', '')}, {endereco.get('localidade', '')}, {endereco.get('uf', '')}"

    st.subheader("Medicamentos")
    lista_medicamentos = []
    qtd_med = st.text_input("Quantidade do Medicamento:")
    nome_med = st.text_input("Nome do Medicamento:")
    if st.button("Adicionar Medicamento"):
        lista_medicamentos.append({"quantidade": qtd_med, "nome": nome_med})
        st.write("Medicamentos Adicionados:", lista_medicamentos)

    st.subheader("Instruções de Uso")
    instrucoes_uso = st.text_area("Digite as instruções de uso:")

    if st.button("Gerar Receita"):
        gerar_pdf_receita(
            paciente=paciente,
            tutor=tutor,
            cpf=cpf,
            rg=rg,
            endereco_formatado=endereco_formatado,
            especie_raca=especie_raca,
            pelagem=pelagem,
            peso=peso,
            idade=idade,
            sexo=sexo,
            chip=chip,
            lista_medicamentos=lista_medicamentos,
            instrucoes_uso=instrucoes_uso
        )

if __name__ == "__main__":
    main()
