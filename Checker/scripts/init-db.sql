-- Docker init: create database and user, then apply full schema
-- Mounted as /docker-entrypoint-initdb.d/01-init.sql

CREATE DATABASE IF NOT EXISTS yaml_terraform_validator
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'validator'@'%' IDENTIFIED BY 'validator_secret';
GRANT ALL PRIVILEGES ON yaml_terraform_validator.* TO 'validator'@'%';
FLUSH PRIVILEGES;
