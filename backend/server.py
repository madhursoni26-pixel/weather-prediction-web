
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, quote
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import json
import os
import mysql.connector
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ==================================================
# PATH CONFIGURATION
# ==================================================

ROOT = Path(__file__).resolve().parent
PROJECT_DIR = ROOT.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"

# Load .env from project root
ENV_FILE = PROJECT_DIR / ".env"
load_dotenv(dotenv_path=ENV_FILE, override=True)

HOST = "127.0.0.1"
PORT = 8000

# ==================================================
# MYSQL CONFIGURATION (FROM .ENV)
# ==================================================

DB_HOST = os.getenv("MYSQL_HOST", "localhost")
DB_USER = os.getenv("MYSQL_USER", "root")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
DB_NAME = os.getenv("MYSQL_DATABASE", "weather_db")


def db_connection(with_database=True):
    config = {
        "host": DB_HOST,
        "user": DB_USER,
        "password": DB_PASSWORD
    }

    if with_database:
        config["database"] = DB_NAME

    return mysql.connector.connect(**config)


# ==================================================
# DATABASE INITIALIZATION
# ==================================================

def init_db():
    # Create database if it doesn't exist
    con = db_connection(with_database=False)

    try:
        cur = con.cursor()

        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
            "CHARACTER SET utf8mb4 "
            "COLLATE utf8mb4_unicode_ci"
        )

        cur.close()
    finally:
        con.close()

    # Connect to the weather database
    con = db_connection()

    try:
        cur = con.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS searches (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                city VARCHAR(150) NOT NULL,
                country VARCHAR(150),
                temperature DECIMAL(6,2),
                `condition` VARCHAR(100),
                humidity INT,
                wind_speed DECIMAL(7,2),
                searched_at DATETIME NOT NULL
            )
        """)

        con.commit()
        cur.close()

    finally:
        con.close()


# ==================================================
# WEATHER API HELPERS
# ==================================================

def get_json(url):
    req = Request(
        url,
        headers={"User-Agent": "WeatherPredictionDemo/1.0"}
    )

    with urlopen(req, timeout=12) as response:
        return json.loads(response.read().decode("utf-8"))


def weather_description(code):
    codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Heavy thunderstorm with hail"
    }

    return codes.get(code, "Unknown conditions")


def weather_icon(code):
    if code == 0:
        return "☀️"
    if code in (1, 2):
        return "🌤️"
    if code == 3:
        return "☁️"
    if code in (45, 48):
        return "🌫️"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "🌧️"
    if code in (71, 73, 75, 77, 85, 86):
        return "❄️"
    if code in (95, 96, 99):
        return "⛈️"

    return "🌡️"


# ==================================================
# FETCH WEATHER DATA
# ==================================================

def fetch_weather(city):

    # Geocoding API
    geo_url = (
        "https://geocoding-api.open-meteo.com/v1/search"
        f"?name={quote(city)}&count=1&language=en&format=json"
    )

    geo = get_json(geo_url)
    results = geo.get("results") or []

    if not results:
        raise ValueError(
            "City not found. Try a larger city or check the spelling."
        )

    place = results[0]

    # Weather forecast API
    params = (
        f"latitude={place['latitude']}"
        f"&longitude={place['longitude']}"
        "&current=temperature_2m,relative_humidity_2m,"
        "apparent_temperature,is_day,precipitation,"
        "weather_code,wind_speed_10m"
        "&daily=weather_code,temperature_2m_max,"
        "temperature_2m_min,precipitation_probability_max"
        "&forecast_days=7&timezone=auto"
    )

    data = get_json(
        "https://api.open-meteo.com/v1/forecast?" + params
    )

    current = data.get("current", {})
    code = int(current.get("weather_code", -1))

    result = {
        "city": place.get("name", city),
        "region": place.get("admin1", ""),
        "country": place.get("country", ""),
        "timezone": data.get("timezone", ""),
        "current": {
            "temperature": current.get("temperature_2m"),
            "feels_like": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"),
            "wind_speed": current.get("wind_speed_10m"),
            "precipitation": current.get("precipitation"),
            "condition": weather_description(code),
            "icon": weather_icon(code),
            "is_day": current.get("is_day", 1)
        },
        "daily": []
    }

    # Build 7-day forecast
    daily = data.get("daily", {})
    dates = daily.get("time", [])

    rain_chances = daily.get("precipitation_probability_max")

    if rain_chances is None:
        rain_chances = [None] * len(dates)

    for i, date in enumerate(dates):
        dcode = int(daily["weather_code"][i])

        result["daily"].append({
            "date": date,
            "icon": weather_icon(dcode),
            "condition": weather_description(dcode),
            "max": daily["temperature_2m_max"][i],
            "min": daily["temperature_2m_min"][i],
            "rain_chance": rain_chances[i]
        })

    # Save search to MySQL
    con = db_connection()

    try:
        cur = con.cursor()

        cur.execute(
            """
            INSERT INTO searches
            (city, country, temperature, `condition`,
             humidity, wind_speed, searched_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                result["city"],
                result["country"],
                result["current"]["temperature"],
                result["current"]["condition"],
                result["current"]["humidity"],
                result["current"]["wind_speed"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )

        con.commit()
        cur.close()

    finally:
        con.close()

    return result


# ==================================================
# HTTP REQUEST HANDLER
# ==================================================

class Handler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        # Serve files from frontend directory
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")

        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)

        # ------------------------------------------
        # WEATHER API
        # ------------------------------------------
        if parsed.path == "/api/weather":

            city = (
                parse_qs(parsed.query).get("city") or [""]
            )[0].strip()

            if not city:
                return self.send_json(
                    {"error": "Please enter a city name."},
                    400
                )

            try:
                return self.send_json(fetch_weather(city))

            except ValueError as e:
                return self.send_json(
                    {"error": str(e)},
                    404
                )

            except (HTTPError, URLError, TimeoutError):
                return self.send_json(
                    {
                        "error": (
                            "Could not reach the weather service. "
                            "Check your internet connection and try again."
                        )
                    },
                    502
                )

            except mysql.connector.Error:
                return self.send_json(
                    {
                        "error": (
                            "MySQL error. Check your database "
                            "credentials and connection."
                        )
                    },
                    500
                )

            except Exception:
                return self.send_json(
                    {
                        "error": (
                            "Weather data could not be loaded. "
                            "Please try again."
                        )
                    },
                    500
                )

        # ------------------------------------------
        # SEARCH HISTORY API
        # ------------------------------------------
        if parsed.path == "/api/history":

            try:
                con = db_connection()

                try:
                    cur = con.cursor(dictionary=True)

                    cur.execute(
                        "SELECT * FROM searches "
                        "ORDER BY id DESC LIMIT 8"
                    )

                    rows = cur.fetchall()

                    for row in rows:

                        if row.get("searched_at"):
                            row["searched_at"] = (
                                row["searched_at"].isoformat(
                                    sep=" ",
                                    timespec="seconds"
                                )
                            )

                        if row.get("temperature") is not None:
                            row["temperature"] = float(
                                row["temperature"]
                            )

                        if row.get("wind_speed") is not None:
                            row["wind_speed"] = float(
                                row["wind_speed"]
                            )

                    cur.close()

                finally:
                    con.close()

                return self.send_json(rows)

            except mysql.connector.Error:
                return self.send_json(
                    {"error": "Could not load search history."},
                    500
                )

        # ------------------------------------------
        # FRONTEND (index.html, CSS, JS)
        # ------------------------------------------
        return super().do_GET()


# ==================================================
# START SERVER
# ==================================================

if __name__ == "__main__":

    # Check frontend folder
    if not FRONTEND_DIR.exists():
        print(f"Frontend folder not found: {FRONTEND_DIR}")
        raise SystemExit(1)

    # Check .env file
    if not ENV_FILE.exists():
        print(f".env file not found: {ENV_FILE}")
        raise SystemExit(1)

    print(f"Loaded environment file: {ENV_FILE}")
    print(f"MySQL host: {DB_HOST}")
    print(f"MySQL user: {DB_USER}")
    print(f"MySQL database: {DB_NAME}")

    # Initialize database
    try:
        init_db()

    except mysql.connector.Error as exc:
        print("Could not connect to MySQL.")
        print("Check that MySQL Server is running and .env credentials are correct.")
        print(f"MySQL error: {exc}")
        raise SystemExit(1)

    print(f"\nWeather dashboard running at http://{HOST}:{PORT}")
    print(f"Serving frontend from: {FRONTEND_DIR}")
    print(f"Using MySQL database: {DB_NAME}")
    print("Press Ctrl+C to stop.\n")

    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.serve_forever()
