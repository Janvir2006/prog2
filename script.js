const container = document.getElementById('container');
const registerBtn = document.getElementById('register');
const InvioCodiceBtn = document.getElementById('invio_codice');
const loginBtn = document.getElementById('login');

registerBtn.addEventListener('click', () => {
    container.classList.add("active");
});

loginBtn.addEventListener('click', () => {
    container.classList.remove("active");
});

InvioCodiceBtn.addEventListener('click', () => {
    container.classList.remove("active");
});
