import pandas as pd
import time
import warnings
from pydantic import BaseModel, EmailStr, Field, ValidationError, field_validator, model_validator, BeforeValidator
from typing import Optional, List, Literal, Union, Any
from datetime import datetime, timedelta


class TicketSchema(BaseModel):
    number: int = Field(..., alias="Ticket")  # Número do ticket - Obrigatório
    type: Literal["Público", "Interno"] = Field(..., alias="Ticket Público/Interno")  # Público ou Interno - Obrigatório
    subject: str = Field(..., alias="Assunto")  # Assunto no máximo 350 caracteres - Obrigatório
    created_by: Any = Field(None, alias="Solicitante")  # ID do Solicitante - Obrigatório
    owner: Any = Field(None, alias="Responsável")  # ID do Responsável - Obrigatório
    owner_team: Optional[str] = Field(None,
                                      alias="Equipe do Responsável")  # Nome da Equipe do responsável - Obrigatório
    service: Optional[Any] = Field(None, alias="Serviço")  # ID do Serviço do ticket - Opcional
    category: Optional[str] = Field(None, alias="Categorias")  # Nome da Categoria do ticket - Opcional
    urgency: Optional[str] = Field(None, alias="Urgência")  # Nome da Urgência do ticket - Opcional
    status: str = Field(..., alias="Status")  # Nome da Status do ticket - Obrigatório
    justification: str | None = Field(None,
                                      alias="Justificativa")  # Nome da Justificativa do Status no ticket - Opcional, mas pode ser obrigatório
    created_at: str = Field(..., alias="Data/Hora abertura")
    closed_at: Optional[Any] = Field(None, alias="Data/hora de encerramento")
    tag: Union[int, str] = Field(..., alias="Tag")
    sequence: Optional[int] = Field(None, alias="Sequencia")

    @field_validator('subject', mode='before')
    @classmethod
    def tratar_assunto_vazio(cls, v):
        # Se for nulo, NaN ou apenas espaços, preenche com a frase padrão
        if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "":
            return "Sem assunto informado no ticket!"
        return str(v).strip()

    @field_validator('service', mode='before')
    @classmethod
    def limpar_servico(cls, v):
        # Se for NaN do Pandas, string vazia ou None, retorna None (válido)
        if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip().lower() in ["nan", "none", ""]:
            return None
        return v

    @field_validator('urgency', mode='before')
    @classmethod
    def corrigir_digitacao_urgencia(cls, v):
        if v is None or str(v).strip() == "":
            return v

        valor_original = str(v).strip()
        valor_comparar = valor_original.lower()

        correcoes = {
            "media": "Média",  # Sem acento
            "médio": "Média",  # Caso escrevam no masculino
            "medio": "Média",
            "alto": "Alta",
            "baixo": "Baixa",
            "normal": "Média"
        }

        # Retorna o valor corrigido ou o original se não estiver na lista
        return correcoes.get(valor_comparar, valor_original)

    @model_validator(mode='after')
    def validar_regras_unificadas_geral(self) -> 'TicketSchema':
        erros_acumulados = []

        # --- 1. Validação de Campos Obrigatórios (Solicitante, Responsável, Equipe) ---
        obrigatorios = {
            "created_by": "Solicitante",
            "owner": "Responsável",
            "owner_team": "Equipe do Responsável"
        }
        for campo, nome_coluna in obrigatorios.items():
            valor = getattr(self, campo)
            if valor is None or str(valor).strip() == "" or (isinstance(valor, float) and pd.isna(valor)):
                erros_acumulados.append(
                    f"{nome_coluna}: Este campo não pode ficar em branco. Por favor, informe um valor.")

        # --- 2. Validação da Justificativa (Regra de Status) ---
        st = str(self.status or "").strip().lower()
        jus = str(self.justification or "").strip()
        if st == "aguardando" and jus == "":
            erros_acumulados.append("Justificativa: Justificativa obrigatória para status 'Aguardando'")

        # --- 3. Validação de Status vs Encerramento ---
        cl_v = str(self.closed_at or "").strip()
        encerramento_vazio = cl_v == "" or cl_v.lower() in ["none", "nan"]

        if st != "fechado" and not encerramento_vazio:
            erros_acumulados.append(
                f"Data/hora de encerramento: A data de encerramento só pode ser preenchida se o status for 'Fechado'. "
                f"Status atual: {self.status}. A data foi removida!"
            )
            # Limpa o valor internamente no objeto
            self.closed_at = ""
        elif st == "fechado" and encerramento_vazio:
            erros_acumulados.append(
                "Data/hora de encerramento: O status é 'Fechado', portanto a data de encerramento é obrigatória.")

        # --- 4. Validação de Cronologia (Só se for Fechado e tiver as duas datas) ---
        if st == "fechado" and not encerramento_vazio and self.created_at:
            try:
                formato = "%d/%m/%Y %H:%M:%S"
                dt_criacao = datetime.strptime(str(self.created_at), formato)
                dt_fechamento = datetime.strptime(cl_v, formato)
                if dt_fechamento < dt_criacao:
                    erros_acumulados.append(
                        "Data/hora de encerramento: A data de encerramento não pode ser anterior à data de criação.")
            except:
                pass

        # --- DISPARO ÚNICO DE TODOS OS ERROS ---
        if erros_acumulados:
            # Usamos o separador " || " para o seu except separar corretamente
            raise ValueError(" || ".join(erros_acumulados))

        return self

    # Validador para capturar o erro de "não é inteiro" com mensagem amigável
    @field_validator('number', 'sequence', mode='before')
    @classmethod
    def validar_inteiro(cls, v, info):
        if v is None or str(v).strip().lower() in ["nan", "none", ""]:
            return None
        try:
            return int(float(str(v).strip()))
        except (ValueError, TypeError):
            # PADRONIZAÇÃO AQUI:
            # Verificamos qual campo falhou e atribuímos o nome da coluna correto
            nome_exibicao = "Ticket" if info.field_name == "number" else "Sequencia"
            raise ValueError(f"{nome_exibicao}: O valor informado deve ser um número inteiro válido.")

    @field_validator('subject', mode='after')
    @classmethod
    def validar_tamanho_assunto(cls, v):
        if len(v) > 350:
            raise ValueError(f"Assunto: O campo excede 350 caracteres (Total: {len(v)})")
        return v

    @field_validator('type', mode='before')
    @classmethod
    def normalizar_tipo(cls, v: str) -> str:
        # 'v' é o valor bruto da planilha (ex: "publico")
        # 'cls' é a própria classe TicketSchema
        if not v or not isinstance(v, str):
            return v

        # Converte para minúsculo e remove espaços para facilitar a busca
        valor_limpo = v.strip().lower()

        # Regra para Público (cobre: público, publico, public, etc)
        if "public" in valor_limpo or "públic" in valor_limpo:
            return "Público"

        elif "publica" in valor_limpo or "pública" in valor_limpo:
            return "Público"

        # Regra para Interno (cobre: interno, interna, intern)
        elif "intern" in valor_limpo:
            return "Interno"

        elif "interna" in valor_limpo:
            return "Interno"

        return v  # Se não bater com nada, retorna o original para o Pydantic gerar o erro de Literal

    @field_validator('justification', mode='before')
    @classmethod
    def limpar_justificativa(cls, v):  # Se for nulo, NaN do pandas ou vazio, retorna None de forma segura
        if pd.isna(v) or v == "" or v is None:
            return None
        return str(v)  # Se tiver qualquer coisa, garante que vira texto

    @model_validator(mode='after')
    def checar_justificativa_obrigatoria(self) -> 'TicketSchema':
        # Normalizamos para comparar
        st = str(self.status).strip().lower()
        js = str(self.justification).strip() if self.justification else ""
        if st == "aguardando" and (not self.justification or str(self.justification).strip() == ""):
            raise ValueError("Justificativa obrigatória para status 'Aguardando'")
        return self

    @field_validator('created_at', 'closed_at', mode='before')
    @classmethod
    def formatar_datas(cls, v):
        if v is None or str(v).strip().lower() in ["nan", "none", ""]:
            return None
        try:
            v_str = str(v).strip()
            # Mesma lógica do loop
            if len(v_str) >= 4 and v_str[:4].isdigit() and "-" in v_str[:8]:
                data_dt = pd.to_datetime(v_str)
            else:
                data_dt = pd.to_datetime(v_str, dayfirst=True, errors='coerce')

            if pd.isna(data_dt):
                return v_str
            return data_dt.strftime("%d/%m/%Y %H:%M:%S")
        except:
            return str(v)

    @model_validator(mode='after')
    def verificar_cronologia_das_datas(self) -> 'TicketSchema':
        # 1. Garantimos que os campos não são nulos antes de converter
        if self.closed_at and self.created_at:
            try:
                # O formato deve ser EXATAMENTE o que você definiu na conversão anterior
                formato = "%d/%m/%Y %H:%M:%S"

                # 2. Convertemos as strings de volta para objetos datetime para comparação matemática
                # str() garante que tratamos o valor como texto
                dt_criacao = datetime.strptime(str(self.created_at), formato)
                dt_fechamento = datetime.strptime(str(self.closed_at), formato)

                # 3. Agora a comparação é cronológica (temporal) e não alfabética
                if dt_fechamento < dt_criacao:
                    raise ValueError(
                        "Data/hora de encerramento: A data de encerramento não pode ser anterior à data de criação.")

            except (ValueError, TypeError):
                # Se a data estiver em um formato inesperado ou vazia,
                # não disparamos erro de cronologia para não travar outras validações
                pass

        return self

    @model_validator(mode='after')
    def validar_status_vs_encerramento(self) -> 'TicketSchema':
        # Captura o status e o valor da data
        status_v = str(self.status or "").strip()
        cl_v = str(self.closed_at or "").strip()

        # Verifica se o campo está vazio (considerando nulos do Pandas)
        encerramento_vazio = cl_v == "" or cl_v.lower() in ["none", "nan"]

        erros = []

        # Regra: Se NÃO for "Fechado" e houver data informada
        if status_v != "Fechado" and not encerramento_vazio:
            # MENSAGEM PERSONALIZADA CONFORME SOLICITADO
            erros.append(
                f"Data/hora de encerramento: A data de encerramento só pode ser preenchida se o status for 'Fechado'. "
                f"Status atual: {status_v}. A data foi removida!"
            )
            # Limpa o valor internamente no objeto Pydantic
            self.closed_at = ""

        # Regra: Se FOR "Fechado" e a data estiver vazia
        elif status_v == "Fechado" and encerramento_vazio:
            erros.append(
                "Data/hora de encerramento: O status é 'Fechado', portanto a data de encerramento é obrigatória.")

        # Regra: Cronologia (apenas se for Fechado e a data existir)
        if status_v == "Fechado" and not encerramento_vazio and self.created_at:
            try:
                formato = "%d/%m/%Y %H:%M:%S"
                dt_criacao = datetime.strptime(str(self.created_at), formato)
                dt_fechamento = datetime.strptime(cl_v, formato)

                if dt_fechamento < dt_criacao:
                    erros.append(
                        "Data/hora de encerramento: A data de encerramento não pode ser anterior à data de criação.")
            except:
                pass

        if erros:
            raise ValueError(" || ".join(erros))
        return self

    @field_validator('tag', mode='before')
    @classmethod
    def ajustar_tags_migrado(cls, v):
        # Se estiver vazio (None, NaN ou string vazia)
        if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "":
            return "Migrado"

        # Se já tiver conteúdo, mantém o original e adiciona ", Migrado"
        conteudo_original = str(v).strip()

        # Evita duplicar se a palavra "Migrado" já estiver lá
        if "Migrado" in conteudo_original:
            return conteudo_original

        return f"{conteudo_original}, Migrado"


"""Função para processar a planilha"""


def processar_validar_planilha_tickets(caminho_entrada, caminho_saida):
    df = pd.read_excel(caminho_entrada)

    # Limpeza básica de nomes de colunas e valores nulos
    df.columns = [c.strip() for c in df.columns]
    df = df.where(pd.notnull(df), None)

    # Criamos a coluna de status e a de detalhamento
    df['Validado'] = 'Sim'
    df['Coluna_com_Erro'] = ''
    df['Mensagem_de_Erro'] = ''

    # Converta as colunas para o tipo 'object' (texto) antes do loop
    # Isso evita o erro de 'incompatible dtype'
    df['Ticket'] = df['Ticket'].astype(object)
    df['Sequencia'] = df['Sequencia'].astype(object)

    # Se houver outras colunas que você atualiza manualmente, faça o mesmo:
    df['Tag'] = df['Tag'].astype(object)

    for index, row in df.iterrows():
        # 1. Preparamos os dados da linha
        dados_linha = row.to_dict()
        dados_limpos = {k: (None if pd.isna(v) else v) for k, v in dados_linha.items()}

        number_ticket = dados_limpos.get('Ticket')

        dados_limpos['Solicitante'] = row.get('Solicitante')
        dados_limpos['Responsável'] = row.get('Responsável')
        dados_limpos['Equipe do Responsável'] = row.get('Equipe do Responsável')
        dados_limpos['Serviço'] = row.get('Serviço')
        dados_limpos['Status'] = row.get('Status')
        dados_limpos['Justificativa'] = row.get('Justificativa')

        """Atualizar o tipo para Público ou Interno"""

        valor_original = str(dados_limpos.get('Ticket Público/Interno', '')).strip().lower()
        if 'publ' in valor_original:
            dados_limpos['Ticket Público/Interno'] = "Público"
            df.at[index, 'Ticket Público/Interno'] = "Público"
        elif 'públ' in valor_original:
            dados_limpos['Ticket Público/Interno'] = "Público"
            df.at[index, 'Ticket Público/Interno'] = "Público"
        elif 'intern' in valor_original:
            dados_limpos['Ticket Público/Interno'] = "Interno"
            df.at[index, 'Ticket Público/Interno'] = "Interno"
        elif 'privad' in valor_original:
            dados_limpos['Ticket Público/Interno'] = "Interno"
            df.at[index, 'Ticket Público/Interno'] = "Interno"

        """Inclusão da Tag "Migrado, caso não esteja preenchida"""

        tag_original = str(dados_limpos.get('Tag', '')).strip()
        if tag_original is None or pd.isna(tag_original) or str(tag_original).strip() == "" or str(
                tag_original).lower() == "none":
            nova_tag = "Migrado"
        elif "Migrado" not in tag_original:
            nova_tag = f"{tag_original}, Migrado"
        else:
            nova_tag = tag_original

        # Atualiza tanto o dicionário quanto a planilha
        dados_limpos['Tag'] = nova_tag
        df.at[index, 'Tag'] = nova_tag

        """Atualizar a sequencia com o valor do número do ticket"""

        val_ticket = dados_limpos.get('Ticket')
        val_sequencia = dados_limpos.get('Sequencia')

        if pd.isna(val_sequencia) or str(val_sequencia).strip() == "":
            # Agora o pandas aceitará o valor, seja ele '123' ou '123A',
            # pois transformamos a coluna em object acima.
            dados_limpos['Sequencia'] = val_ticket
            df.at[index, 'Sequencia'] = val_ticket

        """Correção da data para o formato dd/mm/aaaa hh:mm:ss"""

        # colunas_data = {
        #     'Data/Hora abertura': 'created_at',
        #     'Data/hora de encerramento': 'closed_at'
        # }
        #
        # for col_planilha, attr_pydantic in colunas_data.items():
        #     valor_original = row.get(col_planilha)
        #     if pd.notna(valor_original) and str(valor_original).strip() != "":
        #         try:
        #             # Converte com segurança de formato
        #             dt = pd.to_datetime(valor_original, yearfirst=True)
        #             dt = dt + timedelta(hours=3)  # Se for de Movi x Movi, comentar!
        #
        #             # Salva no DataFrame a string formatada
        #             formato_br = dt.strftime("%d/%m/%Y %H:%M:%S")
        #             df.at[index, col_planilha] = formato_br
        #
        #             # Atualiza o dicionário que vai para o Pydantic
        #             dados_limpos[col_planilha] = formato_br
        #         except:
        #             continue

        colunas_data = {'Data/Hora abertura': 'created_at', 'Data/hora de encerramento': 'closed_at'}
        for col_planilha, attr_pydantic in colunas_data.items():
            valor_original = row.get(col_planilha)
            if pd.notna(valor_original) and str(valor_original).strip() != "":
                try:
                    v_str = str(valor_original).strip()

                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", UserWarning)

                        # REGRA DE OURO: Se começa com 4 dígitos (Ano), o mês é o segundo bloco.
                        # Ex: 2019-03-12 -> 03 é mês, 12 é dia.
                        if len(v_str) >= 4 and v_str[:4].isdigit() and "-" in v_str[:8]:
                            dt = pd.to_datetime(v_str)  # ISO standard
                        else:
                            # Para formatos BR (12/03/2019), garantimos o dia primeiro.
                            dt = pd.to_datetime(v_str, dayfirst=True)

                    dt = dt + timedelta(hours=3) #comente está linha se for planilhas retiradas do banco Movidesk
                    formato_br = dt.strftime("%d/%m/%Y %H:%M:%S")

                    df.at[index, col_planilha] = formato_br
                    dados_limpos[col_planilha] = formato_br
                except:
                    continue


            """ CORREÇÃO DA URGÊNCIA ANTES DA VALIDAÇÃO """

            valor_urgencia = str(dados_limpos.get('Urgência', '')).strip()

            correcoes_urgencia = {
                "media": "Média",
                "médio": "Média",
                "medio": "Média",
                "alto": "Alta",
                "baixo": "Baixa",
                "normal": "Média"
            }

            # Verifica se o valor digitado (em minúsculo) precisa de correção
            sugestao = correcoes_urgencia.get(valor_urgencia.lower())
            if sugestao:
                # Atualiza o dicionário que vai para o Pydantic
                dados_limpos['Urgência'] = sugestao
                # Atualiza a planilha na hora, independente de erros futuros
                df.at[index, 'Urgência'] = sugestao

            """" CORREÇÃO DE ASSUNTO (ANTES DO TRY) """

            # Verificamos se está vazio, "nan" ou nulo
            assunto_original = str(row.get('Assunto', '')).strip()
            if assunto_original == "" or assunto_original.lower() == "nan" or pd.isna(row.get('Assunto')):
                novo_assunto = "Sem assunto informado no ticket!"

                # ATUALIZAÇÃO FORÇADA NO DATAFRAME:
                df.at[index, 'Assunto'] = novo_assunto

                # Atualiza a variável que vai para o dicionário do Pydantic
                dados_limpos['Assunto'] = novo_assunto
            else:
                dados_limpos['Assunto'] = assunto_original

        try:
            ticket = TicketSchema.model_validate(dados_limpos)

            # --- REGRA DE LIMPEZA VISUAL NA PLANILHA ---
            # Se o status não for Fechado, garantimos que a célula fique vazia no Excel
            if str(ticket.status).strip() != "Fechado":
                df.at[index, 'Data/hora de encerramento'] = ""
            else:
                # Se for Fechado, garantimos que grave a data formatada/ajustada
                df.at[index, 'Data/hora de encerramento'] = ticket.closed_at

            df.at[index, 'Validado'] = 'Sim'
            # df.at[index, 'Erros Encontrados'] = ''

        except ValidationError as e:
            df.at[index, 'Validado'] = 'Não'

            # Mesmo dando erro, se o status não for Fechado, limpamos a célula na planilha
            status_atual = str(dados_limpos.get('Status', '')).strip()
            if status_atual != "Fechado":
                df.at[index, 'Data/hora de encerramento'] = ""

            lista_erros_pydantic = e.errors()
            mensagens_finais = []
            colunas_finais = []

            for erro in lista_erros_pydantic:
                msg = erro['msg'].replace("Value error, ", "").replace("Assertion failed, ", "")
                # Se a mensagem vier do nosso acumulador com " || "
                if " || " in msg:
                    sub_mensagens = msg.split(" || ")
                    for sub in sub_mensagens:
                        sub_limpa = sub.strip()
                        mensagens_finais.append(sub_limpa)
                        if ":" in sub_limpa:
                            colunas_finais.append(sub_limpa.split(":")[0].strip())
                else:
                    # Erros individuais (ex: Assunto longo)
                    if ":" in msg:
                        colunas_finais.append(msg.split(":")[0].strip())
                    else:
                        coluna = str(erro['loc'][-1]) if erro['loc'] else "Geral"
                        colunas_finais.append(coluna)
                    mensagens_finais.append(msg)

            # Deduplicação mantendo a ordem
            colunas_formatadas = ", ".join(list(dict.fromkeys(colunas_finais)))
            mensagens_formatadas = " | ".join(list(dict.fromkeys(mensagens_finais)))

            # Salva na planilha respeitando a ordem de detecção
            df.at[index, 'Coluna_com_Erro'] = colunas_formatadas
            df.at[index, 'Mensagem_de_Erro'] = mensagens_formatadas

            # Print de log atualizado
            print(
                f"❌ Ticket: {number_ticket} | Linha: {index} | Colunas: {colunas_formatadas} | Erros: {mensagens_formatadas}")

    # # Salva o resultado
    # df.to_excel(caminho_saida, index=False)
    # print(f"Relatório gerado com sucesso em: {caminho_saida}")

    with pd.ExcelWriter(caminho_saida,
                        engine='xlsxwriter',
                        datetime_format='dd/mm/yyyy hh:mm:ss') as writer:
        df.to_excel(writer, index=False)


if __name__ == "__main__":
    # 1. Registra o momento de início
    inicio = time.time()

    print("Iniciando o processamento da planilha...")

    # Chamada da sua função
    processar_validar_planilha_tickets('files/tickets.xlsx', 'files/tickets-atualizada.xlsx')

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
