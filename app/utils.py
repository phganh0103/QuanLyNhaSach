from app import dao


def check_existing_inventory(product_id, quantity):
    p = dao.get_book_in_inventory(product_id)
    if p is None or p.current_quantity < quantity:
        return False
    return True