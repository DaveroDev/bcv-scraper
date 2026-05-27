import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Permitir conexiones desde cualquier origen (esencial para que Android no lo bloquee)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def scraping_bcv():
    url = "https://www.bcv.org.ve/"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0"
    }
    try:
        respuesta = requests.get(url, headers=headers, verify=False, timeout=15)
        if respuesta.status_code == 200:
            soup = BeautifulSoup(respuesta.text, 'lxml')
            bloque_dolar = soup.find(id="dolar")
            if bloque_dolar:
                elemento_tasa = bloque_dolar.find("strong", class_="strong-tb")
                if elemento_tasa:
                    tasa_sucia = elemento_tasa.text.strip()
                    tasa_limpia = tasa_sucia.replace(',', '.')
                    return float(tasa_limpia)
    except Exception as e:
        print(f"Error en scraping: {e}")
    return None

# Creamos la ruta que consultará la aplicación de Android
@app.get("/v1/cotizaciones")
def obtener_cotizaciones():
    tasa = scraping_bcv()
    
    if tasa:
        # Devolvemos exactamente la estructura que tu Android Studio procesa actualmente
        return [
            {
                "nombre": "Dólar",
                "promedio": tasa
            }
        ]
    else:
        return [{"nombre": "Dólar", "promedio": None}]
