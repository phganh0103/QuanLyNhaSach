from datetime import datetime

from flask import session
from sqlalchemy import func, false
from sqlalchemy.sql.functions import user

from app import db, app
from app import models


# def updateInventory(receipt_details, session):
#     for receipt_detail in receipt_details:
#         inventory = models.BookInventory.query.filter_by(book_id=receipt_detail.book_id).first()
#         if inventory:
#             inventory.current_quantity += receipt_detail.quantity
#             inventory.last_updated = datetime.now()
#         else:
#             new_inventory = models.BookInventory(book_id=receipt_detail.book_id,
#                                                  current_quantity=receipt_detail.quantity, last_updated=datetime.now())
#             session.add(new_inventory)
#
#
# def addBook(user, book_quantity_arr):
#     try:
#         with db.session() as session:
#             receipt = models.BookReceipt(user_id=user.id)
#             receipt_details = []
#             for book, quantity in book_quantity_arr:
#                 receipt_detail = models.BookReceiptDetail(book_id=book.id, quantity=quantity)
#                 receipt_details.append(receipt_detail)
#
#             receipt.book_receipt_details = receipt_details
#             session.add(receipt)
#             updateInventory(receipt_details, session)
#             session.commit()
#     except Exception as e:
#         print(e)

def checkInventory(book_quantity_arr):
    for book, quantity in book_quantity_arr:
        tmp = models.BookInventory.query.filter_by(book_id=book.id).first()
        if tmp is None or tmp.current_quantity < quantity:
            return False
    return True

def decreaseInventory(book_quantity_arr):
    for book, quantity in book_quantity_arr:
        tmp = models.BookInventory.query.filter_by(book_id=book.id).first()
        tmp.current_quantity -= quantity
        tmp.last_updated = datetime.now()

def oderBook(customer, seller, book_quantity_arr):
    try:
        with db.session() as session:
            if checkInventory(book_quantity_arr):
                order = models.Order(customer_id=customer.id, employee_id=seller.id,
                                     order_status=models.OrderStatus.PROCESSING)
                order_details = []
                for book, quantity in book_quantity_arr:
                    order_detail = models.OrderDetail(book_id=book.id, quantity=quantity,
                                                      unit_price=book.price * quantity)
                    order_details.append(order_detail)
                order.other_details = order_details

                decreaseInventory(book_quantity_arr)
                order.order_status = models.OrderStatus.DONE
                session.add(order)
                session.commit()

            else:
                print("Sach hoac so luong chua hop le")
    except Exception as e:
        print(e)

if __name__ == '__main__':
    with app.app_context():
        customer = models.User.query.filter_by(id = 1).first()
        seller = models.User.query.filter_by(id = 2).first()
        # user = models.User.query.filter_by(id=1).first()
        # book_store = models.BookStore.query.first()
        book1 = models.Book.query.first()
        # book2 = models.Book.query.filter_by(id=2).first()
        book3 = models.Book.query.filter_by(id=3).first()
        # addBook(user=user, book_quantity_arr=[(book1, 40), (book3, 10)])
        oderBook(customer=customer, seller=seller, book_quantity_arr=[(book1, 10), (book3, 50)])
