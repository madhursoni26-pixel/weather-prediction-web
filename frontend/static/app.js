const $ = (id) => document.getElementById(id);
const form = $("searchForm");
const input = $("cityInput");
const button = $("searchButton");

function showMessage(message) {
  const el = $("message");
  el.textContent = message;
  el.classList.add("show");
}
function clearMessage() {
  $("message").textContent = "";
  $("message").classList.remove("show");
}
function prettyDate(dateString) {
  return new Date(dateString + "T12:00:00").toLocaleDateString(undefined, {weekday:"short", month:"short", day:"numeric"});
}
function weatherEmoji(condition, fallback) {
  return fallback || "🌤️";
}
function setText(id, value) {
  $(id).textContent = value === null || value === undefined ? "--" : value;
}

async function loadWeather(city) {
  clearMessage();
  if (!city.trim()) {
    showMessage("Please enter a city name first.");
    input.focus();
    return;
  }
  button.disabled = true;
  button.innerHTML = "Loading…";
  try {
    const response = await fetch("/api/weather?city=" + encodeURIComponent(city.trim()));
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Unable to load weather.");
    renderWeather(data);
    await loadHistory();
  } catch (error) {
    showMessage(error.message || "Something went wrong. Please try again.");
  } finally {
    button.disabled = false;
    button.innerHTML = 'Search <span>→</span>';
  }
}

function renderWeather(data) {
  const c = data.current;
  $("locationName").textContent = [data.city, data.region, data.country].filter(Boolean).join(", ");
  setText("conditionText", c.condition);
  setText("temperature", Math.round(c.temperature));
  setText("feelsLike", Math.round(c.feels_like) + "°C");
  setText("feelsMetric", Math.round(c.feels_like));
  setText("humidity", c.humidity);
  setText("wind", c.wind_speed);
  setText("precipitation", c.precipitation);
  $("humidityBar").style.width = Math.max(0, Math.min(100, Number(c.humidity) || 0)) + "%";
  $("heroIcon").textContent = c.icon;
  $("localTime").textContent = data.timezone ? data.timezone.replaceAll("_", " ") : "Local forecast";
  $("updatedLabel").textContent = "Updated " + new Date().toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"});
  const grid = $("forecastGrid");
  grid.innerHTML = "";
  data.daily.forEach((day, i) => {
    const card = document.createElement("article");
    card.className = "forecast-card";
    const dayName = i === 0 ? "Today" : new Date(day.date + "T12:00:00").toLocaleDateString(undefined, {weekday:"short"});
    card.innerHTML = `
      <div class="forecast-day">${dayName}</div>
      <div class="forecast-date">${prettyDate(day.date)}</div>
      <div class="forecast-icon">${day.icon}</div>
      <div class="forecast-condition">${day.condition}</div>
      <div class="forecast-temps">${Math.round(day.max)}° <span>${Math.round(day.min)}°</span></div>
      <div class="rain-chance">☂ ${day.rain_chance == null ? "—" : day.rain_chance + "%"} rain</div>`;
    grid.appendChild(card);
  });
}

async function loadHistory() {
  try {
    const response = await fetch("/api/history");
    const rows = await response.json();
    const container = $("historyRows");
    container.innerHTML = "";
    if (!rows.length) {
      container.innerHTML = '<p class="empty-history">No searches yet. Search for a city to get started.</p>';
      return;
    }
    rows.forEach(row => {
      const item = document.createElement("div");
      item.className = "history-row";
      const time = new Date(row.searched_at).toLocaleString([], {month:"short", day:"numeric", hour:"2-digit", minute:"2-digit"});
      item.innerHTML = `<span class="history-city"></span><span></span><span class="history-temp"></span><span></span>`;
      item.children[0].textContent = [row.city, row.country].filter(Boolean).join(", ");
      item.children[1].textContent = row.condition || "—";
      item.children[2].textContent = row.temperature == null ? "—" : Math.round(row.temperature) + "°C";
      item.children[3].textContent = time;
      item.style.cursor = "pointer";
      item.title = "Click to search this city again";
      item.addEventListener("click", () => {
        input.value = row.city;
        loadWeather(row.city);
        window.scrollTo({top:0, behavior:"smooth"});
      });
      container.appendChild(item);
    });
  } catch (_) {
    $("historyRows").innerHTML = '<p class="empty-history">Search history is temporarily unavailable.</p>';
  }
}

form.addEventListener("submit", event => {
  event.preventDefault();
  loadWeather(input.value);
});
$("refreshHistory").addEventListener("click", loadHistory);
$("todayLabel").textContent = new Date().toLocaleDateString(undefined, {weekday:"short", month:"long", day:"numeric", year:"numeric"});
loadHistory();
loadWeather("Delhi");
