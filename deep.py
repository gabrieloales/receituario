import os
import json
import datetime
import re
import base64
import streamlit as st

# ----------------------------------------------
# CONSTANTES E CONFIGURAÇÕES
# ----------------------------------------------
USERS_FILE = "users.json"
USER_FILES_DIR = "user_files"

# Administrador principal
ADMIN_LOGIN = "larsen"
ADMIN_SENHA = "31415962Isa@"


# ----------------------------------------------
# FUNÇÕES DE SUPORTE A USUÁRIOS
# ----------------------------------------------
def carregar_usuarios():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return {}


def salvar_usuarios(usuarios):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(usuarios, f, indent=4, ensure_ascii=False)


def verificar_login(login, senha):
    if login == ADMIN_LOGIN and senha == ADMIN_SENHA:
        return {"login": login, "is_admin": True, "nome_vet": None, "crmv": None}

    usuarios = carregar_usuarios()
    user_data = usuarios.get(login)
    if user_data and user_data.get("password") == senha:
        return {
            "login": login,
            "is_admin": user_data.get("is_admin", False),
            "nome_vet": user_data.get("nome_vet"),
            "crmv": user_data.get("crmv")
        }
    return None


def cadastrar_usuario(novo_login, nova_senha, nome_vet, crmv, is_admin=False):
    usuarios = carregar_usuarios()
    usuarios[novo_login] = {
        "password": nova_senha,
        "is_admin": is_admin,
        "nome_vet": nome_vet if not is_admin else None,
        "crmv": crmv if not is_admin else None
    }
    salvar_usuarios(usuarios)


def remover_usuario(login):
    usuarios = carregar_usuarios()
    if login in usuarios:
        del usuarios[login]
        salvar_usuarios(usuarios)


# ----------------------------------------------
# INTERFACE PRINCIPAL (STREAMLIT)
# ----------------------------------------------
def main():
    st.title("Gerador de Receituário Veterinário")

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
            else:
                st.error("Login ou senha incorretos.")
        return

    usuario_atual = st.session_state.usuario_logado
    st.write(f"Usuário logado: **{usuario_atual['login']}**")

    if st.button("Sair"):
        st.session_state.autenticado = False
        st.session_state.usuario_logado = None

    menu = ["Gerar Receita", "Meu Perfil"]
    if usuario_atual["is_admin"]:
        menu.append("Administração de Usuários")
    escolha = st.sidebar.selectbox("Menu", menu)

    def tela_admin():
        st.subheader("Administração de Usuários")

        st.write("### Usuários Existentes:")
        usuarios = carregar_usuarios()
        if usuarios:
            for u, data in usuarios.items():
                st.write(f"- **Login**: {u} | Admin: {data.get('is_admin', False)}")
        else:
            st.write("Não há usuários cadastrados.")

        st.write("---")
        st.write("### Cadastrar Novo Usuário")
        novo_login = st.text_input("Novo login")
        nova_senha = st.text_input("Nova senha", type="password")
        admin_flag = st.checkbox("Usuário é administrador?")
        
        nome_vet_input = ""
        crmv_input = ""

        if not admin_flag:
            nome_vet_input = st.text_input("Nome do(a) Veterinário(a):")
            crmv_input = st.text_input("CRMV:")

        if st.button("Cadastrar/Atualizar Usuário"):
            if novo_login and nova_senha:
                cadastrar_usuario(novo_login, nova_senha, nome_vet_input, crmv_input, admin_flag)
                st.success(f"Usuário '{novo_login}' cadastrado/atualizado com sucesso!")
            else:
                st.warning("É necessário preencher login e senha.")

        st.write("---")
        st.write("### Remover Usuário")
        usuario_remover = st.text_input("Login do usuário para remover:")
        if st.button("Remover"):
            if usuario_remover:
                remover_usuario(usuario_remover)
                st.success(f"Usuário '{usuario_remover}' removido com sucesso!")
            else:
                st.warning("Informe o login do usuário a ser removido.")

    def tela_perfil():
        st.subheader("Meu Perfil")
        st.write("Aqui você pode visualizar suas informações.")

        st.write("**Nome do(a) Veterinário(a):**", usuario_atual.get("nome_vet", "Não Definido"))
        st.write("**CRMV:**", usuario_atual.get("crmv", "Não Definido"))

    def tela_receita():
        st.subheader("Gerar Receituário")

        # Exibir dados do veterinário (bloqueados para edição)
        st.write("**Veterinário(a):**", usuario_atual.get("nome_vet", "Não Definido"))
        st.write("**CRMV:**", usuario_atual.get("crmv", "Não Definido"))

        paciente = st.text_input("Nome do Paciente:")
        tutor = st.text_input("Nome do Tutor:")
        cpf = st.text_input("CPF do Tutor:")
        especie_raca = st.text_input("Espécie - Raça:")
        pelagem = st.text_input("Pelagem:")
        peso = st.text_input("Peso:")
        idade = st.text_input("Idade:")
        sexo = st.radio("Sexo:", ["Macho", "Fêmea"])
        chip = st.text_input("Número do Chip (se houver):")
        medicamento = st.text_input("Nome do Medicamento:")
        quantidade = st.text_input("Quantidade:")
        instrucoes = st.text_area("Instruções de Uso:")

        if st.button("Gerar Receita"):
            if paciente and tutor and medicamento and quantidade:
                st.success(f"Receita gerada para {paciente}!")
            else:
                st.warning("Todos os campos devem ser preenchidos.")

    if escolha == "Gerar Receita":
        tela_receita()
    elif escolha == "Meu Perfil":
        tela_perfil()
    elif escolha == "Administração de Usuários":
        if usuario_atual["is_admin"]:
            tela_admin()
        else:
            st.error("Você não tem permissão para acessar esta área.")

if __name__ == "__main__":
    if not os.path.exists(USER_FILES_DIR):
        os.makedirs(USER_FILES_DIR)

    main()
