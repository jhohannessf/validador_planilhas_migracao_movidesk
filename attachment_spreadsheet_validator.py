import pandas as pd
import os
import mimetypes
import time
from pydantic import BaseModel, EmailStr, Field, ValidationError, field_validator, model_validator, BeforeValidator, ValidationInfo
from typing import Optional, List, Literal, Union, Any


class AttachmentsSchema(BaseModel):
    number_ticket: int = Field(..., alias="Ticket")  # Número do ticket ou código da pessoa - Obrigatório
    number_action: int = Field(..., alias="Número da Ação")  # Id do campo
    path: str = Field(..., alias="Caminho")  # Caminho do arquivo na máquina, usar \ - Obrigatório
    name_file: Optional[str] = Field(None, alias="Nome Arquivo")  # Obrigatório
    content_type: Optional[str] = Field(None, alias="Content Type")  # Obrigatório

    @model_validator(mode='before')
    @classmethod
    def validar_e_preencher_obrigatoriamente(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # 1. PEGAR O CAMINHO E LIMPAR AS BARRAS
            # Buscamos tanto pelo nome da variável quanto pelo alias do Excel
            caminho = data.get("Caminho") or data.get("path")

            # Forçamos a conversão para string e o replace
            caminho_limpo = str(caminho).replace("/", "\\") if caminho and not pd.isna(caminho) else ""

            # ATUALIZAMOS O DICIONÁRIO DIRETAMENTE (Isso reflete no objeto mesmo se der erro depois)
            data["Caminho"] = caminho_limpo
            data["path"] = caminho_limpo

            # 2. EXTRAIR NOME DO ARQUIVO SE ESTIVER VAZIO
            nome_original = data.get("Nome Arquivo") or data.get("name_file")

            if not nome_original or str(nome_original).strip().lower() in ["nan", "none", ""]:
                if caminho_limpo and "\\" in caminho_limpo:
                    nome_extraido = os.path.basename(caminho_limpo)
                    data["Nome Arquivo"] = nome_extraido
                    data["name_file"] = nome_extraido
                elif caminho_limpo:  # Caso seja um nome de arquivo sem pastas
                    data["Nome Arquivo"] = caminho_limpo
                    data["name_file"] = caminho_limpo

            # 3. PREENCHER CONTENT TYPE
            nome_para_mime = data.get("Nome Arquivo") or data.get("name_file")
            if nome_para_mime:
                mime_tipo, _ = mimetypes.guess_type(str(nome_para_mime))
                tipo_final = mime_tipo or "application/octet-stream"
                data["Content Type"] = tipo_final
                data["content_type"] = tipo_final

        return data

    @model_validator(mode='after')
    def validar_todas_as_regras(self) -> 'AttachmentsSchema':
        erros_da_linha = []

        # 1. Validação de campos em branco
        obrigatorios = {
            "number_ticket": "Ticket",
            "number_action": "Número da Ação",
            "path": "Caminho",
            "name_file": "Nome Arquivo",
            "content_type": "Content Type",

        }
        for campo, nome_coluna in obrigatorios.items():
            valor = getattr(self, campo)
            if valor is None or str(valor).strip() == "" or (isinstance(valor, float) and pd.isna(valor)):
                erros_da_linha.append(
                    f"{nome_coluna}: Este campo não pode ficar em branco. Por favor, informe um valor.")

        return self

    @field_validator('number_ticket', 'number_action', mode='before')
    @classmethod
    def validar_inteiro(cls, v, info):
        if v is None or str(v).strip().lower() in ["nan", "none", ""]:
            return None
        try:
            return int(float(str(v).strip()))
        except (ValueError, TypeError):
            # Verificamos qual campo falhou e atribuímos o nome da coluna correto
            nome_exibicao = "Ticket" if info.field_name == "number_ticket" else "Número da Ação"
            raise ValueError(f"{nome_exibicao}: O valor informado deve ser um número inteiro válido.")

    @field_validator('number_ticket', mode='before')
    def validar_number_ticket(cls, v):
        # Verifica se o valor é uma string vazia após remover espaços
        if v is None or str(v).strip().lower() in ["nan", "none", ""]:
            raise ValueError('Ticket: Informe o número do ticket!')
        return v

    @field_validator('number_action', mode='before')
    def validar_number_action(cls, v):
        # Verifica se o valor é uma string vazia após remover espaços
        if v is None or str(v).strip().lower() in ["nan", "none", ""]:
            raise ValueError('Número da ação: Informe o número da ação dentro do ticket!')
        return v

    @field_validator('name_file', mode='before')
    @classmethod
    def extract_filename_from_path(cls, v: Any, info: ValidationInfo) -> str:
        # Pega o valor da coluna 'Caminho' diretamente dos dados brutos (alias)
        # O Pandas/Pydantic às vezes usa o alias no info.data
        path_value = info.data.get('path') or info.data.get('Caminho')

        # Se o Nome do Arquivo vier vazio, extraímos do caminho
        if v is None or str(v).strip().lower() in ["nan", "none", ""]:
            if path_value:
                return os.path.basename(str(path_value))
        return v

    @field_validator('path', mode='before')
    @classmethod
    def padronizar_barras(cls, v: Any) -> Any:
        if isinstance(v, str):
            # Substitui barras normais "/" por barras invertidas "\"
            return v.replace("/", "\\")
        return v


def processar_validar_planilha_attachments(caminho_entrada, caminho_saida):
    # Leitura inicial
    df_entrada = pd.read_excel(caminho_entrada)
    df_entrada.columns = [c.strip() for c in df_entrada.columns]

    df = pd.DataFrame(df_entrada)

    novas_linhas = []

    for index, row in df.iterrows():
        # Transforma a linha em dicionário (nomes originais do Excel)
        dados_da_planilha = row.to_dict()

        try:
            # 1. O Pydantic processa e o model_validator preenche o campo
            objeto_valido = AttachmentsSchema.model_validate(dados_da_planilha)

            # 2. IMPORTANTE: Criamos a linha final a partir do objeto VALIDADO
            # O by_alias=True faz o Pydantic devolver as chaves "Nome do Arquivo", "Ticket", etc.
            nova_l = objeto_valido.model_dump(by_alias=True)

            nova_l.update({
                "Validado": "Sim",
                "Coluna_com_Erro": "",
                "Mensagem_de_Erro": ""
            })
            novas_linhas.append(nova_l)

        except ValidationError as e:
            mensagens_finais = []
            colunas_finais = []

            for erro in e.errors():
                msg = erro['msg'].replace("Value error, ", "").replace("Assertion failed, ", "")
                if " || " in msg:
                    for sub in msg.split(" || "):
                        sub_limpa = sub.strip()
                        mensagens_finais.append(sub_limpa)
                        if ":" in sub_limpa: colunas_finais.append(sub_limpa.split(":")[0].strip())
                else:
                    colunas_finais.append(msg.split(":")[0].strip() if ":" in msg else str(erro['loc'][-1]))
                    mensagens_finais.append(msg)

            # Definindo as variáveis que deram erro antes
            col_err = ", ".join(list(dict.fromkeys(colunas_finais)))
            msg_err = " | ".join(list(dict.fromkeys(mensagens_finais)))

            linha_erro = dados_da_planilha.copy()
            linha_erro.update({
                "Validado": "Não",
                "Coluna_com_Erro": col_err,
                "Mensagem_de_Erro": msg_err
            })
            novas_linhas.append(linha_erro)
            print(f"❌ Ticket: {dados_da_planilha.get('Ticket')} | Linha: {index} | Erros: {msg_err}")

    # Salvar
    df_final = pd.DataFrame(novas_linhas)

    # Remove as colunas internas que o Pydantic cria além dos Aliases
    colunas_para_remover = ['name_file', 'path', 'number_ticket', 'number_action', 'content_type']
    for col in colunas_para_remover:
        if col in df_final.columns:
            df_final = df_final.drop(columns=[col])

    # Reorganiza na ordem exata da sua imagem
    ordem_oficial = ["Ticket", "Número da Ação", "Caminho", "Nome Arquivo", "Content Type", "Validado",
                     "Coluna_com_Erro", "Mensagem_de_Erro"]
    df_final = df_final.reindex(columns=[c for c in ordem_oficial if c in df_final.columns])

    with pd.ExcelWriter(caminho_saida, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, index=False)


if __name__ == "__main__":
    # 1. Registra o momento de início
    inicio = time.time()

    print("Iniciando o processamento da planilha...")

    # Chamada da sua função
    processar_validar_planilha_attachments('files/attachments.xlsx', 'files/attachments-atualizada.xlsx')

    # 2. Registra o momento de término
    fim = time.time()

    # 3. Calcula a duração total
    duracao = fim - inicio

    # Exibe o tempo formatado
    if duracao < 60:
        print(f"\n✅ Processamento concluído em: {duracao:.2f} segundos.")
    else:
        minutos = int(duracao // 60)
        segundos = int(duracao % 60)
        print(f"\n✅ Processamento concluído em: {minutos} minuto(s) e {segundos} segundo(s).")
