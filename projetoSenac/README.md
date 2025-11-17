# Sistema de Agendamentos Multimodular

Evolução do sistema de agenda online para suportar múltiplos profissionais e módulos de atendimento.

## Visão geral

- **Profissionais** (gestores) são cadastrados na área administrativa.
- **Módulos / serviços** (ex.: Personal Trainer, Nutricionista, Fisioterapia, etc.) são cadastrados e vinculados a profissionais.
- O **cliente**, ao agendar, escolhe:
  1. O profissional desejado;
  2. O módulo em que aquele profissional atende;
  3. A data (no formato `dd/mm/aaaa`);
  4. Um horário disponível para aquele profissional na data escolhida.

O sistema garante que **não haja conflito de horários por profissional**.

## Tecnologias

- Backend: Python 3 + Flask
- Frontend: HTML + Bootstrap 5 + JS simples
- Banco de dados: MySQL (XAMPP / MySQL Workbench)

## Passos para rodar o projeto

1. **Instalar dependências Python**

   No terminal, dentro da pasta do projeto:

   ```bash
   pip install -r requirements.txt
   ```

2. **Criar o banco de dados**

   - Abra o **phpMyAdmin** (XAMPP) ou o **MySQL Workbench**.
   - Importe/execute o script `db_schema.sql`.
   - Isso irá:
     - Criar o banco `agenda_online`;
     - Criar as tabelas `users`, `professionals`, `services`, `professional_services`, `clients`, `appointments`;
     - Criar um usuário admin padrão:

       - E-mail: `admin@agenda.com`
       - Senha: `admin123`

     - Criar 2 profissionais de exemplo e 3 módulos de atendimento já vinculados.

3. **Configurar conexão com o banco (se necessário)**

   No arquivo `app.py`, ajuste se precisar:

   ```python
   DB_HOST = "localhost"
   DB_USER = "root"
   DB_PASSWORD = ""
   DB_NAME = "agenda_online"
   ```

4. **Rodar o servidor Flask**

   ```bash
   python app.py
   ```

5. **Acessar o sistema**

   - Página inicial: http://127.0.0.1:5000/
   - Agendamento (cliente): http://127.0.0.1:5000/agendar
   - Área do Gestor (admin): http://127.0.0.1:5000/admin/login

## Fluxos principais

### Cliente

1. Acessa `/agendar`.
2. Informa nome, e opcionalmente e-mail e telefone.
3. Seleciona **Profissional**.
4. Sistema carrega automaticamente os **módulos** atendidos por aquele profissional.
5. Informa a **data** (formato `dd/mm/aaaa`).
6. Sistema busca os **horários livres** para aquele profissional e data.
7. Cliente escolhe o horário e confirma o agendamento.
8. Tela de sucesso mostra cliente, profissional, módulo, data, horário e status.

### Gestor / Administrador

- Faz login em `/admin/login` com `admin@agenda.com / admin123`.
- Acessa:
  - **Painel**: visão rápida de agendamentos do dia e próximos atendimentos.
  - **Agendamentos**: listagem com filtro por data, incluindo cliente, profissional, módulo e possibilidade de cancelar.
  - **Profissionais**: cadastro e listagem de profissionais.
  - **Módulos / Serviços**: cadastro de módulos e vínculo entre profissionais e módulos.
  - **Relatórios**: quantidade de agendamentos por dia.

---

Projeto pronto para ser usado como base completa e funcional de uma agenda multimodular, contemplando cadastro de profissionais, módulos, vínculo entre eles e fluxo de agendamento do ponto de vista do cliente.
