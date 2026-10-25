const API_BASE_URL = 'http://localhost:3000';

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json'
    },
    ...options
  });

  const data = await response.json().catch(() => ({
    success: false,
    message: '后端返回了无法解析的响应'
  }));

  if (!response.ok || data.success === false) {
    throw new Error(data.message || '请求失败');
  }

  return data;
}

export async function getHealth() {
  return request('/api/health');
}

export async function getLeds() {
  return request('/api/leds');
}

export async function refreshLedsStatus() {
  return request('/api/leds/status');
}

export async function setLedState(id, state) {
  return request(`/api/leds/${id}`, {
    method: 'POST',
    body: JSON.stringify({ state })
  });
}

export async function setAllLedState(state) {
  return request('/api/leds/all', {
    method: 'POST',
    body: JSON.stringify({ state })
  });
}
