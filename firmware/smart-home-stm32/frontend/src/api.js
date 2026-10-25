const DEFAULT_API_BASE_URL = "http://192.168.31.196/";
const API_BASE_URL = localStorage.getItem("smartHomeApiBaseUrl") || DEFAULT_API_BASE_URL;

(function () {
  function normalizeBaseUrl(url) {
    return String(url || "").trim().replace(/\/+$/, "");
  }

  let apiBaseUrl = normalizeBaseUrl(API_BASE_URL);

  function getBaseUrl() {
    return apiBaseUrl;
  }

  function setBaseUrl(url) {
    apiBaseUrl = normalizeBaseUrl(url);
    localStorage.setItem("smartHomeApiBaseUrl", apiBaseUrl);
  }

  async function request(path) {
    const response = await fetch(`${apiBaseUrl}${path}`, {
      method: "GET",
      cache: "no-store",
    });

    const text = await response.text();
    let data = {};

    if (text) {
      try {
        data = JSON.parse(text);
      } catch (error) {
        throw new Error(`Device returned non-JSON data: ${text.slice(0, 80)}`);
      }
    }

    if (!response.ok || data.ok === false) {
      throw new Error(data.error || `HTTP ${response.status}`);
    }

    return data;
  }

  window.SmartHomeApi = {
    getBaseUrl,
    getDefaultBaseUrl: () => DEFAULT_API_BASE_URL,
    setBaseUrl,
    health: () => request("/api/health"),
    leds: () => request("/api/leds"),
    setLed: (id, state) => request(`/api/led?id=${encodeURIComponent(id)}&state=${state ? "on" : "off"}`),
    setAc: (state) => request(`/api/ac?state=${state ? "on" : "off"}`),
    setAll: (state) => request(`/api/all?state=${state ? "on" : "off"}`),
  };
})();
