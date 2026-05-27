import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta # 👈 Importamos herramientas de tiempo

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🧠 VARIABLES GLOBALES (La memoria de tu servidor en Render)
CACHE_TASA = None
CACHE_ULTIMA_ACTUALIZACION = None
TIEMPO_EXPIRACION = timedelta(minutes=30) # 👈 Definimos tu ventana de 30 minutos

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

@app.get("/v1/cotizaciones")
def obtener_cotizaciones():
    global CACHE_TASA, CACHE_ULTIMA_ACTUALIZACION
    
    ahora = datetime.now()
    
    # 🕵️ LÓGICA DE CONTROL DE TRÁFICO:
    # Si tenemos una tasa guardada Y no han pasado 30 minutos, entregamos el "colchón" al instante
    if CACHE_TASA and CACHE_ULTIMA_ACTUALIZACION and (ahora - CACHE_ULTIMA_ACTUALIZACION < TIEMPO_EXPIRACION):
        print("⚡ Entregando tasa desde la caché de Render (Cero consumo de recursos)")
        return [{"nombre": "Dólar", "promedio": CACHE_TASA}]
    
    # Si la caché no existe o ya expiró (pasaron los 30 min), mandamos al scraper a trabajar
    print("🌐 La caché expiró o está vacía. Buscando nueva tasa en el BCV...")
    nueva_tasa = scraping_bcv()
    
    if nueva_tasa:
        # Actualizamos la memoria del servidor con el nuevo valor y la hora actual
        CACHE_TASA = nueva_tasa
        CACHE_ULTIMA_ACTUALIZACION = ahora
        return [{"nombre": "Dólar", "promedio": CACHE_TASA}]
    else:
        # Si el BCV se cae, como plan de respaldo entregamos la última tasa vieja que tengamos guardada
        if CACHE_TASA:
            return [{"nombre": "Dólar", "promedio": CACHE_TASA}]
        return [{"nombre": "Dólar", "promedio": None}]
