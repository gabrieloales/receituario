import os
import json
import datetime
import re
import base64
import requests
import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors

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
        return {"login": login, "is_admin": True, "fundo": None, "assinatura": None, "nome_vet": None, "crmv": None}

    usuarios = carregar_usuarios()
    user_data = usuarios.get(login)
    if user_data and user_data.get("password") == senha:
        return {
            "login": login,
            "is_admin": user_data.get("is_admin", False),
            "fundo": user_data.get("background_image"),
            "assinatura": user_data.get("signature_image"),
            "nome_vet": user_data.get("nome_vet"),
            "crmv": user_data.get("crmv")
        }
    return None


def cadastrar_usuario(novo_login, nova_senha, nome_vet, crmv, is_admin=False):
    usuarios = carregar_usuarios()
    if novo_login not in usuarios:
        usuarios[novo_login] = {}
    
    usuarios[novo_login]["password"] = nova_senha
    usuarios[novo_login]["is_admin"] = is_admin
    usuarios[novo_login]["nome_vet"] = nome_vet
    usuarios[novo_login]["crmv"] = crmv

    if "background_image" not in usuarios[novo_login]:
        usuarios[novo_login]["background_image"] = None
    if "signature_image" not in usuarios[novo_login]:
        usuarios[novo_login]["signature_image"] = None

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
                st.experimental_rerun()
            else:
                st.error("Login ou senha incorretos.")
        return

    usuario_atual = st.session_state.usuario_logado
    st.write(f"Usuário logado: **{usuario_atual['login']}**")

    if st.button("Sair"):
        st.session_state.autenticado = False
        st.session_state.usuario_logado = None
        st.experimental_rerun()

    menu = ["Meu Perfil"]
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
        st.write("Aqui você pode visualizar suas informações.")

        st.write("**Nome do(a) Veterinário(a):**", usuario_atual.get("nome_vet", "Não Definido"))
        st.write("**CRMV:**", usuario_atual.get("crmv", "Não Definido"))

        st.write("---")
        fundo_file = st.file_uploader("Upload da Imagem de Fundo (opcional)", type=["png", "jpg", "jpeg"])
        if fundo_file is not None:
            fundo_path = os.path.join(USER_FILES_DIR, usuario_atual["login"], "fundo_" + fundo_file.name)
            with open(fundo_path, "wb") as f:
                f.write(fundo_file.getvalue())
            st.success("Imagem de fundo atualizada!")

        assinatura_file = st.file_uploader("Upload da Assinatura (opcional)", type=["png", "jpg", "jpeg"])
        if assinatura_file is not None:
            assinatura_path = os.path.join(USER_FILES_DIR, usuario_atual["login"], "assinatura_" + assinatura_file.name)
            with open(assinatura_path, "wb") as f:
                f.write(assinatura_file.getvalue())
            st.success("Assinatura atualizada!")

        st.write("---")
        st.write("**Imagem de fundo atual**:", usuario_atual.get("fundo"))
        st.write("**Assinatura atual**:", usuario_atual.get("assinatura"))

    if escolha == "Meu Perfil":
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
