from flask import Flask, request, jsonify
import os
import json
import datetime
import re
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors

app = Flask(__name__)

# --- Insira aqui as funções auxiliares e a função de gerar_pdf_receita do seu código original ---

@app.route('/criar_receita', methods=['POST'])
def criar_receita():
    try:
        data = request.json
        
        # Extrair dados do corpo da requisição
        paciente = data.get("paciente", "")
        tutor = data.get("tutor", "")
        cpf = data.get("cpf", "")
        rg = data.get("rg", "")
        endereco_formatado = data.get("endereco_formatado", "")
        especie_raca = data.get("especie_raca", "")
        pelagem = data.get("pelagem", "")
        peso = data.get("peso", "")
        idade = data.get("idade", "")
        sexo = data.get("sexo", "")
        chip = data.get("chip", "")
        lista_medicamentos = data.get("lista_medicamentos", [])
        instrucoes_uso = data.get("instrucoes_uso", "")
        data_receita = data.get("data_receita", datetime.datetime.now().strftime("%d/%m/%Y"))
        
        nome_arquivo_pdf = f"{paciente} - {cpf}.pdf"
        caminho_pdf = os.path.join("Receitas", nome_arquivo_pdf)
        
        os.makedirs("Receitas", exist_ok=True)

        # Gerar PDF
        gerar_pdf_receita(
            nome_pdf=caminho_pdf,
            tipo_farmacia="Farmácia Veterinária",
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
            instrucoes_uso=instrucoes_uso,
            data_receita=data_receita
        )

        return jsonify({"message": "Receita criada com sucesso!", "file_path": caminho_pdf}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/ver_historico', methods=['GET'])
def ver_historico():
    historico_arquivo = "historico_receitas.json"
    if not os.path.exists(historico_arquivo):
        return jsonify({"message": "Nenhum histórico encontrado."}), 404
    try:
        with open(historico_arquivo, "r", encoding="utf-8") as f:
            historico = json.load(f)
        return jsonify(historico), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use a porta definida pela variável de ambiente ou 5000 como padrão
    app.run(host="0.0.0.0", port=port)

