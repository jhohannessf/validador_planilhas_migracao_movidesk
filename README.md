# Validador de planilhas da Migração Movidesk - v 1.0

Este programa consiste em validar individualmente as planilhas utilizadas na migração de dados para o Movidesk. Para algumas colunas ele corrige os dados com erro, para outras informa o erro e você precisará ajustar manualmente, confirmando os dados com o cliente.


## Uso

* Baixar a ultima versão [aqui](https://github.com/jhohannes.freitas/validado_planilhas_migracao_movidesk)
* Descompacte o arquivo em qualquer local no computador
* Você vai precisar de uma ferramenta IDE para edição e execução do código 
* Pode ser o PyCharm ou VS Code. Ambas precisarão de chamado no Jira para a instalação.
    * Baixar o Pycharm [aqui](https://www.jetbrains.com/pt-br/pycharm/download/?section=windows)
      * Como instalar e configurar o Pycharm [aqui](https://www.youtube.com/watch?v=EDQGZEsNARg)
    * Baixe o VS Code [aqui](https://code.visualstudio.com/download)
      * Como instalar e configurar o VS Code [aqui](https://www.youtube.com/watch?v=Zy3iaMZbPO8)
* Com a ferramenta instalada e configurada, você precisará abrir o projeto que baixou
  * No PyCharm, canto superior esquerdo, aperta Alt + \ > File > Open
    * Após abrir o projeto, você precisará importar todos os pacotes e bibliotecas que estão sendo utilizadas
      * Abra o terminal (Alt + F12), escreva pip install -r requirements.txt e aperte `enter` 
        * Aguarde finalizar a instalação por completa
  * No VS Code, canto superior esquerdo > File > Open File ou aperta Ctrl + O 
    * Após abrir o projeto, você precisará importar todos os pacotes e bibliotecas que estão sendo utilizadas
      * Para ler e utilizar o arquivo requirements.txt no VS Code, abra o terminal integrado (Ctrl + ' ou Terminal > Novo Terminal) e execute o comando pip install -r requirements.txt. Isso instalará automaticamente todas as bibliotecas listadas no ambiente virtual ativo.  
* Dentro da pasta `files`, cole os dados dentro das planilhas que deseja validar
  * É imprescindível que as planilhas estejam no layout padrão de Migração
    * Para evitar qualquer tipo de inconsistência, copie e cole os dados nas planilhas que já estão no layout correto dentro da pasta `files`
    * Não altere o nome das colunas das planilhas que estão no layout padrão de Migração

* Para executar no PyCharm, basta clicar com botão direito do mouse no arquivo.py e clicar em `run + nome do arquivo.py`
  * Para validar a planilha de tickets, `run` no arquivo `ticket_spreadsheet_validator.py`
  * Para validar a planilha de actions, `run` no arquivo `action_spreadsheet_validator.py`
  * Para validar a planilha de attachments, `run` no arquivo `attachment_spreadsheet_validator.py`
  * Para validar a planilha de custom-fields, `run` no arquivo `custom_field_spreadsheet_validator.py`
  * Para validar a planilha de persons, `run` no arquivo `person_spreadsheet_validator.py`

* Para executar no VS Code, instale a extensão Python, abra o arquivo .py, clique no botão "Play" no canto superior direito para executar no terminal integrado ou use o terminal (Ctrl+` e python seu_arquivo.py), sendo o botão Play o mais direto para rodar o script inteiro ou seleções. 
  * Para validar a planilha de tickets, `Play` no arquivo `ticket_spreadsheet_validator.py`
  * Para validar a planilha de actions, `Play` no arquivo `action_spreadsheet_validator.py`
  * Para validar a planilha de attachments, `Play` no arquivo `attachment_spreadsheet_validator.py`
  * Para validar a planilha de custom-fields, `Play` no arquivo `custom_field_spreadsheet_validator.py`
  * Para validar a planilha de persons, `Play` no arquivo `person_spreadsheet_validator.py`

* Execute os scripts individualmente, de acordo com a planilha que deseja validar


# O que faz o validador em cada planilha?
  * Valida o preenchimento das colunas das planilhas seguindo as regras da API do Movidesk.

## 1- Planilha de Ticket - [Link API](https://atendimento.movidesk.com/kb/article/256/movidesk-ticket-api?ticketId=&q=api)

* `Coluna` Ticket - Valida se o valor informado nesta coluna é um número inteiro;
* `Coluna` Ticket Público/Interno - Valida e corrige possíveis erros de digitação para Interno ou Público
* `Coluna` Assunto - Valida se possui no máximo 350 caracteres. Se estiver vazio, insere "Sem assunto informado no ticket!"
* `Coluna` Solicitante - Valida se está preenchido, pois é obrigatório;
* `Coluna` Responsável - Valida se está preenchido, pois é obrigatório;
* `Coluna` Equipe do Responsável - Valida se está preenchido, pois é obrigatório;
* `Coluna` Serviço - Não tem validação, preenchimento opcional;
* `Coluna` Categorias - Não tem validação, preenchimento opcional;
* `Coluna` Urgência - Não tem validação, preenchimento opcional;
* `Coluna` Status - Se for "Aguardando", obrigatório inserir "Justificativa". Se for "Fechado", obrigatório inserir "Data/Hora de encerramento";
* `Coluna` Justificativa - Se o Status for "Aguardando", obrigatório inserir "Justificativa";
* `Coluna` Data/Hora abertura - Valida, altera para o formato dd/mm/aaaa hh:mm:ss e insere +3h;
* `Coluna` Data/Hora de encerramento - Valida, altera para o formato dd/mm/aaaa hh:mm:ss e insere +3h. Só é preenchida para Status "Fechado", caso esteja preenchida para outros status, é limpa;
* `Coluna` Tag - Se tiver preenchida, acrescenta a tag "Migrado". Se estiver em branco, insere a tag "Migrado";
* `Coluna` Sequencia - Se não estiver preenchida, preenche com a numeração do ticket informada na coluna "Ticket".

### [Observação importante:](#obs)
       - Se for planilhas retiradas do banco Movidesk, o padrão de data já está no formato UTC+03:00. Não sendo necessário o incremento de +3 horas nas colunas de data, tanto na planilha de tickets quanto de actions.
        - Você precisará comentar (#) essa parte do código que incrementa +3h, antes mesmo de executar o código.
          - `ticket_spreadsheet_validator.py` - comente a linha 410

## 2 - Planilha de Action - [Link API](https://atendimento.movidesk.com/kb/pt-br/article/47001/importacao-de-acoes-movidesk?ticketId=&q=)

* `Coluna` Ticket - Valida se o valor informado nesta coluna é um número inteiro;
* `Coluna` Data/Hora - Valida, altera para o formato dd/mm/aaaa hh:mm:ss e insere +3h;
* `Coluna` Ação Público.Interno - Valida e corrige possíveis erros de digitação para Interno ou Público;
* `Coluna` Gerador - Valida se está preenchido, pois é obrigatório;
* `Coluna` Descrição - Valida se está preenchido, caso contrário insere "Sem descrição informada nesta ação do ticket. Se a descrição ultrapassar o limite de linhas do excel(32.767), ele REMOVE a linha gerada que quebrou a planilha;
* `Coluna` Sequencia - Se não estiver preenchida, preenche a ordem asc com base na "Data/Hora";
* `Coluna` TicketId - Sem validação, obrigatório apenas nas migrações entre bases Movidesk;
* `Coluna` StorageUID - Sem validação, obrigatório apenas nas migrações entre bases Movidesk;


## [Observação importante:](#obs)
       - Se for planilhas retiradas do banco Movidesk, o padrão de data já está no formato UTC+03:00. Não sendo necessário o incremento de +3 horas nas colunas de data, tanto na planilha de tickets quanto de actions.
        - Você precisará comentar (#) essa parte do código que incrementa +3h antes mesmo de executar o código.
          - `action_spreadsheet_validator.py` - comente a linha 309
        - Migração entre bases Movidesk, a coluna descrição deve ser mantida em branco. Terá que ajustar manualmente.

## 3 - Planilha de Attachments - [Link API](https://atendimento.movidesk.com/kb/pt-br/article/46999/importacao-de-anexos-movidesk?ticketId=&q=)

* `Coluna` Ticket - Valida se o valor informado nesta coluna é um número inteiro;
* `Coluna` Número da Ação - Valida se o valor informado nesta coluna é um número inteiro;
* `Coluna` Caminho - Valida o preenchimento, altera / por \;
* `Coluna` Nome Arquivo - Valida o preenchimento. Caso não informado, assume que o final do "Caminho" (após a última barra \) é o nome do arquivo.
* `Coluna` Content Type - Valida se está preenchido. Caso não esteja, é gerado conforme a extensão do "Nome Arquivo".


## [Observação importante:](#obs)
        - Migração entre bases Movidesk, não utiliza esta planilha; 
        - O envio dos anexos é feito via script em python.

## 4 - Planilha de custom-fields - [Link API](https://atendimento.movidesk.com/kb/pt-br/article/427659/importacao-de-campos-adicionais-movidesk)

* `Coluna` id - Valida se foi informado um valor nesta coluna, int ou str;
* `Coluna` CustomFieldId - Valida se foi preenchido o id do campo na base Movidesk, deve ser inserido manualmente;
* `Coluna` CustomFieldName - Valida se foi preenchido o nome do campo na base Movidesk, deve ser inserido manualmente;
* `Coluna` value  - Valida se foi preenchido;
* `Coluna` Type - Valida se foi preenchido, sugerindo entre "Person" ou "Ticket". Caso tenha sido, corrige possíveis erros de digitação para "Person" ou "Ticket".


## [Observação importante:](#obs)
        - Valores para CustomFieldId e CustomFieldName devem ser retirados da base Movides. 

## 5 - Planilha de Person - [Link API](https://atendimento.movidesk.com/kb/article/189/movidesk-person-api?ticketId=&q=api%20pessoas)

* `Coluna` Tipo - Valida o preenchimento, alterando se foi informado Pessoa para 1, Empresa para 2 e Departamento para 4;
* `Coluna` Perfil - Valida o preenchimento, alterando se foi informado Agente para 1, Cliente para 2 e Agente, Cliente para 3;
* `Coluna` Nome fantasia - Valida se foi preenchido, pois é obrigatório;
* `Coluna` Razão social - Valida se está preenchido para o tipo 2, pois caso o "Nome fantasia" não foi informado;
* `Coluna` Usuário - Não tem validação, preenchimento opcional;
* `Coluna` Senha - Não tem validação, preenchimento opcional;
* `Coluna` CPF / CNPJ - Validação de CPF ou CNPJ, retirando os caracteres;
* `Coluna` Cod. Ref. - Valida se foi preenchido, pois é obrigatório e deve ser único;
* `Coluna` Cod. Ref. Adicional - Valida se foi preenchido sem repetir com o "Cod. Ref.",  deve ser único;
* `Coluna` Perfil de acesso - Valida o preenchimento;
* `Coluna` Classificação - Não tem validação, preenchimento opcional;
* `Coluna` Cargo - Não tem validação, preenchimento opcional;
* `Coluna` Superior hierárquico - Não tem validação, preenchimento opcional;
* `Coluna` Tipo do e-mail - Valida se foi preenchida. Caso não, preenche o padrão: "Profissional";
* `Coluna` E-mail - Valida se o e-mail informado existe e segue o padrão "@";
* `Coluna` Tipo do contato - Valida se foi preenchida. Caso não, preenche o padrão: "Telefone celular";
* `Coluna` Contato - Valida o telefone preenchido e insere o formato padrão: (11) 9999-9999;
* `Coluna` Tipo do endereço - Valida se foi preenchida. Caso não, preenche o padrão: "Comercial";
* `Coluna` País - Valida a quantidade de caracteres máxima de 128, preenchimento opcional;
* `Coluna` CEP - Valida a quantidade de caracteres máxima de 32, valida o formato cep 000000-111. O preenchimento é opcional;
* `Coluna` Estado - Se for preenchido, substitui o nome do estado pela sigla. O preenchimento é opcional;
* `Coluna` Cidade - Valida a quantidade de caracteres máxima de 128, preenchimento opcional;
* `Coluna` Bairro - Valida a quantidade de caracteres máxima de 128, preenchimento opcional;
* `Coluna` Rua - Valida a quantidade de caracteres máxima de 128, preenchimento opcional;
* `Coluna` Número - Valida a quantidade de caracteres máxima de 32, preenchimento opcional;
* `Coluna` Complemento - Valida a quantidade de caracteres máxima de 128, preenchimento opcional;
* `Coluna` Referência - Valida a quantidade de caracteres máxima de 128, preenchimento opcional;
* `Coluna` Equipe - Valida o preenchimento obrigatório quando o perfil é igual a 1 ou 3;
* `Coluna` Organização - Caso preenchida, valida o nome preenchido e busca na coluna "Nome Fantasia", retornando o Cód. Ref. da organização;
* `Coluna` Contrato de SLA - Não tem validação, preenchimento opcional;
* `Coluna` Ativo - Valida se foi preenchido. Caso contrário, insere o padrão: "Sim";
* `Coluna` Fuso horário - Valida se foi preenchido. Caso contrário, insere o padrão: "America/Sao_Paulo";
* `Coluna` Idioma - Valida se foi preenchido. Caso contrário, insere o padrão: "pt-BR";

### [Observação importante:](#obs)
       - Se for a planilha de persons retiradas do próprio painel Movidesk, copiar os dados e colar na planilha de layout padrão, respeitando as colunas.
        - A planilha do painel tem colunas a mais que a planilha layout padrão do Migrador.
