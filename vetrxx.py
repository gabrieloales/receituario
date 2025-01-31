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
import pandas as pd  # Importação adicionada

# ----------------------------------------------
# CONSTANTES E CONFIGURAÇÕES
# ----------------------------------------------
USERS_FILE = "users.json"         # Arquivo para armazenar usuários
USER_FILES_DIR = "user_files"     # Pasta base para armazenar arquivos de cada usuário

# Administrador "principal" hard-coded (opcional).
ADMIN_LOGIN = "larsen"
ADMIN_SENHA = "31415962Isa@"

# ----------------------------------------------
# FUNÇÕES DE SUPORTE A USUÁRIOS
# ----------------------------------------------

def carregar_usuarios():
    """Carrega o dicionário de usuários a partir de um arquivo JSON."""
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return {}

def salvar_usuarios(usuarios):
    """Salva o dicionário de usuários em um arquivo JSON."""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(usuarios, f, indent=4, ensure_ascii=False)

def verificar_login(login, senha):
    """
    Verifica se o login e senha correspondem ao administrador HARDCODED
    ou se correspondem a algum usuário no arquivo JSON.
    """
    # Primeiro, checa se é o admin "hard-coded":
    if login == ADMIN_LOGIN and senha == ADMIN_SENHA:
        return {
            "login": login,
            "is_admin": True,
            "fundo": None,
            "assinatura": None,
            "nome_vet": None,
            "crmv": None
        }

    # Caso contrário, verifica no arquivo de usuários:
    usuarios = carregar_usuarios()
    user_data = usuarios.get(login)
    if user_data and user_data.get("password") == senha:
        return {
            "login": login,
            "is_admin": user_data.get("is_admin", False),
            "fundo": user_data.get("background_image"),
            "assinatura": user_data.get("signature_image"),
            # Novos campos no perfil
            "nome_vet": user_data.get("nome_vet"),
            "crmv": user_data.get("crmv")
        }
    return None

def cadastrar_usuario(novo_login, nova_senha, nome_vet=None, crmv=None, is_admin=False):
    """Cadastra um novo usuário (ou atualiza se já existir)."""
    usuarios = carregar_usuarios()
    if novo_login not in usuarios:
        usuarios[novo_login] = {}
    usuarios[novo_login]["password"] = nova_senha
    usuarios[novo_login]["is_admin"] = is_admin
    usuarios[novo_login]["nome_vet"] = nome_vet
    usuarios[novo_login]["crmv"] = crmv
    # Se ainda não existir, define None para imagens
    if "background_image" not in usuarios[novo_login]:
        usuarios[novo_login]["background_image"] = None
    if "signature_image" not in usuarios[novo_login]:
        usuarios[novo_login]["signature_image"] = None

    salvar_usuarios(usuarios)

def remover_usuario(login):
    """Remove um usuário do arquivo JSON."""
    usuarios = carregar_usuarios()
    if login in usuarios:
        del usuarios[login]
        salvar_usuarios(usuarios)
        # Opcional: remover pasta local de arquivos do usuário
        user_folder = os.path.join(USER_FILES_DIR, login)
        if os.path.exists(user_folder):
            import shutil
            shutil.rmtree(user_folder)

def atualizar_imagem_usuario(login, image_path, tipo="fundo"):
    """
    Atualiza o path de imagem de fundo ou assinatura do usuário no JSON.
    tipo='fundo' ou tipo='assinatura'.
    """
    usuarios = carregar_usuarios()
    if login not in usuarios:
        return

    if tipo == "fundo":
        usuarios[login]["background_image"] = image_path
    else:
        usuarios[login]["signature_image"] = image_path

    salvar_usuarios(usuarios)

# ----------------------------------------------
# FUNÇÕES DE APOIO GERAIS
# ----------------------------------------------

def formatar_cpf(cpf_str: str) -> str:
    digits = re.sub(r'\D', '', cpf_str)
    if len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    return cpf_str

def formatar_cep(cep_str: str) -> str:
    """Formata o CEP no padrão 12345-678."""
    digits = re.sub(r'\D', '', cep_str)
    if len(digits) == 8:
        return f"{digits[:5]}-{digits[5:]}"
    return cep_str

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
        # Se "erro" em dados, retorna vazio
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

def wrap_text(text, font_name, font_size, available_width, c):
    """
    Quebra o texto em múltiplas linhas para que não ultrapasse a largura disponível.
    """
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

# ----------------------------------------------
# FUNÇÕES DE HISTÓRICO
# ----------------------------------------------

def carregar_historico(login):
    """Carrega o histórico de prescrições do usuário a partir de um arquivo JSON."""
    historico_path = os.path.join(USER_FILES_DIR, login, "historico.json")
    if not os.path.exists(historico_path):
        return []
    with open(historico_path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []

def salvar_historico(login, historico):
    """Salva o histórico de prescrições do usuário em um arquivo JSON."""
    user_folder = os.path.join(USER_FILES_DIR, login)
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    historico_path = os.path.join(user_folder, "historico.json")
    with open(historico_path, "w", encoding="utf-8") as f:
        json.dump(historico, f, indent=4, ensure_ascii=False)

# ----------------------------------------------
# FUNÇÃO PRINCIPAL PARA GERAR O PDF
# ----------------------------------------------

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
    # Imagens de fundo/assinatura
    imagem_fundo=None,
    imagem_assinatura=None,
    # Nome e CRMV do(a) veterinário(a)
    nome_vet=None,
    crmv=None
):
    """
    Gera o PDF da receita, incluindo:
      - Configurações de posição para assinatura e campos.
      - Quebra de linha para endereço.
      - Outras formatações necessárias.
    """
    if lista_medicamentos is None:
        lista_medicamentos = []
    if not data_receita:
        data_receita = datetime.datetime.now().strftime("%d/%m/%Y")

    # Padroniza se faltar algo
    if not nome_vet:
        nome_vet = "NOME NÃO DEFINIDO"
    if not crmv:
        crmv = "00000"
    nome_vet_up = nome_vet.upper()

    largura, altura = A4
    c = canvas.Canvas(nome_pdf, pagesize=A4)

    # ----- Configurações de Fonte -----
    font_label = "Helvetica-Bold"
    font_value = "Helvetica"
    font_label_size = 9
    font_value_size = 9
    font_title_size = 13
    font_med_title = 10
    font_footer = 10

    # ----- Configurações de Margens -----
    margem_esquerda = 2 * cm
    margem_direita = 2 * cm
    largura_util = largura - margem_esquerda - margem_direita

    # ----- Configurações de Posição -----
    config_posicoes = {
        "assinatura_x": (largura / 2) - 4 * cm,  # 4 cm à esquerda do centro
        "assinatura_y": 6.3 * cm,                 # 6.3 cm do fundo
        "assinatura_width": 4 * cm,
        "assinatura_height": 1.5 * cm,
        "data_y": 5.8 * cm,  # Aproximadamente logo abaixo da assinatura
        "mv_y": 5.3 * cm,
        "crmv_y": 4.8 * cm
    }

    # ----- Inserção da Imagem de Fundo -----
    if imagem_fundo and os.path.exists(imagem_fundo):
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
            st.warning(f"[Aviso] Não foi possível inserir a imagem de fundo: {e}")

    # ----- Título: Tipo de Farmácia -----
    c.setFont(font_label, font_title_size)
    c.drawCentredString(largura / 2, altura - 4 * cm, tipo_farmacia.upper())

    # ----- Dados em Duas Colunas Simétricas -----
    col_width = largura_util / 2
    col_left_x = margem_esquerda
    col_right_x = margem_esquerda + col_width
    y_left = altura - 5 * cm
    y_right = altura - 5 * cm
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
        cep_match = re.search(r'CEP:\s*(\d{5}-\d{3})', endereco_formatado)
        if cep_match:
            cep_raw = cep_match.group(1)
            cep_formatado = formatar_cep(cep_raw)
            endereco_formatado = re.sub(r'CEP:\s*\d{5}-\d{3}', f'CEP: {cep_formatado}', endereco_formatado)
        right_fields.append(("ENDEREÇO: ", endereco_formatado))

    c.setFont(font_label, font_label_size)
    for label, valor in right_fields:
        c.drawString(col_right_x, y_right, label)
        offset = c.stringWidth(label, font_label, font_label_size)
        c.setFont(font_value, font_value_size)
        if label.strip(": ") == "ENDEREÇO":
            available_width = col_width - offset
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

    # ----- Lista de Medicamentos -----
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
        y_atual -= 0.6 * cm

        if conc:
            texto_conc = f"   CONCENTRAÇÃO: {conc}"
            c.setFont(font_value, font_value_size)
            c.drawString(margem_esquerda, y_atual, texto_conc)
            c.setFont("Helvetica-Bold", font_med_title)
            y_atual -= 0.6 * cm

        c.setLineWidth(0.5)
        c.setStrokeColor(colors.black)
        c.line(margem_esquerda, y_atual + 0.3 * cm, largura - margem_direita, y_atual + 0.3 * cm)
        y_atual -= 0.4 * cm

    # ----- Instruções de Uso -----
    y_inst = y_atual - 1.5 * cm
    c.setFont("Helvetica-Bold", font_med_title)
    c.drawString(margem_esquerda, y_inst, "INSTRUÇÕES DE USO: ")
    y_texto = y_inst - 1 * cm
    c.setFont("Helvetica", font_value_size)
    for linha in instrucoes_uso.split("\n"):
        lines = wrap_text(linha.upper(), "Helvetica", font_value_size, largura_util, c)
        for l in lines:
            c.drawString(margem_esquerda, y_texto, l)
            y_texto -= 0.6 * cm

    # ----- Linha Curva -----
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

    # ----- Rodapé: Assinatura, Data, Nome, CRMV -----
    x_assinatura = config_posicoes["assinatura_x"]
    y_assinatura = config_posicoes["assinatura_y"]
    assinatura_width = config_posicoes["assinatura_width"]
    assinatura_height = config_posicoes["assinatura_height"]

    if imagem_assinatura and os.path.exists(imagem_assinatura):
        try:
            c.drawImage(
                imagem_assinatura,
                x_assinatura - (assinatura_width / 2),
                y_assinatura,
                width=assinatura_width,
                height=assinatura_height,
                preserveAspectRatio=True,
                mask='auto'
            )
            y_assinatura -= assinatura_height + 0.2 * cm
        except Exception as e:
            st.warning(f"[Aviso] Não foi possível inserir a assinatura: {e}")

    c.setFont("Helvetica", font_footer)
    c.drawCentredString(x_assinatura, config_posicoes["data_y"], f"CURITIBA, PR, {data_receita}")
    c.drawCentredString(x_assinatura, config_posicoes["mv_y"], f"M. V. {nome_vet_up}")
    c.drawCentredString(x_assinatura, config_posicoes["crmv_y"], f"CRMV-PR: {crmv}")

    c.showPage()
    c.save()
    return nome_pdf

# ----------------------------------------------
# FUNÇÕES DE TELA
# ----------------------------------------------

def tela_admin():
    st.subheader("Administração de Usuários")

    st.write("### Usuários Existentes:")
    usuarios = carregar_usuarios()
    if usuarios:
        for u, data in usuarios.items():
            st.write(f"- **Login**: {u} | Admin: {data.get('is_admin', False)} | Nome Vet: {data.get('nome_vet', 'Não definido')} | CRMV: {data.get('crmv', 'Não definido')}")
    else:
        st.write("Não há usuários cadastrados no arquivo.")

    st.write("---")
    st.write("### Cadastrar/Atualizar Usuário")
    novo_login = st.text_input("Login do Usuário", key="novo_login")
    nova_senha = st.text_input("Senha do Usuário", type="password", key="nova_senha")
    admin_flag = st.checkbox("Usuário é administrador?", key="admin_flag")
    nome_vet = st.text_input("Nome do(a) Veterinário(a)", key="nome_vet")
    crmv = st.text_input("CRMV (somente números ou ex: 12345)", key="crmv")
    if st.button("Cadastrar/Atualizar Usuário"):
        if novo_login and nova_senha and nome_vet and crmv:
            cadastrar_usuario(novo_login, nova_senha, nome_vet=nome_vet, crmv=crmv, is_admin=admin_flag)
            st.success(f"Usuário '{novo_login}' cadastrado/atualizado com sucesso!")
            st.session_state.novo_login = ""
            st.session_state.nova_senha = ""
            st.session_state.admin_flag = False
            st.session_state.nome_vet = ""
            st.session_state.crmv = ""
        else:
            st.warning("É necessário preencher login, senha, nome do(a) veterinário(a) e CRMV.")

    st.write("---")
    st.write("### Remover Usuário")
    usuario_remover = st.text_input("Login do usuário para remover:", key="usuario_remover")
    if st.button("Remover"):
        if usuario_remover:
            remover_usuario(usuario_remover)
            st.success(f"Usuário '{usuario_remover}' removido com sucesso!")
            st.session_state.usuario_remover = ""
        else:
            st.warning("Informe o login do usuário a ser removido.")

def tela_perfil():
    st.subheader("Meu Perfil")
    st.write("Aqui você pode configurar apenas as imagens de fundo e assinatura.")

    user_folder = os.path.join(USER_FILES_DIR, st.session_state.usuario_logado["login"])
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)

    fundo_file = st.file_uploader("Upload da Imagem de Fundo (opcional)", type=["png", "jpg", "jpeg"], key="fundo_file")
    if fundo_file is not None:
        fundo_path = os.path.join(user_folder, "fundo_" + fundo_file.name)
        with open(fundo_path, "wb") as f:
            f.write(fundo_file.getvalue())
        atualizar_imagem_usuario(st.session_state.usuario_logado["login"], fundo_path, tipo="fundo")
        st.success("Imagem de fundo atualizada com sucesso!")
        st.session_state.usuario_logado["fundo"] = fundo_path

    assinatura_file = st.file_uploader("Upload da Assinatura (opcional)", type=["png", "jpg", "jpeg"], key="assinatura_file")
    if assinatura_file is not None:
        assinatura_path = os.path.join(user_folder, "assinatura_" + assinatura_file.name)
        with open(assinatura_path, "wb") as f:
            f.write(assinatura_file.getvalue())
        atualizar_imagem_usuario(st.session_state.usuario_logado["login"], assinatura_path, tipo="assinatura")
        st.success("Assinatura atualizada com sucesso!")
        st.session_state.usuario_logado["assinatura"] = assinatura_path

    st.write("---")
    st.write("**Imagem de fundo atual**:", os.path.basename(st.session_state.usuario_logado.get("fundo")) if st.session_state.usuario_logado.get("fundo") else "Nenhuma")
    st.write("**Assinatura atual**:", os.path.basename(st.session_state.usuario_logado.get("assinatura")) if st.session_state.usuario_logado.get("assinatura") else "Nenhuma")
    st.write("**Nome Vet:**", st.session_state.usuario_logado.get("nome_vet") or "Não definido")
    st.write("**CRMV:**", st.session_state.usuario_logado.get("crmv") or "Não definido")

def tela_receita():
    st.subheader("Criar Receituário")

    if "lista_medicamentos" not in st.session_state:
        st.session_state.lista_medicamentos = []

    opcoes_farmacia = [
        "FARMÁCIA VETERINÁRIA",
        "FARMÁCIA HUMANA",
        "FARMÁCIA DE MANIPULAÇÃO - VETERINÁRIA",
        "FARMÁCIA DE MANIPULAÇÃO - HUMANO"
    ]
    tipo_farmacia = st.selectbox("Selecione o tipo de Farmácia:", opcoes_farmacia)

    eh_controlado = st.radio("Medicamento Controlado?", ("Não", "Sim"))

    rg = ""
    endereco_formatado = ""

    if eh_controlado == "Sim":
        rg = st.text_input("RG do Tutor(a):")

        st.write("### Preenchimento do Endereço")
        modo_endereco = st.radio(
            "Escolha a forma de preenchimento do endereço:",
            ("Automático (via CEP)", "Manual")
        )

        if modo_endereco == "Automático (via CEP)":
            if "cep_tutor" not in st.session_state:
                st.session_state.cep_tutor = ""
            if "end_busca" not in st.session_state:
                st.session_state.end_busca = {}

            cep_digitado = st.text_input(
                "CEP do Tutor(a):",
                value=st.session_state.cep_tutor,
                help="Digite o CEP sem hífen, por exemplo: 12345678"
            )

            if cep_digitado != st.session_state.cep_tutor:
                st.session_state.cep_tutor = cep_digitado
                if re.fullmatch(r'\d{8}', cep_digitado):
                    dados_end = buscar_endereco_via_cep(cep_digitado)
                    st.session_state.end_busca = dados_end
                    if dados_end:
                        st.success(f"Endereço encontrado: {dados_end.get('logradouro')}, {dados_end.get('bairro')}, {dados_end.get('localidade')}-{dados_end.get('uf')}")
                    else:
                        st.warning("CEP não encontrado. Por favor, preencha o endereço manualmente ou verifique o CEP.")
                elif cep_digitado.strip():
                    st.warning("CEP inválido. Deve conter exatamente 8 dígitos.")

            dados_cep = st.session_state.end_busca if st.session_state.end_busca else {}
            if dados_cep:
                logradouro = dados_cep.get("logradouro", "")
                bairro = dados_cep.get("bairro", "")
                cidade = dados_cep.get("localidade", "")
                uf = dados_cep.get("uf", "")
                numero = st.text_input("Número:")
                complemento = st.text_input("Complemento (opcional):")
                endereco_formatado = f"{logradouro}, {numero}, {bairro}, {cidade}-{uf}"
                if complemento:
                    endereco_formatado += f" (Compl.: {complemento})"
                if re.fullmatch(r'\d{5}-\d{3}', formatar_cep(cep_digitado)):
                    endereco_formatado += f" - CEP: {formatar_cep(cep_digitado)}"
            else:
                if st.session_state.cep_tutor.strip() and not re.fullmatch(r'\d{8}', st.session_state.cep_tutor):
                    st.warning("Por favor, preencha os campos de endereço manualmente abaixo.")

        else:
            rua = st.text_input("Rua:")
            numero = st.text_input("Número:")
            bairro = st.text_input("Bairro:")
            cidade = st.text_input("Cidade:")
            uf = st.text_input("Estado:")
            cep_manual = st.text_input(
                "CEP:",
                help="Digite o CEP no formato 12345-678"
            )
            complemento = st.text_input("Complemento (opcional):")

            if cep_manual:
                cep_formatado = formatar_cep(cep_manual)
                if re.fullmatch(r'\d{5}-\d{3}', cep_formatado):
                    endereco_formatado = f"{rua}, {numero}, {bairro}, {cidade}-{uf}"
                    if complemento:
                        endereco_formatado += f" (Compl.: {complemento})"
                    endereco_formatado += f" - CEP: {cep_formatado}"
                else:
                    st.warning("CEP inválido. Deve estar no formato 12345-678.")

    st.write("---")
    paciente = st.text_input("Nome do Paciente:")
    especie_raca = st.text_input("Espécie - Raça:")
    pelagem = st.text_input("Pelagem:")
    peso = st.text_input("Peso:")
    idade = st.text_input("Idade:")
    sexo = st.radio("Sexo:", ("Macho", "Fêmea"))
    chip = st.text_input("Número do Chip (se houver):")

    st.write("---")
    tutor = st.text_input("Nome do Tutor(a):")
    cpf = st.text_input("CPF do Tutor(a):")

    st.write("---")
    with st.form(key='form_medicamentos', clear_on_submit=False):
        qtd_med = st.text_input("Quantidade do Medicamento:")
        nome_med = st.text_input("Nome do Medicamento:")
        conc_med = st.text_input("Concentração do Medicamento (ex: 500mg, 200mg/ml):")
        submit_med = st.form_submit_button("Adicionar Medicamento")
        if submit_med:
            if qtd_med and nome_med:
                st.session_state.lista_medicamentos.append({
                    "quantidade": qtd_med,
                    "nome": nome_med,
                    "concentracao": conc_med
                })
                st.success("Medicamento adicionado!")
            else:
                st.warning("Informe quantidade e nome do medicamento.")

    st.write("### Medicamentos Adicionados:")
    if st.session_state.lista_medicamentos:
        for i, med in enumerate(st.session_state.lista_medicamentos, start=1):
            conc = med.get('concentracao', '')
            texto_med = f"{i}) QTD: {med['quantidade']} - MEDICAMENTO: {med['nome']}"
            if conc:
                texto_med += f" - CONCENTRAÇÃO: {conc}"
            st.write(texto_med)
    else:
        st.write("Nenhum medicamento adicionado.")

    st.write("---")
    instrucoes_uso = st.text_area("Digite as instruções de uso:")

    st.write("---")
    data_receita = st.date_input(
        "Data da Receita:",
        value=datetime.date.today(),
        help="Selecione a data da receita. O padrão é a data atual."
    )

    if st.button("Gerar Receita"):
        if eh_controlado == "Sim":
            if not rg:
                st.error("RG do Tutor(a) é obrigatório para medicamentos controlados.")
                return
            if not endereco_formatado:
                st.error("Endereço do Tutor(a) é obrigatório para medicamentos controlados.")
                return

        if not paciente:
            st.error("Nome do Paciente é obrigatório.")
            return
        if not tutor:
            st.error("Nome do Tutor(a) é obrigatório.")
            return
        if not cpf:
            st.error("CPF do Tutor(a) é obrigatório.")
            return
        if eh_controlado == "Sim":
            cep_utilizado = cep_manual if 'cep_manual' in locals() and cep_manual else st.session_state.get('cep_tutor', '')
            cep_formatado = formatar_cep(cep_utilizado)
            if not re.fullmatch(r'\d{5}-\d{3}', cep_formatado):
                st.error("CEP inválido. Deve estar no formato 12345-678.")
                return

        imagem_fundo = st.session_state.usuario_logado.get("fundo")
        imagem_assinatura = st.session_state.usuario_logado.get("assinatura")
        nome_vet = st.session_state.usuario_logado.get("nome_vet") or ""
        crmv = st.session_state.usuario_logado.get("crmv") or ""

        cpf_formatado = formatar_cpf(cpf)
        paciente_sanitizado = re.sub(r'[^\w\s-]', '', paciente).strip().replace(' ', '_')
        nome_pdf = f"{paciente_sanitizado} - {cpf_formatado}.pdf"

        data_receita_str = data_receita.strftime("%d/%m/%Y")

        nome_pdf = gerar_pdf_receita(
            nome_pdf=nome_pdf,
            tipo_farmacia=tipo_farmacia,
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
            lista_medicamentos=st.session_state.lista_medicamentos,
            instrucoes_uso=instrucoes_uso,
            imagem_fundo=imagem_fundo,
            imagem_assinatura=imagem_assinatura,
            nome_vet=nome_vet,
            crmv=crmv,
            data_receita=data_receita_str
        )
        with open(nome_pdf, "rb") as f:
            st.download_button(
                label="Baixar Receita",
                data=f,
                file_name=nome_pdf,
                mime="application/pdf"
            )

        # Salvar no Histórico com os detalhes adicionais
        historico = carregar_historico(st.session_state.usuario_logado["login"])
        registro = {
            "Nome do Paciente": paciente,
            "CPF do Tutor": formatar_cpf(cpf),
            "Nome do Tutor": tutor,
            "Medicamento Controlado": "Sim" if eh_controlado == "Sim" else "Não",
            "Data Emitida": data_receita_str,
            "Medicamentos": st.session_state.lista_medicamentos,
            "Instruções de Uso": instrucoes_uso,
            "Tipo de Farmácia": tipo_farmacia,
            "Espécie - Raça": especie_raca,
            "Pelagem": pelagem,
            "Peso": peso,
            "Sexo": sexo,
            "Número do Chip": chip
        }
        # Se for medicamento controlado, adiciona o Endereço
        if eh_controlado == "Sim":
            registro["Endereço"] = endereco_formatado
        historico.append(registro)
        salvar_historico(st.session_state.usuario_logado["login"], historico)
        st.success("Prescrição gerada e adicionada ao histórico com sucesso!")

def tela_historico():
    st.subheader("Histórico de Prescrições")

    login = st.session_state.usuario_logado["login"]
    historico = carregar_historico(login)

    if not historico:
        st.info("Nenhuma prescrição encontrada no histórico.")
        return

    # Cabeçalho da tabela customizada
    col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 2, 2, 1])
    col1.markdown("**Paciente**")
    col2.markdown("**CPF Tutor**")
    col3.markdown("**Tutor**")
    col4.markdown("**Ctrl?**")
    col5.markdown("**Data**")
    col6.markdown("**Detalhes**")

    # Itera sobre os registros e exibe cada linha com botão "Ver"
    for idx, registro in enumerate(historico):
        col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 2, 2, 1])
        col1.write(registro.get("Nome do Paciente", ""))
        col2.write(registro.get("CPF do Tutor", ""))
        col3.write(registro.get("Nome do Tutor", ""))
        col4.write(registro.get("Medicamento Controlado", ""))
        col5.write(registro.get("Data Emitida", ""))
        if col6.button("Ver", key=f"ver_{idx}"):
            st.session_state.detalhe = registro
            st.session_state.current_page = "Detalhes"

def tela_detalhes():
    st.subheader("Detalhes da Prescrição")
    registro = st.session_state.get("detalhe", None)
    if registro:
        st.write("### Informações Gerais")
        st.write(f"**Nome do Paciente:** {registro.get('Nome do Paciente', '')}")
        st.write(f"**CPF do Tutor:** {registro.get('CPF do Tutor', '')}")
        st.write(f"**Nome do Tutor:** {registro.get('Nome do Tutor', '')}")
        st.write(f"**Medicamento Controlado:** {registro.get('Medicamento Controlado', '')}")
        st.write(f"**Data Emitida:** {registro.get('Data Emitida', '')}")
        st.write(f"**Tipo de Farmácia:** {registro.get('Tipo de Farmácia', '')}")
        st.write(f"**Espécie - Raça:** {registro.get('Espécie - Raça', '')}")
        st.write(f"**Pelagem:** {registro.get('Pelagem', '')}")
        st.write(f"**Peso:** {registro.get('Peso', '')}")
        st.write(f"**Sexo:** {registro.get('Sexo', '')}")
        st.write(f"**Número do Chip:** {registro.get('Número do Chip', '')}")
        if registro.get("Medicamento Controlado", "Não") == "Sim":
            st.write(f"**Endereço:** {registro.get('Endereço', '')}")

        st.write("---")
        st.write("### Medicamentos")
        medicamentos = registro.get("Medicamentos", [])
        if medicamentos:
            for med in medicamentos:
                qtd = med.get("quantidade", "")
                nome_med = med.get("nome", "")
                conc = med.get("concentracao", "")
                st.write(f"- **Quantidade:** {qtd} | **Medicamento:** {nome_med} | **Concentração:** {conc}")
        else:
            st.write("Nenhum medicamento informado.")

        st.write("---")
        st.write("### Instruções de Uso")
        instrucoes = registro.get("Instruções de Uso", "")
        st.write(instrucoes)
    else:
        st.write("Nenhum detalhe encontrado.")

    if st.button("Voltar"):
        st.session_state.current_page = "Histórico"

def main():
    st.set_page_config(layout="wide")
    st.title("VetyRx - Receituário Veterinário")

    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if "usuario_logado" not in st.session_state:
        st.session_state.usuario_logado = None

    if not st.session_state.autenticado:
        st.subheader("Login")
        login = st.text_input("Login:")
        senha = st.text_input("Senha:", type="password")
        if st.button("Entrar"):
            user_info = verificar_login(login, senha)
            if user_info:
                st.session_state.autenticado = True
                st.session_state.usuario_logado = user_info
                st.success("Login bem-sucedido!")
            else:
                st.error("Login ou senha incorretos.")
        return

    usuario_atual = st.session_state.usuario_logado
    left_col_width = 2
    content_col_width = 10
    left_col, content_col = st.columns([left_col_width, content_col_width])

    with left_col:
        st.markdown("### Menu de Navegação")
        if st.button("Criar Receituário"):
            st.session_state.current_page = "Criar Receituário"
        if st.button("Histórico"):
            st.session_state.current_page = "Histórico"
        if st.button("Meu Perfil"):
            st.session_state.current_page = "Meu Perfil"
        if usuario_atual["is_admin"]:
            if st.button("Administração de Usuários"):
                st.session_state.current_page = "Administração de Usuários"
        st.write("\n" * 20)
        st.markdown("---")
        st.write(f"**Usuário logado:** {usuario_atual['login']}")
        if st.button("Sair"):
            st.session_state.autenticado = False
            st.session_state.usuario_logado = None
            if "lista_medicamentos" in st.session_state:
                del st.session_state.lista_medicamentos
            if "current_page" in st.session_state:
                del st.session_state.current_page
            st.success("Logout realizado com sucesso!")

    if "current_page" not in st.session_state:
        st.session_state.current_page = "Criar Receituário"

    with content_col:
        if st.session_state.current_page == "Criar Receituário":
            tela_receita()
        elif st.session_state.current_page == "Histórico":
            tela_historico()
        elif st.session_state.current_page == "Meu Perfil":
            tela_perfil()
        elif st.session_state.current_page == "Administração de Usuários":
            tela_admin()
        elif st.session_state.current_page == "Detalhes":
            tela_detalhes()

if __name__ == "__main__":
    if not os.path.exists(USER_FILES_DIR):
        os.makedirs(USER_FILES_DIR)
    main()
