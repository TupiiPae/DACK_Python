from flask import Flask, render_template, request, flash, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os
from functools import wraps
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, TextAreaField, DecimalField, IntegerField, SelectField, FileField, SubmitField
from wtforms.validators import DataRequired, NumberRange
from flask_wtf.file import FileField, FileAllowed
from flask import current_app

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.urandom(24)  # Tạo secret key ngẫu nhiên
app.config['UPLOAD_FOLDER'] = 'static/uploads'  # Thư mục lưu ảnh upload
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
# Cấu hình upload trong app.py hoặc __init__.py
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # giới hạn kích thước file (16MB)



# Decorator kiểm tra admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Bạn không có quyền truy cập trang này!', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

import os
from werkzeug.utils import secure_filename

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(uploaded_file):
    """
    Save the uploaded image to the configured upload folder
    Args:
        uploaded_file: FileStorage object from form submission
    Returns:
        str: filename of saved image or None if save failed
    """
    if not uploaded_file:
        return None

    # Define allowed extensions
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    try:
        # Get original filename and check extension
        original_filename = uploaded_file.filename
        extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else None
        
        if extension not in ALLOWED_EXTENSIONS:
            return None

        # Create unique filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = secure_filename(f"{timestamp}_{original_filename}")
        
        # Get upload folder path from app config
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
        
        # Create upload folder if it doesn't exist
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        # Save the file
        file_path = os.path.join(upload_folder, filename)
        uploaded_file.save(file_path)
        
        return filename

    except Exception as e:
        current_app.logger.error(f"Error saving image: {str(e)}")
        return None
    
# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    full_name = db.Column(db.String(150))
    address = db.Column(db.String(500))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cart_items = db.relationship('CartItem', backref='user', lazy=True)
    orders = db.relationship('Order', backref='user', lazy=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    products = db.relationship('Product', backref='category', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    sale_price = db.Column(db.Float)  # Giá khuyến mãi
    image_url = db.Column(db.String(500))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    stock = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    cart_items = db.relationship('CartItem', backref='product', lazy=True)
    order_items = db.relationship('OrderItem', backref='product', lazy=True)
    
class ProductForm(FlaskForm):
    name = StringField('Tên sản phẩm', validators=[DataRequired()])
    price = FloatField('Giá', validators=[DataRequired(), NumberRange(min=0)])
    stock = IntegerField('Số lượng trong kho', validators=[DataRequired(), NumberRange(min=0)])
    category_id = SelectField('Danh mục', coerce=int, validators=[DataRequired()])
    description = TextAreaField('Mô tả')
    image = FileField('Hình ảnh sản phẩm', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Chỉ cho phép file ảnh!')
    ])

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(50), default='pending')
    total_amount = db.Column(db.Float, nullable=False)
    shipping_address = db.Column(db.String(500), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes cho người dùng
@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 12  # Số sản phẩm mỗi trang
    categories = Category.query.all()
    category_id = request.args.get('category', type=int)
    search_query = request.args.get('search', '')
    
    products_query = Product.query
    if category_id:
        products_query = products_query.filter_by(category_id=category_id)
    if search_query:
        products_query = products_query.filter(Product.name.ilike(f'%{search_query}%'))
    
    products = products_query.paginate(page=page, per_page=per_page, error_out=False)
    return render_template('index.html', products=products, categories=categories)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    related_products = Product.query.filter_by(category_id=product.category_id).filter(Product.id != product_id).limit(4).all()
    return render_template('product_detail.html', product=product, related_products=related_products)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Mật khẩu không khớp!', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Tên đăng nhập đã tồn tại!', 'danger')
            return redirect(url_for('register'))
            
        if User.query.filter_by(email=email).first():
            flash('Email đã được sử dụng!', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            full_name=request.form.get('full_name'),
            address=request.form.get('address'),
            phone=request.form.get('phone')
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Đăng ký thành công! Vui lòng đăng nhập.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('index'))
        flash('Tên đăng nhập hoặc mật khẩu không đúng!', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.full_name = request.form.get('full_name')
        current_user.email = request.form.get('email')
        current_user.address = request.form.get('address')
        current_user.phone = request.form.get('phone')
        
        if request.form.get('new_password'):
            if check_password_hash(current_user.password, request.form.get('current_password')):
                current_user.password = generate_password_hash(request.form.get('new_password'))
            else:
                flash('Mật khẩu hiện tại không đúng!', 'danger')
                return redirect(url_for('profile'))
                
        db.session.commit()
        flash('Cập nhật thông tin thành công!', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html')

# Routes cho giỏ hàng và đặt hàng
@app.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity', 1))
    
    if quantity > product.stock:
        flash(f'Chỉ còn {product.stock} sản phẩm trong kho!', 'danger')
        return redirect(url_for('product_detail', product_id=product_id))
        
    cart_item = CartItem.query.filter_by(
        user_id=current_user.id,
        product_id=product_id
    ).first()
    
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(
            user_id=current_user.id,
            product_id=product_id,
            quantity=quantity
        )
        db.session.add(cart_item)
    
    db.session.commit()
    flash('Đã thêm vào giỏ hàng!', 'success')
    return redirect(url_for('product_detail', product_id=product_id))

@app.route('/cart')
@login_required
def view_cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def update_cart(item_id):
    cart_item = CartItem.query.get_or_404(item_id)
    if cart_item.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    quantity = int(request.form.get('quantity'))
    if quantity > cart_item.product.stock:
        return jsonify({
            'error': f'Chỉ còn {cart_item.product.stock} sản phẩm trong kho!'
        }), 400
        
    cart_item.quantity = quantity
    db.session.commit()
    return jsonify({
        'message': 'Updated successfully',
        'subtotal': cart_item.product.price * quantity,
        'total': sum(item.product.price * item.quantity 
                    for item in current_user.cart_items)
    })

@app.route('/cart/remove/<int:item_id>')
@login_required
def remove_from_cart(item_id):
    cart_item = CartItem.query.get_or_404(item_id)
    if cart_item.user_id == current_user.id:
        db.session.delete(cart_item)
        db.session.commit()
    return redirect(url_for('view_cart'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Giỏ hàng trống!', 'danger')
        return redirect(url_for('view_cart'))
        
    if request.method == 'POST':
        # Kiểm tra lại số lượng tồn kho
        for item in cart_items:
            if item.quantity > item.product.stock:
                flash(f'Sản phẩm {item.product.name} chỉ còn {item.product.stock} trong kho!', 'danger')
                return redirect(url_for('checkout'))
        
        # Tạo đơn hàng
        order = Order(
            user_id=current_user.id,
            shipping_address=request.form.get('address'),
            phone=request.form.get('phone'),
            note=request.form.get('note'),
            total_amount=sum(item.product.price * item.quantity for item in cart_items)
        )
        db.session.add(order)
        
        # Thêm chi tiết đơn hàng
        for cart_item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity,
                price=cart_item.product.price
            )
            db.session.add(order_item)
            
            # Cập nhật số lượng tồn kho
            cart_item.product.stock -= cart_item.quantity
            
            # Xóa item khỏi giỏ hàng
            db.session.delete(cart_item)
        
        db.session.commit()
        flash('Đặt hàng thành công!', 'success')
        return redirect(url_for('view_orders'))
        
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('checkout.html', cart_items=cart_items, total=total)

@app.route('/orders')
@login_required
def view_orders():
    orders = Order.query.filter_by(user_id=current_user.id)\
        .order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=orders)
@app.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and not current_user.is_admin:
        flash('Bạn không có quyền xem đơn hàng này!', 'danger')
        return redirect(url_for('view_orders'))
    return render_template('order_detail.html', order=order)

# Routes cho admin
@app.route('/admin')
@admin_required
def admin_dashboard():
    total_users = User.query.count()
    total_orders = Order.query.count()
    total_products = Product.query.count()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    low_stock_products = Product.query.filter(Product.stock < 10).all()
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_orders=total_orders,
                         total_products=total_products,
                         recent_orders=recent_orders,
                         low_stock_products=low_stock_products)

@app.route('/admin/products')
@admin_required
def admin_products():
    page = request.args.get('page', 1, type=int)
    products = Product.query.order_by(Product.created_at.desc())\
        .paginate(page=page, per_page=20)
    categories = Category.query.all()
    
    return render_template('admin/products.html', 
                           products=products,
                           categories=categories)

@app.route('/admin/product/new', methods=['GET', 'POST'])
@admin_required
def admin_new_product():
    form = ProductForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]

    if form.validate_on_submit():
        try:
            # Xử lý upload ảnh
            image_filename = None
            if form.image.data:
                image_filename = save_image(form.image.data)
                if not image_filename:
                    flash('Lỗi khi upload ảnh. Vui lòng kiểm tra định dạng file.', 'error')
                    return render_template('admin/product_form.html', form=form)

            # Tạo sản phẩm mới
            new_product = Product(
                name=form.name.data,
                price=form.price.data,
                stock=form.stock.data,
                category_id=form.category_id.data,
                description=form.description.data,
                image_url=image_filename
            )
            
            db.session.add(new_product)
            db.session.commit()

            flash('Sản phẩm mới đã được thêm thành công!', 'success')
            return redirect(url_for('admin_products'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating product: {str(e)}")
            flash('Có lỗi xảy ra khi thêm sản phẩm. Vui lòng thử lại.', 'error')
            
    return render_template('admin/product_form.html', form=form)

@app.route('/admin/product/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(product_id):
    product = Product.query.get_or_404(product_id)  # Fetch the product by ID
    form = ProductForm(obj=product)  # Prepopulate the form with the product data
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]  # Populate categories

    if form.validate_on_submit():
        # Update product attributes with the form data
        product.name = form.name.data
        product.description = form.description.data
        product.price = form.price.data
        product.stock = form.stock.data
        product.category_id = form.category_id.data

        # Handle file upload for the image (if necessary)
        if form.image.data:
            # Assuming you have a method to handle image saving
            product.image_url = save_image(form.image.data)

        # Commit the changes to the database
        db.session.commit()
        flash('Product updated successfully!', 'success')  # Flash a success message
        return redirect(url_for('admin_products'))  # Redirect to the products list

    return render_template('admin/product_form.html', form=form)


@app.route('/admin/product/delete/<int:product_id>', methods=['POST'])
@admin_required
def admin_delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.image_url:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], product.image_url))
        except:
            pass
    db.session.delete(product)
    db.session.commit()
    flash('Đã xóa sản phẩm!', 'success')
    return redirect(url_for('admin_products'))

@app.route('/admin/product/delete/<int:product_id>', methods=['GET'])
@admin_required
def admin_delete_product_confirm(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('admin/delete_product.html', product=product)


@app.route('/admin/categories')
@admin_required
def admin_categories():
    categories = Category.query.all()
    return render_template('admin/categories.html', categories=categories)

@app.route('/admin/category/new', methods=['GET', 'POST'])
@admin_required
def admin_new_category():
    if request.method == 'POST':
        category = Category(
            name=request.form.get('name'),
            description=request.form.get('description')
        )
        db.session.add(category)
        db.session.commit()
        flash('Thêm danh mục thành công!', 'success')
        return redirect(url_for('admin_categories'))
    return render_template('admin/category_form.html')

@app.route('/admin/category/edit/<int:category_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_category(category_id):
    category = Category.query.get_or_404(category_id)
    if request.method == 'POST':
        category.name = request.form.get('name')
        category.description = request.form.get('description')
        db.session.commit()
        flash('Cập nhật danh mục thành công!', 'success')
        return redirect(url_for('admin_categories'))
    return render_template('admin/category_form.html', category=category)

@app.route('/admin/category/delete/<int:category_id>', methods=['POST'])
@admin_required
def admin_delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    if category.products:
        flash('Không thể xóa danh mục đang có sản phẩm!', 'danger')
    else:
        db.session.delete(category)
        db.session.commit()
        flash('Đã xóa danh mục!', 'success')
    return redirect(url_for('admin_categories'))

@app.route('/admin/orders')
@admin_required
def admin_orders():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status')
    
    query = Order.query
    if status:
        query = query.filter_by(status=status)
        
    orders = query.order_by(Order.created_at.desc())\
        .paginate(page=page, per_page=20)
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/order/<int:order_id>')
@admin_required
def admin_order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('admin/order_detail.html', order=order)

@app.route('/admin/order/status/<int:order_id>', methods=['POST'])
@admin_required
def admin_update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    status = request.form.get('status')
    if status in ['pending', 'confirmed', 'shipping', 'completed', 'cancelled']:
        order.status = status
        db.session.commit()
        flash('Cập nhật trạng thái đơn hàng thành công!', 'success')
    return redirect(url_for('admin_order_detail', order_id=order_id))

if __name__ == '__main__':
    app.run(debug=True)