import os
import json
import datetime
import re
import requests
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import Image
import streamlit as st

# ----------------------------------------------
# CONSTANTES E CONFIGURAÇÕES
# ----------------------------------------------
USERS_FILE = "users.json"  # Arquivo para armazenar usuários
USER_FILES_DIR = "user_files"  # Pasta base para armazenar arquivos de cada usuário

# Administrador "principal" hard-coded (opcional).
ADMIN_LOGIN = "larsen"
ADMIN_SENHA = "31415962Isa@"


# ----------------------------------------------
# FUNÇÕES DE SUPORTE
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
        return {"login": login, "is_admin": True, "fundo": None, "assinatura": None}

    # Caso contrário, verifica no arquivo de usuários:
    usuarios = carregar_usuarios()
    user_data = usuarios.get(login)
    if user_data and user_data.get("password") == senha:
        return {
            "login": login,
            "is_admin": user_data.get("is_admin", False),
            "fundo": user_data.get("background_image"),
            "assinatura": user_data.get("signature_image")
        }
    return None


def cadastrar_usuario(novo_login, nova_senha, is_admin=False):
    """Cadastra um novo usuário (ou atualiza se já existir)."""
    usuarios = carregar_usuarios()
    usuarios[novo_login] = {
        "password": nova_senha,
        "is_admin": is_admin,
        "background_image": None,
        "signature_image": None
    }
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
        st.warning(f"Erro ao buscar CEP: {e}")
        return {}


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
    # Novos campos:
    imagem_fundo=None,
    imagem_assinatura=None
):
    if lista_medicamentos is None:
        lista_medicamentos = []
    if not data_receita:
        data_receita = datetime.datetime.now().strftime("%d/%m/%Y")

    largura, altura = A4
    c = canvas.Canvas(nome_pdf, pagesize=A4)

    # Se existir imagem de fundo, desenha no background (ajuste se necessário)
    if imagem_fundo and os.path.exists(imagem_fundo):
        # Preenche a página inteira
        c.drawImage(imagem_fundo, 0, 0, width=largura, height=altura)

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
    y_med = min(y_left, y_right) - 1 * cm  # Começa abaixo do menor dos dois lados
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

    # Se existir imagem de assinatura, desenha acima da linha de assinatura
    if imagem_assinatura and os.path.exists(imagem_assinatura):
        # Ajuste a largura/altura da assinatura conforme necessário:
        assinatura_largura = 4 * cm
        assinatura_altura = 2 * cm
        c.drawImage(
            imagem_assinatura,
            margem_esquerda,  # x
            y_rodape - 0.7 * cm - assinatura_altura,  # y (logo acima da linha)
            width=assinatura_largura,
            height=assinatura_altura
        )
        c.drawString(
            margem_esquerda,
            y_rodape - 1.0 * cm - assinatura_altura,
            "_________________________________"
        )
    else:
        # Caso não tenha assinatura, apenas imprime a linha
        c.drawString(margem_esquerda, y_rodape - 0.7 * cm, "Assinatura: ___________________________")

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
    # MENU
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
        st.write("Aqui você pode fazer o upload das suas imagens de fundo e assinatura.")

        # Pasta do usuário
        user_folder = os.path.join(USER_FILES_DIR, usuario_atual["login"])
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)

        # Upload de imagem de fundo
        fundo_file = st.file_uploader("Upload da Imagem de Fundo (opcional)", type=["png", "jpg", "jpeg"])
        if fundo_file is not None:
            # Salvar localmente
            fundo_path = os.path.join(user_folder, "fundo_" + fundo_file.name)
            with open(fundo_path, "wb") as f:
                f.write(fundo_file.getvalue())
            # Atualiza no JSON
            atualizar_imagem_usuario(usuario_atual["login"], fundo_path, tipo="fundo")
            st.success("Imagem de fundo atualizada com sucesso!")
            # Atualiza session_state
            usuario_atual["fundo"] = fundo_path

        # Upload de assinatura
        assinatura_file = st.file_uploader("Upload da Assinatura (opcional)", type=["png", "jpg", "jpeg"])
        if assinatura_file is not None:
            # Salvar localmente
            assinatura_path = os.path.join(user_folder, "assinatura_" + assinatura_file.name)
            with open(assinatura_path, "wb") as f:
                f.write(assinatura_file.getvalue())
            # Atualiza no JSON
            atualizar_imagem_usuario(usuario_atual["login"], assinatura_path, tipo="assinatura")
            st.success("Assinatura atualizada com sucesso!")
            # Atualiza session_state
            usuario_atual["assinatura"] = assinatura_path

        st.write("---")
        st.write("**Imagem de fundo atual**:", usuario_atual["fundo"])
        st.write("**Assinatura atual**:", usuario_atual["assinatura"])

    def tela_receita():
        # Inicializa a lista de medicamentos no session_state
        if "lista_medicamentos" not in st.session_state:
            st.session_state.lista_medicamentos = []

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
        qtd_med = st.text_input("Quantidade do Medicamento:")
        nome_med = st.text_input("Nome do Medicamento:")
        if st.button("Adicionar Medicamento"):
            st.session_state.lista_medicamentos.append({"quantidade": qtd_med, "nome": nome_med})
            st.success("Medicamento adicionado!")

        st.write("Medicamentos Adicionados:")
        for i, med in enumerate(st.session_state.lista_medicamentos, start=1):
            st.write(f"{i}) QTD: {med['quantidade']} - MEDICAMENTO: {med['nome']}")

        st.subheader("Instruções de Uso")
        instrucoes_uso = st.text_area("Digite as instruções de uso:")

        if st.button("Gerar Receita"):
            # Carregamos as imagens do fundo/assinatura do usuário atual (se houver)
            imagem_fundo = usuario_atual.get("fundo")
            imagem_assinatura = usuario_atual.get("assinatura")

            nome_pdf = gerar_pdf_receita(
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
                imagem_assinatura=imagem_assinatura
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
