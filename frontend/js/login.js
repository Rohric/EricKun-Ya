"use strict";

// Skip the login page when a session already exists.
if (getAccess()) window.location.href = "dashboard.html";

document.getElementById("toggle-auth").addEventListener("click", (e) => {
  e.preventDefault();
  _toggleForms();
});

document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await login(inputValue("login-email"), inputValue("login-password"));
    window.location.href = "dashboard.html";
  } catch (err) {
    showMessage(errorText(err));
  }
});

document.getElementById("register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await register(
      inputValue("reg-email"), inputValue("reg-name"),
      inputValue("reg-password"), inputValue("reg-password2"),
    );
    window.location.href = "dashboard.html";
  } catch (err) {
    showMessage(errorText(err));
  }
});

// Switch between the login and registration forms.
function _toggleForms() {
  const loginForm = document.getElementById("login-form");
  const registerForm = document.getElementById("register-form");
  const link = document.getElementById("toggle-auth");
  const showRegister = loginForm.style.display !== "none";
  loginForm.style.display = showRegister ? "none" : "block";
  registerForm.style.display = showRegister ? "block" : "none";
  link.textContent = showRegister ? "Schon ein Konto? Anmelden" : "Noch kein Konto? Registrieren";
  showMessage("", false);
}
