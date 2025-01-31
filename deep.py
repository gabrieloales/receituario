if st.button("Gerar Receita"):
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
        crmv=crmv
    )
    with open(nome_pdf, "rb") as f:
        st.download_button(
            label="Baixar Receita",
            data=f,
            file_name=nome_pdf,
            mime="application/pdf"
        )
    st.experimental_rerun()  # Força o recarregamento da página para exibir o botão de download
