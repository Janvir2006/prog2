// Funzione per aggiornare il contatore del carrello
function updateCartCounter() {
    const carrello = getCart();
    const counter = document.querySelector(".nav-cart span");
    if (counter) {
        counter.textContent = carrello.length;
    }
}

// Funzione per ottenere il carrello
function getCart() {
    return JSON.parse(localStorage.getItem("carrello")) || [];
}

// Funzione per aggiungere un prodotto al carrello
function aggiungiAlCarrello(nome, prezzo, immagine) {
    const carrello = getCart();
    
    // Controlla se il prodotto è già nel carrello
    const prodottoEsistente = carrello.find(item => 
        item.nome === nome && item.prezzo === prezzo && item.immagine === immagine
    );
    
    if (prodottoEsistente) {
        // Incrementa la quantità se esiste già
        prodottoEsistente.quantita = (prodottoEsistente.quantita || 1) + 1;
    } else {
        // Aggiungi nuovo prodotto con quantità 1
        carrello.push({nome, prezzo, immagine, quantita: 1});
    }
    
    localStorage.setItem("carrello", JSON.stringify(carrello));
    alert("Articolo aggiunto al carrello!");
    updateCartCounter();
}

// Funzione per svuotare il carrello
function svuotaCarrello() {
    localStorage.removeItem("carrello");
    location.reload();
}

// Funzione per calcolare il totale
function calcolaTotale() {
    const carrello = getCart();
    return carrello.reduce((totale, item) => {
        return totale + (item.prezzo * (item.quantita || 1));
    }, 0).toFixed(2);
}

// Mostra il carrello quando la pagina è caricata
document.addEventListener("DOMContentLoaded", () => {
    const container = document.getElementById("carrello-container");
    const carrello = getCart();
    
    if (carrello.length === 0) {
        container.innerHTML = "<p>Il carrello è vuoto.</p>";
    } else {
        let html = `
            <div class="carrello-header">
                <span>Prodotto</span>
                <span>Prezzo</span>
                <span>Quantità</span>
                <span>Totale</span>
            </div>
        `;
        
        carrello.forEach(item => {
            const totaleProdotto = (item.prezzo * (item.quantita || 1)).toFixed(2);
            html += `
                <div class="carrello-item">
                    <div class="carrello-item-img">
                        <img src="${item.immagine}" alt="${item.nome}">
                        <span>${item.nome}</span>
                    </div>
                    <div class="carrello-item-prezzo">€${item.prezzo.toFixed(2)}</div>
                    <div class="carrello-item-quantita">${item.quantita || 1}</div>
                    <div class="carrello-item-totale">€${totaleProdotto}</div>
                </div>
            `;
        });
        
        // Aggiungi il totale generale
        html += `
            <div class="carrello-totale">
                <strong>Totale: €${calcolaTotale()}</strong>
            </div>
        `;
        
        container.innerHTML = html;
    }
    
    updateCartCounter();
});
