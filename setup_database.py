"""
Database Setup Script for Retail Inventory Tracker

This script initializes the SQLite database with all required tables
and populates them with sample data for testing and demonstration.
"""

import sqlite3
import os
from datetime import datetime, timedelta
import hashlib
import random

def hash_password(password):
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def create_database():
    """Create database directory and initialize database with tables and sample data."""
    
    # Create database directory if it doesn't exist
    database_dir = 'database'
    if not os.path.exists(database_dir):
        os.makedirs(database_dir)
    
    database_path = os.path.join(database_dir, 'inventory.db')
    
    # Remove existing database for fresh start
    if os.path.exists(database_path):
        os.remove(database_path)
        print(f"Removed existing database: {database_path}")
    
    # Create new database connection
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    try:
        print("Creating database tables...")
        
        # Create Users table
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                full_name VARCHAR(100) NOT NULL,
                role VARCHAR(20) DEFAULT 'employee' CHECK (role IN ('admin', 'manager', 'employee')),
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # Create Suppliers table
        cursor.execute('''
            CREATE TABLE suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                contact_person VARCHAR(100),
                email VARCHAR(100),
                phone VARCHAR(20),
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create Products table
        cursor.execute('''
            CREATE TABLE products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                category VARCHAR(50) NOT NULL,
                sku VARCHAR(50) UNIQUE NOT NULL,
                barcode VARCHAR(100),
                description TEXT,
                unit_price DECIMAL(10,2) NOT NULL,
                cost_price DECIMAL(10,2),
                supplier_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
            )
        ''')
        
        # Create Warehouses table
        cursor.execute('''
            CREATE TABLE warehouses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                location VARCHAR(200) NOT NULL,
                capacity INTEGER,
                manager_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (manager_id) REFERENCES users(id)
            )
        ''')
        
        # Create Inventory table
        cursor.execute('''
            CREATE TABLE inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                warehouse_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                reserved_quantity INTEGER NOT NULL DEFAULT 0,
                reorder_level INTEGER NOT NULL DEFAULT 10,
                max_stock_level INTEGER NOT NULL DEFAULT 1000,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (warehouse_id) REFERENCES warehouses(id),
                UNIQUE(product_id, warehouse_id)
            )
        ''')
        
        # Create Stock Movements table
        cursor.execute('''
            CREATE TABLE stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                warehouse_id INTEGER NOT NULL,
                movement_type VARCHAR(20) NOT NULL CHECK (movement_type IN 
                    ('IN', 'OUT', 'TRANSFER_IN', 'TRANSFER_OUT', 'ADJUSTMENT_IN', 
                     'ADJUSTMENT_OUT', 'RETURN', 'DAMAGED', 'INITIAL', 'REMOVED')),
                quantity INTEGER NOT NULL,
                reference_number VARCHAR(50),
                notes TEXT,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (warehouse_id) REFERENCES warehouses(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Create Alerts table
        cursor.execute('''
            CREATE TABLE alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type VARCHAR(50) NOT NULL,
                product_id INTEGER,
                warehouse_id INTEGER,
                message TEXT NOT NULL,
                severity VARCHAR(20) DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
                is_read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (warehouse_id) REFERENCES warehouses(id)
            )
        ''')
        
        # Create Sessions table
        cursor.execute('''
            CREATE TABLE user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        print("✅ Database tables created successfully")
        
        # Insert sample data
        print("Inserting sample data...")
        
        # Insert Users
        users_data = [
            ('admin', hash_password('admin123'), 'admin@retailtracker.com', 'System Administrator', 'admin'),
            ('manager', hash_password('manager123'), 'manager@retailtracker.com', 'Store Manager', 'manager'),
            ('employee', hash_password('employee123'), 'employee@retailtracker.com', 'Store Employee', 'employee'),
            ('john_doe', hash_password('password123'), 'john@retailtracker.com', 'John Doe', 'manager'),
            ('jane_smith', hash_password('password123'), 'jane@retailtracker.com', 'Jane Smith', 'employee')
        ]
        
        cursor.executemany('''
            INSERT INTO users (username, password_hash, email, full_name, role)
            VALUES (?, ?, ?, ?, ?)
        ''', users_data)
        
        # Insert Suppliers
        suppliers_data = [
            ('TechCorp Solutions', 'Mike Johnson', 'mike@techcorp.com', '+1-555-0101', '123 Tech Street, Silicon Valley, CA'),
            ('Fashion Forward Ltd', 'Sarah Wilson', 'sarah@fashionforward.com', '+1-555-0102', '456 Fashion Ave, New York, NY'),
            ('Home Essentials Co', 'Robert Brown', 'robert@homeessentials.com', '+1-555-0103', '789 Home Blvd, Chicago, IL'),
            ('Sports Gear Inc', 'Lisa Davis', 'lisa@sportsgear.com', '+1-555-0104', '321 Sports Lane, Denver, CO'),
            ('BookWorld Publishers', 'David Garcia', 'david@bookworld.com', '+1-555-0105', '654 Book Street, Boston, MA')
        ]
        
        cursor.executemany('''
            INSERT INTO suppliers (name, contact_person, email, phone, address)
            VALUES (?, ?, ?, ?, ?)
        ''', suppliers_data)
        
        # Insert Warehouses
        warehouses_data = [
            ('Main Warehouse', 'New York, NY - 123 Main St', 50000, 2),
            ('West Coast Hub', 'Los Angeles, CA - 456 West Ave', 35000, 4),
            ('Central Distribution', 'Chicago, IL - 789 Central Blvd', 40000, 2),
            ('East Coast Facility', 'Boston, MA - 321 East Road', 30000, 4)
        ]
        
        cursor.executemany('''
            INSERT INTO warehouses (name, location, capacity, manager_id)
            VALUES (?, ?, ?, ?)
        ''', warehouses_data)
        
        # Insert Products
        products_data = [
            # Electronics
            ('Laptop Pro 15"', 'Electronics', 'LAPTOP-PRO-15', '123456789012', 'High-performance laptop for professionals', 1299.99, 899.99, 1),
            ('Smartphone X', 'Electronics', 'PHONE-X-128', '123456789013', 'Latest smartphone with advanced features', 899.99, 649.99, 1),
            ('Wireless Headphones', 'Electronics', 'HEADPHONE-WL-01', '123456789014', 'Premium wireless headphones with noise cancellation', 199.99, 129.99, 1),
            ('Tablet Air 11"', 'Electronics', 'TABLET-AIR-11', '123456789015', 'Lightweight tablet for productivity and entertainment', 599.99, 429.99, 1),
            ('Smart Watch Series 5', 'Electronics', 'WATCH-SMART-5', '123456789016', 'Advanced fitness and connectivity features', 399.99, 279.99, 1),
            
            # Clothing
            ('Cotton T-Shirt', 'Clothing', 'TSHIRT-COT-M', '234567890123', 'Comfortable cotton t-shirt in medium size', 19.99, 8.99, 2),
            ('Denim Jeans', 'Clothing', 'JEANS-DENIM-32', '234567890124', 'Classic denim jeans, waist size 32', 59.99, 29.99, 2),
            ('Running Shoes', 'Clothing', 'SHOES-RUN-42', '234567890125', 'Professional running shoes, size 42', 129.99, 79.99, 2),
            ('Winter Jacket', 'Clothing', 'JACKET-WINTER-L', '234567890126', 'Warm winter jacket, large size', 199.99, 119.99, 2),
            ('Baseball Cap', 'Clothing', 'CAP-BASEBALL-BLK', '234567890127', 'Classic black baseball cap', 24.99, 12.99, 2),
            
            # Home & Garden
            ('Coffee Maker Deluxe', 'Home & Garden', 'COFFEE-DELUXE-01', '345678901234', '12-cup programmable coffee maker', 89.99, 54.99, 3),
            ('Garden Tool Set', 'Home & Garden', 'GARDEN-TOOLS-SET', '345678901235', 'Complete 10-piece garden tool set', 149.99, 89.99, 3),
            ('LED Desk Lamp', 'Home & Garden', 'LAMP-LED-DESK', '345678901236', 'Adjustable LED desk lamp with USB charging', 49.99, 29.99, 3),
            ('Throw Pillow Set', 'Home & Garden', 'PILLOW-THROW-4PC', '345678901237', 'Set of 4 decorative throw pillows', 79.99, 39.99, 3),
            ('Kitchen Scale Digital', 'Home & Garden', 'SCALE-KITCHEN-DIG', '345678901238', 'Precision digital kitchen scale', 34.99, 19.99, 3),
            
            # Sports & Recreation
            ('Basketball Official', 'Sports & Recreation', 'BALL-BASKETBALL', '456789012345', 'Official size basketball', 29.99, 17.99, 4),
            ('Yoga Mat Premium', 'Sports & Recreation', 'MAT-YOGA-PREM', '456789012346', 'Extra-thick premium yoga mat', 79.99, 49.99, 4),
            ('Tennis Racket Pro', 'Sports & Recreation', 'RACKET-TENNIS-PRO', '456789012347', 'Professional tennis racket', 199.99, 129.99, 4),
            ('Dumbbell Set 20kg', 'Sports & Recreation', 'DUMBBELL-20KG-SET', '456789012348', 'Adjustable dumbbell set up to 20kg', 299.99, 199.99, 4),
            ('Camping Tent 4-Person', 'Sports & Recreation', 'TENT-CAMPING-4P', '456789012349', 'Waterproof camping tent for 4 people', 249.99, 169.99, 4),
            
            # Books & Media
            ('Programming Guide Python', 'Books & Media', 'BOOK-PYTHON-GUIDE', '567890123456', 'Complete guide to Python programming', 49.99, 24.99, 5),
            ('Mystery Novel Bestseller', 'Books & Media', 'BOOK-MYSTERY-01', '567890123457', 'Thrilling mystery novel by acclaimed author', 14.99, 7.99, 5),
            ('Cookbook Italian Cuisine', 'Books & Media', 'BOOK-COOK-ITALIAN', '567890123458', 'Authentic Italian recipes cookbook', 34.99, 19.99, 5),
            ('History of Technology', 'Books & Media', 'BOOK-HIST-TECH', '567890123459', 'Comprehensive history of technological advancement', 39.99, 24.99, 5),
            ('Art Photography Book', 'Books & Media', 'BOOK-ART-PHOTO', '567890123460', 'Beautiful collection of contemporary photography', 59.99, 34.99, 5)
        ]
        
        cursor.executemany('''
            INSERT INTO products (name, category, sku, barcode, description, unit_price, cost_price, supplier_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', products_data)
        
        print("✅ Sample data inserted successfully")
        
        # Generate sample inventory data
        print("Generating inventory data...")
        
        # Get all products and warehouses
        cursor.execute('SELECT id FROM products')
        product_ids = [row[0] for row in cursor.fetchall()]
        
        cursor.execute('SELECT id FROM warehouses')
        warehouse_ids = [row[0] for row in cursor.fetchall()]
        
        # Generate inventory records (not every product in every warehouse)
        inventory_data = []
        movement_data = []
        
        for product_id in product_ids:
            # Each product will be in 2-3 random warehouses
            selected_warehouses = random.sample(warehouse_ids, random.randint(2, min(3, len(warehouse_ids))))
            
            for warehouse_id in selected_warehouses:
                quantity = random.randint(20, 500)
                reserved = random.randint(0, min(10, quantity // 4))
                reorder_level = random.randint(10, 50)
                max_level = random.randint(reorder_level * 10, 2000)
                
                inventory_data.append((
                    product_id, warehouse_id, quantity, reserved,
                    reorder_level, max_level
                ))
                
                # Create initial stock movement
                movement_data.append((
                    product_id, warehouse_id, 'INITIAL', quantity,
                    f'INIT-{datetime.now().strftime("%Y%m%d")}-{len(movement_data)+1:04d}',
                    'Initial inventory setup', 1  # admin user
                ))
        
        cursor.executemany('''
            INSERT INTO inventory (product_id, warehouse_id, quantity, reserved_quantity,
                                 reorder_level, max_stock_level)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', inventory_data)
        
        cursor.executemany('''
            INSERT INTO stock_movements (product_id, warehouse_id, movement_type,
                                       quantity, reference_number, notes, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', movement_data)
        
        print("✅ Inventory data generated successfully")
        
        # Generate some additional stock movements for history
        print("Generating stock movement history...")
        
        additional_movements = []
        movement_types = ['IN', 'OUT', 'ADJUSTMENT_IN', 'ADJUSTMENT_OUT']
        
        for _ in range(50):  # Generate 50 additional movements
            inventory_record = random.choice(inventory_data)
            product_id, warehouse_id = inventory_record[0], inventory_record[1]
            
            movement_type = random.choice(movement_types)
            quantity = random.randint(1, 50)
            user_id = random.choice([1, 2, 3, 4, 5])  # Random user
            
            # Generate date within last 30 days
            days_ago = random.randint(0, 30)
            movement_date = datetime.now() - timedelta(days=days_ago)
            
            additional_movements.append((
                product_id, warehouse_id, movement_type, quantity,
                f'{movement_type}-{movement_date.strftime("%Y%m%d")}-{len(additional_movements)+1:04d}',
                f'Sample {movement_type.lower()} movement', user_id,
                movement_date.strftime('%Y-%m-%d %H:%M:%S')
            ))
        
        cursor.executemany('''
            INSERT INTO stock_movements (product_id, warehouse_id, movement_type,
                                       quantity, reference_number, notes, user_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', additional_movements)
        
        print("✅ Stock movement history generated successfully")
        
        # Generate some alerts
        print("Generating sample alerts...")
        
        alerts_data = [
            ('LOW_STOCK', 1, 1, 'Laptop Pro 15" is running low in Main Warehouse (15 units remaining)', 'medium'),
            ('OUT_OF_STOCK', 5, 2, 'Smart Watch Series 5 is out of stock in West Coast Hub', 'high'),
            ('REORDER_POINT', 10, 3, 'Dumbbell Set 20kg has reached reorder point in Central Distribution', 'medium'),
            ('HIGH_DEMAND', 3, 1, 'Wireless Headphones showing unusual high demand pattern', 'low'),
            ('SYSTEM', None, None, 'Daily inventory sync completed successfully', 'low')
        ]
        
        cursor.executemany('''
            INSERT INTO alerts (alert_type, product_id, warehouse_id, message, severity)
            VALUES (?, ?, ?, ?, ?)
        ''', alerts_data)
        
        print("✅ Sample alerts generated successfully")
        
        # Create indexes for better performance
        print("Creating database indexes...")
        
        cursor.execute('CREATE INDEX idx_inventory_product_warehouse ON inventory(product_id, warehouse_id)')
        cursor.execute('CREATE INDEX idx_stock_movements_product ON stock_movements(product_id)')
        cursor.execute('CREATE INDEX idx_stock_movements_warehouse ON stock_movements(warehouse_id)')
        cursor.execute('CREATE INDEX idx_stock_movements_date ON stock_movements(created_at)')
        cursor.execute('CREATE INDEX idx_products_sku ON products(sku)')
        cursor.execute('CREATE INDEX idx_products_category ON products(category)')
        cursor.execute('CREATE INDEX idx_alerts_unread ON alerts(is_read)')
        cursor.execute('CREATE INDEX idx_users_username ON users(username)')
        cursor.execute('CREATE INDEX idx_sessions_token ON user_sessions(session_token)')
        
        print("✅ Database indexes created successfully")
        
        # Commit all changes
        conn.commit()
        print(f"\n🎉 Database setup completed successfully!")
        print(f"📍 Database location: {os.path.abspath(database_path)}")
        print("\n📊 Database Statistics:")
        
        # Display statistics
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM products')
        product_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM warehouses')
        warehouse_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM inventory')
        inventory_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM stock_movements')
        movement_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM alerts')
        alert_count = cursor.fetchone()[0]
        
        print(f"   👥 Users: {user_count}")
        print(f"   📦 Products: {product_count}")
        print(f"   🏬 Warehouses: {warehouse_count}")
        print(f"   📋 Inventory Records: {inventory_count}")
        print(f"   📈 Stock Movements: {movement_count}")
        print(f"   🚨 Alerts: {alert_count}")
        
        print("\n🔑 Default Login Credentials:")
        print("   Admin:    username: admin,    password: admin123")
        print("   Manager:  username: manager,  password: manager123")
        print("   Employee: username: employee, password: employee123")
        
        print("\n🚀 Ready to start the application!")
        print("   Run: python app.py")
        print("   Then open: http://localhost:5000")
        
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()

if __name__ == "__main__":
    print("🔧 Setting up Retail Inventory Tracker Database...")
    print("=" * 60)
    create_database()
    print("=" * 60)