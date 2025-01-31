import os
import json
import datetime
import re
import requests
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors


# ----- Função Auxiliar para Quebra de Texto (Wrap) -----

def wrap_text(text, font_name, font_size, available_width, c):
    words = text.split()
    lines = []
    current_line = ""
    c.setFont(font_name, font_size)
    for word in words:
        test_line = word if current_line == "" else current_line + " " + word
        if c.stringWidth(test_line, font_name, font_size) <= available_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines


# ----- Funções de Apoio ----------------------------------------

def formatar_cpf(cpf_str: str) -> str:
    digits = re.sub(r'\D', '', cpf_str)
    if len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    return cpf_str


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
        print(f"[Aviso] Erro ao buscar CEP: {e}")
        return {}


def salvar_no_historico(paciente, cpf_formatado, tutor, data_criacao):
    registro = {
        "paciente": paciente,
        "cpf": cpf_formatado,
        "tutor": tutor,
        "data_criacao": data_criacao
    }
    historico_arquivo = "historico_receitas.json"
    if not os.path.exists(historico_arquivo):
        historico = []
    else:
        with open(historico_arquivo, "r", encoding="utf-8") as f:
            try:
                historico = json.load(f)
            except json.JSONDecodeError:
                historico = []
    historico.append(registro)
    with open(historico_arquivo, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=4)


def ver_historico():
    historico_arquivo = "historico_receitas.json"
    if not os.path.exists(historico_arquivo):
        print("Nenhum histórico encontrado.")
        return
    with open(historico_arquivo, "r", encoding="utf-8") as f:
        try:
            historico = json.load(f)
        except json.JSONDecodeError:
            print("Histórico corrompido.")
            return
    if not historico:
        print("Histórico vazio.")
        return
    print("\n=== HISTÓRICO DE RECEITAS ===")
    for i, rec in enumerate(historico, start=1):
        print(
            f"{i}) Paciente: {rec.get('paciente')}, CPF: {rec.get('cpf')}, Tutor(a): {rec.get('tutor')}, Data: {rec.get('data_criacao')}")


# ----- Função de Geração de PDF ----------------------------------

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
        data_receita=None,
        imagem_fundo="modelo_receituario.png"
):
    if lista_medicamentos is None:
        lista_medicamentos = []
    if not data_receita:
        data_receita = datetime.datetime.now().strftime("%d/%m/%Y")

    largura, altura = A4
    c = canvas.Canvas(nome_pdf, pagesize=A4)

    # Define as fontes reduzindo em 1 pt
    font_label = "Helvetica-Bold"
    font_value = "Helvetica"
    font_label_size = 9
    font_value_size = 9
    font_title_size = 13
    font_med_title = 10
    font_footer = 10

    # Definindo margens: 2 cm à esquerda e 2 cm à direita
    margem_esquerda = 2 * cm
    margem_direita = 2 * cm
    largura_util = largura - margem_esquerda - margem_direita  # 21 cm - 4 cm = 17 cm

    # Distância do tipo de farmácia com o topo: 4 cm (em vez de 5 cm)
    y_titulo = altura - 4 * cm

    try:
        c.drawImage(
            imagem_fundo,
            0, 0,
            width=largura,
            height=altura,
            preserveAspectRatio=True,
            mask='auto'
        )
    except Exception as e:
        print(f"[Aviso] Não foi possível inserir a imagem de fundo: {e}")

    # Título: Tipo de Farmácia
    c.setFont(font_label, font_title_size)
    titulo = tipo_farmacia.upper()
    x_centro_pagina = largura / 2
    c.drawCentredString(x_centro_pagina, y_titulo, titulo)

    # ---- Dados em duas colunas simétricas ----
    # Dividindo a largura útil igualmente: cada coluna terá col_width = 17/2 = 8.5 cm
    col_width = largura_util / 2
    col_left_x = margem_esquerda
    col_right_x = margem_esquerda + col_width
    y_left = y_titulo - 1 * cm
    y_right = y_titulo - 1 * cm
    esp_line = 0.7 * cm

    # Coluna Esquerda: Dados do Animal
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
        c.drawString(col_left_x, y_left, label)
        offset = c.stringWidth(label, font_label, font_label_size)
        c.setFont(font_value, font_value_size)
        c.drawString(col_left_x + offset, y_left, valor)
        c.setFont(font_label, font_label_size)
        y_left -= esp_line

    # Coluna Direita: Dados do Tutor e Documentos
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
        c.drawString(col_right_x, y_right, label)
        offset = c.stringWidth(label, font_label, font_label_size)
        c.setFont(font_value, font_value_size)
        if label.strip(": ") == "ENDEREÇO":
            # Disponibiliza toda a linha usando a mesma margem da coluna direita
            available_width = (col_right_x + col_width) - col_right_x
            # Se o endereço não couber, faz wrap de linha mantendo a mesma margem
            if c.stringWidth(valor, font_value, font_value_size) <= available_width:
                c.drawString(col_right_x + offset, y_right, valor)
            else:
                lines = wrap_text(valor, font_value, font_value_size, available_width, c)
                if lines:
                    c.drawString(col_right_x + offset, y_right, lines[0])
                    for linha in lines[1:]:
                        y_right -= esp_line
                        c.drawString(col_right_x, y_right, linha)
        else:
            c.drawString(col_right_x + offset, y_right, valor)
        c.setFont(font_label, font_label_size)
        y_right -= esp_line

    y_campos = min(y_left, y_right) - 0.5 * cm

    # ---- Lista de Medicamentos ----
    y_inicial = y_campos - 1.2 * cm
    c.setFont("Helvetica-Bold", font_med_title)
    esp_med = 1.6 * cm
    y_atual = y_inicial
    for i, med in enumerate(lista_medicamentos, start=1):
        qtd = med.get("quantidade", "").upper()
        nome_med = med.get("nome", "").upper()
        conc = med.get("concentracao", "")
        texto_med = f"{i}) QTD: {qtd} - MEDICAMENTO: {nome_med}"
        c.drawString(margem_esquerda, y_atual, texto_med)
        x_fim = largura - margem_direita
        c.setLineWidth(1)
        c.line(margem_esquerda, y_atual - 0.2 * cm, x_fim, y_atual - 0.2 * cm)
        if conc:
            c.setFont("Helvetica-Bold", font_med_title)  # rótulo em negrito
            label_conc = "CONCENTRAÇÃO: "
            c.drawString(margem_esquerda, y_atual - 1 * cm, label_conc)
            offset_conc = c.stringWidth(label_conc, "Helvetica-Bold", font_med_title)
            c.setFont("Helvetica", font_med_title)  # dados em fonte normal
            # Aqui, imprimimos os dados de concentração conforme digitados (sem forçar caixa alta)
            c.drawString(margem_esquerda + offset_conc, y_atual - 1 * cm, conc)
            c.setFont("Helvetica-Bold", font_med_title)
        y_atual -= esp_med

    # ---- Instruções de Uso ----
    c.setFont("Helvetica-Bold", font_med_title)
    y_instrucoes = y_atual - 1.5 * cm
    c.drawString(margem_esquerda, y_instrucoes, "INSTRUÇÕES DE USO: ")
    y_texto = y_instrucoes - 1 * cm
    c.setFont("Helvetica", font_value_size)
    for linha in instrucoes_uso.split("\n"):
        c.drawString(margem_esquerda, y_texto, linha.upper())
        y_texto -= 0.6 * cm

    # ---- Linha Curva ----
    y_curva_inicial = y_texto - 1.5 * cm
    if y_curva_inicial < 0:
        y_curva_inicial = 0
    y_curva_final = 8 * cm
    c.setLineWidth(2)
    c.setStrokeColor(colors.grey)
    c.bezier(margem_esquerda, y_curva_inicial,
             largura / 2, y_curva_inicial + 2 * cm,
             largura / 2, y_curva_final - 2 * cm,
             largura - margem_direita, y_curva_final)
    c.setStrokeColor(colors.black)

    # ---- Rodapé: Assinatura, Data, Nome, CRMV ----
    x_centro_rodape = (largura / 2) + 2 * cm - 6 * cm  # equivale a (largura/2) - 4 cm
    y_rodape = 6 * cm
    assinatura_width = 4 * cm
    assinatura_height = 1.5 * cm
    try:
        c.drawImage(
            "assinatura_isa.png",
            x_centro_rodape - (assinatura_width / 2),
            y_rodape,
            width=assinatura_width,
            height=assinatura_height,
            preserveAspectRatio=True,
            mask='auto'
        )
        y_rodape -= assinatura_height
        y_rodape -= (0.05 * cm - 1 * cm)  # aproxima 1 cm do texto
    except Exception as e:
        print(f"[Aviso] Não foi possível inserir a assinatura: {e}")

    c.setFont("Helvetica", font_footer)
    c.drawCentredString(x_centro_rodape, y_rodape, f"CURITIBA, PR, {data_receita}")
    y_rodape -= 0.5 * cm
    c.drawCentredString(x_centro_rodape, y_rodape, "M. V. ISABELA ZAMBONI")
    y_rodape -= 0.5 * cm
    c.drawCentredString(x_centro_rodape, y_rodape, "CRVM-PR: 22845")

    c.showPage()
    c.save()
    print(f"PDF gerado com sucesso em: {nome_pdf}")


# ----- Fluxo Principal -----------------------------------------

def criar_receita():
    print("=== Receituário Veterinário (Controle de Receita) ===")

    medic_controlado = input("Receita de medicamento controlado? (S/N): ").strip().lower()
    eh_controlado = (medic_controlado == "s")

    opcoes = [
        "Farmácia Veterinária",
        "Farmácia Humana",
        "Farmácia de Manipulação - Veterinária",
        "Farmácia de Manipulação - Humano"
    ]
    print("\nEscolha o tipo de farmácia:")
    for i, op in enumerate(opcoes, start=1):
        print(f"{i}) {op}")
    try:
        escolha_int = int(input("Digite o número da opção desejada: "))
        tipo_farmacia = opcoes[escolha_int - 1]
    except:
        print("Opção inválida. Usando padrão: Farmácia Veterinária")
        tipo_farmacia = "Farmácia Veterinária"

    print("\n-- Dados do Paciente - Tutor --")
    paciente = input("Nome do Paciente: ").strip()
    tutor = input("Nome do Tutor(a): ").strip()
    cpf_bruto = input("CPF (sem pontuação): ").strip()
    cpf_format = formatar_cpf(cpf_bruto)

    print("\n-- Detalhes do Paciente --")
    especie_raca = input("Espécie - Raça: ").strip()
    pelagem = input("Pelagem: ").strip()
    peso = input("Peso: ").strip()
    idade = input("Idade: ").strip()
    sexo_input = input("Sexo (M ou F): ").strip().upper()
    if sexo_input == "M":
        sexo = "Macho"
    elif sexo_input == "F":
        sexo = "Fêmea"
    else:
        sexo = sexo_input
    chip_resp = input("Possui Chip? (S/N): ").strip().lower()
    if chip_resp == "s":
        chip_num = input("Número do Chip: ").strip()
        chip_final = chip_num if chip_num else "(não informado)"
    else:
        chip_final = "Não"

    rg = ""
    endereco_formatado = ""
    if eh_controlado:
        print("\n-- Dados de Medicamento Controlado --")
        rg = input("RG (com pontuações): ").strip()
        print("Escolha a forma de preenchimento do endereço:")
        print("1) Manual")
        print("2) Automática (via CEP)")
        forma_end = input("Digite 1 ou 2: ").strip()
        if forma_end == "2":
            cep_auto = input("CEP: ").strip()
            numero_auto = input("Número: ").strip()
            dados_end = buscar_endereco_via_cep(cep_auto)
            if dados_end:
                rua = dados_end.get("logradouro", "")
                bairro = dados_end.get("bairro", "")
                cidade = dados_end.get("localidade", "")
                estado = dados_end.get("uf", "")
            else:
                print("CEP não encontrado. Preencha manualmente.")
                rua = input("Rua: ").strip()
                bairro = input("Bairro: ").strip()
                cidade = input("Cidade: ").strip()
                estado = input("Estado: ").strip()
            endereco_formatado = f"{rua}, {numero_auto} - {bairro} - {cidade} - {estado} - Brasil - {cep_auto}"
        else:
            rua = input("Rua: ").strip()
            numero = input("Número: ").strip()
            bairro = input("Bairro: ").strip()
            cidade = input("Cidade: ").strip()
            estado = input("Estado: ").strip()
            cep_manual = input("CEP: ").strip()
            endereco_formatado = f"{rua}, {numero} - {bairro} - {cidade} - {estado} - Brasil - {cep_manual}"
        comp = input("Possui Complemento? (S/N): ").strip().lower()
        if comp == "s":
            complemento = input("Digite o Complemento: ").strip()
            endereco_formatado += f" - Complemento: {complemento}"

    lista_medicamentos = []
    print("\n-- Cadastro de Medicamentos")
    while True:
        qtd = input("Quantidade (ex: '2 caixas', '1 frasco'): ").strip()
        nome_med = input("Nome do medicamento: ").strip()
        conc = input("Concentração (ex: '500mg', '200mg/ml'): ").strip()
        lista_medicamentos.append({
            "quantidade": qtd,
            "nome": nome_med,
            "concentracao": conc
        })
        cont = input("Adicionar outro medicamento? (S/N): ").strip().lower()
        if cont != "s":
            break

    print("\n-- Instruções de Uso --")
    instrucoes = input("Digite as instruções (pode separar por linhas):\n")

    data_info = input("\nData (deixe vazio p/ usar data de hoje, ex: 25/12/2025): ").strip()
    if not data_info:
        data_info = datetime.datetime.now().strftime("%d/%m/%Y")
    try:
        data_dt = datetime.datetime.strptime(data_info, "%d/%m/%Y")
    except:
        data_dt = datetime.datetime.now()
        print("[Aviso] Data inválida. Usando data atual.")

    ano_mes = f"{data_dt.year}-{data_dt.month:02d}"
    pasta_destino = os.path.join("Receitas", ano_mes)
    os.makedirs(pasta_destino, exist_ok=True)

    nome_arquivo_pdf = f"{paciente} - {cpf_format}.pdf"
    caminho_pdf = os.path.join(pasta_destino, nome_arquivo_pdf)

    gerar_pdf_receita(
        nome_pdf=caminho_pdf,
        tipo_farmacia=tipo_farmacia,
        paciente=paciente,
        tutor=tutor,
        cpf=cpf_bruto,
        rg=rg,
        endereco_formatado=endereco_formatado,
        especie_raca=especie_raca,
        pelagem=pelagem,
        peso=peso,
        idade=idade,
        sexo=sexo,
        chip=chip_final,
        lista_medicamentos=lista_medicamentos,
        instrucoes_uso=instrucoes,
        data_receita=data_info,
        imagem_fundo="modelo_receituario.png"
    )

    data_criacao_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    salvar_no_historico(paciente, cpf_format, tutor, data_criacao_str)


def main():
    while True:
        print("\n=== MENU INICIAL ===")
        print("1) Criar nova receita")
        print("2) Ver histórico de receitas")
        print("3) Sair")
        opc = input("Escolha uma opção: ").strip()
        if opc == "1":
            criar_receita()
        elif opc == "2":
            ver_historico()
        elif opc == "3":
            print("Saindo do programa...")
            break
        else:
            print("Opção inválida. Tente novamente.")


if __name__ == "__main__":
    main()
