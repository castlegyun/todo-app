const API = "/api/todos";
const authView = document.getElementById("auth");
const appView = document.getElementById("app");
const authForm = document.getElementById("auth-form");
const authMessage = document.getElementById("auth-message");
const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");
const signupBtn = document.getElementById("signup-btn");
const logoutBtn = document.getElementById("logout-btn");
const userEmail = document.getElementById("user-email");

const list = document.getElementById("list");
const empty = document.getElementById("empty");
const message = document.getElementById("message");
const form = document.getElementById("add-form");
const titleInput = document.getElementById("title");
const dueInput = document.getElementById("due");
const tabAll = document.getElementById("tab-all");
const tabToday = document.getElementById("tab-today");

let filter = "all";

function showError(text) {
  message.textContent = text;
  message.hidden = !text;
}

function showAuthMessage(text, isError = true) {
  authMessage.textContent = text;
  authMessage.hidden = !text;
  authMessage.classList.toggle("info", !isError);
}

function showAuth() {
  appView.hidden = true;
  authView.hidden = false;
}

function showApp(email) {
  userEmail.textContent = email || "";
  authView.hidden = true;
  appView.hidden = false;
  showAuthMessage("");
  passwordInput.value = "";
  load();
}

async function request(url, options) {
  const res = await fetch(url, options);
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (res.status === 401) {
    showAuth();
    throw new Error(data.error || "로그인이 필요합니다.");
  }
  if (!res.ok) throw new Error(data.error || "요청에 실패했습니다.");
  return data;
}

function jsonOptions(method, body) {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

function todayString() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function render(todos) {
  list.replaceChildren();
  const today = todayString();

  for (const todo of todos) {
    const li = document.createElement("li");
    if (todo.is_done) li.classList.add("done");

    const check = document.createElement("input");
    check.type = "checkbox";
    check.checked = !!todo.is_done;
    check.setAttribute("aria-label", "완료 표시");
    check.addEventListener("change", () => toggle(todo.id, check.checked));

    const body = document.createElement("div");
    body.className = "body";
    const title = document.createElement("div");
    title.className = "title";
    title.textContent = todo.title;
    body.append(title);

    if (todo.due_date) {
      const due = document.createElement("div");
      due.className = "due";
      due.textContent = `마감 ${todo.due_date}`;
      if (!todo.is_done && todo.due_date < today) {
        due.classList.add("overdue");
        due.textContent += " (지남)";
      }
      body.append(due);
    }

    const del = document.createElement("button");
    del.type = "button";
    del.className = "del";
    del.textContent = "삭제";
    del.addEventListener("click", () => remove(todo.id));

    li.append(check, body, del);
    list.append(li);
  }

  empty.hidden = todos.length > 0;
  empty.textContent = filter === "today" ? "오늘 할 일이 없습니다." : "할 일이 없습니다. 위에서 추가해 보세요.";
}

async function load() {
  try {
    const url = filter === "today" ? `${API}?filter=today` : API;
    render(await request(url));
    showError("");
  } catch (err) {
    showError(err.message);
  }
}

async function toggle(id, isDone) {
  try {
    await request(`${API}/${id}`, jsonOptions("PATCH", { is_done: isDone }));
  } catch (err) {
    showError(err.message);
  }
  await load();
}

async function remove(id) {
  try {
    await request(`${API}/${id}`, { method: "DELETE" });
    await load();
  } catch (err) {
    showError(err.message);
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await request(API, jsonOptions("POST", { title: titleInput.value, due_date: dueInput.value || null }));
    titleInput.value = "";
    dueInput.value = "";
    titleInput.focus();
    await load();
  } catch (err) {
    showError(err.message);
  }
});

function setFilter(next) {
  filter = next;
  tabAll.classList.toggle("active", next === "all");
  tabToday.classList.toggle("active", next === "today");
  tabAll.setAttribute("aria-pressed", String(next === "all"));
  tabToday.setAttribute("aria-pressed", String(next === "today"));
  load();
}

tabAll.addEventListener("click", () => setFilter("all"));
tabToday.addEventListener("click", () => setFilter("today"));

// ---------- 로그인 ----------

function credentials() {
  return { email: emailInput.value, password: passwordInput.value };
}

authForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const data = await request("/api/auth/login", jsonOptions("POST", credentials()));
    showApp(data.email);
  } catch (err) {
    showAuth();
    showAuthMessage(err.message);
  }
});

signupBtn.addEventListener("click", async () => {
  if (!authForm.reportValidity()) return;
  try {
    const data = await request("/api/auth/signup", jsonOptions("POST", credentials()));
    if (data.logged_in) {
      showApp(data.email);
    } else {
      showAuthMessage(data.message, false);
    }
  } catch (err) {
    showAuthMessage(err.message);
  }
});

logoutBtn.addEventListener("click", async () => {
  try {
    await request("/api/auth/logout", { method: "POST" });
  } catch (err) {
    // 로그아웃 실패는 무시하고 로그인 화면으로 돌아간다
  }
  list.replaceChildren();
  showAuth();
});

async function init() {
  try {
    const me = await request("/api/me");
    showApp(me.email);
  } catch (err) {
    showAuth();
  }
}

init();
