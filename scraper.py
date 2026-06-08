import os
import asyncio  
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
# 🛡️ IMPORTACIONES PARA LA SEGURIDAD ANTI-SPAM
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Inicializamos el limitador basado en la IP del teléfono que hace la consulta
limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
TIEMPO_EXPIRACION = timedelta(minutes=15)

# 🛡️ ESCUDO ANTI-ESTAMPIDA (Request Collapsing)
SCRAPING_EN_CURSO = False
LOCK_CONCURRENCIA = asyncio.Lock()

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

# 🔒 Añadimos el decorador '@limiter.limit'. Máximo 5 peticiones por minuto por IP.
@app.get("/v1/cotizaciones")
@limiter.limit("5/minute")
async def obtener_cotizaciones(
    request: Request,
    x_app_token: str = Header(None, alias="x-app-token")
):  
    global CACHE_TASAS, CACHE_ULTIMA_ACTUALIZACION, SCRAPING_EN_CURSO

    TOKEN_SECRETO_REQUERIDO = os.getenv("API_SECRET_TOKEN", "")
    
    # Si el token enviado por la app no coincide con el guardado...
    if not x_app_token or x_app_token != TOKEN_SECRETO_REQUERIDO:
        raise HTTPException(
            status_code=401, 
            detail="Acceso no autorizado."
        )
    
    ahora = datetime.now()
    
    # 1. Si la caché está fresca, responder volando
    if CACHE_TASAS and CACHE_ULTIMA_ACTUALIZACION and (ahora - CACHE_ULTIMA_ACTUALIZACION < TIEMPO_EXPIRACION):
        print("⚡ Entregando tasas desde la caché de Render (Dólar y Euro)")
        return [
            {"nombre": "Dólar", "promedio": CACHE_TASAS.get("Dólar")},
            {"nombre": "Euro", "promedio": CACHE_TASAS.get("Euro")}
        ]
    
    # 2. Si la caché expiró pero YA HAY otra solicitud raspando el BCV...
    if SCRAPING_EN_CURSO:
        print("⏳ Estampida detectada: Esta petición esperará en cola el resultado del scraper en curso...")
        while SCRAPING_EN_CURSO:
            await asyncio.sleep(0.2)  # Duerme asíncronamente 200ms y vuelve a chequear
        
        # Una vez que la petición líder termina, las demás consumen la caché recién actualizada
        if CACHE_TASAS:
            print("📦 Cola liberada. Entregando la nueva caché generada por el hilo líder.")
            return [
                {"nombre": "Dólar", "promedio": CACHE_TASAS.get("Dólar")},
                {"nombre": "Euro", "promedio": CACHE_TASAS.get("Euro")}
            ]

    # 3. Si nadie está haciendo scraping, esta petición toma el control y bloquea el paso
    async with LOCK_CONCURRENCIA:
        SCRAPING_EN_CURSO = True

    try:
        print("🌐 La caché expiró o está vacía. Buscando nuevas tasas en el BCV...")
        nuevas_tasas = raspar_tasas_bcv()
        
        if nuevas_tasas:
            CACHE_TASAS = nuevas_tasas
            CACHE_ULTIMA_ACTUALIZACION = datetime.now()
        
        if not nuevas_tasas and CACHE_TASAS:
            print("⚠️ Falló el scraping. Usando respaldo de la caché global.")
            nuevas_tasas = CACHE_TASAS

    finally:
        # Pase lo que pase (éxito o error fatal), liberamos la bandera para los que esperan en la cola
        SCRAPING_EN_CURSO = False

    if not nuevas_tasas:
        raise HTTPException(status_code=502, detail="No se pudieron obtener las cotizaciones del BCV")

    respuesta_json = [
        {"nombre": "Dólar", "promedio": nuevas_tasas.get("Dólar")},
        {"nombre": "Euro", "promedio": nuevas_tasas.get("Euro")}
    ]
    return respuesta_json
