# SkyCast Weather Prediction Web Application (MySQL version)

Python standard-library HTTP server (no Flask), HTML/CSS/JavaScript frontend, MySQL history database, and Open-Meteo weather API.

## Requirements
- Python 3.9+
- MySQL Server running locally
- Internet connection for weather/geocoding API

## Setup on Windows
1. Extract this ZIP and open a terminal in the extracted folder.
2. Install the only Python dependency: `python -m pip install -r requirements.txt`
3. Set your MySQL credentials in the same Command Prompt (change `your_mysql_password`):
   ```bat
   set MYSQL_HOST=localhost
   set MYSQL_USER=root
   set MYSQL_PASSWORD=your_mysql_password
   set MYSQL_DATABASE=weather_db
   ```
4. Run `python server.py`. The app creates `weather_db` and its `searches` table automatically.
5. Open http://127.0.0.1:8000 in your browser.

If your MySQL root account has no password, use `set MYSQL_PASSWORD=`. You can alternatively run `schema.sql` in MySQL Workbench first.

## Features
- City search, current weather and seven-day forecast
- Humidity, wind, precipitation and feels-like temperature
- Recent searches stored in MySQL
- Responsive dashboard interface

Weather data is provided by Open-Meteo (https://open-meteo.com/). Internet access is required.
