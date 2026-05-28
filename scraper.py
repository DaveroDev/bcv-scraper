from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🧠 VARIABLES GLOBALES (La memoria de tu servidor en Render)
CACHE_TASAS = None
CACHE_ULTIMA_ACTUALIZACION = None
TIEMPO_EXPIRACION = timedelta(minutes=30)  # Ventana de 30 minutos

def raspar_tasas_bcv():
    url = "https://www.bcv.org.ve/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        respuesta = requests.get(url, headers=headers, verify=False, timeout=15)
        if respuesta.status_code != 200:
            return None
            
        soup = BeautifulSoup(respuesta.text, 'lxml')
        tasas = {}
        
        monedas_a_buscar = {
            "Dólar": "dolar",
            "Euro": "euro"
        }
        
        for nombre, id_html in monedas_a_buscar.items():
            bloque_moneda = soup.find(id=id_html)
            if bloque_moneda:
                elemento_tasa = bloque_moneda.find("strong", class_="strong-tb")
                if elemento_tasa:
                    tasa_limpia = elemento_tasa.text.strip().replace(',', '.')
                    tasas[nombre] = float(tasa_limpia)
            
        return tasas if tasas else None

    except Exception:
        return None

@app.get("/v1/cotizaciones")
def obtener_cotizaciones():
    global CACHE_TASAS, CACHE_ULTIMA_ACTUALIZACION
    
    ahora = datetime.now()
    
    # 🕵️ LÓGICA DE CONTROL DE TRÁFICO (CACHÉ EN RENDER):
    if CACHE_TASAS and CACHE_ULTIMA_ACTUALIZACION and (ahora - CACHE_ULTIMA_ACTUALIZACION < TIEMPO_EXPIRACION):
        print("⚡ Entregando tasas desde la caché de Render (Dólar y Euro)")
        return [
            {"nombre": "Dólar", "promedio": CACHE_TASAS.get("Dólar")},
            {"nombre": "Euro", "promedio": CACHE_TASAS.get("Euro")}
        ]
    
    print("🌐 La caché expiró o está vacía. Buscando nuevas tasas en el BCV...")
    nuevas_tasas = raspar_tasas_bcv()
    
    if nuevas_tasas:
        CACHE_TASAS = nuevas_tasas
        CACHE_ULTIMA_ACTUALIZACION = ahora
    
    if not nuevas_tasas and CACHE_TASAS:
        print("⚠️ Falló el scraping. Usando respaldo de la caché global.")
        nuevas_tasas = CACHE_TASAS

    if not nuevas_tasas:
        raise HTTPException(status_code=502, detail="No se pudieron obtener las cotizaciones del BCV")

    respuesta_json = [
        {"nombre": "Dólar", "promedio": nuevas_tasas.get("Dólar")},
        {"nombre": "Euro", "promedio": nuevas_tasas.get("Euro")}
    ]
    return respuesta_json
