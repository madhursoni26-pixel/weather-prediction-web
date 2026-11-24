CREATE DATABASE IF NOT EXISTS weather_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE weather_db;
CREATE TABLE IF NOT EXISTS searches (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    city VARCHAR(150) NOT NULL,
    country VARCHAR(150),
    temperature DECIMAL(6,2),
    `condition` VARCHAR(100),
    humidity INT,
    wind_speed DECIMAL(7,2),
    searched_at DATETIME NOT NULL
);
