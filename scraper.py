import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException

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
TIEMPO_EXPIRACION = timedelta(minutes=30) # Definimos ventana de 30 minutos

def scraping_bcv():
=======
def raspar_tasas_bcv():
>>>>>>> 7dc5034 (Backend: Añadido soporte para extraer Dólar y Euro del BCV)
    url = "https://www.bcv.org.ve/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        # Hacemos la petición desactivando la verificación SSL estricta por si el BCV tiene problemas de certificado
        respuesta = requests.get(url, headers=headers, verify=False, timeout=15)
        if respuesta.status_code != 200:
            raise HTTPException(status_code=502, detail="No se pudo acceder a la página del BCV")
            
        soup = BeautifulSoup(respuesta.text, 'lxml')
        
        # Diccionario para almacenar los resultados limpios
        tasas = {}
        
        # Lista de las monedas que queremos buscar y sus IDs correspondientes en el HTML del BCV
        monedas_a_buscar = {
            "Dólar": "dolar",
            "Euro": "euro"
        }
        
        for nombre, id_html in monedas_a_buscar.items():
            bloque_moneda = soup.find(id=id_html)
            if bloque_moneda:
                elemento_tasa = bloque_moneda.find("strong", class_="strong-tb")
                if elemento_tasa:
                    # Limpiamos el texto, cambiamos comas por puntos y lo convertimos a float
                    tasa_limpia = elemento_tasa.text.strip().replace(',', '.')
                    tasas[nombre] = float(tasa_limpia)
            
        # Si por alguna razón no se extrajo ninguna tasa, lanzamos error
        if not tasas:
            raise HTTPException(status_code=500, detail="Error al formatear los datos del BCV")
            
        return tasas

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el scraper: {str(e)}")

@app.get("/v1/cotizaciones")
def obtener_cotizaciones():
    diccionario_tasas = raspar_tasas_bcv()
    
<<<<<<< HEAD
    ahora = datetime.now()
    
    # 🕵️ LÓGICA DE CONTROL DE TRÁFICO:
    # Si tenemos una tasa guardada Y no han pasado 30 minutos, entregamos el respaldo que es la ultima tasa al instante
    if CACHE_TASA and CACHE_ULTIMA_ACTUALIZACION and (ahora - CACHE_ULTIMA_ACTUALIZACION < TIEMPO_EXPIRACION):
        print("⚡ Entregando tasa desde la caché de Render (Cero consumo de recursos)")
        return [{"nombre": "Dólar", "promedio": CACHE_TASA}]
    
    # Si la caché no existe o ya expiró (pasaron los 30 min), mandar al scraper a trabajar
    print("🌐 La caché expiró o está vacía. Buscando nueva tasa en el BCV...")
    nueva_tasa = scraping_bcv()
    
    if nueva_tasa:
        # Actualizar la memoria del servidor con el nuevo valor y la hora actual
        CACHE_TASA = nueva_tasa
        CACHE_ULTIMA_ACTUALIZACION = ahora
        return [{"nombre": "Dólar", "promedio": CACHE_TASA}]
    else:
        # Si el BCV se cae, como plan de respaldo entrega la última tasa vieja que tengamos guardada
        if CACHE_TASA:
            return [{"nombre": "Dólar", "promedio": CACHE_TASA}]
        return [{"nombre": "Dólar", "promedio": None}]
=======
    # Formateamos la respuesta como una lista de objetos para que Android la lea fácilmente
    respuesta_json = [
        {"nombre": "Dólar", "promedio": diccionario_tasas.get("Dólar")},
        {"nombre": "Euro", "promedio": diccionario_tasas.get("Euro")}
    ]
    return respuesta_json
>>>>>>> 7dc5034 (Backend: Añadido soporte para extraer Dólar y Euro del BCV)
