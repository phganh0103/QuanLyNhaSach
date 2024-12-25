import datetime
import hashlib
from sqlalchemy import cast, Integer

from sqlalchemy import Integer
from sqlalchemy.sql import func

from app import db, Genre, Order, OrderStatus, BookReceipt, BookInventory, ConfigSystem, app, Book_Genre
from app.models import User, Book, OrderDetail, AccountRole, Author, BookReceiptDetail


def check_login(username, password):
    try:
        password = str(hashlib.md5(password.strip().encode("utf-8")).hexdigest())
        return User.query.filter(User.username == username,
                                 User.password == password).first()
    except Exception as e:
        return None


def add_user(username, password, first_name, last_name, avatar, phone_number, email):
    try:
        user = User(username=username, password=str(hashlib.md5(password.strip().encode("utf-8")).hexdigest()),
                    first_name=first_name, last_name=last_name, avatar=avatar, phone_number=phone_number, email=email)
        db.session.add(user)
        db.session.commit()
        return user
    except Exception as e:
        db.session.rollback()
        raise e


def get_user_by_id(user_id):
    return User.query.get(user_id)


def get_all_book(query=None):
    if query:
        return Book.query.filter(Book.name.like(f"%{query}%")).order_by(Book.create_date.desc()).all()
    return Book.query.order_by(Book.create_date.desc()).all()


def get_book_by_id(book_id):
    return Book.query.get(book_id)


def get_cart_by_user_id(user_id):
    return Order.query.filter_by(customer_id=user_id, order_status=OrderStatus.PENDING).first()


def get_orders_with_details_by_status(order_status):
    return OrderDetail.query.join(Order, Order.id == OrderDetail.order_id).filter(
        Order.order_status == order_status).all()


def create_cart(user_id):
    cart = get_cart_by_user_id(user_id)
    if cart is None:
        cart = Order(customer_id=user_id, order_status=OrderStatus.PENDING)
        db.session.add(cart)
        db.session.commit()
    return cart


def add_product_in_cart(**kwargs):
    o = OrderDetail(**kwargs)
    current_order = OrderDetail.query.filter_by(book_id=o.book_id, order_id=o.order_id).first()
    if current_order is None:
        db.session.add(o)
    else:
        current_order.quantity += int(o.quantity)
        current_order.unit_price += float(o.unit_price)
    db.session.commit()


def get_total_price(cart):
    rs = 0
    for cart_detail in cart.order_details:
        rs += cart_detail.unit_price
    return rs


def delete_product_in_cart(cart_id, user_id):
    o = OrderDetail.query.join(Order, Order.id == OrderDetail.order_id).filter(OrderDetail.id == cart_id,
                                                                               Order.customer_id == user_id).first()
    if o:
        db.session.delete(o)
        db.session.commit()


def update_cart(product_in_cart_id, new_quantity):
    o = OrderDetail.query.filter_by(id=product_in_cart_id).first()
    o.quantity = new_quantity
    o.unit_price = o.book.price * new_quantity
    db.session.commit()


def get_cart_total_quantity(user_id):
    cart = create_cart(user_id)
    rs = 0
    for cart_detail in cart.order_details:
        rs += cart_detail.quantity
    return rs


def get_product_in_cart(product_id, cart, user_id):
    if cart.customer_id == user_id:
        for cart_detail in cart.order_details:
            if cart_detail.book.id == int(product_id):
                return cart_detail
        return None


def get_product_in_cart_by_cart_detail_id(cart_detail_id):
    return OrderDetail.query.filter_by(id=cart_detail_id).first()


def get_product_detail(product_id):
    return Book.query.get(product_id)


def get_order_by_id(order_id, user_id=None, status=None):
    if user_id:
        return Order.query.filter_by(customer_id=user_id, id=order_id).first()
    return Order.query.get(order_id)


def change_status_order(order, new_created_date, order_status):
    o = Order.query.filter_by(id=order.id, order_status=order.order_status).first()
    o.order_status = order_status
    o.created_date = new_created_date
    db.session.commit()


def find_customer_by_email(email):
    return User.query.filter_by(email=email, account_role=AccountRole.KhachHang).first()


def get_all_genre():
    return Genre.query.all()


def get_all_author():
    return Author.query.all()


def find_genres(genre_ids):
    rs = []
    for genre_id in genre_ids:
        genre = Genre.query.get(genre_id)
        rs.append(genre)
    return rs


def find_authors(authors):
    rs = []
    for author in authors:
        author = Author.query.get(author)
        rs.append(author)
    return rs


def create_book_receipt(store_manager_id):
    book_receipt = BookReceipt(user_id=store_manager_id)
    db.session.add(book_receipt)
    db.session.commit()
    return book_receipt


def create_book_receipt_detail(data, book_receipt):
    book_receipt_detail = BookReceiptDetail(book=get_book_by_id(data['id']), quantity=data['quantity'],
                                            receipt=book_receipt)
    db.session.add(book_receipt_detail)
    db.session.commit()
    return book_receipt_detail


def get_book_in_inventory(book_id):
    return BookInventory.query.filter_by(book_id=book_id).first()


def check_inventory(data):
    for item in data:
        if item['quantity'] < int(get_config_system('inventory_min_import').value):
            return False
        book = get_book_by_id(item['id'])
        if book is None:
            return False
        book_in_inventory = get_book_in_inventory(book.id)
        if book_in_inventory and book_in_inventory.current_quantity > int(
                get_config_system('inventory_import_limit').value):
            return False
    return True


def import_into_inventory(book_receipt_details):
    for book_receipt_detail in book_receipt_details:
        tmp = get_book_in_inventory(book_receipt_detail.book_id)
        if tmp:
            tmp.current_quantity += book_receipt_detail.quantity
            tmp.last_updated = datetime.datetime.now()
            db.session.add(tmp)
        else:
            book_inventory = BookInventory(book_id=book_receipt_detail.book_id,
                                           current_quantity=book_receipt_detail.quantity)
            db.session.add(book_inventory)
        db.session.commit()


def export_out_to_inventory(order_details):
    for order_detail in order_details:
        book = get_book_in_inventory(order_detail.book_id)
        book.current_quantity -= order_detail.quantity
        db.session.add(book)
    db.session.commit()


def get_inventory(genre=None, orderby=None, q=None, page=None, page_size=None):
    query = db.session.query(BookInventory).join(Book, BookInventory.book_id == Book.id)
    if genre:
        query = query.join(Book_Genre, Book_Genre.c.book_id == Book.id)
        query = query.join(Genre, Genre.id == Book_Genre.c.genre_id)
        query = query.filter(Genre.name == genre)
    if orderby == 'o1':
        query = query.order_by(Book.id)
    if orderby == 'o2':
        query = query.order_by(Book.id.desc())
    if q:
        query = query.filter(Book.name.like(f"%{q}%"))
    start = (page - 1) * page_size
    return query.offset(start).limit(page_size).all()


def get_total_quantity_in_inventory():
    rs = db.session.query(func.sum(BookInventory.current_quantity)).scalar()
    return rs or 0


def get_count_inventory(genre=None, query=None):
    if genre:
        return (db.session.query(func.count(BookInventory.id))
                .join(Book, Book.id == BookInventory.book_id)
                .join(Book_Genre, Book_Genre.c.book_id == Book.id)
                .join(Genre, Genre.id == Book_Genre.c.genre_id)
                .filter(Genre.name == genre)
                .scalar()
                )
    if query:
        return BookInventory.query.join(Book, Book.id == BookInventory.book_id).filter(
            Book.name.like(f"%{query}%")).count()
    return BookInventory.query.count()


def get_config_system(key=None):
    if key is None:
        return ConfigSystem.query.all()
    return ConfigSystem.query.filter_by(key=key).first()


def update_config_system(data):
    for key, value in data.items():
        tmp = ConfigSystem.query.filter_by(key=key).first()
        if tmp is None:
            raise Exception('Config system not found')
        tmp.value = value
        db.session.add(tmp)
    db.session.commit()


def get_revenue_by_month():
    return ((db.session.query(func.extract('month', Order.create_date, ),
                              func.extract('year', Order.create_date),
                              func.sum(OrderDetail.unit_price),
                              cast(func.sum(OrderDetail.quantity), Integer),
                              )
             .join(Order, Order.id == OrderDetail.order_id))
            .where(Order.order_status == OrderStatus.DONE)
            .group_by(func.extract('month', Order.create_date),
                      func.extract('year', Order.create_date),
                      )
            .order_by(func.extract('year', Order.create_date),
                      func.extract('month', Order.create_date, )
                      )
            .all()
            )


def get_sales_data_by_month_and_book():
    return (db.session.query(func.extract('month', Order.create_date),
                             func.extract('year', Order.create_date),
                             Book.name,
                             cast(func.sum(OrderDetail.quantity), Integer)
                             )
            .join(Order, Order.id == OrderDetail.order_id)
            .join(Book, Book.id == OrderDetail.book_id)
            .where(Order.order_status == OrderStatus.DONE)
            .group_by(func.extract('month', Order.create_date),
                      func.extract('year', Order.create_date),
                      Book.name)
            .order_by(func.extract('year', Order.create_date),
                      func.extract('month', Order.create_date, )
                      )
            .all()
            )


if __name__ == '__main__':
    with app.app_context():
        print(get_total_quantity_in_inventory())
