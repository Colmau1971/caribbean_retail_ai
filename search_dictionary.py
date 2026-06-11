# ==================================================
# CENTRAL SEARCH DICTIONARY
# Caribbean Retail AI
# Terms by commercial category and market
# ==================================================

SEARCH_DICTIONARY = {

    "WHITE_BREAD": {
        "Dominican Republic": [
            "pan sandwich",
            "pan viga blanco"
        ],
        "Guyana": [
            "white bread",
            "sandwich bread"
        ],
        "Aruba": [
            "white bread",
            "sandwich bread",
            "witte bollen"
        ],
    },

    "WHOLE_WHEAT_BREAD": {
        "Dominican Republic": [
            "pan integral",
            "pan viga integral"
        ],
        "Guyana": [
            "whole wheat bread",
            "brown bread"
        ],
        "Aruba": [
            "whole wheat bread",
            "volkoren bread"
        ],
    },

    "SPECIALTY_BREAD": {
        "Dominican Republic": [
            "pan multicereal",
            "pan multigrano"
        ],
        "Guyana": [
            "multigrain bread"
        ],
        "Aruba": [
            "multigrain bread"
        ],
    },

    "HAMBURGER_BUNS": {
        "Dominican Republic": [
            "pan hamburguesa"
        ],
        "Guyana": [
            "hamburger buns"
        ],
        "Aruba": [
            "hamburger buns"
        ],
    },

    "HOTDOG_BUNS": {
        "Dominican Republic": [
            "pan hot dog"
        ],
        "Guyana": [
            "hot dog buns"
        ],
        "Aruba": [
            "hot dog buns"
        ],
    },

    "TORTILLAS_WRAPS": {
        "Dominican Republic": [
        "tortilla de maiz",
        "tortilla de harina",
        "wrap"
        ],
        "Guyana": [
            "tortilla",
            "wrap"
        ],
        "Aruba": [
            "tortilla",
            "wrap",
            "tex mex"
        ],
    },

    "PITA_FLATBREAD": {
        "Dominican Republic": [
            "pan pita"
        ],
        "Guyana": [
            "pita",
            "naan"
        ],
        "Aruba": [
            "pita",
            "naan"
        ],
    },

    "TOASTED_BREAD": {
        "Dominican Republic": [
            "tostadas"
        ],
        "Guyana": [
            "melba toast"
        ],
        "Aruba": [
            "beschuit"
        ],
    },

    "BAGELS": {
        "Dominican Republic": [
            "bagel"
        ],
        "Guyana": [
            "bagel"
        ],
        "Aruba": [
            "bagel"
        ],
    },

    "SWEET_COOKIES": {
        "Dominican Republic": [
            "oreo",
            "festival",
            "chokis",
            "emperador"
        ],
        "Guyana": [
            "oreo",
            "biscuits"
        ],
        "Aruba": [
            "oreo",
            "biscuits",
            "festival"
        ],
    },

    "SAVORY_CRACKERS": {
        "Dominican Republic": [
            "ritz",
            "saltinas",
            "club social"
        ],
        "Guyana": [
            "ritz",
            "saltine crackers"
        ],
        "Aruba": [
            "ritz",
            "saltine crackers",
            "club social"
        ],
    },

    "WAFERS": {
        "Dominican Republic": [
            "wafer",
            "barquillo"
        ],
        "Guyana": [
            "wafer"
        ],
        "Aruba": [
            "wafer"
        ],
    },

    "SALTY_SNACKS": {
        "Dominican Republic": [
            "pringles",
            "doritos",
            "takis"
        ],
        "Guyana": [
            "pringles",
            "doritos",
            "fritos"
        ],
        "Aruba": [
            "pringles",
            "doritos",
            "lays",
            "takis"
        ],
    },

    "SWEET_BAKERY": {
        "Dominican Republic": [
            "croissant",
            "muffin",
            "bizcocho"
        ],
        "Guyana": [
            "croissant",
            "muffin",
            "cake"
        ],
        "Aruba": [
            "croissant",
            "muffin",
            "cake"
        ],
    },

    "FROZEN_BAKERY": {
        "Dominican Republic": [
            "pan baguette congelado",
            "pan congelado",
            "masa fermentada congelada",
        ],
        "Guyana": [
            "frozen bread",
            "frozen pastry"
        ],
        "Aruba": [
            "frozen bread",
            "frozen pastry"
        ],
    },
}


def get_search_terms():
    return SEARCH_DICTIONARY


def get_terms_for_market(category, country):
    category_terms = SEARCH_DICTIONARY.get(category, {})

    terms = []

    terms.extend(category_terms.get("default", []))
    terms.extend(category_terms.get(country, []))

    return sorted(set(terms))


def get_market_search_terms(country):
    market_terms = {}

    for category in SEARCH_DICTIONARY:
        market_terms[category] = get_terms_for_market(
            category,
            country
        )

    return market_terms


def flatten_search_terms(country=None):
    terms = []

    for category in SEARCH_DICTIONARY:

        if country:
            values = get_terms_for_market(category, country)
        else:
            values = []

            for group_terms in SEARCH_DICTIONARY[category].values():
                values.extend(group_terms)

            values = sorted(set(values))

        for term in values:
            terms.append(
                {
                    "commercial_category": category,
                    "term": term,
                    "country": country or "ALL",
                }
            )

    return terms