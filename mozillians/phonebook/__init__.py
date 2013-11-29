from product_details import product_details


ENGLISH_LANGUAGE_CHOICES = sorted(
    [(key.lower(), value['English'])
     for key, value in product_details.languages.items()],
    key=lambda language: language[1])
