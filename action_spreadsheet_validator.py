import pandas as pd
import time
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from typing import Optional, List, Literal, Any
from datetime import datetime, timedelta


class ActionSchema(BaseModel):
    number: int = Field(..., alias="Ticket")
    created_at: str = Field(..., alias="Data.Hora")
    type: Literal["Público", "Interno"] = Field(None, alias="Ação.Público.Interno")
    created_by: Any = Field(None, alias="Gerador")
    description: str = Field(None, alias="Descrição")
    sequence: Optional[int] = Field(None, alias="Sequencia")
    ticket_id: Optional[Any] = Field(None, alias="TicketId")
    storage: Optional[Any] = Field(None, alias="StorageUID")

    @model_validator(mode='after')
    def validar_todas_as_regras(self) -> 'ActionSchema':
        # Mantém sua lógica de validação de campos em branco
        obrigatorios = {
            "number": "Ticket",
            "created_at": "Data.Hora",
            "type": "Ação.Público.Interno",
            "created_by": "Gerador",
            "description": "Descrição",
            "sequence": "Sequencia"
        }
        for campo, nome_coluna in obrigatorios.items():
            valor = getattr(self, campo)
            if valor is None or str(valor).strip() == "" or (isinstance(valor, float) and pd.isna(valor)):
                # Nota: Para o Pydantic v2 capturar isso como erro de validação,
                # o ideal é disparar um ValueError aqui se quiser mensagens customizadas no loop
                pass
        return self

    @field_validator('number', 'sequence', mode='before')
    @classmethod
    def validar_inteiro(cls, v, info):
        if v is None or str(v).strip().lower() in ["nan", "none", ""]:
            return None
        try:
            return int(float(str(v).strip()))
        except (ValueError, TypeError):
            nome_exibicao = "Ticket" if info.field_name == "number" else "Sequencia"
            raise ValueError(f"{nome_exibicao}: O valor informado deve ser um número inteiro válido.")

    @field_validator('created_at', mode='before')
    @classmethod
    def formatar_datas(cls, v):
        if v is None or str(v).strip().lower() in ["nan", "none", ""]:
            return None

        try:
            # Se já for um objeto de data, não precisamos converter, apenas formatar
            if isinstance(v, (datetime, pd.Timestamp)):
                data_dt = v
            else:
                # Tentamos converter explicitamente.
                # O Pandas agora saberá que se houver dúvida, o dia vem antes.
                data_dt = pd.to_datetime(v, dayfirst=True, errors='coerce')

            if pd.isna(data_dt):
                return str(v)

            # Seu ajuste de +3h mantido
            data_ajustada = data_dt + timedelta(hours=3)

            # Retorno padrão brasileiro
            return data_ajustada.strftime("%d/%m/%Y %H:%M:%S")
        except:
            return str(v)

    @field_validator('created_at', mode='before')
    @classmethod
    def validar_e_converter_data(cls, v):
        # 1. Identifica se está vazio (NaN, None, string vazia ou "nan")
        esta_vazio = (
                v is None or
                (isinstance(v, float) and pd.isna(v)) or
                str(v).strip().lower() in ["nan", "none", ""]
        )

        if esta_vazio:
            # Em vez de retornar None, disparar o erro que você deseja
            raise ValueError("Data.Hora: Formato de data inválido. Use o formato dd/mm/aaaa hh:mm:ss")

        # 2. Se já for um objeto datetime (vindo do Pandas/Excel)
        if isinstance(v, datetime):
            return v.strftime("%d/%m/%Y %H:%M:%S")

        # 3. Se for string, tenta converter e formatar
        if isinstance(v, str):
            try:
                # Tenta ler o formato esperado
                dt = datetime.strptime(v.strip(), "%d/%m/%Y %H:%M:%S")
                return dt.strftime("%d/%m/%Y %H:%M:%S")
            except ValueError:
                # Se a string existir mas estiver no formato errado
                raise ValueError("Data.Hora: Formato de data inválido. Use o formato dd/mm/aaaa hh:mm:ss")

        return str(v)

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

    @field_validator('created_by', mode='before')
    def validar_gerador(cls, v):
        # Verifica se o valor é uma string vazia após remover espaços
        if v is None or str(v).strip().lower() in ["nan", "none", ""]:
            raise ValueError('Gerador: Informe o código de referência de quem gerou a ação')
        return v

    @field_validator('description', mode='before')
    @classmethod
    def tratar_descricao_vazia(cls, v):
        # Se for nulo, NaN ou apenas espaços, preenche com a frase padrão
        if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "":
            return "Sem descrição informada na ação!"
        return str(v).strip()

    # Validador que prepara a descrição
    @field_validator('description', mode='before')
    def format_description(cls, v):
        return str(v) if v is not None else ""

    def quebrar_descricao(self) -> List[str]:
        """Lógica de divisão baseada no limite do Excel"""
        limite = 32767
        texto = self.description
        return [texto[i:i + limite] for i in range(0, len(texto), limite)]

    @field_validator('description', mode='before')
    @classmethod
    def clean_description(cls, v):
        if v is None:
            return ""
        # Converte para string e remove quebras de linha que "expulsam" o texto para a linha de baixo
        v_str = str(v).replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        return " ".join(v_str.split())  # Remove espaços duplos internos

    @classmethod
    def validar_e_unificar(cls, df: pd.DataFrame) -> pd.DataFrame:
        linhas_processadas = []
        linha_acumulada = None

        for _, row in df.iterrows():
            # Identifica se é uma linha nova (tem Ticket preenchido e é numérico)
            ticket_raw = row.get("Ticket")
            is_new_row = pd.notna(ticket_raw) and str(ticket_raw).strip().isdigit()

            if is_new_row:
                # Se já vínhamos acumulando uma linha, salvamos ela agora
                if linha_acumulada is not None:
                    linhas_processadas.append(linha_acumulada)
                linha_atual_dict = row.to_dict()
                # Garante que a descrição seja string para o acúmulo
                linha_atual_dict["Descrição"] = str(linha_atual_dict.get("Descrição", ""))
                linha_acumulada = linha_atual_dict
            else:
                # Se não tem Ticket, é um fragmento. Anexamos à descrição da linha anterior.
                if linha_acumulada is not None:
                    # Pegamos o texto da primeira coluna ou da coluna Descrição
                    fragmento = str(row.iloc[0]) if pd.isna(row.get("Descrição")) else str(row.get("Descrição"))
                    if fragmento.lower() != 'nan':
                        linha_acumulada["Descrição"] += " " + fragmento

        # Adiciona a última linha processada
        if linha_acumulada is not None:
            linhas_processadas.append(linha_acumulada)

        return pd.DataFrame(linhas_processadas)

    @field_validator('ticket_id', 'storage', mode='before')
    @classmethod
    def tornar_realmente_opcional(cls, v):
        # Se o Pandas mandar NaN, None ou string vazia, retornamos None
        # O Pydantic aceita None em campos Optional sem validar o tipo
        if pd.isna(v) or v is None or str(v).strip().lower() in ["nan", "none", ""]:
            return None
        return v


def processar_validar_planilha_actions(caminho_entrada, caminho_saida):
    # Leitura inicial
    df_entrada = pd.read_excel(caminho_entrada)
    df_entrada.columns = [c.strip() for c in df_entrada.columns]

    if 'Descrição' in df_entrada.columns:
        df_entrada['Descrição'] = df_entrada['Descrição'].astype(str).replace(['nan', 'NaN', 'None'], '')
    else:
        # Se a coluna nem existir, criamos ela já como objeto
        df_entrada['Descrição'] = ""
        df_entrada['Descrição'] = df_entrada['Descrição'].astype(object)

    # --- 1. RECONSTRUÇÃO: UNIR LINHAS QUEBRADAS PELO EXCEL ---
    linhas_unificadas = []
    linha_mestra = None

    for _, row in df_entrada.iterrows():
        ticket_raw = row.get("Ticket")
        if pd.notna(ticket_raw) and str(ticket_raw).strip().isdigit():
            if linha_mestra is not None:
                linhas_unificadas.append(linha_mestra)
            linha_mestra = row.to_dict()
        else:
            if linha_mestra is not None:
                fragmento = str(row.get("Descrição") if pd.notna(row.get("Descrição")) else row.iloc[0])
                if fragmento.lower() != 'nan':
                    linha_mestra["Descrição"] = f"{linha_mestra.get('Descrição', '')} {fragmento}"

    if linha_mestra:
        linhas_unificadas.append(linha_mestra)
    df = pd.DataFrame(linhas_unificadas)

    # --- 2. SEQUÊNCIA CONDICIONAL POR DATA (LÓGICA MANUAL) ---
    # Ordenamos primeiro para garantir a cronologia
    df['dt_temp'] = pd.to_datetime(df['Data.Hora'], format='mixed', dayfirst=True, errors='coerce')
    df = df.sort_values(by=['Ticket', 'dt_temp'], ascending=[True, True]).reset_index(drop=True)

    # Criamos um dicionário para contar as sequências de cada ticket
    contadores = {}
    sequencias_calculadas = []

    for _, row in df.iterrows():
        tkt = row['Ticket']
        seq_atual = str(row.get('Sequencia', '')).strip().lower()

        # Se a sequência original estiver vazia ou for nan
        if seq_atual in ["", "nan", "none"]:
            # Se é a primeira vez que vemos esse ticket, começa em 1
            if tkt not in contadores:
                contadores[tkt] = 1
            else:
                contadores[tkt] += 1
            sequencias_calculadas.append(contadores[tkt])
        else:
            # Se já tinha sequência na planilha, respeitamos o valor e atualizamos o contador
            try:
                val = int(float(seq_atual))
                sequencias_calculadas.append(val)
                contadores[tkt] = max(contadores.get(tkt, 0), val)
            except:
                sequencias_calculadas.append(None)  # Deixa o Pydantic dar erro de inteiro depois

    df['Sequencia'] = sequencias_calculadas
    df = df.drop(columns=['dt_temp'])

    # --- 3. LOOP DE VALIDAÇÃO E DUPLICAÇÃO ---
    novas_linhas = []
    limite_excel = 32000

    for index, row in df.iterrows():
        dados_limpos = row.to_dict()

        # (Insira aqui sua lógica de tratamento: data +3h, normalizar tipo, etc.)
        """Atualizar o tipo para Público ou Interno"""

        valor_original = str(dados_limpos.get('Ação.Público.Interno', '')).strip().lower()
        if 'publ' in valor_original:
            dados_limpos['Ação.Público.Interno'] = "Público"
            df.at[index, 'Ação.Público.Interno'] = "Público"
        elif 'públ' in valor_original:
            dados_limpos['Ação.Público.Interno'] = "Público"
            df.at[index, 'Ação.Público.Interno'] = "Público"
        elif 'intern' in valor_original:
            dados_limpos['Ação.Público.Interno'] = "Interno"
            df.at[index, 'Ação.Público.Interno'] = "Interno"
        elif 'privad' in valor_original:
            dados_limpos['Ação.Público.Interno'] = "Interno"
            df.at[index, 'Ação.Público.Interno'] = "Interno"

        """Correção da data para o formato dd/mm/aaaa hh:mm:ss"""

        colunas_data = {
            'Data.Hora': 'created_at',
        }

        for col_planilha, attr_pydantic in colunas_data.items():
            valor_original = row.get(col_planilha)
            if pd.notna(valor_original) and str(valor_original).strip() != "":
                try:
                    # Converte com segurança de formato
                    dt = pd.to_datetime(valor_original, yearfirst=True)
                    dt = dt + timedelta(hours=3)  # Se for de Movi x Movi, comentar!

                    # Salva no DataFrame a string formatada
                    formato_br = dt.strftime("%d/%m/%Y %H:%M:%S")
                    df.at[index, col_planilha] = formato_br

                    # Atualiza o dicionário que vai para o Pydantic
                    dados_limpos[col_planilha] = formato_br
                except:
                    continue

        """" Correção da descrição se for vazia """

        descricao_original = str(row.get('Descrição', '')).strip()

        if descricao_original in ["", "nan", "None"]:
            nova_descricao = "Sem descrição informada nesta ação do ticket!"
            df.at[index, 'Descrição'] = nova_descricao
            dados_limpos['Descrição'] = nova_descricao
        else:
            dados_limpos['Descrição'] = descricao_original

        """ Sequencia """
        dados_limpos['Sequencia'] = row['Sequencia']

        try:
            # Validação Pydantic
            valido = ActionSchema.model_validate(dados_limpos)
            texto = valido.description
            blocos = [texto[i:i + limite_excel] for i in range(0, len(texto), limite_excel)]

            for i, bloco in enumerate(blocos):
                nova_l = dados_limpos.copy()
                nova_l.update({
                    "Descrição": bloco,
                    "Validado": "Sim",
                    "Coluna_com_Erro": "",
                    "Mensagem_de_Erro": "" if i == 0 else f"Continuação Ticket {dados_limpos['Ticket']}"
                })
                novas_linhas.append(nova_l)

        except ValidationError as e:
            # --- SUA LÓGICA DE ERRO CORRIGIDA ---
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
            print(f"❌ Ticket: {dados_limpos.get('Ticket')} | Erros: {msg_err}")

    # Salvar
    df_final = pd.DataFrame(novas_linhas)
    with pd.ExcelWriter(caminho_saida, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, index=False)


if __name__ == "__main__":
    # 1. Registra o momento de início
    inicio = time.time()

    print("Iniciando o processamento da planilha...")

    # Chamada da sua função
    processar_validar_planilha_actions('files/actions.xlsx', 'files/actions-atualizada.xlsx')

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
