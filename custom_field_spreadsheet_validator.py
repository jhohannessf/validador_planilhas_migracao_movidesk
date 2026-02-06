import pandas as pd
import time
from pydantic import BaseModel, EmailStr, Field, ValidationError, field_validator, model_validator, BeforeValidator
from typing import Optional, List, Literal, Union, Any
from datetime import datetime


class CustomFieldsSchema(BaseModel):
    number: int = Field(..., alias="id")  # Número do ticket ou código da pessoa - Obrigatório
    custom_field_id: int = Field(..., alias="CustomFieldId")  # Id do campo
    custom_field_name: str = Field(..., alias="CustomFieldName")  # Nome do campo
    value: Any = Field(None, alias="value")  # valor do campo - Obrigatório
    type: Literal["Person", "Ticket"] = Field(..., alias="Type")  # Person ou Ticket - Obrigatório

    # @model_validator(mode='after')
    # def validar_todas_as_regras(self) -> 'CustomFieldsSchema':
    #     erros_da_linha = []
    #
    #     # 1. Validação de campos em branco
    #     obrigatorios = {
    #         "number": "id",
    #         "custom_field_id": "CustomFieldId",
    #         "custom_field_name": "CustomFieldName",
    #         "value": "value",
    #         "type": "Type",
    #
    #     }
    #     for campo, nome_coluna in obrigatorios.items():
    #         valor = getattr(self, campo)
    #         if valor is None or str(valor).strip() == "" or (isinstance(valor, float) and pd.isna(valor)):
    #             erros_da_linha.append(
    #                 f"{nome_coluna}: Este campo não pode ficar em branco. Por favor, informe um valor.")
    #
    #     return self

    @field_validator('number', 'custom_field_id', mode='before')
    @classmethod
    def validar_inteiro(cls, v, info):
        if v is None or str(v).strip().lower() in ["nan", "none", ""]:
            return None
        try:
            return int(float(str(v).strip()))
        except (ValueError, TypeError):
            # Verificamos qual campo falhou e atribuímos o nome da coluna correto
            nome_exibicao = "id" if info.field_name == "number" else "CustomFieldId"
            raise ValueError(f"{nome_exibicao}: O valor informado deve ser um número inteiro válido.")


    @field_validator('type', mode='before')
    @classmethod
    def normalizar_tipo(cls, v: str) -> str:
        # 'v' é o valor bruto da planilha (ex: "publico")
        # 'cls' é a própria classe TicketSchema
        if not v or not isinstance(v, str):
            return v

        # Converte para minúsculo e remove espaços para facilitar a busca
        valor_limpo = v.strip().lower()

        # Regra para Ticket
        if "ticke" in valor_limpo or "ticket" in valor_limpo:
            return "Ticket"

        elif "tickets" in valor_limpo or "Tickets" in valor_limpo:
            return "Ticket"

        # Regra para Person
        elif "person" in valor_limpo:
            return "Person"

        elif "Persons" in valor_limpo:
            return "Person"

        elif "person" in valor_limpo:
            return "Person"

        elif "pessoa" in valor_limpo:
            return "Person"

        return v  # Se não bater com nada, retorna o original para o Pydantic gerar o erro de Literal

    @field_validator('custom_field_id', mode='before')
    def validar_custom_field_id(cls, v):
        # Verifica se o valor é uma string vazia após remover espaços
        if v is None or str(v).strip().lower() in ["nan", "none", ""]:
            raise ValueError('CustomFieldId: Informe o código do campo adiconal dentro da base Movidesk. Não pode ficar em branco!')
        return v

    @field_validator('custom_field_name', mode='before')
    def validar_custom_field_name(cls, v):
        # Verifica se o valor é uma string vazia após remover espaços
        if v is None or str(v).strip().lower() in ["nan", "none", ""]:
            raise ValueError('CustomFieldName: Informe o nome do campo adiconal dentro da base Movidesk. Não pode ficar em branco!')
        return v

    @field_validator('value', mode='before')
    def validar_value(cls, v):
        # Verifica se o valor é uma string vazia após remover espaços
        if v is None or str(v).strip().lower() in ["nan", "none", ""]:
            raise ValueError('Value: Informe o valor/opção do campo. Não pode ficar em branco!')
        return v

    @field_validator('type', mode='before')
    @classmethod
    def validar_custom_field_id_preenchido(cls, v):
        # 1. Tratamento para campo Vazio
        if v is None or str(v).strip().lower() in ["nan", "none", ""]:
            raise ValueError('Type: Se for campo de pessoa, informe: Person. Se for campo de ticket, informe: Ticket')

        # 2. Normalização e Validação de conteúdo
        v_str = str(v).strip()

        # Opcional: Você pode ser flexível e aceitar "person" ou "PERSON" convertendo aqui
        if v_str.lower() == "person":
            return "Person"
        if v_str.lower() == "persons":
            return "Person"
        if v_str.lower() == "ticket":
            return "Ticket"
        if v_str.lower() == "tickets":
            return "Ticket"

        # 3. Se preencheu algo diferente de Person ou Ticket, lança seu erro customizado
        raise ValueError('Type: Valor inválido. Informe exatamente "Person" ou "Ticket".')


def processar_validar_planilha_custom_fields(caminho_entrada, caminho_saida):
    # Leitura inicial
    df_entrada = pd.read_excel(caminho_entrada)
    df_entrada.columns = [c.strip() for c in df_entrada.columns]

    # --- 1. RECONSTRUÇÃO: UNIR LINHAS QUEBRADAS PELO EXCEL ---
    linhas_unificadas = []
    linha_mestra = None

    df = pd.DataFrame(df_entrada)

    # --- 3. LOOP DE VALIDAÇÃO E DUPLICAÇÃO ---
    novas_linhas = []
    limite_excel = 32000

    for index, row in df.iterrows():
        dados_limpos = row.to_dict()

        """Atualizar o tipo para Person ou Ticket"""

        valor_original = str(dados_limpos.get('Type', '')).strip().lower()
        if 'ticket' in valor_original:
            dados_limpos['Type'] = "Ticket"
            df.at[index, 'Type'] = "Ticket"
        elif 'tickets' in valor_original:
            dados_limpos['Type'] = "Ticket"
            df.at[index, 'Type'] = "Ticket"
        elif 'Tickets' in valor_original:
            dados_limpos['Type'] = "Ticket"
            df.at[index, 'Type'] = "Ticket"
        elif 'person' in valor_original:
            dados_limpos['Type'] = "Person"
            df.at[index, 'Type'] = "Person"
        elif 'Persons' in valor_original:
            dados_limpos['Type'] = "Person"
            df.at[index, 'Type'] = "Person"
        elif 'pessoa' in valor_original:
            dados_limpos['Type'] = "Person"
            df.at[index, 'Type'] = "Person"
        elif 'pessoas' in valor_original:
            dados_limpos['Type'] = "Person"
            df.at[index, 'Type'] = "Person"

        try:
            # 1. Validação Pydantic (valida a linha atual isoladamente)
            # Certifique-se de que o esquema aqui seja o CustomFieldsSchema
            valido = CustomFieldsSchema.model_validate(dados_limpos)

            # 2. Criamos a linha para a planilha final
            # Como não há descrição longa, fazemos apenas um append direto
            nova_l = dados_limpos.copy()
            nova_l.update({
                "Validado": "Sim",
                "Coluna_com_Erro": "",
                "Mensagem_de_Erro": ""
            })

            # Adiciona na lista final - aqui cada linha original vira exatamente uma linha final
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

            linha_erro = dados_limpos.copy()
            linha_erro.update({
                "Validado": "Não",
                "Coluna_com_Erro": col_err,
                "Mensagem_de_Erro": msg_err
            })
            novas_linhas.append(linha_erro)
            print(f"❌ Ticket/Person: {dados_limpos.get('id')} | Erros: {msg_err}")

    # Salvar
    df_final = pd.DataFrame(novas_linhas)
    with pd.ExcelWriter(caminho_saida, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, index=False)


if __name__ == "__main__":
    # 1. Registra o momento de início
    inicio = time.time()

    print("Iniciando o processamento da planilha...")

    # Chamada da sua função
    processar_validar_planilha_custom_fields('files/custom-fields.xlsx', 'files/custom-fields-atualizada.xlsx')

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
