import mysql.connector
from fastapi import FastAPI, Form, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import hashlib
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import json
from pydantic import BaseModel
app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key="ciao")
template = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Funzioni di connessione al database e altre funzioni di utilità (come prima)
def connessione():
    conn = mysql.connector.connect(
        host='192.168.3.92',
        user='admquintaainfo',
        password='admquintaainfo',
        database='supermercato'
    )
    return conn

def PassHash(password):
    return hashlib.sha256(password.encode()).hexdigest()

def confrontoPass(DbPass, InputPass):
    return DbPass == PassHash(InputPass)

def invia_email(destinatario, codice):
    sender_email = "patadmpatberna@gmail.com"
    password = "rmem vklz zcrp lxsy"
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    subject = "Codice di verifica per cambio password"
    body = f"Il tuo codice di verifica per cambiare la password è: {codice}"

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = destinatario
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, password)
        text = msg.as_string()
        server.sendmail(sender_email, destinatario, text)
        server.quit()
    except Exception as e:
        print(f"Errore nell'invio dell'email: {e}")


@app.get("/")
def root():
    return RedirectResponse(url="/loginRegister")

@app.get("/inviaCodice", response_class=HTMLResponse)
def IcPage(request: Request):
    return template.TemplateResponse("inviaCodice.html", {"request": request})

@app.get("/cambiaPass", response_class=HTMLResponse)
def CpPage(request: Request):
    return template.TemplateResponse("cambiaPass.html", {"request": request})

@app.get("/admin_dashboard", response_class=HTMLResponse)
def Dash_Page(request: Request):
    return template.TemplateResponse("admin_dashboard.html", {"request": request})

@app.get("/loginRegister", response_class=HTMLResponse)
def loginPage(request: Request):
    return template.TemplateResponse("loginRegister.html", {"request": request})

@app.post("/loginRegister")
def login_register(request: Request,
                         username: str = Form(...),
                         password: str = Form(...),
                         email: str = Form(None)):
    conn = connessione()
    cursor = conn.cursor()

    if email is None:  # Login
        try:
            query = "SELECT * FROM utenti WHERE username = %s"
            cursor.execute(query, (username,))
            tupla = cursor.fetchone()
            
            if tupla is None or not confrontoPass(tupla[3], password):
                return template.TemplateResponse("loginRegister.html", 
                    {"request": request, "error": "Credenziali non valide"})

            # Memorizza l'utente in sessione
            request.session['user_id'] = tupla[0]
            request.session['username'] = tupla[1]
            request.session['role'] = tupla[4]

            # Reindirizzamento basato sul ruolo
            role_redirects = {
                "cliente": "/user_dashboard",
                "dipendente": "/dipendente_dashboard",
                "fornitore": "/fornitore_dashboard",
                "admin": "/admin_dashboard"
            }

            if tupla[4] in role_redirects:
                return RedirectResponse(
                    url=role_redirects[tupla[4]], 
                    status_code=303)
            
            return template.TemplateResponse("loginRegister.html", 
                {"request": request, "error": "Ruolo non valido"})

        finally:
            cursor.close()
            conn.close()

    else:
        try:
            cursor.execute("SELECT * FROM utenti WHERE email = %s", (email,))
            if cursor.fetchone():
                return template.TemplateResponse("loginRegister.html", {"request": request, "error": "Email già registrata"})

            cursor.execute("SELECT * FROM utenti WHERE username = %s", (username,))
            if cursor.fetchone():
                return template.TemplateResponse("loginRegister.html", {"request": request, "error": "Username già esistente"})

            hashed_password = PassHash(password)
            cursor.execute("INSERT INTO utenti (username, email, password, ruolo) VALUES (%s, %s, %s, %s)", (username, email, hashed_password, 'cliente'))
            conn.commit()

            return template.TemplateResponse("loginRegister.html", {"request": request, "success": f"{username} registrato con successo"})

        except Exception as e:
            conn.rollback()
            return template.TemplateResponse("loginRegister.html", {"request": request, "error": f"Errore durante la registrazione: {str(e)}"})

        finally:
            cursor.close()
            conn.close()

@app.get("/user_dashboard", response_class=HTMLResponse)
def loginPage(request: Request):
    return template.TemplateResponse("user_dashboard.html", {"request": request})

@app.post("/inviaCodice")
def invia_codice(request: Request, email: str = Form(...)):
    conn = connessione()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM utenti WHERE email = %s", (email,))
        utente = cursor.fetchone()
        if utente is None:
            return template.TemplateResponse("inviaCodice.html", {"request": request, "error": "Email non trovata"})

        codice = str(random.randint(100000, 999999))
        scadenza = datetime.now() + timedelta(minutes=10)

        request.session['codice'] = codice
        request.session['scadenza'] = scadenza.isoformat()

        invia_email(email, codice)
        return RedirectResponse("/cambiaPass", status_code=303)

    finally:
        cursor.close()
        conn.close()

@app.post("/cambiaPass")
def cambia_password(request: Request, email: str = Form(...), codice: str = Form(...), new_password: str = Form(...)):
    conn = connessione()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM utenti WHERE email = %s", (email,))
        utente = cursor.fetchone()
        if utente is None:
            return template.TemplateResponse("cambiaPass.html", {"request": request, "error": "Email non trovata"})

        codice_salvato = request.session.get('codice')
        scadenza_str = request.session.get('scadenza')

        if not codice_salvato or not scadenza_str:
            return template.TemplateResponse("cambiaPass.html", {"request": request, "error": "Codice non inviato o sessione scaduta."})

        scadenza = datetime.fromisoformat(scadenza_str)

        if codice != codice_salvato:
            return template.TemplateResponse("cambiaPass.html", {"request": request, "error": "Codice errato"})
        if datetime.now() > scadenza:
            return template.TemplateResponse("cambiaPass.html", {"request": request, "error": "Il codice è scaduto"})

        hashed_password = PassHash(new_password)
        cursor.execute("UPDATE utenti SET password = %s WHERE email = %s", (hashed_password, email))
        conn.commit()

        del request.session['codice']
        del request.session['scadenza']

        return template.TemplateResponse("cambiaPass.html", {"request": request, "success": "Password cambiata con successo"})

    finally:
        cursor.close()
        conn.close()

@app.post("/admin_dashboard")
def aggiungi_utente(request: Request,
                    new_username: str = Form(...),
                    new_email: str = Form(...),
                    new_password: str = Form(...),
                    new_role: str = Form(...)):
    conn = connessione()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM utenti WHERE username = %s", (new_username,))
        if cursor.fetchone():
            return template.TemplateResponse("admin_dashboard.html", {"request": request, "error": "Username già esistente"})

        cursor.execute("SELECT * FROM utenti WHERE email = %s", (new_email,))
        if cursor.fetchone():
            return template.TemplateResponse("admin_dashboard.html", {"request": request, "error": "Email già registrata"})

        hashed_password = PassHash(new_password)

        cursor.execute("INSERT INTO utenti (username, email, password, ruolo) VALUES (%s, %s, %s, %s)",
                       (new_username, new_email, hashed_password, new_role))
        conn.commit()

        return RedirectResponse(url="/admin_dashboard", status_code=303)

    except Exception as e:
        conn.rollback()
        return template.TemplateResponse("admin_dashboard.html", {"request": request, "error": f"Errore durante l'aggiunta dell'utente: {str(e)}"})

    finally:
        cursor.close()
        conn.close()

@app.get("/admin_dashboard/{role}")
def get_users_by_role(role: str):
    conn = connessione()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT username, email, password, ruolo as ruolo FROM utenti WHERE ruolo = %s", (role,))
        users = cursor.fetchall()
        return {"users": users}
    finally:
        cursor.close()
        conn.close()

@app.get("/admin_dashboard/edit/{username}")
def edit_user_page(request: Request, username: str):
    conn = connessione()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM utenti WHERE username = %s", (username,))
        user = cursor.fetchone()
        if not user:
            return RedirectResponse(url="/admin_dashboard")
        return template.TemplateResponse("admin_dashboard.html", {"request": request, "user": user})
    finally:
        cursor.close()
        conn.close()

@app.post("/admin_dashboard/update/{username}")
def update_user(request: Request, username: str,
                new_username: str = Form(...),
                new_email: str = Form(...),
                new_role: str = Form(...)):
    conn = connessione()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE utenti SET username = %s, email = %s, ruolo = %s WHERE username = %s",
                       (new_username, new_email, new_role, username))
        conn.commit()
        return RedirectResponse(url="/admin_dashboard", status_code=303)
    except Exception as e:
        conn.rollback()
        return template.TemplateResponse("admin_dashboard.html", {"request": request, "error": f"Errore durante l'aggiornamento: {str(e)}"})
    finally:
        cursor.close()
        conn.close()

@app.get("/admin_dashboard/delete/{username}")
def delete_user(username: str):
    conn = connessione()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM utenti WHERE username = %s", (username,))
        conn.commit()
        return RedirectResponse(url="/admin_dashboard", status_code=303)
    except Exception as e:
        conn.rollback()
        return template.TemplateResponse("admin_dashboard.html", {"request": request, "error": f"Errore durante l'aggiunta dell'utente: {str(e)}"})
    finally:
        cursor.close()
        conn.close()

@app.get("/hot_products.html", response_class=HTMLResponse)
def hot_products(request: Request):
    return template.TemplateResponse("hot_products.html", {"request": request})

@app.get("/carrello.html", response_class=HTMLResponse)
def carrello(request: Request):
    context = {
        "request": request,
        "static_url": "/static",  # Aggiungi questo
        "carrello_items": request.session.get("carrello", [])  # Passa i dati del carrello
    }
    return template.TemplateResponse("carrello.html", context)



# -------------------------------------------------------------------------------------
# CARRELLO 
# -------------------------------------------------------------------------------------
def get_carrello(request: Request) -> list:
    """Recupera il carrello dalla sessione."""
    return request.session.get("carrello", [])

def update_carrello(request: Request, carrello: list):
    """Aggiorna il carrello nella sessione."""
    request.session["carrello"] = carrello
    
@app.post("/carrello/aggiorna/{prodotto_id}")
async def aggiorna_quantita_carrello(request: Request, prodotto_id: int, quantita: int = Form(...)):
    """Aggiorna la quantità di un prodotto nel carrello."""
    carrello = get_carrello(request)
    
    # Cerca il prodotto nel carrello
    prodotto_trovato = False
    for item in carrello:
        if item['id'] == prodotto_id:
            if quantita > 0:
                item['quantita'] = quantita
            else:
                carrello.remove(item)
            prodotto_trovato = True
            break
    
    if not prodotto_trovato:
        raise HTTPException(status_code=404, detail="Prodotto non trovato nel carrello")
    
    update_carrello(request, carrello)
    return RedirectResponse(url="/carrello", status_code=303)

@app.post("/carrello/rimuovi/{prodotto_id}")
async def rimuovi_dal_carrello(request: Request, prodotto_id: int):
    """Rimuove completamente un prodotto dal carrello."""
    carrello = get_carrello(request)
    nuovo_carrello = [item for item in carrello if item['id'] != prodotto_id]
    
    if len(nuovo_carrello) == len(carrello):
        raise HTTPException(status_code=404, detail="Prodotto non trovato nel carrello")
    
    update_carrello(request, nuovo_carrello)
    return RedirectResponse(url="/carrello", status_code=303)

@app.get("/carrello/totale")
async def calcola_totale(request: Request):
    """Calcola il totale del carrello."""
    carrello = get_carrello(request)
    totale = sum(item['prezzo'] * item['quantita'] for item in carrello)
    return {"totale": totale}

@app.post("/carrello/svuota")
async def svuota_carrello(request: Request):
    """Svuota completamente il carrello."""
    update_carrello(request, [])
    return {"message": "Carrello svuotato con successo"}

# -------------------------------------------------------------------------------------
# CHECKOUT E ORDINI
# -------------------------------------------------------------------------------------

class OrdineCreate(BaseModel):
    indirizzo: str
    note: Optional[str] = None

@app.post("/ordine/crea")
async def crea_ordine(request: Request, ordine_data: OrdineCreate):
    """Crea un nuovo ordine dal contenuto del carrello."""
    carrello = get_carrello(request)
    
    if not carrello:
        raise HTTPException(status_code=400, detail="Il carrello è vuoto")
    
    conn = connessione()
    cursor = conn.cursor()
    
    try:
        # Creazione ordine
        cursor.execute(
            "INSERT INTO ordini (utente_id, indirizzo, note, stato) VALUES (%s, %s, %s, 'in_attesa')",
            (request.session.get('user_id'), ordine_data.indirizzo, ordine_data.note)
        )
        ordine_id = cursor.lastrowid
        
        # Aggiungi prodotti all'ordine
        for item in carrello:
            cursor.execute(
                """INSERT INTO ordine_prodotti 
                (ordine_id, prodotto_id, quantita, prezzo_unitario) 
                VALUES (%s, %s, %s, %s)""",
                (ordine_id, item['id'], item['quantita'], item['prezzo'])
            )
        
        # Svuota carrello
        update_carrello(request, [])
        conn.commit()
        
        return {
            "message": "Ordine creato con successo",
            "ordine_id": ordine_id,
            "totale": sum(item['prezzo'] * item['quantita'] for item in carrello)
        }
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Errore durante la creazione dell'ordine: {str(e)}")
    
    finally:
        cursor.close()
        conn.close()