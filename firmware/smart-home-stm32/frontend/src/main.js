const ledGrid = document.querySelector("#ledGrid");
const errorBox = document.querySelector("#errorBox");
const loadingText = document.querySelector("#loadingText");
const connectionStatus = document.querySelector("#connectionStatus");
const apiBaseUrlInput = document.querySelector("#apiBaseUrl");
const saveApiBaseUrlButton = document.querySelector("#saveApiBaseUrl");
const refreshButton = document.querySelector("#refreshButton");
const allOnButton = document.querySelector("#allOnButton");
const allOffButton = document.querySelector("#allOffButton");

let leds = [
  { id: 1, name: "\u5ba2\u5385\u706f", pin: "PA4", state: false },
  { id: 2, name: "\u5367\u5ba4\u706f", pin: "PA5", state: false },
  { id: 3, name: "\u53a8\u623f\u706f", pin: "PA6", state: false },
  { id: 4, name: "\u536b\u751f\u95f4\u706f", pin: "PA7", state: false },
  { id: 5, name: "\u68b3\u5986\u53f0\u706f", pin: "PB0", state: false },
  { id: 6, name: "\u7a7a\u8c03", pin: "PA15", state: false },
];

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function setLoading(isLoading) {
  loadingText.hidden = !isLoading;
  document.body.classList.toggle("is-loading", isLoading);
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = !message;
}

function setConnection(online, text) {
  connectionStatus.textContent = text;
  connectionStatus.classList.toggle("status-online", online);
  connectionStatus.classList.toggle("status-offline", !online);
}

function setCommandWarning(error) {
  setConnection(true, "\u547d\u4ee4\u5df2\u53d1\u9001");
  showError(`${error.message || "Fetch failed"}\uff1b\u706f\u5df2\u6309\u672c\u6b21\u64cd\u4f5c\u66f4\u65b0\uff0c\u53ef\u70b9\u51fb\u5237\u65b0\u72b6\u6001\u518d\u6821\u51c6\u3002`);
}

function setLocalLedState(ledId, state) {
  leds = leds.map((led) => (led.id === ledId ? { ...led, state } : led));
  renderLeds();
}

function setLocalAllState(state) {
  leds = leds.map((led) => ({ ...led, state }));
  renderLeds();
}

function renderLeds() {
  ledGrid.innerHTML = leds.map((led) => `
    <article class="led-card ${led.state ? "is-on" : "is-off"}">
      <div class="led-meta">
        <div class="lamp-symbol" aria-hidden="true"></div>
        <div>
          <h2>${led.name}</h2>
          <p>${led.pin}</p>
        </div>
      </div>
      <button class="switch" type="button" data-led-id="${led.id}" aria-pressed="${led.state}">
        <span>${led.state ? "ON" : "OFF"}</span>
      </button>
    </article>
  `).join("");

  ledGrid.querySelectorAll(".switch").forEach((button) => {
    button.addEventListener("click", async () => {
      const ledId = Number(button.dataset.ledId);
      const current = leds.find((item) => item.id === ledId);
      if (!current) {
        return;
      }

      const nextState = !current.state;
      await runAction(async () => {
        setLocalLedState(ledId, nextState);
        try {
          await window.SmartHomeApi.setLed(ledId, nextState);
        } catch (error) {
          setCommandWarning(error);
        }
        await refreshLedsQuietly();
      });
    });
  });
}

async function refreshHealth() {
  const health = await window.SmartHomeApi.health();
  setConnection(true, `${health.hostname || "smart-home-stm32"} \u5728\u7ebf`);
}

async function refreshLeds() {
  const data = await window.SmartHomeApi.leds();
  if (Array.isArray(data.leds)) {
    leds = data.leds;
  }
  renderLeds();
}

async function refreshLedsQuietly() {
  try {
    await sleep(500);
    await refreshLeds();
  } catch (error) {
    // The ESP8266 AT server is single-threaded; local state already reflects the accepted command.
  }
}

async function runAction(action) {
  setLoading(true);
  showError("");
  try {
    await action();
    setConnection(true, "\u8bbe\u5907\u5728\u7ebf");
  } catch (error) {
    setConnection(false, "\u8fde\u63a5\u5931\u8d25");
    showError(error.message || "\u8bf7\u6c42\u5931\u8d25\uff0c\u8bf7\u68c0\u67e5\u8bbe\u5907\u5730\u5740\u3001Wi-Fi \u548c ESP8266 \u4f9b\u7535\u3002");
  } finally {
    setLoading(false);
  }
}

async function loadInitialState() {
  try {
    await refreshHealth();
    await sleep(350);
    await refreshLeds();
  } catch (error) {
    const fallbackUrl = window.SmartHomeApi.getDefaultBaseUrl();
    if (window.SmartHomeApi.getBaseUrl() !== fallbackUrl) {
      window.SmartHomeApi.setBaseUrl(fallbackUrl);
      apiBaseUrlInput.value = fallbackUrl;
      await refreshHealth();
      await sleep(350);
      await refreshLeds();
      return;
    }
    throw error;
  }
}

saveApiBaseUrlButton.addEventListener("click", () => {
  window.SmartHomeApi.setBaseUrl(apiBaseUrlInput.value);
  runAction(loadInitialState);
});

refreshButton.addEventListener("click", () => {
  runAction(loadInitialState);
});

allOnButton.addEventListener("click", () => {
  runAction(async () => {
    setLocalAllState(true);
    try {
      await window.SmartHomeApi.setAll(true);
    } catch (error) {
      setCommandWarning(error);
    }
    await refreshLedsQuietly();
  });
});

allOffButton.addEventListener("click", () => {
  runAction(async () => {
    setLocalAllState(false);
    try {
      await window.SmartHomeApi.setAll(false);
    } catch (error) {
      setCommandWarning(error);
    }
    await refreshLedsQuietly();
  });
});

apiBaseUrlInput.value = window.SmartHomeApi.getBaseUrl();
renderLeds();
runAction(loadInitialState);
