import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    InvalidSessionIdException,
    WebDriverException,
    NoSuchElementException
)

import pandas as pd
import re
import time
from pathlib import Path

# =====================================================
# CONFIGURACIÓN MONEDA
# =====================================================

EXCHANGE_RATE_DOP_USD = 63.11

# =====================================================
# CATEGORIAS
# =====================================================

SEARCH_TERMS = {

    "Galletas": [
        "galletas",
        "galleta",
        "oreo",
        "wafer",
        "club social",
        "festival",
    ],

    "Tortillas": [
        "tortilla",
        "wrap",
        "burrito",
        "pita",
    ],

    "Panaderia": [
        "pan viga",
        "pan integral",
        "pan sandwich",
        "pan de hamburguesa",
        "pan de hot dog",
        "croissant",
        "bagel",
        "brioche",
        "flatbread","Pan Mini",
        "Pan Maxi",
        "Pan con macadamia",
        "Flat Bread",
    ],

    "Pasteleria": [
        "bizcocho",
        "cake",
        "brownie",
        "muffin",
        "cupcake",
    ]
}
# =====================================================
# MARCAS
# =====================================================

MARCAS = [

    # Galletas
    "Guarina", "Bravo", "Hatuey", "Aviva",
    "Dino", "Gamesa", "Oreos", "Oreo",
    "Club Social", "Colombina", "Princesa",
    "Gullon", "Wala", "Bocel", "Líder",
    "Choco Wow", "Nabisco", "Ritz",
    "Members Selection","Galleta Sandwich",
    "Galleta De Soda",

    # Tortillas / wraps
    "Maria", "María", "La Real",
    "Old El Paso", "Toufayan",
    "El Charrito", "Productos Charros",
    "Tortilla Factory", "Food Club",
    "Siete", "Joseph's", "Stonefire",

    # Panadería
    "Mi Trigo", "Molino del Sol",
    "Canyon", "Nature's Own",
    "Natures Own", "Bauducco",
    "Bauduco", "Bimbo", "Sara Lee",
    "Pepperidge Farm", "Arnold",
    "Wonder", "Martin's","Dulcesol",
    "Buenhorno","Atlanta",

    # Pastelería
    "Entenmann's", "Hostess",
    "Little Debbie", "Dulce",
    "Gold Selects", "La Panera",
    "Bakemate", "Royal Dansk",
    "Beautiful Denmark",

    # Otros
    "Qiin", "Best", "Crich",
    "Pirulin", "Ferrero",
    "Duetto", "Bergen",
    "Chips Ahoy", "YPM",
    
    # Mexico / Bakery / Tortillas
    "Tia Rosa",
    "Tía Rosa",
    "Sanissimo",
    "Saníssimo",
    "Mission",
    "Guerrero",

    # Bakery USA
    "Oroweat",
    "Thomas",
    "Brownberry",
    "Dave's Killer Bread",

    # Sweet Bakery
    "Bauducco","Hostess","Entenmann's","little debbie",
    

    # Healthy
    "Simple Mills",
    "Mary's Gone Crackers",
]

# =====================================================
# OUTPUT
# =====================================================

BASE_DIR = Path("/Users/mauriciogonzalez/Documents/caribbean_retail_ai")
OUTPUT_DIR = BASE_DIR / "outputs" / "rd"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = OUTPUT_DIR / "benchmark_rd_master.csv"
OUTPUT_XLSX = OUTPUT_DIR / "benchmark_rd_master.xlsx"

# =====================================================
# DRIVER
# =====================================================

def crear_driver(headless=True):

    driver_path = chromedriver_autoinstaller.install()

    options = Options()

    options.add_argument("--start-maximized")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--remote-debugging-port=9222")

    if headless:
        options.add_argument("--headless=new")

    driver = webdriver.Chrome(
        service=Service(driver_path),
        options=options
    )

    driver.set_page_load_timeout(45)

    return driver


def reiniciar_driver(driver):

    print("⚠️ Driver caído. Reiniciando Chrome...")

    try:
        driver.quit()
    except Exception:
        pass

    time.sleep(2)

    return crear_driver(headless=True)


def abrir_url(driver, url, espera=3, reintentos=2):
    

    for intento in range(1, reintentos + 1):

        try:
            driver.get(url)
            time.sleep(espera)
            return driver

        except (InvalidSessionIdException, WebDriverException) as e:

            print(f"⚠️ Error abriendo URL intento {intento}: {e}")
            driver = reiniciar_driver(driver)

    return driver


# =====================================================
# BUILD SEARCH URL
# =====================================================
def click_load_more(driver, max_clicks=10):

    for i in range(max_clicks):

        try:
            buttons = driver.find_elements(
                By.XPATH,
                "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚ', 'abcdefghijklmnopqrstuvwxyzáéíóú'), 'load more') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚ', 'abcdefghijklmnopqrstuvwxyzáéíóú'), 'mostrar más') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚ', 'abcdefghijklmnopqrstuvwxyzáéíóú'), 'mostrar mas') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚ', 'abcdefghijklmnopqrstuvwxyzáéíóú'), 'ver más') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚ', 'abcdefghijklmnopqrstuvwxyzáéíóú'), 'ver mas')]"
            )

            if not buttons:
                break

            button = buttons[-1]

            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});",
                button
            )

            time.sleep(1)

            driver.execute_script(
                "arguments[0].click();",
                button
            )

            time.sleep(3)

            print(f"Load more click: {i + 1}")

        except Exception as e:
            print(f"No more load more: {e}")
            break
        
def build_search_url(term):

    return (
        "https://supermercadosrd.com/explorar?q="
        + term.replace(" ", "+")
    )


# =====================================================
# FUNCIONES
# =====================================================

def extract_barcode(text):

    if not text:
        return None

    patterns = [
        r'"gtin13"\s*:\s*"?(\d+)"?',
        r'"gtin12"\s*:\s*"?(\d+)"?',
        r'"gtin14"\s*:\s*"?(\d+)"?',
        r'"gtin"\s*:\s*"?(\d+)"?',
        r'"ean"\s*:\s*"?(\d+)"?',
        r'"upc"\s*:\s*"?(\d+)"?',
        r'"barcode"\s*:\s*"?(\d+)"?',
        r'"sku"\s*:\s*"?(\d{8,14})"?',
        r'\b(\d{12})\b',
        r'\b(\d{13})\b',
        r'\b(\d{14})\b',
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return str(match.group(1))

    return None


def normalize_barcode(value):

    if pd.isna(value) or value is None:
        return None

    value = (
        str(value)
        .strip()
        .replace(".0", "")
    )

    if not value.isdigit():
        return None

    if len(value) == 11:
        return value.zfill(12)

    if len(value) in [12, 13, 14]:
        return value

    return value


def nombre_desde_url(url):

    partes = url.rstrip("/").split("/")

    if len(partes) >= 2:
        slug = partes[-2]
    else:
        slug = url

    return slug.replace("-", " ").title()


def detectar_marca(nombre):

    marcas_ordenadas = sorted(
        MARCAS,
        key=len,
        reverse=True
    )

    for marca in marcas_ordenadas:

        if re.search(
            rf"\b{re.escape(marca.lower())}\b",
            nombre.lower()
        ):
            return marca

    return "Other"


def es_categoria(nombre, keywords):

    n = nombre.lower()

    return any(k in n for k in keywords)


def presentacion(texto):

    patrones = [
        r"(\d+(?:\.\d+)?\s?OZ)",
        r"(\d+(?:\.\d+)?\s?GR)",
        r"(\d+(?:\.\d+)?\s?G)",
        r"(\d+(?:\.\d+)?\s?UND)",
        r"(\d+(?:\.\d+)?\s?UNIDADES)"
    ]

    for p in patrones:

        m = re.search(p, texto.upper())

        if m:
            return m.group(1)

    return "-"


def extract_weight_kg(pres):

    try:

        if pres == "-":
            return None

        texto = pres.upper().replace(",", ".")

        valor = float(
            re.findall(r"[\d.]+", texto)[0]
        )

        if "KG" in texto:
            return valor

        if "GR" in texto or (
            "G" in texto and "KG" not in texto
        ):
            return valor / 1000

        if "OZ" in texto:
            return valor * 0.0283495

        if "LB" in texto:
            return valor * 0.453592

        return None

    except Exception:
        return None


def precio_100g(precio, pres):

    try:

        pres = pres.upper().replace(",", ".")

        if "GR" in pres:

            gramos = float(
                re.findall(r"[\d.]+", pres)[0]
            )

        elif "G" in pres and "OZ" not in pres:

            gramos = float(
                re.findall(r"[\d.]+", pres)[0]
            )

        elif "OZ" in pres:

            oz = float(
                re.findall(r"[\d.]+", pres)[0]
            )

            gramos = oz * 28.3495

        else:
            return None

        if gramos <= 0:
            return None

        return round((precio / gramos) * 100, 2)

    except Exception:
        return None


def segmento(valor):

    if valor is None:
        return "N/A"

    if valor < 20:
        return "Value"

    if valor < 40:
        return "Mainstream"

    return "Premium"


def retailer_desde_href(href):

    if not href:
        return "N/A"

    h = href.lower()

    if "mercajumbo" in h:
        return "Merca Jumbo"

    if "jumbo" in h:
        return "Jumbo"

    if "sirena" in h:
        return "Sirena"

    if "bravo" in h or "superbravo" in h:
        return "Bravo"

    if "ritmo" in h:
        return "Ritmo"

    if "nacional" in h:
        return "Nacional"

    if "ole" in h:
        return "Ole"

    if "plazalama" in h or "plaza-lama" in h:
        return "Plaza Lama"

    if "garrido" in h:
        return "Garrido"

    return "N/A"

def es_exclusion(nombre):

    n = nombre.lower()

    exclusiones = [
        "cafe",
        "café",
        "molido",
        "bebida",
        "jugo",
        "arroz",
        "aceite",
        "detergente",
    ]

    return any(x in n for x in exclusiones)

def clasificar(nombre, categoria):

    n = nombre.lower()

    if categoria == "Galletas":

        if "wafer" in n or "waffer" in n:
            return "Wafer"

        if "sandwich" in n or "oreo" in n:
            return "Dulce Sandwich"

        if "soda" in n or "saltina" in n or "salada" in n:
            return "Salada"

        if (
            "integral" in n
            or "fibra" in n
            or "avena" in n
            or "linaza" in n
        ):
            return "Funcional"

        return "Galleta"

    if categoria == "Tortillas":

        if "wrap" in n:
            return "Wrap"

        if "maiz" in n or "maíz" in n:
            return "Maíz"

        if "trigo" in n:
            return "Trigo"

        if "low carb" in n or "keto" in n:
            return "Low Carb/Keto"

        return "Tortilla"

    if categoria == "Panaderia":

        if "bagel" in n:
            return "Bagel"

        if "pita" in n:
            return "Pita"

        if "naan" in n:
            return "Naan"

        if "brioche" in n:
            return "Brioche"

        return "Panadería"

    if categoria == "Pasteleria":

        if "brownie" in n:
            return "Brownie"

        if "muffin" in n:
            return "Muffin"

        if "cupcake" in n:
            return "Cupcake"

        return "Pastelería"

    return categoria

# =====================================================
# START
# =====================================================

print("\n===================================")
print(" BENCHMARK RD MASTER")
print("===================================\n")

driver = crear_driver(headless=True)

# =====================================================
# SCRAPING
# =====================================================

productos = []
seen_urls = set()

for categoria, terms in SEARCH_TERMS.items():

    print("\n===================================")
    print("CATEGORIA:", categoria)
    print("===================================")

    for term in terms:

        url = build_search_url(term)

        print(
            f"\nBUSQUEDA: "
            f"{categoria} | {term}"
        )

        driver = abrir_url(
            driver,
            url,
            espera=3
        )
        click_load_more(driver)
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
        )
        
        time.sleep(2)

        links = driver.find_elements(
            By.XPATH,
            "//a[contains(@href,'/productos/')]"
        )   
    

        productos_links = set()
    
        for link in links:
    
            href = link.get_attribute("href")
    
            if href and "/productos/" in href:
                productos_links.add(href)
    
        productos_links = sorted(productos_links)
    
        print("Productos encontrados:", len(productos_links))

        # =================================================
    
        for idx, link in enumerate(productos_links):
            if link in seen_urls:
                continue
            
            seen_urls.add(link)
                
            try:
    
                print(f"\n[{idx + 1}/{len(productos_links)}] {link}")
    
                driver = abrir_url(
                    driver,
                    link,
                    espera=2
                )
    
                try:
    
                    html = driver.page_source
    
                    texto = driver.find_element(
                        By.TAG_NAME,
                        "body"
                    ).text
    
                except (
                    InvalidSessionIdException,
                    WebDriverException
                ):
    
                    driver = reiniciar_driver(driver)
    
                    driver = abrir_url(
                        driver,
                        link,
                        espera=2
                    )
    
                    html = driver.page_source
    
                    texto = driver.find_element(
                        By.TAG_NAME,
                        "body"
                    ).text
    
                barcode = normalize_barcode(
                    extract_barcode(html)
                )
    
                try:
                
                    nombre = driver.find_element(
                        By.TAG_NAME,
                        "h1"
                    ).text.strip()
                
                except Exception:
                
                    nombre = nombre_desde_url(link)
    
                pres = presentacion(nombre)
    
                lineas = [
                    x.strip()
                    for x in texto.splitlines()
                    if x.strip()
                ]
    
                for linea in lineas:
    
                    p = presentacion(linea)
    
                    if p != "-":
                        pres = p
                        break
    
                if not es_categoria(nombre, terms) or es_exclusion(nombre):
    
                    print("NO ES CATEGORIA:", nombre)
    
                    continue
    
                marca = detectar_marca(nombre)
    
                tipo = clasificar(
                    nombre,
                    categoria
                )
    
                weight_kg = extract_weight_kg(pres)
    
                print("PRODUCTO:", nombre)
                print("PRESENTACIÓN:", pres)
    
                if barcode:
                    print("BARCODE:", barcode)
    
                botones = driver.find_elements(
                    By.XPATH,
                    "//*[contains(text(), 'Buscar')]"
                )
    
                if not botones:
    
                    print("SIN BOTONES")
    
                    continue
    
                for boton in botones:
    
                    try:
    
                        href_retailer = boton.get_attribute("href")
    
                        retailer = retailer_desde_href(
                            href_retailer
                        )
    
                        try:
    
                            card = boton.find_element(
                                By.XPATH,
                                "./ancestor::div[contains(@class,'grid')][1]"
                            )
    
                        except NoSuchElementException:
    
                            card = boton.find_element(
                                By.XPATH,
                                "./ancestor::div[1]"
                            )
    
                        card_text = card.text
    
                        precios = re.findall(
                            r"RD\$ ?([\d,.]+)",
                            card_text
                        )
    
                        if not precios:
                            continue
    
                        precio_rd = float(
                            precios[0].replace(",", "")
                        )
    
                        precio_100g_rd = precio_100g(
                            precio_rd,
                            pres
                        )
    
                        # =================================================
                        # CONVERSIONES USD
                        # =================================================
    
                        precio_usd = round(
                            precio_rd / EXCHANGE_RATE_DOP_USD,
                            2
                        )
    
                        precio_kg_usd = None
    
                        if precio_100g_rd is not None:
    
                            precio_kg_rd = (
                                precio_100g_rd * 10
                            )
    
                            precio_kg_usd = round(
                                precio_kg_rd / EXCHANGE_RATE_DOP_USD,
                                2
                            )
    
                        productos.append({
                            "search_term": term,
                            # Regional standard
                            "country": "Dominican Republic",
                            "currency": "DOP",
    
                            # Core fields
                            "category": categoria,
                            "source_category": categoria,
                            "retailer": retailer,
                            "brand": marca,
                            "product_name": nombre,
    
                            # SKU Identity
                            "barcode": barcode,
                            "barcode_length": (
                                len(barcode)
                                if barcode
                                else None
                            ),
    
                            # Pricing
                            "price_local": precio_rd,
                            "price_usd": precio_usd,
    
                            # Weight
                            "presentation": pres,
                            "weight_kg": weight_kg,
    
                            # Price architecture
                            "price_per_100g_local": precio_100g_rd,
                            "price_per_kg_usd": precio_kg_usd,
    
                            # Strategic fields
                            "segment": segmento(
                                precio_100g_rd
                            ),
    
                            "type": tipo,
    
                            # URLs
                            "product_url": link,
                            "retailer_url": href_retailer
                        })
    
                        print(
                            "OK:",
                            retailer,
                            "| RD$",
                            precio_rd,
                            "| USD",
                            precio_usd
                        )
    
                    except Exception as e:
    
                        print("ERROR CARD:", e)
    
            except Exception as e:
    
                print("ERROR PRODUCTO:", e)

# =====================================================
# CLOSE DRIVER
# =====================================================

try:
    driver.quit()
except Exception:
    pass

# =====================================================
# DATAFRAME
# =====================================================

df = pd.DataFrame(productos)

if not df.empty and "barcode" in df.columns:

    df["barcode"] = (
        df["barcode"]
        .apply(normalize_barcode)
    )

    df["barcode_length"] = (
        df["barcode"]
        .astype("string")
        .str.len()
    )

df = df.drop_duplicates()

# =====================================================
# RESUMENES
# =====================================================

if not df.empty:

    df = df.sort_values(
        by=[
            "category",
            "product_name",
            "retailer",
            "price_local"
        ]
    )

    dispersion = (
        df.groupby([
            "category",
            "product_name"
        ])
        .agg(
            Precio_Min=("price_local", "min"),
            Precio_Max=("price_local", "max"),
            Retailers=("retailer", "nunique"),
            Conteo_Precios=("price_local", "count")
        )
        .reset_index()
    )

    dispersion["Gap %"] = round(
        (
            (
                dispersion["Precio_Max"]
                -
                dispersion["Precio_Min"]
            )
            /
            dispersion["Precio_Min"]
        ) * 100,
        1
    )

    resumen_retailer = (
        df.groupby([
            "category",
            "retailer"
        ])
        .agg(
            Registros=("product_name", "count"),
            Productos=("product_name", "nunique"),
            Precio_Promedio_Local=("price_local", "mean"),
            Precio_Promedio_USD=("price_usd", "mean")
        )
        .reset_index()
    )

    resumen_retailer[
        "Precio_Promedio_Local"
    ] = round(
        resumen_retailer[
            "Precio_Promedio_Local"
        ],
        2
    )

    resumen_retailer[
        "Precio_Promedio_USD"
    ] = round(
        resumen_retailer[
            "Precio_Promedio_USD"
        ],
        2
    )

else:

    dispersion = pd.DataFrame()

    resumen_retailer = pd.DataFrame()

# =====================================================
# EXPORT
# =====================================================

df.to_csv(
    OUTPUT_CSV,
    index=False,
    encoding="utf-8-sig"
)

with pd.ExcelWriter(
    OUTPUT_XLSX,
    engine="openpyxl"
) as writer:

    df.to_excel(
        writer,
        sheet_name="raw_data",
        index=False
    )

    dispersion.to_excel(
        writer,
        sheet_name="dispersion",
        index=False
    )

    resumen_retailer.to_excel(
        writer,
        sheet_name="retailers",
        index=False
    )

# =====================================================
# OUTPUT
# =====================================================

print("\n===================================")
print(" EXPORT COMPLETADO")
print("===================================\n")

print("CSV :", OUTPUT_CSV)
print("XLSX:", OUTPUT_XLSX)
print("Total registros:", len(df))

if not df.empty:

    print("\nRegistros por categoría:")
    print(df["category"].value_counts())

    print("\nRetailers encontrados:")
    print(df["retailer"].value_counts())

    print("\nPrecio promedio USD:")
    print(
        round(
            df["price_usd"].mean(),
            2
        )
    )

    if "barcode" in df.columns:

        print("\nBarcodes encontrados:")
        print(
            df["barcode"]
            .notna()
            .sum()
        )

        print("\nDistribución barcode_length:")
        print(
            df["barcode_length"]
            .value_counts(dropna=False)
        )
