#!/usr/bin/env python3
"""
Retail Chain Inventory Tracker
Main Flask Application

This application provides comprehensive inventory management for retail chains,
including user authentication, AI-powered predictions, warehouse management,
and detailed reporting capabilities.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime, timedelta
import logging

# Import custom modules
from auth.roles import RoleManager
from auth.session_manager import SessionManager
from ai_engine.predictor import InventoryPredictor
from warehouse.warehouse_controller import WarehouseController
from reports.exporter import ReportExporter
from api.inventory_api import InventoryAPI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

# Configuration
DATABASE_PATH = 'database/inventory.db'
app.config['DATABASE'] = DATABASE_PATH

# Initialize components
role_manager = RoleManager()
session_manager = SessionManager()
inventory_predictor = InventoryPredictor()
warehouse_controller = WarehouseController()
report_exporter = ReportExporter()
inventory_api = InventoryAPI()

def init_database():
    """Initialize the SQLite database with required tables."""
    if not os.path.exists('database'):
        os.makedirs('database')
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            full_name TEXT,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'employee',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # Products table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            sku TEXT UNIQUE NOT NULL,
            barcode TEXT,
            description TEXT,
            unit_price REAL NOT NULL,
            cost_price REAL,
            supplier_id INTEGER,
            reorder_level INTEGER DEFAULT 10,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Inventory table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            warehouse_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            reserved_quantity INTEGER NOT NULL DEFAULT 0,
            reorder_level INTEGER NOT NULL DEFAULT 10,
            max_stock_level INTEGER NOT NULL DEFAULT 1000,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id),
            FOREIGN KEY (warehouse_id) REFERENCES warehouses (id)
        )
    ''')
    
    # Warehouses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS warehouses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            capacity INTEGER,
            manager_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (manager_id) REFERENCES users (id)
        )
    ''')
    
    # Suppliers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact_person TEXT,
            email TEXT,
            phone TEXT,
            address TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Stock movements table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            warehouse_id INTEGER NOT NULL,
            movement_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            reference_number TEXT,
            notes TEXT,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id),
            FOREIGN KEY (warehouse_id) REFERENCES warehouses (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Alerts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type TEXT NOT NULL,
            product_id INTEGER,
            warehouse_id INTEGER,
            message TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'medium',
            is_read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id),
            FOREIGN KEY (warehouse_id) REFERENCES warehouses (id)
        )
    ''')
    
    # Create default admin user
    cursor.execute('SELECT * FROM users WHERE username = ?', ('admin',))
    if cursor.fetchone() is None:
        admin_password = generate_password_hash('admin123')
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, role)
            VALUES (?, ?, ?, ?)
        ''', ('admin', 'admin@retailtracker.com', admin_password, 'admin'))
    
    # Create sample warehouse
    cursor.execute('SELECT * FROM warehouses WHERE name = ?', ('Main Warehouse',))
    if cursor.fetchone() is None:
        cursor.execute('''
            INSERT INTO warehouses (name, location, capacity)
            VALUES (?, ?, ?)
        ''', ('Main Warehouse', 'New York, NY', 10000))
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")



# Authentication routes
@app.route('/')
def index():
    """Redirect to login or dashboard based on authentication."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id, password_hash, role FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['username'] = username
            session['role'] = user[2]
            
            # Update last login
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', (datetime.now(), user[0]))
            conn.commit()
            conn.close()
            
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page."""
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'employee')
        
        # Validation
        if not all([full_name, username, email, password, confirm_password]):
            flash('All fields are required.', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('register.html')
        
        if len(username) < 3 or len(username) > 50:
            flash('Username must be 3-50 characters long.', 'error')
            return render_template('register.html')
        
        # Role validation (only admin can assign roles)
        if session.get('role') != 'admin':
            role = 'employee'  # Default role for non-admin registrations
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        try:
            # Check if username or email already exists
            cursor.execute('SELECT username, email FROM users WHERE username = ? OR email = ?', 
                          (username, email))
            existing_user = cursor.fetchone()
            
            if existing_user:
                if existing_user[0] == username:
                    flash('Username already exists. Please choose a different one.', 'error')
                else:
                    flash('Email address already registered. Please use a different email.', 'error')
                conn.close()
                return render_template('register.html')
            
            # Create new user
            hashed_password = generate_password_hash(password)
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, role, full_name, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, email, hashed_password, role, full_name, datetime.now()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"New user registered: {username} ({email}) with role {role}")
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
            
        except sqlite3.Error as e:
            conn.close()
            logger.error(f"Database error during registration: {e}")
            flash('Registration failed. Please try again.', 'error')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    """Main dashboard with key metrics."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Get key metrics
    cursor.execute('SELECT COUNT(*) FROM products')
    total_products = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(quantity) FROM inventory')
    total_inventory = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(*) FROM alerts WHERE is_read = 0')
    unread_alerts = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM warehouses')
    total_warehouses = cursor.fetchone()[0]
    
    # Get low stock alerts
    cursor.execute('''
        SELECT p.name, i.quantity, i.reorder_level, w.name
        FROM inventory i
        JOIN products p ON i.product_id = p.id
        JOIN warehouses w ON i.warehouse_id = w.id
        WHERE i.quantity <= i.reorder_level
        ORDER BY i.quantity ASC
        LIMIT 5
    ''')
    low_stock_items = cursor.fetchall()
    
    # Get recent stock movements
    cursor.execute('''
        SELECT p.name, sm.movement_type, sm.quantity, w.name, sm.created_at
        FROM stock_movements sm
        JOIN products p ON sm.product_id = p.id
        JOIN warehouses w ON sm.warehouse_id = w.id
        ORDER BY sm.created_at DESC
        LIMIT 10
    ''')
    recent_movements = cursor.fetchall()
    
    conn.close()
    
    return render_template('dashboard.html',
                         total_products=total_products,
                         total_inventory=total_inventory,
                         unread_alerts=unread_alerts,
                         total_warehouses=total_warehouses,
                         low_stock_items=low_stock_items,
                         recent_movements=recent_movements)

@app.route('/inventory')
def inventory():
    """Inventory management page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Get inventory data with product and warehouse info
    cursor.execute('''
        SELECT p.id, p.name, p.category, p.sku, i.quantity, i.reorder_level,
               w.name as warehouse_name, p.unit_price
        FROM inventory i
        JOIN products p ON i.product_id = p.id
        JOIN warehouses w ON i.warehouse_id = w.id
        ORDER BY p.name
    ''')
    inventory_data = cursor.fetchall()
    
    conn.close()
    
    return render_template('inventory.html', inventory_data=inventory_data)

@app.route('/alerts')
def alerts():
    """Alerts and notifications page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Get existing alerts from alerts table
    cursor.execute('''
        SELECT a.id, a.alert_type, a.message, a.severity, a.is_read, a.created_at,
               p.name as product_name, w.name as warehouse_name
        FROM alerts a
        LEFT JOIN products p ON a.product_id = p.id
        LEFT JOIN warehouses w ON a.warehouse_id = w.id
        ORDER BY a.created_at DESC
    ''')
    alerts_data = cursor.fetchall()

    # Get low stock alerts (real-time detection)
    cursor.execute('''
        SELECT p.id, p.name, p.sku, p.reorder_level, w.name as warehouse_name,
               COALESCE(i.quantity, 0) as current_stock
        FROM products p
        LEFT JOIN inventory i ON p.id = i.product_id
        LEFT JOIN warehouses w ON i.warehouse_id = w.id
        WHERE p.reorder_level > 0 AND COALESCE(i.quantity, 0) <= p.reorder_level
        ORDER BY (COALESCE(i.quantity, 0) * 1.0 / NULLIF(p.reorder_level, 1)) ASC
    ''')
    low_stock_alerts = cursor.fetchall()

    # Get zero stock alerts
    cursor.execute('''
        SELECT p.id, p.name, p.sku, w.name as warehouse_name
        FROM products p
        LEFT JOIN inventory i ON p.id = i.product_id
        LEFT JOIN warehouses w ON i.warehouse_id = w.id
        WHERE COALESCE(i.quantity, 0) = 0
        ORDER BY p.name
    ''')
    zero_stock_alerts = cursor.fetchall()
    
    conn.close()
    
    return render_template('alerts.html', 
                         alerts_data=alerts_data,
                         low_stock_alerts=low_stock_alerts,
                         zero_stock_alerts=zero_stock_alerts)

@app.route('/warehouse')
def warehouse():
    """Warehouse management page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT w.id, w.name, w.location, w.capacity,
               COUNT(i.id) as total_products,
               SUM(i.quantity) as total_inventory
        FROM warehouses w
        LEFT JOIN inventory i ON w.id = i.warehouse_id
        GROUP BY w.id, w.name, w.location, w.capacity
    ''')
    warehouses_data = cursor.fetchall()
    
    conn.close()
    
    return render_template('warehouse.html', warehouses_data=warehouses_data)

@app.route('/products')
def products():
    """Products management page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Get products with stock information
    cursor.execute('''
        SELECT p.id, p.name, p.category, p.sku, p.barcode, p.description,
               p.unit_price, p.cost_price, p.supplier_id, p.created_at, p.updated_at,
               COALESCE(SUM(i.quantity), 0) as total_stock,
               COALESCE(MIN(i.reorder_level), 10) as reorder_level
        FROM products p
        LEFT JOIN inventory i ON p.id = i.product_id
        GROUP BY p.id, p.name, p.category, p.sku, p.barcode, p.description,
                 p.unit_price, p.cost_price, p.supplier_id, p.created_at, p.updated_at
        ORDER BY p.name
    ''')
    
    products_data = []
    for row in cursor.fetchall():
        products_data.append({
            'id': row[0], 'name': row[1], 'category': row[2], 'sku': row[3],
            'barcode': row[4], 'description': row[5], 'unit_price': row[6],
            'cost_price': row[7], 'supplier_id': row[8], 'created_at': row[9],
            'updated_at': row[10], 'total_stock': row[11], 'reorder_level': row[12]
        })
    
    # Get unique categories
    cursor.execute('SELECT DISTINCT category FROM products ORDER BY category')
    categories = [row[0] for row in cursor.fetchall()]
    
    # Get suppliers
    cursor.execute('SELECT id, name FROM suppliers ORDER BY name')
    suppliers = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
    
    conn.close()
    
    return render_template('products.html', products_data=products_data, 
                          categories=categories, suppliers=suppliers)

@app.route('/add_product', methods=['POST'])
def add_product():
    """Add new product."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        name = request.form.get('name', '').strip()
        sku = request.form.get('sku', '').strip()
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        unit_price = float(request.form.get('unit_price', 0))
        cost_price = float(request.form.get('cost_price', 0) or 0)
        barcode = request.form.get('barcode', '').strip()
        supplier_id = request.form.get('supplier_id') or None
        
        if not all([name, sku, category]) or unit_price <= 0:
            flash('Name, SKU, category, and valid unit price are required.', 'error')
            return redirect(url_for('products'))
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check if SKU already exists
        cursor.execute('SELECT id FROM products WHERE sku = ?', (sku,))
        if cursor.fetchone():
            flash('SKU already exists. Please use a unique SKU.', 'error')
            conn.close()
            return redirect(url_for('products'))
        
        # Insert product
        cursor.execute('''
            INSERT INTO products (name, category, sku, barcode, description,
                                unit_price, cost_price, supplier_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, category, sku, barcode or None, description or None,
              unit_price, cost_price, supplier_id))
        
        conn.commit()
        conn.close()
        
        flash('Product added successfully!', 'success')
        
    except ValueError:
        flash('Invalid price values. Please enter valid numbers.', 'error')
    except Exception as e:
        logger.error(f'Error adding product: {e}')
        flash('Failed to add product. Please try again.', 'error')
    
    return redirect(url_for('products'))

@app.route('/edit_product/<int:product_id>')
def edit_product(product_id):
    """Edit product page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    
    if not product:
        flash('Product not found.', 'error')
        return redirect(url_for('products'))
    
    conn.close()
    return render_template('edit_product.html', product=product)

@app.route('/update_product/<int:product_id>', methods=['POST'])
def update_product(product_id):
    """Update existing product."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        name = request.form.get('name', '').strip()
        sku = request.form.get('sku', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        unit_price = float(request.form.get('unit_price', 0))
        reorder_level = int(request.form.get('reorder_level', 0))
        supplier_id = request.form.get('supplier_id')
        
        if not all([name, sku]):
            flash('Product name and SKU are required.', 'error')
            return redirect(url_for('edit_product', product_id=product_id))
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check for duplicate SKU (excluding current product)
        cursor.execute('SELECT id FROM products WHERE sku = ? AND id != ?', (sku, product_id))
        if cursor.fetchone():
            flash('SKU already exists. Please use a different SKU.', 'error')
            conn.close()
            return redirect(url_for('edit_product', product_id=product_id))
        
        cursor.execute('''
            UPDATE products SET name = ?, sku = ?, description = ?, category = ?,
                              unit_price = ?, reorder_level = ?, supplier_id = ?
            WHERE id = ?
        ''', (name, sku, description or None, category or None,
              unit_price, reorder_level, supplier_id or None, product_id))
        
        conn.commit()
        conn.close()
        
        flash('Product updated successfully!', 'success')
        
    except Exception as e:
        logger.error(f'Error updating product: {e}')
        flash('Failed to update product. Please try again.', 'error')
    
    return redirect(url_for('products'))

@app.route('/suppliers')
def suppliers():
    """Suppliers management page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT s.id, s.name, s.contact_person, s.email, s.phone,
               s.address, s.created_at,
               COUNT(p.id) as product_count
        FROM suppliers s
        LEFT JOIN products p ON s.id = p.supplier_id
        GROUP BY s.id, s.name, s.contact_person, s.email, s.phone,
                 s.address, s.created_at
        ORDER BY s.name
    ''')
    suppliers_data = cursor.fetchall()
    
    conn.close()
    
    return render_template('suppliers.html', suppliers_data=suppliers_data)

@app.route('/add_supplier', methods=['POST'])
def add_supplier():
    """Add new supplier."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        name = request.form.get('name', '').strip()
        contact_person = request.form.get('contact_person', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        notes = request.form.get('notes', '').strip()
        
        if not name:
            flash('Supplier name is required.', 'error')
            return redirect(url_for('suppliers'))
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO suppliers (name, contact_person, email, phone, address, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, contact_person or None, email or None, 
              phone or None, address or None, notes or None))
        
        conn.commit()
        conn.close()
        
        flash('Supplier added successfully!', 'success')
        
    except Exception as e:
        logger.error(f'Error adding supplier: {e}')
        flash('Failed to add supplier. Please try again.', 'error')
    
    return redirect(url_for('suppliers'))

@app.route('/bulk_product_action', methods=['POST'])
def bulk_product_action():
    """Handle bulk product operations."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        action = request.form.get('bulk_action')
        product_ids = request.form.getlist('product_ids')
        
        if not action or not product_ids:
            flash('Please select an action and products.', 'error')
            return redirect(url_for('products'))
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        if action == 'delete':
            placeholders = ','.join(['?' for _ in product_ids])
            cursor.execute(f'DELETE FROM products WHERE id IN ({placeholders})', product_ids)
            flash(f'{len(product_ids)} product(s) deleted successfully!', 'success')
            
        elif action == 'update_category':
            new_category = request.form.get('new_category', '').strip()
            if new_category:
                placeholders = ','.join(['?' for _ in product_ids])
                cursor.execute(f'UPDATE products SET category = ? WHERE id IN ({placeholders})', 
                             [new_category] + product_ids)
                flash(f'{len(product_ids)} product(s) category updated!', 'success')
            else:
                flash('Category is required for bulk update.', 'error')
                
        elif action == 'export':
            # Export selected products to CSV
            placeholders = ','.join(['?' for _ in product_ids])
            cursor.execute(f'SELECT * FROM products WHERE id IN ({placeholders})', product_ids)
            products = cursor.fetchall()
            
            # Create CSV response
            import csv
            from io import StringIO
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(['ID', 'Name', 'SKU', 'Description', 'Category', 'Unit Price', 'Reorder Level'])
            for product in products:
                writer.writerow(product[:7])  # First 7 columns
            
            response = app.response_class(
                response=output.getvalue(),
                status=200,
                mimetype='text/csv',
                headers={'Content-Disposition': 'attachment; filename=products_export.csv'}
            )
            conn.close()
            return response
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f'Error in bulk product action: {e}')
        flash('Bulk operation failed. Please try again.', 'error')
    
    return redirect(url_for('products'))

@app.route('/stock_movements')
def stock_movements():
    """Stock movements tracking page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT sm.id, sm.movement_type, sm.quantity, sm.reference_number,
               sm.notes, sm.created_at, p.name as product_name, 
               w.name as warehouse_name, u.username as user_name
        FROM stock_movements sm
        JOIN products p ON sm.product_id = p.id
        JOIN warehouses w ON sm.warehouse_id = w.id
        LEFT JOIN users u ON sm.user_id = u.id
        ORDER BY sm.created_at DESC
        LIMIT 100
    ''')
    
    movements_data = cursor.fetchall()
    conn.close()
    
    return render_template('stock_movements.html', movements_data=movements_data)

@app.route('/add_stock_movement', methods=['POST'])
def add_stock_movement():
    """Add new stock movement."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        movement_type = request.form.get('movement_type')
        product_id = request.form.get('product_id')
        warehouse_id = request.form.get('warehouse_id')
        quantity = int(request.form.get('quantity'))
        reference_number = request.form.get('reference_number', '').strip()
        notes = request.form.get('notes', '').strip()
        movement_date = request.form.get('movement_date')
        
        if not all([movement_type, product_id, warehouse_id, quantity]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('stock_movements'))
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Insert stock movement
        cursor.execute('''
            INSERT INTO stock_movements (movement_type, product_id, warehouse_id, 
                                       quantity, reference_number, notes, user_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (movement_type, product_id, warehouse_id, quantity,
              reference_number or None, notes or None, session['user_id'],
              movement_date or datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        # Update inventory based on movement type
        if movement_type in ['in', 'adjustment']:
            # Add to inventory
            cursor.execute('''
                INSERT OR REPLACE INTO inventory (product_id, warehouse_id, quantity)
                VALUES (?, ?, COALESCE(
                    (SELECT quantity FROM inventory WHERE product_id = ? AND warehouse_id = ?), 0
                ) + ?)
            ''', (product_id, warehouse_id, product_id, warehouse_id, quantity))
        elif movement_type in ['out']:
            # Remove from inventory
            cursor.execute('''
                UPDATE inventory SET quantity = quantity - ?
                WHERE product_id = ? AND warehouse_id = ?
            ''', (quantity, product_id, warehouse_id))
        
        conn.commit()
        conn.close()
        
        flash('Stock movement added successfully!', 'success')
        
    except Exception as e:
        logger.error(f'Error adding stock movement: {e}')
        flash('Failed to add stock movement. Please try again.', 'error')
    
    return redirect(url_for('stock_movements'))

@app.route('/admin_panel')
def admin_panel():
    """Admin panel for user and system management."""
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, username, email, role, created_at, last_login FROM users')
    users_data = cursor.fetchall()
    
    conn.close()
    
    return render_template('admin_panel.html', users_data=users_data)

@app.route('/export_reports')
def export_reports():
    """Reports and export page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Get inventory summary stats
    cursor.execute('''
        SELECT COUNT(DISTINCT p.id) as total_products,
               COUNT(DISTINCT w.id) as total_warehouses,
               COALESCE(SUM(i.quantity), 0) as total_stock_units,
               COALESCE(SUM(i.quantity * p.unit_price), 0) as total_stock_value
        FROM products p
        LEFT JOIN inventory i ON p.id = i.product_id
        LEFT JOIN warehouses w ON i.warehouse_id = w.id
    ''')
    
    inventory_stats = cursor.fetchone()
    
    # Get low stock count
    cursor.execute('''
        SELECT COUNT(*) FROM products p
        LEFT JOIN inventory i ON p.id = i.product_id
        WHERE p.reorder_level > 0 AND COALESCE(i.quantity, 0) <= p.reorder_level
    ''')
    low_stock_count = cursor.fetchone()[0]
    
    # Get recent movements count
    cursor.execute('''
        SELECT COUNT(*) FROM stock_movements 
        WHERE created_at > datetime('now', '-30 days')
    ''')
    recent_movements = cursor.fetchone()[0]
    
    # Get top products by stock value
    cursor.execute('''
        SELECT p.name, p.sku, COALESCE(SUM(i.quantity), 0) as total_quantity,
               p.unit_price, COALESCE(SUM(i.quantity), 0) * p.unit_price as stock_value
        FROM products p
        LEFT JOIN inventory i ON p.id = i.product_id
        GROUP BY p.id, p.name, p.sku, p.unit_price
        ORDER BY stock_value DESC
        LIMIT 10
    ''')
    top_products_by_value = cursor.fetchall()
    
    conn.close()
    
    return render_template('export_reports.html',
                         inventory_stats=inventory_stats,
                         low_stock_count=low_stock_count,
                         recent_movements=recent_movements,
                         top_products_by_value=top_products_by_value)

@app.route('/api_docs')
def api_docs():
    """API documentation page."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('api_docs.html')

# API Routes
@app.route('/api/inventory', methods=['GET'])
def api_get_inventory():
    """Get inventory data via API."""
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    return inventory_api.get_inventory()

@app.route('/api/inventory', methods=['POST'])
def api_add_inventory():
    """Add inventory item via API."""
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    return inventory_api.add_inventory(request.json, session['user_id'])

@app.route('/api/inventory/<int:item_id>', methods=['PUT'])
def api_update_inventory(item_id):
    """Update inventory item via API."""
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    return inventory_api.update_inventory(item_id, request.json, session['user_id'])

@app.route('/api/products/<int:product_id>', methods=['GET'])
def api_get_product(product_id):
    """Get product details via API."""
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT p.id, p.name, p.category, p.sku, p.barcode, p.description,
                   p.unit_price, p.cost_price, p.supplier_id, p.created_at, p.updated_at,
                   COALESCE(SUM(i.quantity), 0) as total_stock
            FROM products p
            LEFT JOIN inventory i ON p.id = i.product_id
            WHERE p.id = ?
            GROUP BY p.id
        ''', (product_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            product = {
                'id': row[0], 'name': row[1], 'category': row[2], 'sku': row[3],
                'barcode': row[4], 'description': row[5], 'unit_price': row[6],
                'cost_price': row[7], 'supplier_id': row[8], 'created_at': row[9],
                'updated_at': row[10], 'total_stock': row[11]
            }
            return jsonify({'success': True, 'data': product})
        else:
            return jsonify({'success': False, 'error': 'Product not found'}), 404
            
    except Exception as e:
        logger.error(f'Error getting product: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def api_delete_product(product_id):
    """Delete product via API."""
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check if product has inventory
        cursor.execute('SELECT SUM(quantity) FROM inventory WHERE product_id = ?', (product_id,))
        total_stock = cursor.fetchone()[0] or 0
        
        if total_stock > 0:
            conn.close()
            return jsonify({
                'success': False, 
                'error': 'Cannot delete product with existing inventory'
            }), 400
        
        # Delete product
        cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
        
        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Product deleted successfully'})
        else:
            conn.close()
            return jsonify({'success': False, 'error': 'Product not found'}), 404
            
    except Exception as e:
        logger.error(f'Error deleting product: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/alerts/mark_read/<int:alert_id>', methods=['POST'])
def api_mark_alert_read(alert_id):
    """Mark alert as read via API."""
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE alerts SET is_read = 1 WHERE id = ?', (alert_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success'})

@app.route('/api/predictions/<int:product_id>')
def api_get_predictions(product_id):
    """Get AI predictions for a product."""
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    predictions = inventory_predictor.predict_demand(product_id)
    return jsonify(predictions)

@app.route('/api/products')
def api_products():
    """Get all products for dropdown."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, name, sku FROM products ORDER BY name')
        products = []
        
        for row in cursor.fetchall():
            products.append({
                'id': row[0],
                'name': row[1],
                'sku': row[2]
            })
        
        conn.close()
        return jsonify(products)
    
    except Exception as e:
        logger.error(f'Error fetching products: {e}')
        return jsonify({'error': 'Failed to fetch products'}), 500

@app.route('/api/warehouses')
def api_warehouses():
    """Get all warehouses for dropdown."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, name FROM warehouses ORDER BY name')
        warehouses = []
        
        for row in cursor.fetchall():
            warehouses.append({
                'id': row[0],
                'name': row[1]
            })
        
        conn.close()
        return jsonify(warehouses)
    
    except Exception as e:
        logger.error(f'Error fetching warehouses: {e}')
        return jsonify({'error': 'Failed to fetch warehouses'}), 500

@app.route('/api/suppliers')
def api_suppliers():
    """Get all suppliers for dropdown."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, name FROM suppliers ORDER BY name')
        suppliers = []
        
        for row in cursor.fetchall():
            suppliers.append({
                'id': row[0],
                'name': row[1]
            })
        
        conn.close()
        return jsonify(suppliers)
    
    except Exception as e:
        logger.error(f'Error fetching suppliers: {e}')
        return jsonify({'error': 'Failed to fetch suppliers'}), 500

@app.route('/api/suppliers/<int:supplier_id>', methods=['DELETE'])
def delete_supplier_api(supplier_id):
    """Delete supplier via API."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM suppliers WHERE id = ?', (supplier_id,))
        
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'error': 'Supplier not found'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    
    except Exception as e:
        logger.error(f'Error deleting supplier: {e}')
        return jsonify({'success': False, 'error': 'Failed to delete supplier'}), 500

@app.route('/api/suppliers/<int:supplier_id>', methods=['GET'])
def get_supplier_api(supplier_id):
    """Get supplier details via API."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM suppliers WHERE id = ?', (supplier_id,))
        supplier = cursor.fetchone()
        
        if not supplier:
            return jsonify({'error': 'Supplier not found'}), 404
        
        supplier_data = {
            'id': supplier[0],
            'name': supplier[1],
            'contact_person': supplier[2],
            'email': supplier[3],
            'phone': supplier[4],
            'address': supplier[5],
            'notes': supplier[6]
        }
        
        conn.close()
        return jsonify(supplier_data)
    
    except Exception as e:
        logger.error(f'Error fetching supplier: {e}')
        return jsonify({'error': 'Failed to fetch supplier'}), 500

@app.route('/api/suppliers/<int:supplier_id>', methods=['PUT'])
def update_supplier_api(supplier_id):
    """Update supplier via API."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.json
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({'success': False, 'error': 'Supplier name is required'}), 400
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE suppliers SET name = ?, contact_person = ?, email = ?, 
                               phone = ?, address = ?, notes = ?
            WHERE id = ?
        ''', (name, data.get('contact_person'), data.get('email'),
              data.get('phone'), data.get('address'), data.get('notes'), supplier_id))
        
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'error': 'Supplier not found'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    
    except Exception as e:
        logger.error(f'Error updating supplier: {e}')
        return jsonify({'success': False, 'error': 'Failed to update supplier'}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('base.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('base.html'), 500

if __name__ == '__main__':
    # Initialize database on startup
    init_database()
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)