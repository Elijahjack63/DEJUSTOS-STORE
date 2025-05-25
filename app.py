# app.py
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from database import db
from orders import orders_bp
from auth import auth_bp
from sqlalchemy import and_
from models import Product
import json
import os

app = Flask(__name__, static_folder='build', static_url_path='/')
CORS(app)

# ✅ Use PostgreSQL from Render env variable
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

# ⚠️ Optional: Only use create_all() if NOT using Flask-Migrate
# with app.app_context():
#     db.create_all()

# ✅ Serve React frontend
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# API Routes
@app.route('/tables')
def show_tables():
    inspector = db.inspect(db.engine)
    return {'tables': inspector.get_table_names()}

@app.route('/api/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    return jsonify([product.to_dict() for product in products])

@app.route('/api/products/<int:id>', methods=['GET'])
def get_product(id):
    product = Product.query.get(id)
    if product:
        return jsonify(product.to_dict())
    else:
        return jsonify({"error": "Product not found"}), 404

@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.json
    new_product = Product(
        name=data['name'],
        description=data.get('description'),
        price=data['price'],
        image_url=data.get('image_url'),
        category=data.get('category'),
        stock=data.get('stock', 0),
        images=json.dumps(data.get('images', [])),
        is_popular=data.get('is_popular', False)
    )
    db.session.add(new_product)
    db.session.commit()
    return jsonify(new_product.to_dict()), 201

@app.route('/api/popular-products', methods=['GET'])
def get_popular_products():
    popular_products = Product.query.filter_by(is_popular=True).all()
    return jsonify([product.to_dict() for product in popular_products])

@app.route('/api/category/<slug>', methods=['GET'])
def get_products_by_category(slug):
    sort = request.args.get('sort')
    in_stock = request.args.get('inStock')
    min_price = float(request.args.get('minPrice', 0))
    max_price = float(request.args.get('maxPrice', 1e6))

    filters = [Product.category == slug, Product.price >= min_price, Product.price <= max_price]

    if in_stock == 'true':
        filters.append(Product.stock > 0)
    elif in_stock == 'false':
        filters.append(Product.stock == 0)

    query = Product.query.filter(and_(*filters))
    products = query.all()

    return jsonify([product.to_dict() for product in products])

@app.route('/api/products/<int:id>', methods=['PUT'])
def update_product(id):
    product = Product.query.get_or_404(id)
    data = request.json
    product.name = data['name']
    product.description = data.get('description')
    product.price = data['price']
    product.image_url = data.get('image_url')
    product.category = data.get('category')
    product.stock = data.get('stock', product.stock)
    product.images = json.dumps(data.get('images', []))
    db.session.commit()
    return jsonify(product.to_dict())

@app.route('/api/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted"})

# Register blueprints
app.register_blueprint(orders_bp)
app.register_blueprint(auth_bp)

# ✅ Run the server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)

