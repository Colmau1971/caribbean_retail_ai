# ==================================================
# CENTRAL SEARCH DICTIONARY
# Caribbean Retail AI
# Terms by commercial category and market
# ==================================================

SEARCH_DICTIONARY = {

    "WHITE_BREAD": {
        "default": ["white bread", "bread"],
        "Dominican Republic": ["pan blanco", "pan sandwich", "pan viga blanco"],
        "Guyana": ["white bread", "bread", "loaf"],
        "Aruba": ["white bread", "wit brood", "white buns"],
    },

    "WHOLE_WHEAT_BREAD": {
        "default": ["whole wheat bread", "wholewheat bread"],
        "Dominican Republic": ["pan integral", "pan viga integral"],
        "Guyana": ["whole wheat bread", "wholewheat bread", "wheat bread"],
        "Aruba": ["whole wheat bread", "volkoren bread", "bruine brood"],
    },

    "SPECIALTY_BREAD": {
        "default": ["multigrain bread", "seed bread"],
        "Dominican Republic": ["multicereal", "multigranos", "avena"],
        "Guyana": ["multigrain bread", "oat bread", "seed bread"],
        "Aruba": ["multigrain bread", "volkoren", "seed bread"],
    },

    "HAMBURGER_BUNS": {
        "default": ["hamburger buns", "burger buns"],
        "Dominican Republic": ["pan hamburguesa", "hamburguesa"],
        "Guyana": ["hamburger buns", "burger buns"],
        "Aruba": ["hamburger buns", "burger buns"],
    },

    "HOTDOG_BUNS": {
        "default": ["hot dog buns", "hotdog buns"],
        "Dominican Republic": ["pan hot dog", "hot dog"],
        "Guyana": ["hot dog buns", "hotdog buns"],
        "Aruba": ["hot dog buns", "hotdog buns"],
    },

    "TORTILLAS_WRAPS": {
        "default": ["tortilla", "wrap", "burrito", "taco"],
        "Dominican Republic": ["tortilla", "tortillas", "wrap", "burrito", "taco"],
        "Guyana": ["tortilla", "tortillas", "wrap", "wraps", "burrito"],
        "Aruba": ["tortilla", "tortillas", "wrap", "wraps", "burrito"],
    },

    "PITA_FLATBREAD": {
        "default": ["pita", "flatbread", "naan"],
        "Dominican Republic": ["pita", "pan pita", "flatbread", "naan"],
        "Guyana": ["pita", "flatbread", "naan"],
        "Aruba": ["pita", "flatbread", "naan", "lavash"],
    },

    "TOASTED_BREAD": {
        "default": ["toast", "melba toast"],
        "Dominican Republic": ["tostada", "tostadas", "pan tostado"],
        "Guyana": ["toast", "melba toast"],
        "Aruba": ["toast", "melba toast", "beschuit"],
    },

    "BAGELS": {
        "default": ["bagel", "bagels"],
        "Dominican Republic": ["bagel", "bagels"],
        "Guyana": ["bagel", "bagels"],
        "Aruba": ["bagel", "bagels"],
    },

    "SWEET_COOKIES": {
        "default": ["cookies", "oreo", "chips ahoy"],
        "Dominican Republic": ["galletas", "oreo", "chips ahoy", "festival", "chokis", "emperador"],
        "Guyana": ["cookies", "biscuits", "oreo", "chips ahoy"],
        "Aruba": ["cookies", "biscuits", "oreo", "chips ahoy"],
    },

    "SAVORY_CRACKERS": {
        "default": ["crackers", "soda crackers", "ritz"],
        "Dominican Republic": ["galleta de soda", "galletas de soda", "saltinas", "ritz", "club social"],
        "Guyana": ["crackers", "soda crackers", "saltine crackers", "ritz"],
        "Aruba": ["crackers", "soda crackers", "sodas crackers", "ritz"],
    },

    "WAFERS": {
        "default": ["wafer", "wafers"],
        "Dominican Republic": ["wafer", "wafers", "barquillo"],
        "Guyana": ["wafer", "wafers"],
        "Aruba": ["wafer", "wafers", "waffer"],
    },

    "SALTY_SNACKS": {
        "default": ["pringles", "tostitos", "doritos", "cheetos", "chips"],
        "Dominican Republic": ["pringles", "tostitos", "doritos", "cheetos", "chips"],
        "Guyana": ["pringles", "tostitos", "doritos", "cheetos", "chips", "popcorn", "pretzels"],
        "Aruba": ["pringles", "tostitos", "doritos", "cheetos", "lays", "chips"],
    },

    "SWEET_BAKERY": {
        "default": ["croissant", "muffin", "brownie", "cake"],
        "Dominican Republic": ["croissant", "muffin", "brownie", "bizcocho", "ponque"],
        "Guyana": ["croissant", "muffin", "brownie", "cake", "cupcake"],
        "Aruba": ["croissant", "muffin", "brownie", "cake", "suiker vlinder"],
    },

    "FROZEN_BAKERY": {
        "default": ["frozen"],
        "Dominican Republic": ["frozen", "congelado"],
        "Guyana": ["frozen bread", "frozen dough", "frozen pastry", "frozen pizza"],
        "Aruba": ["frozen", "frozen bread", "frozen pizza"],
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