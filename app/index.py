import math
import random
from collections import defaultdict
from datetime import datetime, timedelta
import re

from sqlalchemy.exc import IntegrityError

from app import app, login_manager, dao, OrderStatus, redis_client, models, utils
from flask import render_template, redirect, url_for, request, session, jsonify, json
from flask_login import login_user, logout_user, current_user
from redis_tasks import redis_utils
from app.decorator import role_required
import cloudinary
import cloudinary.uploader


@app.context_processor
def inject_cart_quantity():
    if current_user.is_authenticated and current_user.account_role == models.AccountRole.KhachHang:
        cart_total_quantity = dao.get_cart_total_quantity(current_user.id)
        return {'cart_total_quantity': cart_total_quantity}
    return {'cart_total_quantity': 0}


@app.context_processor
def inject_config_system():
    system_config = {
        # se cache sau vi du 'max_stock_threshold': redis.get('config:stock_import_limit') or dao.get_config('stock_import_limit'),
        'inventory_min_import': dao.get_config_system('inventory_min_import').value,
        'inventory_import_limit': dao.get_config_system('inventory_import_limit').value,
        'order_online_cancel_timeout': dao.get_config_system('order_online_cancel_timeout').value,
        'order_offline_cancel_timeout': dao.get_config_system('order_offline_cancel_timeout').value,
    }
    return {'system_config': system_config}


@app.route('/')
def home():
    genre = request.args.get('genre')
    orderby = request.args.get('orderby')
    query = request.args.get('query')
    page = request.args.get('page', 1, type=int)
    page_size = 4
    inventory = dao.get_inventory(genre=genre, orderby=orderby, q=query, page=page, page_size=page_size)
    books = []
    for item in inventory:
        books.append({
            'book': item.book,
            'quantity': item.current_quantity,
        })
    total = dao.get_count_inventory(genre, query)
    title_book = None
    if len(books) != 0:
        title_book = books[random.randint(0, len(books) - 1)]

    return render_template('index.html', books=books, title_book=title_book, genre=genre,
                           pages=math.ceil(total / page_size),
                           current_page=page, orderby=orderby, query=query)


@login_manager.user_loader
def load_user(user_id):
    return models.User.get(user_id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    err_msg = ""
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")
        user = dao.check_login(username=username, password=password)
        if user:
            login_user(user=user)
            if user.account_role == models.AccountRole.KhachHang:
                return redirect(url_for('home'))
            elif user.account_role == models.AccountRole.NhanVien:
                return redirect(url_for('staff'))
            elif user.account_role == models.AccountRole.QuanLyKho:
                return redirect(url_for('store_manager'))
            elif user.account_role == models.AccountRole.ADMIN:
                return redirect(url_for('admin'))
        else:
            err_msg = "Something wrong!!!"
    return render_template("login.html", err_msg=err_msg)


@app.route("/logout")
@role_required(['khachHang', 'nhanVien', 'quanLyKho', 'admin'])
def logout():
    logout_user()
    return redirect('/')


@app.route("/signup", methods=["get", "post"])
def signup():
    try:
        if session.get('user'):
            return redirect(request.url)
        err_msg = ""
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            password_confirm = request.form.get("password_confirm")
            first_name = request.form.get("first_name")
            last_name = request.form.get("last_name")
            phone_number = request.form.get("phone-number")
            email = request.form.get("email")
            avatar_url = None
            pattern = r'^(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{8,}$'
            if not re.match(pattern, password.strip()):
                err_msg = "Mật khẩu phải có ít nhất 8 ký tự, bao gồm ít nhất một chữ cái viết hoa, một chữ cái viết thường và một chữ số."
            elif password.strip() != password_confirm.strip():
                err_msg = "Mật khẩu không khớp"
            else:
                if 'avatar' in request.files and request.files['avatar'].filename != '':
                    avatar_file = request.files['avatar']
                    try:
                        upload_result = cloudinary.uploader.upload(avatar_file)
                        print(upload_result)
                        avatar_url = upload_result['secure_url']
                    except Exception as e:
                        print(avatar_url)
                        err_msg = f"Avatar upload failed: {str(e)}"
                        return render_template("signup.html", err_msg=err_msg)
                if dao.add_user(username=username, password=password, first_name=first_name, last_name=last_name,
                                avatar=avatar_url, phone_number=phone_number, email=email):
                    return redirect(url_for("login"))
                else:
                    err_msg = "Something Wrong!!!"

    except ValidationError as ve:
        err_msg = f"{str(ve)}"
    except IntegrityError as e:
        if "Duplicate entry" in str(e.orig):
            if "phone_number" in str(e.orig):
                err_msg = "Số điện thoại này đã được sử dụng. Vui lòng sử dụng số khác."
            elif "email" in str(e.orig):
                err_msg = "Email này đã được sử dụng. Vui lòng sử dụng email khác."
            elif "username" in str(e.orig):
                err_msg = "Tên đăng nhập đã tồn tại. Vui lòng chọn tên khác."
            else:
                err_msg = "Đã có lỗi xảy ra. Vui lòng thử lại."
        else:
            err_msg = "Lỗi cơ sở dữ liệu: {str(e)}"
    except Exception as e:
        err_msg = f"{str(e)}"

    return render_template("signup.html", err_msg=err_msg)


@app.route('/cart', methods=['GET', 'POST'])
@role_required(['khachHang'])
def cart():
    if request.method == 'POST':
        try:
            product = request.form.to_dict()
            product_id = product['book_id']
            product_quantity = int(product['quantity'])
            book_in_inventory = dao.get_book_in_inventory(product_id)

            my_cart = dao.create_cart(current_user.id)
            book_in_cart = dao.get_product_in_cart(product_id, my_cart, current_user.id)
            if (book_in_cart and utils.check_existing_inventory(product_id,
                                                                product_quantity + book_in_cart.quantity)) or (
                    not book_in_cart and utils.check_existing_inventory(product_id, product_quantity)):
                product['order_id'] = my_cart.id
                product['unit_price'] = int(product['quantity']) * book_in_inventory.book.price
                dao.add_product_in_cart(**product)
                return jsonify({
                    'success': True,
                    'message': 'Item added to cart successfully'
                }), 201
            else:
                return jsonify({
                    'success': False,
                    'message': 'Item added to cart failed'
                }), 400
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            }), 500

    my_carts = dao.get_cart_by_user_id(current_user.id)
    total_price = 0
    if my_carts:
        total_price = dao.get_total_price(my_carts)
    return render_template('cart.html', carts=my_carts, total_price=total_price)


@app.route('/delete/cart/<int:cart_id>', methods=['DELETE'])
@role_required(['khachHang'])
def delete_product_in_cart(cart_id):
    try:
        dao.delete_product_in_cart(cart_id, current_user.id)
        return '', 204
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500


@app.route('/products/<int:product_id>', methods=['GET'])
def products_detail(product_id):
    book = dao.get_product_detail(product_id)
    if book:
        book_inventory = dao.get_book_in_inventory(book.id)
        return render_template('products_detail.html', book=book,
                               book_inventory_quantity=book_inventory.current_quantity)
    else:
        return redirect(url_for('home'))


@app.route('/update-cart', methods=['PATCH'])
@role_required(['khachHang'])
def update_cart():
    data = request.get_json()
    product_in_cart_id = data.get("product_in_cart_id")
    quantity = data.get("quantity")
    try:
        book_in_cart_detail = dao.get_product_in_cart_by_cart_detail_id(product_in_cart_id)
        book_in_inventory = dao.get_book_in_inventory(book_in_cart_detail.book.id)
        if not utils.check_existing_inventory(book_in_cart_detail.book.id, quantity):
            return jsonify({
                'success': False,
                'message': f'Not enough quantity! Maximum quantity for this item is {book_in_inventory.current_quantity}'
            }), 400
        dao.update_cart(product_in_cart_id, quantity)
        return jsonify({
            'success': True,
            'message': 'Item update successfully'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500


@app.route('/checkout', methods=['GET'])
@role_required(['khachHang'])
def checkout():
    carts = dao.get_cart_by_user_id(current_user.id)
    if carts is None:
        return redirect(url_for('not_found_page'))
    total_price = 0
    if carts:
        total_price = dao.get_total_price(carts)
    return render_template('checkout_templates/checkout.html', carts=carts, total_price=total_price)


def checkout_method(method, ttl):
    order_id = request.args.get('order_id')
    carts = dao.get_cart_by_user_id(current_user.id)
    if carts is None:
        return redirect(url_for('not_found_page'))
    total_price = dao.get_total_price(carts)
    carts.create_date = datetime.now()
    deadline = carts.create_date + timedelta(seconds=ttl)
    dao.change_status_order(carts, carts.create_date, OrderStatus.PROCESSING)
    dao.export_out_to_inventory(carts.order_details)
    redis_utils.set_ttl_order(order_id, ttl, "PROCESSING")
    return render_template(f'/checkout_templates/checkout_{method}.html', order_id=int(order_id),
                           total_price=total_price, deadline=deadline)


@app.route('/checkout/offline', methods=['GET'])
@role_required(['khachHang'])
def checkout_offline():
    return checkout_method("offline", int(dao.get_config_system('order_offline_cancel_timeout').value))


@app.route('/checkout/online', methods=['GET'])
@role_required(['khachHang'])
def checkout_online():
    return checkout_method("online", int(dao.get_config_system('order_online_cancel_timeout').value))


@app.route('/checkout/confirm', methods=['POST'])
@role_required(['khachHang', 'nhanVien'])
def checkout_confirm():
    data = request.get_json()
    order_id = data.get("order_id")
    order = None
    if current_user.account_role == models.AccountRole.KhachHang:
        order = dao.get_order_by_id(order_id, current_user.id)
    elif current_user.account_role == models.AccountRole.NhanVien:
        order = dao.get_order_by_id(order_id)
    if order is None:
        return jsonify({'success': False, 'message': 'order not found'})
    if order.order_status != OrderStatus.FAILED:
        dao.change_status_order(order, order.create_date, OrderStatus.DONE)
    else:
        return jsonify({'success': False, 'message': 'order failed'})
    redis_client.delete(int(order_id))
    return jsonify({'success': True, 'message': 'Checkout done'})


@login_manager.user_loader
def load_user(user_id):
    return dao.get_user_by_id(user_id)


# staff

@app.route('/staff', methods=['GET'])
@role_required(['nhanVien'])
def staff():
    return render_template('/staff/staff.html')


@app.route("/staff/receive-online-order", methods=['GET'])
@role_required(['nhanVien'])
def receive_online_order():
    return render_template("/staff/receive_online_order.html")


@app.route('/staff/receive-online-order/find_order', methods=['POST'])
@role_required(['nhanVien'])
def receive_online_get_order():
    data = request.get_json()
    order_id = data.get("order_id")
    order = dao.get_order_by_id(order_id)
    if order:
        return jsonify({'success': True, 'order': {
            'first_name': order.customer.first_name,
            'last_name': order.customer.last_name,
            'total_price': dao.get_total_price(order),
            'phone_number': order.customer.phone_number,
            'order_status': order.order_status.value
        }
                        })
    return jsonify({'success': False, 'message': "order not found"})


@app.route('/staff/sell-book', methods=['GET'])
@role_required(['nhanVien'])
def sell_book():
    query = request.args.get('query')
    page = request.args.get('page', 1, type=int)
    page_size = 6
    inventory = dao.get_inventory(q=query, page=page, page_size=page_size)
    total = dao.get_count_inventory(query=query)
    return render_template('/staff/sell_book.html', inventory=inventory, pages=math.ceil(total / page_size),
                           current_page=page, query=query)


@app.route('/staff/sell-book/find-customer-by-email', methods=['POST'])
@role_required(['nhanVien'])
def find_customer_email():
    data = request.get_json()
    email = data.get('email')
    user = dao.find_customer_by_email(email)
    if user is None:
        return jsonify({'success': False, 'message': 'email not found'})
    return jsonify({'success': True, 'user': user.to_dic()})


@app.route('/staff/sell-book/checkout', methods=['POST'])
@role_required(['nhanVien'])
def staff_checkout():
    data = request.get_json()
    customer_id = data.get('customer_id')
    seller_id = data.get('seller_id')
    order = models.Order(customer_id=customer_id, employee_id=seller_id, order_status=OrderStatus.DONE)

    order_details = data.get('order_details')
    if order_details is None:
        return jsonify({'success': False, 'message': 'order not found'})
    ods = []
    order_details = json.loads(order_details)
    for order_detail in order_details:
        if utils.check_existing_inventory(order_detail.get('id'), order_detail.get('quantity')):
            od = models.OrderDetail(book_id=order_detail.get('id'), quantity=order_detail.get('quantity'),
                                    unit_price=order_detail.get('quantity') * order_detail.get('price'))
            ods.append(od)
        else:
            book_in_inventory = dao.get_book_in_inventory(order_detail.get('id'))
            if not book_in_inventory:
                return jsonify({'success': False, 'message': f'{order_detail.get("name")} not found in inventory'})
            return jsonify({'success': False,
                            'message': f'Maximum of {order_detail.get("name")} is {book_in_inventory.current_quantity}'})
    order.order_details = ods
    dao.export_out_to_inventory(order.order_details)
    db.session.add(order)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Checkout done'})


# store manager

@app.route('/store_manager', methods=['GET'])
@role_required(['quanLyKho'])
def store_manager():
    books = dao.get_all_book()
    genres = dao.get_all_genre()
    authors = dao.get_all_author()
    return render_template('/store_manager/store_manager.html', books=books, genres=genres, authors=authors)


@app.route('/store_manager/add_genres', methods=['POST'])
@role_required(['quanLyKho'])
def add_genres():
    try:
        data = request.get_json()
        for genre in data:
            g = models.Genre(name=genre)
            db.session.add(g)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Genres added'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Add genres failed'})


@app.route('/store_manager/add_authors', methods=['POST'])
@role_required(['quanLyKho'])
def add_authors():
    try:
        data = request.get_json()
        for author in data:
            a = models.Author(name=author)
            db.session.add(a)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Authors added'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Add authors failed'})


@app.route('/store_manager/add_books', methods=['POST'])
@role_required(['quanLyKho'])
def add_books():
    try:
        books_data = json.loads(request.form['books'])
        image_url = ""
        index = 0
        for book_data in books_data:
            authors = dao.find_authors(book_data.get('authors'))
            genres = dao.find_genres(book_data.get('genres'))
            del book_data['authors']
            del book_data['genres']
            if request.files:
                image_file = request.files[f'images[{index}]']
                try:
                    upload_result = cloudinary.uploader.upload(image_file)
                    print(upload_result)
                    image_url = upload_result['secure_url']
                except Exception as e:
                    err_msg = f"Avatar upload failed: {str(e)}"
                    return jsonify({'success': False, 'message': 'Upload image failed'})
            book = models.Book(**book_data, authors=authors, genres=genres, image=image_url)
            db.session.add(book)
            index += 1
        db.session.commit()
        return jsonify({'success': True, 'message': 'Books added'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Add books failed'})


@app.route('/store_manager/import_books', methods=['POST'])
@role_required(['quanLyKho'])
def import_books():
    try:
        data = request.get_json()
        if dao.check_inventory(data):
            book_receipt = dao.create_book_receipt(current_user.id)
            book_receipt_arr = []
            for item in data:
                book_receipt_detail = dao.create_book_receipt_detail(item, book_receipt)
                book_receipt_arr.append(book_receipt_detail)
            dao.import_into_inventory(book_receipt_arr)
            return jsonify({'success': True, 'message': 'Import book done'})
        else:
            raise Exception('Số lượng không phù hợp')
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


# admin

@app.route('/admin', methods=['GET'])
@role_required(['admin'])
def admin():
    revenue_data = dao.get_revenue_by_month()
    total_book_in_invetory = dao.get_total_quantity_in_inventory()
    sales_data_by_book = dao.get_sales_data_by_month_and_book()
    sales_data_by_month = defaultdict(lambda: defaultdict(int))

    for month, year, book, sales in sales_data_by_book:
        key = f"{month}/{year}"
        sales_data_by_month[key][book] += sales
    return render_template('/admin/my_index.html', revenue_data=revenue_data,
                           total_book_in_invetory=total_book_in_invetory, sales_data_by_month=sales_data_by_month)


@app.route('/update_config_system', methods=['PUT'])
@role_required(['admin'])
def update_config_system():
    try:
        data = request.get_json()
        dao.update_config_system(data)
        return jsonify({'success': True, 'message': 'Config system updated'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


if __name__ == '__main__':
    from app.admin import *

    app.run(debug=True)
