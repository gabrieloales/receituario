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

def cadastrar_usuario(novo_login, nova_senha, is_admin=False):
    """Cadastra um novo usuário (ou atualiza se já existir)."""
    usuarios = carregar_usuarios()
    if novo_login not in usuarios:
        usuarios[novo_login] = {}
    usuarios[novo_login]["password"] = nova_senha
    usuarios[novo_login]["is_admin"] = is_admin
    # Se ainda não existir, define None
    if "background_image" not in usuarios[novo_login]:
        usuarios[novo_login]["background_image"] = None
    if "signature_image" not in usuarios[novo_login]:
        usuarios[novo_login]["signature_image"] = None
    if "nome_vet" not in usuarios[novo_login]:
        usuarios[novo_login]["nome_vet"] = None
    if "crmv" not in usuarios[novo_login]:
        usuarios[novo_login]["crmv"] = None

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

def atualizar_dados_veterinario(login, nome_vet, crmv):
    """
    Atualiza o nome do(a) veterinário(a) e CRMV no perfil do usuário.
    """
    usuarios = carregar_usuarios()
    if login not in usuarios:
        return
    usuarios[login]["nome_vet"] = nome_vet
    usuarios[login]["crmv"] = crmv
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

# ----------------------------------------------
# FUNÇÃO PRINCIPAL PARA GERAR O PDF
# (Com posição da assinatura 2 cm à esquerda,
#  Bezier e uso de M. V. {nome_vet} e CRMV-PR: {crmv})
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
      - Pergunta de tipo de farmácia.
      - Bezier (artefato Blezie) para impedir escrita posterior.
      - Assinatura 2cm à esquerda do centro.
      - M. V. {nome_vet} e CRMV-PR: {crmv}.
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

    # Tenta desenhar imagem de fundo
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

    # Configurações de fonte
    font_label = "Helvetica-Bold"
    font_value = "Helvetica"
    font_label_size = 9
    font_value_size = 9
    font_title_size = 13
    font_med_title = 10
    font_footer = 10

    # Margens
    margem_esquerda = 2 * cm
    margem_direita = 2 * cm
    largura_util = largura - margem_esquerda - margem_direita

    # Título
    y_titulo = altura - 4 * cm
    c.setFont(font_label, font_title_size)
    c.drawCentredString(largura / 2, y_titulo, tipo_farmacia.upper())

    # Dados do Paciente - (coluna esquerda)
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

    # Dados do Tutor - (coluna direita)
    y_right = y_titulo - 1 * cm
    right_fields = [
        ("TUTOR(A): ", tutor),
        ("CPF: ", formatar_cpf(cpf))
    ]
    if rg:
        right_fields.append(("RG: ", rg))
    if endereco_formatado:
        # Formatar o CEP dentro do endereço
        # Extrair o CEP do endereco_formatado para formatá-lo
        cep_match = re.search(r'CEP:\s*(\d{5}-\d{3})', endereco_formatado)
        if cep_match:
            cep_raw = cep_match.group(1)
            cep_formatado = formatar_cep(cep_raw)
            endereco_formatado = re.sub(r'CEP:\s*\d{5}-\d{3}', f'CEP: {cep_formatado}', endereco_formatado)
        right_fields.append(("ENDEREÇO: ", endereco_formatado))

    for label, valor in right_fields:
        c.drawString(margem_esquerda + largura_util / 2, y_right, label)
        offset = c.stringWidth(label, font_label, font_label_size)
        c.setFont(font_value, font_value_size)
        c.drawString(margem_esquerda + largura_util / 2 + offset, y_right, valor)
        c.setFont(font_label, font_label_size)
        y_right -= 0.7 * cm

    # Lista de Medicamentos
    y_med = min(y_left, y_right) - 1.2 * cm
    c.setFont(font_label, font_med_title)
    for i, med in enumerate(lista_medicamentos, start=1):
        texto_med = f"{i}) QTD: {med.get('quantidade', '').upper()} - MEDICAMENTO: {med.get('nome', '').upper()}"
        c.drawString(margem_esquerda, y_med, texto_med)
        y_med -= 0.8 * cm

    # Instruções de Uso
    y_inst = y_med - 1.5 * cm
    c.setFont(font_label, font_med_title)
    c.drawString(margem_esquerda, y_inst, "INSTRUÇÕES DE USO: ")
    y_inst -= 0.9 * cm
    c.setFont(font_value, font_value_size)
    for linha in instrucoes_uso.split("\n"):
        c.drawString(margem_esquerda, y_inst, linha.upper())
        y_inst -= 0.6 * cm

    # "Artefato Blezie": Desenha uma curva para impedir escrita abaixo
    y_curva_inicial = y_inst - 1.5 * cm
    if y_curva_inicial < 0:
        y_curva_inicial = 0
    y_curva_final = 8 * cm  # altura onde a curva terminará
    c.setLineWidth(2)
    c.setStrokeColor(colors.grey)
    c.bezier(margem_esquerda, y_curva_inicial,
             largura / 2, y_curva_inicial + 2 * cm,
             largura / 2, y_curva_final - 2 * cm,
             largura - margem_direita, y_curva_final)
    c.setStrokeColor(colors.black)

    # Rodapé: Assinatura, Data, Nome, CRMV
    # Posição 2 cm à esquerda do centro
    x_centro_rodape = (largura / 2) - 2 * cm
    y_rodape = 6 * cm

    # Desenha a imagem da assinatura (se existir)
    assinatura_width = 4 * cm
    assinatura_height = 1.5 * cm
    if imagem_assinatura and os.path.exists(imagem_assinatura):
        try:
            c.drawImage(
                imagem_assinatura,
                x_centro_rodape - (assinatura_width / 2),
                y_rodape,
                width=assinatura_width,
                height=assinatura_height,
                preserveAspectRatio=True,
                mask='auto'
            )
        except Exception as e:
            st.warning(f"[Aviso] Não foi possível inserir a assinatura: {e}")

    # Ajusta y após colocar a imagem
    y_rodape -= (assinatura_height + 0.5 * cm)

    c.setFont(font_value, font_footer)
    # Data
    c.drawCentredString(x_centro_rodape, y_rodape, f"CURITIBA, PR, {data_receita}")
    y_rodape -= 0.5 * cm
    # Nome veterinário
    c.drawCentredString(x_centro_rodape, y_rodape, f"M. V. {nome_vet_up}")
    y_rodape -= 0.5 * cm
    # CRMV
    c.drawCentredString(x_centro_rodape, y_rodape, f"CRMV-PR: {crmv}")

    c.showPage()
    c.save()
    return nome_pdf

# ----------------------------------------------
# INTERFACE PRINCIPAL (STREAMLIT)
# ----------------------------------------------
def main():
    st.title("Gerador de Receituário Veterinário")

    # Verifica se o usuário está autenticado
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if "usuario_logado" not in st.session_state:
        st.session_state.usuario_logado = None

    # ----------------------------------
    # TELA DE LOGIN
    # ----------------------------------
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
        return  # Impede o acesso ao restante do aplicativo se não estiver autenticado

    # Se chegou aqui, está autenticado
    usuario_atual = st.session_state.usuario_logado
    st.write(f"Usuário logado: **{usuario_atual['login']}**")

    # ----------------------------------
    # BOTÃO PARA SAIR
    # ----------------------------------
    if st.button("Sair"):
        st.session_state.autenticado = False
        st.session_state.usuario_logado = None
        st.experimental_rerun()

    # ----------------------------------
    # MENU LATERAL
    # ----------------------------------
    menu = ["Gerar Receita", "Meu Perfil"]
    if usuario_atual["is_admin"]:
        menu.append("Administração de Usuários")

    escolha = st.sidebar.selectbox("Menu", menu)

    # ----------------------------------
    # FUNÇÕES DE TELA
    # ----------------------------------
    def tela_admin():
        st.subheader("Administração de Usuários")

        st.write("### Usuários Existentes:")
        usuarios = carregar_usuarios()
        if usuarios:
            for u, data in usuarios.items():
                st.write(f"- **Login**: {u} | Admin: {data.get('is_admin', False)}")
        else:
            st.write("Não há usuários cadastrados no arquivo.")

        st.write("---")
        st.write("### Cadastrar Novo Usuário")
        novo_login = st.text_input("Novo login")
        nova_senha = st.text_input("Nova senha", type="password")
        admin_flag = st.checkbox("Usuário é administrador?")
        if st.button("Cadastrar/Atualizar Usuário"):
            if novo_login and nova_senha:
                cadastrar_usuario(novo_login, nova_senha, admin_flag)
                st.success(f"Usuário '{novo_login}' cadastrado/atualizado com sucesso!")
                st.experimental_rerun()
            else:
                st.warning("É necessário preencher login e senha.")

        st.write("---")
        st.write("### Remover Usuário")
        usuario_remover = st.text_input("Login do usuário para remover:")
        if st.button("Remover"):
            if usuario_remover:
                remover_usuario(usuario_remover)
                st.success(f"Usuário '{usuario_remover}' removido com sucesso!")
                st.experimental_rerun()
            else:
                st.warning("Informe o login do usuário a ser removido.")

    def tela_perfil():
        st.subheader("Meu Perfil")
        st.write("Aqui você pode configurar os dados de Veterinário(a), imagens etc.")

        # Pasta do usuário
        user_folder = os.path.join(USER_FILES_DIR, usuario_atual["login"])
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)

        # Nome Veterinário(a) e CRMV
        nome_vet_atual = usuario_atual.get("nome_vet") or ""
        crmv_atual = usuario_atual.get("crmv") or ""

        nome_vet_input = st.text_input("Nome do(a) Veterinário(a):", value=nome_vet_atual)
        crmv_input = st.text_input("CRMV (somente números ou ex: 12345):", value=crmv_atual)
        if st.button("Salvar Dados Veterinário"):
            atualizar_dados_veterinario(usuario_atual["login"], nome_vet_input, crmv_input)
            st.success("Dados de Veterinário(a) atualizados!")
            # Atualiza session_state
            usuario_atual["nome_vet"] = nome_vet_input
            usuario_atual["crmv"] = crmv_input

        st.write("---")
        # Upload de imagem de fundo
        fundo_file = st.file_uploader("Upload da Imagem de Fundo (opcional)", type=["png", "jpg", "jpeg"])
        if fundo_file is not None:
            fundo_path = os.path.join(user_folder, "fundo_" + fundo_file.name)
            with open(fundo_path, "wb") as f:
                f.write(fundo_file.getvalue())
            atualizar_imagem_usuario(usuario_atual["login"], fundo_path, tipo="fundo")
            st.success("Imagem de fundo atualizada com sucesso!")
            usuario_atual["fundo"] = fundo_path

        # Upload de assinatura
        assinatura_file = st.file_uploader("Upload da Assinatura (opcional)", type=["png", "jpg", "jpeg"])
        if assinatura_file is not None:
            assinatura_path = os.path.join(user_folder, "assinatura_" + assinatura_file.name)
            with open(assinatura_path, "wb") as f:
                f.write(assinatura_file.getvalue())
            atualizar_imagem_usuario(usuario_atual["login"], assinatura_path, tipo="assinatura")
            st.success("Assinatura atualizada com sucesso!")
            usuario_atual["assinatura"] = assinatura_path

        st.write("---")
        st.write("**Imagem de fundo atual**:", usuario_atual.get("fundo"))
        st.write("**Assinatura atual**:", usuario_atual.get("assinatura"))
        st.write("**Nome Vet:**", usuario_atual.get("nome_vet"))
        st.write("**CRMV:**", usuario_atual.get("crmv"))

    def tela_receita():
        st.subheader("Gerar Receituário")

        # Inicializa a lista de medicamentos no session_state
        if "lista_medicamentos" not in st.session_state:
            st.session_state.lista_medicamentos = []
        # Caso queira limpar sempre, poderíamos fazer:
        # else:
        #     st.session_state.lista_medicamentos = []

        # Escolha do Tipo de Farmácia
        opcoes_farmacia = [
            "FARMÁCIA VETERINÁRIA",
            "FARMÁCIA HUMANA",
            "FARMÁCIA DE MANIPULAÇÃO - VETERINÁRIA",
            "FARMÁCIA DE MANIPULAÇÃO - HUMANO"
        ]
        tipo_farmacia = st.selectbox("Selecione o tipo de Farmácia:", opcoes_farmacia)

        # Pergunta se é medicamento controlado
        eh_controlado = st.radio("Medicamento Controlado?", ("Não", "Sim"))

        # Se for controlado, RG e CEP/Endereço são necessários
        rg = ""
        endereco_formatado = ""

        if eh_controlado == "Sim":
            rg = st.text_input("RG do Tutor(a):")

            st.write("### Preenchimento do Endereço")
            # Escolha entre Automático ou Manual
            modo_endereco = st.radio(
                "Escolha a forma de preenchimento do endereço:",
                ("Automático (via CEP)", "Manual")
            )

            if modo_endereco == "Automático (via CEP)":
                # CEP - busca automática
                if "cep_tutor" not in st.session_state:
                    st.session_state.cep_tutor = ""
                if "end_busca" not in st.session_state:
                    st.session_state.end_busca = {}  # dicionário com logradouro, bairro, etc.

                cep_digitado = st.text_input(
                    "CEP do Tutor(a):",
                    value=st.session_state.cep_tutor,
                    help="Digite o CEP sem hífen, por exemplo: 12345678"
                )

                # Se o CEP mudou, tentamos buscar novamente
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
                # Preenchimento Manual
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

        # Dados do Paciente
        st.write("---")
        paciente = st.text_input("Nome do Paciente:")
        especie_raca = st.text_input("Espécie - Raça:")
        pelagem = st.text_input("Pelagem:")
        peso = st.text_input("Peso:")
        idade = st.text_input("Idade:")
        sexo = st.radio("Sexo:", ("Macho", "Fêmea"))
        chip = st.text_input("Número do Chip (se houver):")

        # Dados do Tutor
        st.write("---")
        tutor = st.text_input("Nome do Tutor(a):")
        cpf = st.text_input("CPF do Tutor(a):")

        # Medicamentos
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

        # Instruções de Uso
        st.write("---")
        instrucoes_uso = st.text_area("Digite as instruções de uso:")

        # Gerar Receita
        if st.button("Gerar Receita"):
            # Validações necessárias
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
            if eh_controlado == "Sim" and not re.fullmatch(r'\d{5}-\d{3}', formatar_cep(cep_manual if 'cep_manual' in locals() else st.session_state.get('cep_tutor', ''))):
                st.error("CEP inválido. Deve estar no formato 12345-678.")
                return

            # Preparar dados para o PDF
            imagem_fundo = usuario_atual.get("fundo")
            imagem_assinatura = usuario_atual.get("assinatura")
            nome_vet = usuario_atual.get("nome_vet") or ""
            crmv = usuario_atual.get("crmv") or ""

            # Nome do PDF (pode personalizar)
            nome_pdf = f"{paciente.replace(' ', '_')}_receita.pdf"

            # Gera PDF
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
                data_receita=datetime.datetime.now().strftime("%d/%m/%Y")
            )
            with open(nome_pdf, "rb") as f:
                st.download_button(
                    label="Baixar Receita",
                    data=f,
                    file_name=nome_pdf,
                    mime="application/pdf"
                )

    # ----------------------------------
    # NAVEGAÇÃO ENTRE AS TELAS
    # ----------------------------------
    if escolha == "Gerar Receita":
        tela_receita()
    elif escolha == "Meu Perfil":
        tela_perfil()
    elif escolha == "Administração de Usuários":
        if usuario_atual["is_admin"]:
            tela_admin()
        else:
            st.error("Você não tem permissão para acessar esta área.")

# ----------------------------------------------
# INICIALIZAÇÃO
# ----------------------------------------------
if __name__ == "__main__":
    # Cria pasta para arquivos de usuários, se não existir
    if not os.path.exists(USER_FILES_DIR):
        os.makedirs(USER_FILES_DIR)

    main()
