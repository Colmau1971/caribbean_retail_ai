import re
import pandas as pd


PRODUCT_DICTIONARY = {

    "oreo_original": [
        "oreo original",
        "galletas oreo original",
        "oreo cookies original",
    ],

    "oreo_chocolate": [
        "oreo chocolate",
        "galletas de chocolate oreo",
        "oreo chocolate cookies",
    ],

    "oreo_vanilla": [
        "oreo vanilla",
        "oreo golden vanilla",
        "galletas de vainilla oreo",
    ],

    "pringles_sour_cream_onion": [
        "pringles sour cream onion",
        "pringles sour cream & onion",
        "pringles sour cream and onion",
        "pringles s cream onion",
    ],

    "pringles_cheddar": [
        "pringles cheddar",
        "pringles cheddar cheese",
    ],

    "pringles_pizza": [
        "pringles pizza",
    ],

    "ritz_original": [
        "ritz",
        "galleta ritz",
        "ritz crackers",
    ],

    "chips_ahoy_original": [
        "chips ahoy",
        "galletas chips ahoy",
        "chips ahoy cookies",
    ],

    "bauducco_wafer_chocolate": [
        "bauducco wafer chocolate",
        "galletas wafer chocolate bauducco",
        "wafer bauducco chocolate",
    ],

    "bauducco_wafer_vanilla": [
        "bauducco wafer vanilla",
        "wafer bauducco vanilla",
    ],

    "festival_strawberry": [
        "festival strawberry",
        "noel festival strawberry",
        "festival fresa",
    ],

    "toufayan_bagels": [
        "toufayan bagels",
        "bagels toufayan",
    ],

    "club_social_original": [
        "club social original",
        "galletas club social original",
        "galleta integral multicereal club social",
    ],

    "club_social_integral": [
        "club social integral",
        "galleta integral club social",
        "galletas integrales club social",
    ],

    "guarina_leche": [
        "galletas de leche guarina",
        "guarina leche",
    ],

    "guarina_saladitas": [
        "galletas saladitas guarina",
        "saladitas guarina",
    ],

    "guarina_club_max_queso": [
        "guarina club max queso",
        "galletas saladas guarina club max queso",
    ],

    "dino_chocolate": [
        "dino galleta sandwich chocolate",
        "galleta sandwich chocolate dino",
    ],

    "dino_vainilla": [
        "dino galleta sandwich vainilla",
        "galleta sandwich vainilla dino",
    ],

    "dino_duplex": [
        "dino galleta sandwich duplex",
        "galleta sandwich duplex dino",
    ],

    "gamesa_chokis": [
        "galleta mini chokis gamesa",
        "galletas chokis",
        "chokis gamesa",
    ],

    "gamesa_emperador_chocolate": [
        "galleta de chocolate gamesa emperador",
        "emperador chocolate gamesa",
    ],

    "gamesa_emperador_vainilla": [
        "galleta emperador vainilla gamesa",
        "emperador vainilla gamesa",
    ],

    "toufayan_pita_integral": [
        "mini pita integral toufayan",
        "pita integral toufayan",
    ],

    "toufayan_bagels_cinnamon_raisin": [
        "bagels de pasas y canela toufayan",
        "toufayan bagels cinnamon raisin",
        "bagels canela pasas",
    ],

    "toufayan_bagels_everything": [
        "bagels everything toufayan",
        "toufayan bagels everything",
    ],

    "maria_tortilla_burrito": [
        "maria tortillas de trigo estilo burritos",
        "tortilla de trigo burrito maria",
        "burrito trigo maria",
    ],

    "maria_tortilla_taco": [
        "maria tortillas de trigo estilo tacos",
        "tortilla de trigo tacos maria",
        "tacos trigo maria",
    ],

    "tostitos_hint_lime": [
        "chips de tortilla de maiz sabor hint of lime tostitos",
        "tostitos hint of lime",
        "hint lime tostitos",
    ],

    "tostitos_santa_elena": [
        "chips de tortillas de maiz tostitos santa elena",
        "tostitos santa elena",
    ],

    "bauducco_wafer_fresa": [
        "galleta wafer con relleno sabor fresa bauducco",
        "bauducco wafer fresa",
        "bauducco wafer strawberry",
    ],

    "bauducco_wafer_lemon": [
        "bauducco wafer lemon",
        "bauducco wafer limon",
        "wafer limon bauducco",
    ],   


    "saltina_cracker": [
        "galleta de soda saltina aviva",
        "saltina aviva",
        "galleta de soda saltina hatuey",
        "saltina hatuey",
    ],   
    "club_social_saladas": [
        "galletas saladas club social",
        "club social saladas",
    ],    
    "guarina_club_max": [
        "club max saladas",
        "galletas saladas guarina club max",
    ],
    "oreo_cookies_cream": [
        "cookies and cream oreo",
        "cookie n cream oreo",
        "cream dulce oreo",
        "chocolate crema oreo",
    ],
    "wheat_tortilla": [
        "tortilla trigo",
        "tortillas de trigo",
        "wrap trigo",
    ],
        "hamburger_buns": [
        "pan de hamburguesa",
        "hamburguesa",
        "hamburger buns",
    ],
    "hotdog_buns": [
        "pan de hot dog",
        "hot dog",
        "hotdog",
    ],
    "multigrain_bread": [
        "multigranos",
        "multicereal",
        "7 cereales",
    ],
    "wafer_vanilla": [
        "wafer vainilla",
        "wafer vanilla",
    ],
    "wafer_chocolate": [
        "wafer chocolate",
        "wafer choco",
    ],
    "soda_cracker": [

        "soda crackers",
        "sodas crackers",
        "sodas cracker",

        "galleta de soda",
        "galletas de soda",

        "hatuey soda",
        "aviva soda",
        "lider soda",

        "noel sodas crackers",
        "dux crackers sodas",

    ],

}


def normalize_text(x):

    if pd.isna(x):
        return ""

    x = str(x).lower()

    x = re.sub(
        r"[^a-z0-9\s&]",
        " ",
        x
    )

    x = re.sub(
        r"\s+",
        " ",
        x
    ).strip()

    return x


def infer_product_from_dictionary(product_name):

    text = normalize_text(product_name)

    for canonical, variants in PRODUCT_DICTIONARY.items():

        for variant in variants:

            variant = normalize_text(variant)

            if variant and variant in text:
                return canonical

    return None
