# cards/wo_app/product_rules.py

PRODUCT_GROUPS = {
    'pants': {
        'label': 'Брюки',
        'keywords': ['брюк', 'штаны', 'джоггер',  'карго',  ]
    },
    'top': {
        'label': 'Верх',
        'keywords': ['топ', 'футболк', 'майк', 'рубашк', 'блуз', 'худи', 'свитшот', 'лонгслив', 'водолазк']
    },
    'outerwear': {
        'label': 'Верхняя одежда',
        'keywords': ['куртк', 'пальт', 'пухов', 'плащ', 'ветровк', 'парк']
    },
    'dress_skirt': {
        'label': 'Платья и юбки',
        'keywords': ['плать', 'сарафан', 'юбк']
    },
    'accessory': {
        'label': 'Аксессуары',
        'keywords': ['чехол', 'кейс', 'сумк', 'рюкзак', 'ремень', 'кошелек']
    },
    'underwear': {
        'label': 'Нижнее белье',
        'keywords': ['носок', 'трус', 'бра', 'бюстгальтер', 'стринги']
    }
}

def get_product_family(title: str) -> tuple:
    """
    Определяет группу товара по названию
    Возвращает: (key, label)
    """
    if not title:
        return ('other', 'Другое')
    
    title_lower = title.lower()
    for key, group in PRODUCT_GROUPS.items():
        for keyword in group['keywords']:
            if keyword in title_lower:
                return (key, group['label'])
    
    return ('other', 'Другое')