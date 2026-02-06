import pandas as pd
import numpy as np
import re
import time
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator, EmailStr
from typing import Optional, Any



class PersonSchema(BaseModel):
    # Mapeamento exato com os nomes das colunas da planilha
    type: Any = Field(..., alias="Tipo")
    profile: Any = Field(..., alias="Perfil")
    business_name: Optional[Any] = Field(None, alias="Nome fantasia")
    corporate_name: Optional[Any] = Field(None, alias="Razão social")
    user_name: Optional[Any] = Field(None, alias="Usuário")
    password: Optional[Any] = Field(None, alias="Senha")
    cpf_cnpj: Optional[Any] = Field(None, alias="CPF / CNPJ")
    code_reference: Any = Field(..., alias="Cod. Ref.")
    code_reference_add: Optional[Any] = Field(None, alias="Cod. Ref. Adicional")
    access_profile: Any = Field(..., alias="Perfil de acesso")
    email_type: Optional[str] = Field(None, alias="Tipo do e-mail")
    email: Optional[EmailStr] = Field(None, alias="E-mail")
    contact_type: Optional[str] = Field(None, alias="Tipo do contato")
    contact: Optional[Any] = Field(None, alias="Contato")
    address_type: Optional[str] = Field(None, alias="Tipo do endereço")
    team: Optional[Any] = Field(None, alias="Equipe")
    organization: Optional[Any] = Field(None, alias="Organização")
    ativo: str = Field("Sim", alias="Ativo")
    time_zone: str = Field("America/Sao_Paulo", alias="Fuso horário")
    language: str = Field("pt-BR", alias="Idioma")  # Obrigatório - Sempre "pt-BR"

    # NOVOS CAMPOS DE ENDEREÇO
    pais: Optional[Any] = Field(None, alias="País")
    cep: Optional[Any] = Field(None, alias="CEP")
    estado: Optional[Any] = Field(None, alias="Estado")
    city: Optional[Any] = Field(None, alias="Cidade")
    neighborhood: Optional[Any] = Field(None, alias="Bairro")
    street: Optional[Any] = Field(None, alias="Rua")
    number: Optional[Any] = Field(None, alias="Número")
    complement: Optional[Any] = Field(None, alias="Complemento")
    reference: Optional[Any] = Field(None, alias="Referência")

    # --- VALIDATORES DE TAMANHO E FORMATAÇÃO ---

    @field_validator('pais', 'estado', 'city', 'neighborhood', 'street', 'complement', 'reference', mode='before')
    @classmethod
    def validar_tamanho_128(cls, v, info):
        if v is None or str(v).strip() == "": return None
        txt = str(v).strip()
        if len(txt) > 128:
            raise ValueError(f"{info.field_name.capitalize()}: Máximo de 128 caracteres permitidos.")
        return normalizar_estado(txt) if info.field_name == 'estado' else txt

    @field_validator('cep', mode='before')
    @classmethod
    def validar_e_formatar_cep(cls, v):
        if v is None or str(v).strip() == "": return None
        txt = str(v).strip()
        if len(txt) > 31:
            raise ValueError("CEP: O campo excede 31 caracteres.")
        return formatar_cep(txt)

    @field_validator('number', mode='before')
    @classmethod
    def validar_numero(cls, v):
        if v is None or str(v).strip() == "": return None
        txt = str(v).strip()
        if len(txt) > 32:
            raise ValueError("Número: O campo excede 32 caracteres.")
        return txt


    @field_validator('type', mode='before')
    @classmethod
    def transform_type(cls, v):
        if pd.isna(v) or str(v).strip() == "": return v
        s = str(v).lower()
        if 'pessoa' in s: return 1
        if 'empresa' in s: return 2
        if 'departamento' in s: return 4
        try:
            return int(float(v))
        except:
            return v

    @field_validator('profile', mode='before')
    @classmethod
    def transform_profile(cls, v):
        if pd.isna(v) or str(v).strip() == "": return v
        s = str(v).lower()
        if 'agente, cliente' in s or ',' in s: return 3
        if 'agente' in s: return 1
        if 'cliente' in s: return 2
        try:
            return int(float(v))
        except:
            return v

    @field_validator('cpf_cnpj', mode='before')
    @classmethod
    def validar_e_limpar_cpf_cnpj(cls, v):
        # Se estiver vazio, apenas retorna (visto que é opcional no seu Schema)
        if v is None or str(v).strip().lower() in ["", "none", "nan"]:
            return None

        # 1. Remove qualquer caractere que não seja número (pontos, traços, barras, espaços)
        apenas_numeros = "".join(filter(str.isdigit, str(v)))

        # 2. Verifica a quantidade de dígitos
        qtd = len(apenas_numeros)

        if qtd == 11:
            # É um CPF válido em tamanho
            return apenas_numeros
        elif qtd == 14:
            # É um CNPJ válido em tamanho
            return apenas_numeros
        else:
            # Se não tiver 11 nem 14, levanta erro com mensagem amigável
            raise ValueError(
                f"CPF / CNPJ: Valor inválido. O campo deve conter 11 dígitos (CPF) ou 14 dígitos (CNPJ). "
                f"Foram encontrados {qtd} números."
            )

    @field_validator('email_type', 'contact_type', 'address_type', mode='before')
    @classmethod
    def set_defaults(cls, v, info):
        if v is None or str(v).strip().lower() in ["", "none", "nan"]:
            defaults = {
                "email_type": "Profissional",
                "contact_type": "Telefone celular",
                "address_type": "Comercial"
            }
            return defaults.get(info.field_name)
        return str(v).strip()

    @model_validator(mode='after')
    def validar_regras_negocio(self) -> 'PersonSchema':
        erros = []
        is_empresa = str(self.type) == "2"
        fantasia_vazio = not self.business_name or str(self.business_name).strip() == ""
        razao_vazia = not self.corporate_name or str(self.corporate_name).strip() == ""

        if is_empresa and fantasia_vazio and razao_vazia:
            erros.append("Razão social: Obrigatória para Empresas quando o Nome Fantasia não é informado.")
        if not is_empresa and fantasia_vazio:
            erros.append("Nome fantasia: Este campo é obrigatório.")

        if erros: raise ValueError(" || ".join(erros))
        return self

    @field_validator('code_reference', 'code_reference_add', mode='before')
    @classmethod
    def validar_tamanho_e_limpar(cls, v, info):
        val = clean_numeric_string(v)
        if val and len(val) > 64:
            label = "Cod. Ref." if info.field_name == "code_reference" else "Cod. Ref. Adicional"
            raise ValueError(f"{label}: O campo excede 64 caracteres.")
        return val

    @model_validator(mode='after')
    def executar_todas_as_validacoes(self) -> 'PersonSchema':
        erros = []

        # 1. Campos Obrigatórios
        obrigatorios = {
            "type": "Tipo",
            "profile": "Perfil",
            "business_name": "Nome fantasia",
            "code_reference": "Cod. Ref.",
            "access_profile": "Perfil de acesso",
            "ativo": "Ativo",
            "time_zone": "Fuso horário",
            "language": "Idioma"
        }
        for campo, nome_coluna in obrigatorios.items():
            valor = getattr(self, campo)
            if valor is None or str(valor).strip() in ["", "None", "nan"]:
                erros.append(f"{nome_coluna}: Este campo é obrigatório.")

        # 2. Regra de Equipe (Agentes)
        if self.profile in [1, 3]:
            equipe = str(self.team).strip().lower() if self.team else ""
            if equipe in ["", "none", "nan"]:
                erros.append("Equipe: Obrigatória para perfis que incluem 'Agente'.")

        # 3. Regra de E-mail (se preenchido, deve ser válido)
        if self.email and "@" not in str(self.email):
            erros.append("E-mail: O formato do e-mail informado é inválido.")

        # Se houver qualquer erro na lista, levantamos a exceção para o 'try' capturar
        if erros:
            raise ValueError(" || ".join(erros))

        return self

    @field_validator('type', 'profile', mode='after')
    @classmethod
    def validar_inteiro(cls, v, info):
        if v is None or str(v).strip().lower() in ["nan", "none", ""]:
            return None
        try:
            return int(float(str(v).strip()))
        except (ValueError, TypeError):
            # Verificamos qual campo falhou e atribuímos o nome da coluna correto
            nome_exibicao = "Tipo" if info.field_name == "type" else "Profile"
            raise ValueError(f"{nome_exibicao}: O valor informado deve ser um número inteiro válido.")

    @field_validator('code_reference', mode='before')
    @classmethod
    def validar_obrigatoriedade_ref(cls, v):
        # Transforma qualquer tipo de "vazio" em None para o Pydantic entender que falta dado
        if v is None or str(v).strip().lower() in ["", "nan", "none"]:
            raise ValueError("Cod. Ref.: Este campo é obrigatório e não pode ficar em branco.")
        return str(v).strip()

    @field_validator('contact', mode='before')
    @classmethod
    def validar_e_formatar_telefone(cls, v):
        if v is None or str(v).strip() == "": return None
        formatado = formatar_telefone(v)
        # Se após formatar não tiver o padrão esperado, avisa o erro
        if not re.match(r'^\(\d{2}\) \d{4,5}-\d{4}$', formatado):
            raise ValueError(f"Contato: O telefone '{v}' é inválido. Use o padrão (11) 99999-9999.")
        return formatado


# --- FUNÇÃO AUXILIAR DE LIMPEZA DE IDs E TELEFONE ---
def clean_numeric_string(v):
    """Garante que o valor seja string e remove o .0 indesejado"""
    if v is None or str(v).strip().lower() in ["", "nan", "none"]:
        return None
    s = str(v).strip()
    # Remove o .0 se existir no final da string
    if s.endswith('.0'):
        s = s[:-2]
    return s


def formatar_telefone(v):
    if v is None or str(v).strip().lower() in ["", "nan", "none"]:
        return None

    # Remove tudo que não é número
    nums = "".join(filter(str.isdigit, str(v)))

    # Valida tamanho (Brasil: 10 dígitos para fixo ou 11 para celular com DDD)
    if len(nums) == 10:
        return f"({nums[:2]}) {nums[2:6]}-{nums[6:]}"
    elif len(nums) == 11:
        return f"({nums[:2]}) {nums[2:7]}-{nums[7:]}"
    else:
        # Se não tiver 10 ou 11 dígitos, retorna o original para o validador acusar erro se necessário
        return nums


def formatar_cep(v):
    v = clean_numeric_string(v)  # Primeiro remove o .0 (ex: 67113480.0 -> 67113480)
    if not v: return None

    # Agora extraímos apenas os números da string já limpa
    nums = "".join(filter(str.isdigit, v))

    if len(nums) == 8:
        return f"{nums[:5]}-{nums[5:]}"
    return v  # Retorna o valor limpo (sem .0) mesmo que não tenha 8 dígitos


def normalizar_estado(v):
    if v is None or str(v).strip() == "":
        return None
    estados_map = {
        'acre': 'AC', 'alagoas': 'AL', 'amapa': 'AP', 'amazonas': 'AM', 'bahia': 'BA',
        'ceara': 'CE', 'distrito federal': 'DF', 'espirito santo': 'ES', 'goias': 'GO',
        'maranhao': 'MA', 'mato grosso': 'MT', 'mato grosso do sul': 'MS', 'minas gerais': 'MG',
        'para': 'PA', 'paraiba': 'PB', 'parana': 'PR', 'pernambuco': 'PE', 'piaui': 'PI',
        'rio de janeiro': 'RJ', 'rio grande do norte': 'RN', 'rio grande do sul': 'RS',
        'rondonia': 'RO', 'roraima': 'RR', 'santa catarina': 'SC', 'sao paulo': 'SP',
        'sergipe': 'SE', 'tocantins': 'TO'
    }
    # Limpa acentos básicos e coloca em minúsculo para comparar
    nome_limpo = str(v).strip().lower().replace('á', 'a').replace('ã', 'a').replace('â', 'a').replace('é', 'e').replace(
        'ê', 'e').replace('í', 'i').replace('ó', 'o').replace('õ', 'o').replace('ô', 'o').replace('ú', 'u').replace('ç',
                                                                                                                    'c')

    if len(nome_limpo) == 2:
        return nome_limpo.upper()
    return estados_map.get(nome_limpo, str(v).upper())

"""Função para processar a planilha"""


def processar_validar_planilha_persons(caminho_entrada, caminho_saida):
    df = pd.read_excel(caminho_entrada)
    # Limpeza básica de nomes de colunas e valores nulos
    df.columns = [c.strip() for c in df.columns]
    df = df.where(pd.notnull(df), None)

    # 1. MAPEAMENTO PROCV (Nome Fantasia -> Cod. Ref.)
    mapa_organizacao = {}
    for _, row_map in df.iterrows():
        nome = str(row_map.get('Nome fantasia', '')).strip()
        cod = clean_numeric_string(row_map.get('Cod. Ref.'))
        if nome and cod and nome.lower() not in ["none", "nan", ""]:
            mapa_organizacao[nome] = cod

    # 2. CÁLCULO DE UNICIDADE GLOBAL
    c1 = df['Cod. Ref.'].apply(clean_numeric_string).dropna()
    c2 = df['Cod. Ref. Adicional'].apply(clean_numeric_string).dropna()
    duplicados_globais = pd.concat([c1, c2])[pd.concat([c1, c2]).duplicated()].unique().tolist()

    df['Validado'] = 'Sim'
    df['Coluna_com_Erro'] = ''
    df['Mensagem_de_Erro'] = ''

    for index, row in df.iterrows():
        # 1. Preparamos os dados da linha
        dados_linha = row.to_dict()
        dados_limpos = {k: (None if pd.isna(v) else v) for k, v in dados_linha.items()}
        current_code = clean_numeric_string(dados_limpos.get('Cod. Ref.'))
        current_name = str(dados_limpos.get('Nome fantasia', '')).strip()

        code_reference = dados_limpos.get('Cod. Ref.')

        # Identificador para o log
        id_log = clean_numeric_string(dados_limpos.get('Cod. Ref.')) or f"LINHA {index + 1}"

        # """Atualizar o 'Tipo': Pessoa=1 ; Empresa=2 ou Departamento=4"""
        #
        # valor_original = str(dados_limpos.get('Tipo', '')).strip().lower()
        # if 'pessoa' in valor_original:
        #     dados_limpos['Tipo'] = 1
        #     df.at[index, 'Tipo'] = 1
        # elif 'pessoas' in valor_original:
        #     dados_limpos['Tipo'] = 1
        #     df.at[index, 'Tipo'] = 1
        # elif 'empresa' in valor_original:
        #     dados_limpos['Tipo'] = 2
        #     df.at[index, 'Tipo'] = 2
        # elif 'empresas' in valor_original:
        #     dados_limpos['Tipo'] = 2
        #     df.at[index, 'Tipo'] = 2
        # elif 'departamento' in valor_original:
        #     dados_limpos['Tipo'] = 4
        #     df.at[index, 'Tipo'] = 4
        # elif 'departamentos' in valor_original:
        #     dados_limpos['Tipo'] = 4
        #     df.at[index, 'Tipo'] = 4
        #
        # """Atualizar o 'Perfil': Agente=1 ; Cliente=2 ou Agente, Cliente=3"""
        #
        # valor_original = str(dados_limpos.get('Perfil', '')).strip().lower()
        # if 'agente' in valor_original:
        #     dados_limpos['Perfil'] = 1
        #     df.at[index, 'Perfil'] = 1
        # elif 'agentes' in valor_original:
        #     dados_limpos['Perfil'] = 1
        #     df.at[index, 'Perfil'] = 1
        # elif 'cliente' in valor_original:
        #     dados_limpos['Perfil'] = 2
        #     df.at[index, 'Perfil'] = 2
        # elif 'clientes' in valor_original:
        #     dados_limpos['Perfil'] = 2
        #     df.at[index, 'Perfil'] = 2
        # elif 'agente, cliente' in valor_original:
        #     dados_limpos['Perfil'] = 3
        #     df.at[index, 'Perfil'] = 3
        #
        # """Inclusão do 'Tipo do e-mail' padrão = Profissional, caso não esteja preenchido"""
        #
        # email_type = str(dados_limpos.get('Tipo do e-mail', '')).strip()
        # if email_type is None or pd.isna(email_type) or str(email_type).strip() == "" or str(
        #         email_type).lower() == "none":
        #     new_email_type = "Profissional"
        # else:
        #     new_email_type = email_type
        #
        # # Atualiza tanto o dicionário quanto a planilha
        # dados_limpos['Tipo do e-mail'] = new_email_type
        # df.at[index, 'Tipo do e-mail'] = new_email_type
        #
        # """Inclusão do 'Tipo do contato' padrão = Telefone celular, caso não esteja preenchido"""
        #
        # contact_type = str(dados_limpos.get('Tipo do contato', '')).strip()
        # if contact_type is None or pd.isna(contact_type) or str(contact_type).strip() == "" or str(
        #         contact_type).lower() == "none":
        #     new_contact_type = "Telefone celular"
        # else:
        #     new_contact_type = contact_type
        #
        # # Atualiza tanto o dicionário quanto a planilha
        # dados_limpos['Tipo do contato'] = new_contact_type
        # df.at[index, 'Tipo do contato'] = new_contact_type
        #
        # """Inclusão do 'Tipo do endereço' padrão = Comercial, caso não esteja preenchido"""
        #
        # address_type = str(dados_limpos.get('Tipo do endereço', '')).strip()
        # if address_type is None or pd.isna(address_type) or str(address_type).strip() == "" or str(
        #         address_type).lower() == "none":
        #     new_address_type = "Comercial"
        # else:
        #     new_address_type = address_type
        #
        # # Atualiza tanto o dicionário quanto a planilha
        # dados_limpos['Tipo do endereço'] = new_address_type
        # df.at[index, 'Tipo do endereço'] = new_address_type

        # Correção do TIPO
        # 1. SANEAMENTO
        val_tipo = str(dados_limpos.get('Tipo', '')).strip().lower()
        novo_tipo = dados_limpos.get('Tipo')
        if 'pessoa' in val_tipo:
            novo_tipo = 1
        elif 'empresa' in val_tipo:
            novo_tipo = 2
        elif 'departamento' in val_tipo:
            novo_tipo = 4

        dados_limpos['Tipo'] = novo_tipo
        df.at[index, 'Tipo'] = novo_tipo

        # Correção do PERFIL
        val_perfil = str(dados_limpos.get('Perfil', '')).strip().lower()
        novo_perfil = dados_limpos.get('Perfil')
        if 'agente, cliente' in val_perfil or ',' in val_perfil:
            novo_perfil = 3
        elif 'agente' in val_perfil:
            novo_perfil = 1
        elif 'cliente' in val_perfil:
            novo_perfil = 2

        dados_limpos['Perfil'] = novo_perfil
        df.at[index, 'Perfil'] = novo_perfil

        # Preenchimento de PADRÕES (E-mail, Contato, Endereço)
        map_padroes = {
            'Tipo do e-mail': 'Profissional',
            'Tipo do contato': 'Telefone celular',
            'Tipo do endereço': 'Comercial'
        }
        for col, padrao in map_padroes.items():
            val = str(dados_limpos.get(col, '')).strip().lower()
            if val in ["", "none", "nan"]:
                dados_limpos[col] = padrao
                df.at[index, col] = padrao

        # Limpeza de CPF/CNPJ (Somente números)
        if dados_limpos.get('CPF / CNPJ'):
            numeros = "".join(filter(str.isdigit, str(dados_limpos['CPF / CNPJ'])))
            dados_limpos['CPF / CNPJ'] = numeros
            df.at[index, 'CPF / CNPJ'] = numeros

        # Razão Social -> Nome Fantasia
        if str(dados_limpos.get('Tipo')) == "2":  # Se for Empresa
            fantasia = dados_limpos.get('Nome fantasia')
            razao = dados_limpos.get('Razão social')
            if (not fantasia or str(fantasia).strip() == "") and (razao and str(razao).strip() != ""):
                dados_limpos['Nome fantasia'] = razao
                df.at[index, 'Nome fantasia'] = razao

        # 2. VALIDAÇÃO DE UNICIDADE (Manual antes do Pydantic)
        erros_unicidade = []
        c_ref = str(dados_limpos.get('Cod. Ref.', '')).strip()
        c_ref_add = str(dados_limpos.get('Cod. Ref. Adicional', '')).strip()

        if c_ref in duplicados_globais:
            erros_unicidade.append(f"Cod. Ref.: O valor '{c_ref}' está duplicado na planilha.")

        if c_ref_add not in ["", "None", "nan"] and c_ref_add in duplicados_globais:
            erros_unicidade.append(f"Cod. Ref. Adicional: O valor '{c_ref_add}' está duplicado na planilha.")

        # --- LÓGICA PROCV ORGANIZAÇÃO ---
        org_original = dados_limpos.get('Organização')

        # Só processa se a coluna Organização estiver preenchida E o nome nela for DIFERENTE do Nome Fantasia
        if org_original and str(org_original).strip().lower() not in ["", "none", "nan"]:
            nome_buscar = str(org_original).strip()

            # Se o que está na coluna Organização é o nome de OUTRA empresa (PROCV)
            if nome_buscar in mapa_organizacao and nome_buscar != current_name:
                cod_alvo = mapa_organizacao[nome_buscar]
                dados_limpos['Organização'] = cod_alvo
                df.at[index, 'Organização'] = cod_alvo

            # Se o nome for igual ao da própria empresa, limpamos (pois a empresa não é organização de si mesma neste contexto)
            elif nome_buscar == current_name:
                dados_limpos['Organização'] = None
                df.at[index, 'Organização'] = None

        # Padrões: Ativo, Fuso horário, Idioma
        padroes_fixos = {
            'Ativo': 'Sim',
            'Fuso horário': 'America/Sao_Paulo',
            'Idioma': 'pt-BR'
        }
        for col, val_padrao in padroes_fixos.items():
            if not dados_limpos.get(col) or str(dados_limpos[col]).strip().lower() in ["", "none", "nan"]:
                dados_limpos[col] = val_padrao
                df.at[index, col] = val_padrao

        # 5. SANEAMENTO DE ENDEREÇO E CONTATO
        # 1. CEP (Limpa .0 e formata 00000-000)
        dados_limpos['CEP'] = formatar_cep(dados_limpos.get('CEP'))
        df.at[index, 'CEP'] = dados_limpos['CEP']

        # 2. Número (Limpa .0)
        dados_limpos['Número'] = clean_numeric_string(dados_limpos.get('Número'))
        df.at[index, 'Número'] = dados_limpos['Número']

        # 3. Estado (Converte para Sigla)
        dados_limpos['Estado'] = normalizar_estado(dados_limpos.get('Estado'))
        df.at[index, 'Estado'] = dados_limpos['Estado']

        # 4. Demais campos de texto (Apenas retira espaços e .0 se houver)
        for c in ['País', 'Cidade', 'Bairro', 'Rua', 'Complemento', 'Referência']:
            val_limpo = clean_numeric_string(dados_limpos.get(c))
            dados_limpos[c] = val_limpo
            df.at[index, c] = val_limpo

        try:
            person = PersonSchema.model_validate(dados_limpos)
            df.at[index, 'Contato'] = person.contact
            df.at[index, 'E-mail'] = person.email
            df.at[index, 'CEP'] = person.cep
            df.at[index, 'Estado'] = person.estado
            df.at[index, 'País'] = person.pais
            df.at[index, 'Cidade'] = person.city
            df.at[index, 'Bairro'] = person.neighborhood
            df.at[index, 'Rua'] = person.street
            df.at[index, 'Número'] = person.number
            df.at[index, 'Complemento'] = person.complement
            df.at[index, 'Referência'] = person.reference

            if current_code in duplicados_globais:
                raise ValueError(f"Cod. Ref.: Valor '{current_code}' duplicado.")

            df.at[index, 'Validado'] = 'Sim'

        except (ValidationError, ValueError) as e:
            df.at[index, 'Validado'] = 'Não'
            lista_erros_pydantic = e.errors() if isinstance(e, ValidationError) else [
                {'msg': str(e), 'loc': ['Manual']}]

            mensagens_finais = []
            colunas_finais = []

            for erro in lista_erros_pydantic:
                msg = erro['msg'].replace("Value error, ", "").replace("Assertion failed, ", "")
                if "value is not a valid email address" in msg:
                    msg = "E-mail: O formato do e-mail é inválido."

                if " || " in msg:
                    for sub in msg.split(" || "):
                        mensagens_finais.append(sub.strip())
                        if ":" in sub: colunas_finais.append(sub.split(":")[0].strip())
                else:
                    if ":" in msg:
                        colunas_finais.append(msg.split(":")[0].strip())
                    else:
                        colunas_finais.append(str(erro['loc'][-1]) if erro['loc'] else "Geral")
                    mensagens_finais.append(msg)

            df.at[index, 'Coluna_com_Erro'] = ", ".join(list(dict.fromkeys(colunas_finais)))
            df.at[index, 'Mensagem_de_Erro'] = " | ".join(list(dict.fromkeys(mensagens_finais)))
            print(f"❌ Pessoa: {current_code} | Erros: {df.at[index, 'Mensagem_de_Erro']}")

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
    processar_validar_planilha_persons('files/persons.xlsx', 'files/persons-atualizada.xlsx')

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
