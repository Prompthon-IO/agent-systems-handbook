"use strict";
document.querySelector("#demo-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const name = document.querySelector("#name").value.trim();
  document.querySelector("#form-result").textContent = `Thanks, ${name}. This local demo did not send or store your details.`;
});
