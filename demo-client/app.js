const state = {
  propertyId: "",
  leaseId: "",
  notificationId: "",
};

const cards = document.querySelector("#statusCards");

function value(id) {
  return document.querySelector(`#${id}`).value.trim();
}

function setDefaults() {
  const now = new Date();
  const today = now.toISOString().slice(0, 10);
  const end = new Date(now);
  end.setUTCDate(end.getUTCDate() + 30);

  document.querySelector("#rentDueDay").value = String(now.getUTCDate());
  document.querySelector("#startDate").value = today;
  document.querySelector("#endDate").value = end.toISOString().slice(0, 10);
}

function addCard(title, message, ok = true) {
  const card = document.createElement("article");
  card.className = `card ${ok ? "ok" : "error"}`;
  card.innerHTML = `<h3>${escapeHtml(title)}</h3><p>${escapeHtml(message)}</p>`;
  cards.prepend(card);
}

function escapeHtml(input) {
  return String(input)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function decodeTenantClaim(token) {
  const payload = token.split(".")[1];
  if (!payload) {
    throw new Error("Token is not a JWT.");
  }
  const normalized = payload.replaceAll("-", "+").replaceAll("_", "/");
  const decoded = JSON.parse(atob(normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=")));
  if (!decoded["custom:tenant_id"]) {
    throw new Error("Token does not include custom:tenant_id.");
  }
  return decoded["custom:tenant_id"];
}

async function postLocal(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Local demo server request failed.");
  }
  return data;
}

async function apiRequest(method, path, body) {
  return postLocal("/local/proxy", {
    apiBaseUrl: value("apiBaseUrl"),
    token: value("idToken"),
    method,
    path,
    body,
  });
}

async function runHealth() {
  const result = await apiRequest("GET", "/health");
  addCard("Health", `GET /health => ${result.statusCode}`, result.statusCode === 200);
}

async function createProperty() {
  const body = {
    tenant_id: "client-supplied-tenant-must-be-ignored",
    name: value("propertyName"),
    address: value("propertyAddress"),
  };
  const result = await apiRequest("POST", "/properties", body);
  const expectedTenant = decodeTenantClaim(value("idToken"));
  const tenantCheck = result.body.tenant_id === expectedTenant;
  state.propertyId = result.body.property_id || "";
  addCard(
    "Create property",
    `POST /properties => ${result.statusCode}; tenant override check: ${
      tenantCheck ? "passed" : "failed"
    }`,
    result.statusCode === 201 && tenantCheck,
  );
}

async function listProperties() {
  const result = await apiRequest("GET", "/properties");
  const items = result.body.items || [];
  const containsCreated = items.some((item) => item.property_id === state.propertyId);
  addCard(
    "List properties",
    `GET /properties => ${result.statusCode}; items: ${items.length}; created item present: ${
      containsCreated ? "yes" : "not checked"
    }`,
    result.statusCode === 200,
  );
}

async function createLease() {
  if (!state.propertyId) {
    throw new Error("Create a property before creating a lease.");
  }
  const body = {
    property_id: state.propertyId,
    resident_name: value("residentName"),
    rent_due_day_of_month: Number(value("rentDueDay")),
    start_date: value("startDate"),
    end_date: value("endDate"),
  };
  const result = await apiRequest("POST", "/leases", body);
  state.leaseId = result.body.lease_id || "";
  addCard("Create lease", `POST /leases => ${result.statusCode}`, result.statusCode === 201);
}

async function listLeases() {
  const result = await apiRequest("GET", "/leases");
  const items = result.body.items || [];
  const containsCreated = items.some((item) => item.lease_id === state.leaseId);
  addCard(
    "List leases",
    `GET /leases => ${result.statusCode}; items: ${items.length}; created item present: ${
      containsCreated ? "yes" : "not checked"
    }`,
    result.statusCode === 200,
  );
}

async function dueSoon() {
  const result = await apiRequest("GET", "/lease-reminders/due-soon?days=7");
  const items = result.body.items || [];
  const containsLease = items.some((item) => item.lease_id === state.leaseId);
  addCard(
    "Due soon",
    `GET /lease-reminders/due-soon?days=7 => ${result.statusCode}; candidates: ${
      items.length
    }; created lease present: ${containsLease ? "yes" : "not checked"}`,
    result.statusCode === 200,
  );
}

async function scan() {
  const result = await postLocal("/local/reminder-scan", {
    token: value("idToken"),
    region: value("awsRegion"),
    functionName: value("backendFunction"),
    days: 7,
    asOfDate: value("startDate"),
  });
  const body = result.body || {};
  addCard(
    "Reminder scan",
    `scan => ${result.statusCode}; candidates: ${body.candidate_count ?? "?"}; created: ${
      body.created_count ?? "?"
    }; duplicates: ${body.duplicate_count ?? "?"}`,
    result.statusCode === 200,
  );
}

async function notifications() {
  const result = await apiRequest("GET", "/notifications");
  const items = result.body.items || [];
  const match = items.find((item) => item.lease_id === state.leaseId && item.type === "rent_due_soon");
  state.notificationId = match?.notification_id || "";
  addCard(
    "Notifications",
    `GET /notifications => ${result.statusCode}; items: ${items.length}; due reminder present: ${
      state.notificationId ? "yes" : "no"
    }`,
    result.statusCode === 200 && Boolean(state.notificationId),
  );
}

async function markRead() {
  if (!state.notificationId) {
    throw new Error("Load notifications before marking one read.");
  }
  const result = await apiRequest("PATCH", `/notifications/${state.notificationId}/read`);
  addCard(
    "Mark notification read",
    `PATCH /notifications/{notification_id}/read => ${result.statusCode}; read_at set: ${
      result.body.read_at ? "yes" : "no"
    }`,
    result.statusCode === 200 && Boolean(result.body.read_at),
  );
}

const actions = {
  health: runHealth,
  createProperty,
  listProperties,
  createLease,
  listLeases,
  dueSoon,
  scan,
  notifications,
  markRead,
};

document.querySelectorAll("[data-action]").forEach((button) => {
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      await actions[button.dataset.action]();
    } catch (error) {
      addCard(button.textContent, error.message, false);
    } finally {
      button.disabled = false;
    }
  });
});

setDefaults();
