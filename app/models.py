import enum
import re

from sqlalchemy.orm import validates
from wtforms.validators import ValidationError

from app import db, app
import datetime
from flask_login import UserMixin

class Item(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    create_date = db.Column(db.DateTime, default=datetime.datetime.now())

class AccountRole(enum.Enum):
    ADMIN = 'admin'
    NhanVien = 'nhanVien'
    QuanLyKho = 'quanLyKho'
    KhachHang = 'khachHang'

class User(Item, UserMixin):
    username = db.Column(db.String(30), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(30), unique=False, nullable=False)
    last_name = db.Column(db.String(30), unique=False, nullable=False)
    email = db.Column(db.String(30), unique=True, nullable=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    avatar = db.Column(db.String(255), nullable=True)

    account_role = db.Column(db.Enum(AccountRole), nullable=False, default=AccountRole.KhachHang)
    book_receipts = db.relationship('BookReceipt', backref='user', lazy=True)
    buy_orders = db.relationship('Order', backref='customer', lazy=True, foreign_keys='Order.customer_id')
    sell_orders = db.relationship('Order', backref='seller', lazy=True, foreign_keys='Order.employee_id')

    @validates('phone_number')
    def validate_password(self, key, value):
        pattern = r'(84|0[3|5|7|8|9])+([0-9]{8})\b'
        if not re.match(pattern, value):
            raise ValidationError(
                "Số điện thoại không hợp lệ")  # W
        return value

    def __str__(self):
        return self.first_name + ' ' + self.last_name

    def get_id(self):
        return str(self.id)

    def to_dic(self):
        return {
            "id": self.id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone_number": self.phone_number,
            "is_active": self.is_active,
            "avatar": self.avatar,
            "account_role": self.account_role.name if self.account_role else None,
            "book_receipts": [receipt.id for receipt in self.book_receipts] if self.book_receipts else [],
            "buy_orders": [order.id for order in self.buy_orders] if self.buy_orders else [],
            "sell_orders": [order.id for order in self.sell_orders] if self.sell_orders else []
        }

class ConfigSystem(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key = db.Column(db.String(255), unique=True, nullable=False)
    value = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    last_update = db.Column(db.DateTime, default=datetime.datetime.now())

Book_Author = db.Table('book_author',
                       db.Column('author_id', db.Integer, db.ForeignKey('author.id'), primary_key=True),
                       db.Column('book_id', db.Integer, db.ForeignKey('book.id'), primary_key=True))

Book_Genre = db.Table('book_genre',
                       db.Column('genre_id', db.Integer, db.ForeignKey('genre.id'), primary_key=True),
                       db.Column('book_id', db.Integer, db.ForeignKey('book.id'), primary_key=True))


class Author(Item):
    name = db.Column(db.String(50), unique=True, nullable=False)
    def __str__(self):
        return self.name

class Genre(Item):
    name = db.Column(db.String(50), unique=True, nullable=False)
    def __str__(self):
        return self.name

class Book(Item):
    name = db.Column(db.String(50), unique=True, nullable=False)
    authors = db.relationship('Author', secondary=Book_Author, lazy=True, backref=db.backref('books', lazy=True))
    genres = db.relationship('Genre',  secondary=Book_Genre ,backref=db.backref('books', lazy=True), lazy=True)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=False, default='Đây là sản phẩm mới')
    pages = db.Column(db.Integer, nullable=False)
    duration = db.Column(db.Float, nullable=False)

    book_receipts = db.relationship('BookReceiptDetail', backref='book', lazy=True)
    order_details = db.relationship('OrderDetail', backref='book', lazy=True)
    book_inventory = db.relationship('BookInventory', backref='book', lazy=True, uselist=False)

    def __str__(self):
        return self.name

class BookReceipt(Item):
    book_receipt_details = db.relationship('BookReceiptDetail', backref='receipt', lazy=True, cascade="all,delete")
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)

    def __str__(self):
        return f"Receipt {self.id}"

class BookReceiptDetail(db.Model):
    book_id = db.Column(db.Integer, db.ForeignKey(Book.id), primary_key=True)
    book_receipt_id = db.Column(db.Integer, db.ForeignKey(BookReceipt.id), primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)

class BookInventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    current_quantity = db.Column(db.Integer, nullable=False)
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now())
    book_id = db.Column(db.Integer, db.ForeignKey(Book.id), nullable=False, unique=True)

class OrderStatus(enum.Enum):
    DONE = 'done'
    PROCESSING = 'processing'
    FAILED = 'failed'
    PENDING = 'pending'

class Order(Item):
    customer_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=True)
    employee_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=True)
    order_details = db.relationship('OrderDetail', backref='order', lazy=True, cascade='all,delete')
    order_status = db.Column(db.Enum(OrderStatus), nullable=False, default=OrderStatus.DONE)


class OrderDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    quantity = db.Column(db.Integer, nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey(Book.id), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey(Order.id), nullable=False)
    unit_price = db.Column(db.Float, nullable=False)

if __name__ == '__main__':
    with app.app_context():
        if int(input('1:Tao moi\n0:Xoa\n')):
            db.create_all()
        else:
            db.drop_all()