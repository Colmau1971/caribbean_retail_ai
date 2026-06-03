# =====================================================
# GLOBAL BRAND DICTIONARY
# Caribbean Retail Intelligence
# =====================================================

BRAND_KEYWORDS = {
    # BIMBO / GB
    "bimbo": "Bimbo",
    "marinela": "Marinela",
    "tia rosa": "Tía Rosa",
    "tía rosa": "Tía Rosa",
    "sanissimo": "Saníssimo",
    "sanísimo": "Saníssimo",
    "takis": "Takis",

    # Mondelez
    "oreo": "Oreo",
    "ritz": "Ritz",
    "nabisco": "Nabisco",
    "chips ahoy": "Chips Ahoy",
    "club social": "Club Social",
    "belvita": "Belvita",
    "triscuit": "Triscuit",
    "tuc": "Tuc",

    # Pepsico / Snacks
    "lays": "Lays",
    "lay's": "Lays",
    "doritos": "Doritos",
    "cheetos": "Cheetos",
    "tostitos": "Tostitos",
    "pringles": "Pringles",
    "sun chips": "Sun Chips",
    "ruffles": "Ruffles",

    # Bakery / Tortillas
    "mission": "Mission",
    "toufayan": "Toufayan",
    "old el paso": "Old El Paso",
    "sara lee": "Sara Lee",
    "wonder": "Wonder",
    "thomas": "Thomas",
    "pepperidge": "Pepperidge Farm",
    "nature's own": "Nature's Own",
    "natures own": "Nature's Own",
    "oroweat": "Oroweat",
    "brownberry": "Brownberry",
    "dave's killer": "Dave's Killer Bread",

    # Regional Caribe / Latam
    "guarina": "Guarina",
    "hatuey": "Hatuey",
    "aviva": "Aviva",
    "dino": "Dino",
    "duetto": "Duetto",
    "gamesa": "Gamesa",
    "gullon": "Gullon",
    "colombina": "Colombina",
    "noel": "Noel",
    "bermudez": "Bermudez",
    "wibisco": "Wibisco",
    "sunshine": "Sunshine",
    "crix": "Crix",
    "kiss": "Kiss",
    "holiday": "Holiday",
    "mi trigo": "Mi Trigo",
    "molino del sol": "Molino Del Sol",
    "lumijor": "Lumijor",
    "la panera": "La Panera",
    "maria": "Maria",
    "maría": "Maria",

    # Imported / US / Europe
    "food club": "Food Club",
    "keebler": "Keebler",
    "kellogg": "Kellogg",
    "goldfish": "Goldfish",
    "stacy's": "Stacy's",
    "mcvitie": "McVitie's",
    "walkers": "Walkers",
    "lu ": "LU",
    "wasa": "WASA",
    "schar": "Schar",
    "bolletje": "Bolletje",
    "ducales": "Ducales",
    "crunchmaster": "Crunchmaster",
    "glutino": "Glutino",
    "hollandia": "Hollandia",
    "laurieri": "Laurieri",
    "van der meulen": "Van Der Meulen",

    # Others
    "quaker": "Quaker",
    "bauducco": "Bauducco",
    "hostess": "Hostess",
    "entenmann": "Entenmann's",
    "little debbie": "Little Debbie",
    "planters": "Planters",
    "snickers": "Snickers",
    "ovaltine": "Ovaltine",
    "goya": "Goya",
    "siete": "Siete",
    "reynolds": "Reynolds",
    "glad": "Glad",
    "toppers": "Toppers",
    "soldanza": "Soldanza",
    "motto": "Motto",
    "phidelia": "Phidelia",
    "whytes": "Whytes",
}


def infer_brand(name):

    if not name:
        return "Other"

    name_clean = (
        str(name)
        .lower()
        .replace("-", " ")
        .strip()
    )

    for keyword, brand in sorted(
        BRAND_KEYWORDS.items(),
        key=lambda x: len(x[0]),
        reverse=True
    ):
        if keyword.strip() in name_clean:
            return brand

    return "Other"
