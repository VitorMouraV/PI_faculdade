-- Criação do banco e tabelas para o Sistema de Agendamentos Multimodular

CREATE DATABASE IF NOT EXISTS agenda_online
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE agenda_online;

-- Tabela de usuários (gestores / administradores do sistema)
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(100) NOT NULL UNIQUE,
  password VARCHAR(100) NOT NULL,
  role ENUM('admin', 'gestor') NOT NULL DEFAULT 'admin',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Usuário padrão para acessar a área administrativa
INSERT INTO users (name, email, password, role)
VALUES ('Administrador', 'admin@agenda.com', 'admin123', 'admin')
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- Tabela de profissionais (quem realiza os atendimentos)
CREATE TABLE IF NOT EXISTS professionals (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(100),
  phone VARCHAR(20),
  active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de serviços / módulos
CREATE TABLE IF NOT EXISTS services (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  description VARCHAR(255),
  active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Relação muitos-para-muitos entre profissionais e serviços
CREATE TABLE IF NOT EXISTS professional_services (
  professional_id INT NOT NULL,
  service_id INT NOT NULL,
  PRIMARY KEY (professional_id, service_id),
  CONSTRAINT fk_ps_professional
    FOREIGN KEY (professional_id) REFERENCES professionals(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_ps_service
    FOREIGN KEY (service_id) REFERENCES services(id)
    ON DELETE CASCADE
);

-- Tabela de clientes
CREATE TABLE IF NOT EXISTS clients (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(100),
  phone VARCHAR(20),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de agendamentos
CREATE TABLE IF NOT EXISTS appointments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  client_id INT NOT NULL,
  professional_id INT NOT NULL,
  service_id INT NOT NULL,
  appointment_date DATE NOT NULL,
  appointment_time TIME NOT NULL,
  status ENUM('scheduled', 'cancelled') NOT NULL DEFAULT 'scheduled',
  notes VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_appointments_client
    FOREIGN KEY (client_id) REFERENCES clients(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_appointments_professional
    FOREIGN KEY (professional_id) REFERENCES professionals(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_appointments_service
    FOREIGN KEY (service_id) REFERENCES services(id)
    ON DELETE RESTRICT,
  CONSTRAINT uc_appointment UNIQUE (appointment_date, appointment_time, professional_id)
);

-- Dados de exemplo (profissionais)
INSERT INTO professionals (name, email, phone) VALUES
  ('Carlos Silva - Personal Trainer', 'carlos@agenda.com', '11999990001'),
  ('Mariana Souza - Nutricionista', 'mariana@agenda.com', '11999990002')
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- Dados de exemplo (serviços / módulos)
INSERT INTO services (name, description) VALUES
  ('Avaliação física', 'Sessão de avaliação física completa com análise de composição corporal.'),
  ('Treino personalizado', 'Treino de musculação/cardio ajustado aos objetivos do aluno.'),
  ('Consulta nutricional', 'Consulta completa com plano alimentar personalizado.')
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- Vínculos iniciais entre profissionais e módulos
-- Assumindo que os IDs começaram em 1 na ordem de inserção
INSERT IGNORE INTO professional_services (professional_id, service_id) VALUES
  (1, 1), -- Carlos -> Avaliação física
  (1, 2), -- Carlos -> Treino personalizado
  (2, 3); -- Mariana -> Consulta nutricional
