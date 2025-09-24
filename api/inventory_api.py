"""
REST API endpoints for Retail Inventory Tracker

This module provides comprehensive RESTful API endpoints for
inventory management, including CRUD operations and advanced features.
"""

import sqlite3
from flask import jsonify, request, current_app
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class InventoryAPI:
    """RESTful API for inventory management operations."""
    
    def __init__(self, database_path='database/inventory.db'):
        """Initialize the inventory API."""
        self.database_path = database_path
    
    def get_inventory(self, warehouse_id: Optional[int] = None, 
                     product_id: Optional[int] = None) -> Dict:
        """
        Get inventory items with optional filtering.
        
        Args:
            warehouse_id (int, optional): Filter by warehouse
            product_id (int, optional): Filter by product
            
        Returns:
            dict: API response with inventory data
        """
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            query = '''
                SELECT i.id, i.product_id, p.name as product_name, p.category,
                       p.sku, p.unit_price, i.warehouse_id, w.name as warehouse_name,
                       i.quantity, i.reserved_quantity, i.reorder_level,
                       i.max_stock_level, i.last_updated
                FROM inventory i
                JOIN products p ON i.product_id = p.id
                JOIN warehouses w ON i.warehouse_id = w.id
                WHERE 1=1
            '''
            
            params = []
            
            if warehouse_id:
                query += ' AND i.warehouse_id = ?'
                params.append(warehouse_id)
            
            if product_id:
                query += ' AND i.product_id = ?'
                params.append(product_id)
            
            query += ' ORDER BY p.name, w.name'
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            inventory_items = []
            for row in rows:
                item = {
                    'id': row[0],
                    'product_id': row[1],
                    'product_name': row[2],
                    'category': row[3],
                    'sku': row[4],
                    'unit_price': row[5],
                    'warehouse_id': row[6],
                    'warehouse_name': row[7],
                    'quantity': row[8],
                    'reserved_quantity': row[9],
                    'available_quantity': row[8] - row[9],
                    'reorder_level': row[10],
                    'max_stock_level': row[11],
                    'last_updated': row[12],
                    'stock_status': self._get_stock_status(row[8], row[10])
                }
                inventory_items.append(item)
            
            conn.close()
            
            return {
                'success': True,
                'data': inventory_items,
                'total': len(inventory_items),
                'message': f'Retrieved {len(inventory_items)} inventory items'
            }
            
        except Exception as e:
            logger.error(f"Error getting inventory: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to retrieve inventory data'
            }
    
    def get_inventory_item(self, item_id: int) -> Dict:
        """
        Get a specific inventory item by ID.
        
        Args:
            item_id (int): Inventory item ID
            
        Returns:
            dict: API response with inventory item data
        """
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT i.id, i.product_id, p.name as product_name, p.category,
                       p.sku, p.unit_price, p.description, i.warehouse_id,
                       w.name as warehouse_name, w.location, i.quantity,
                       i.reserved_quantity, i.reorder_level, i.max_stock_level,
                       i.last_updated
                FROM inventory i
                JOIN products p ON i.product_id = p.id
                JOIN warehouses w ON i.warehouse_id = w.id
                WHERE i.id = ?
            ''', (item_id,))
            
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return {
                    'success': False,
                    'error': 'Item not found',
                    'message': f'Inventory item with ID {item_id} not found'
                }
            
            # Get recent stock movements for this item
            cursor.execute('''
                SELECT movement_type, quantity, created_at, reference_number,
                       notes, u.username
                FROM stock_movements sm
                JOIN users u ON sm.user_id = u.id
                WHERE sm.product_id = ? AND sm.warehouse_id = ?
                ORDER BY sm.created_at DESC
                LIMIT 10
            ''', (row[1], row[7]))
            
            movements = []
            for movement_row in cursor.fetchall():
                movements.append({
                    'type': movement_row[0],
                    'quantity': movement_row[1],
                    'date': movement_row[2],
                    'reference': movement_row[3],
                    'notes': movement_row[4],
                    'user': movement_row[5]
                })
            
            conn.close()
            
            item = {
                'id': row[0],
                'product_id': row[1],
                'product_name': row[2],
                'category': row[3],
                'sku': row[4],
                'unit_price': row[5],
                'description': row[6],
                'warehouse_id': row[7],
                'warehouse_name': row[8],
                'warehouse_location': row[9],
                'quantity': row[10],
                'reserved_quantity': row[11],
                'available_quantity': row[10] - row[11],
                'reorder_level': row[12],
                'max_stock_level': row[13],
                'last_updated': row[14],
                'stock_status': self._get_stock_status(row[10], row[12]),
                'inventory_value': row[5] * row[10],
                'recent_movements': movements
            }
            
            return {
                'success': True,
                'data': item,
                'message': 'Inventory item retrieved successfully'
            }
            
        except Exception as e:
            logger.error(f"Error getting inventory item: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to retrieve inventory item'
            }
    
    def add_inventory(self, data: Dict, user_id: int) -> Dict:
        """
        Add new inventory record.
        
        Args:
            data (dict): Inventory data
            user_id (int): User ID performing the action
            
        Returns:
            dict: API response with creation result
        """
        try:
            # Validate required fields
            required_fields = ['product_id', 'warehouse_id', 'quantity']
            for field in required_fields:
                if field not in data:
                    return {
                        'success': False,
                        'error': 'Missing required field',
                        'message': f'Field "{field}" is required'
                    }
            
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Check if inventory record already exists
            cursor.execute('''
                SELECT id FROM inventory
                WHERE product_id = ? AND warehouse_id = ?
            ''', (data['product_id'], data['warehouse_id']))
            
            if cursor.fetchone():
                conn.close()
                return {
                    'success': False,
                    'error': 'Duplicate entry',
                    'message': 'Inventory record already exists for this product in this warehouse'
                }
            
            # Validate product and warehouse exist
            cursor.execute('SELECT name FROM products WHERE id = ?', (data['product_id'],))
            if not cursor.fetchone():
                conn.close()
                return {
                    'success': False,
                    'error': 'Invalid product',
                    'message': f'Product ID {data["product_id"]} not found'
                }
            
            cursor.execute('SELECT name FROM warehouses WHERE id = ?', (data['warehouse_id'],))
            if not cursor.fetchone():
                conn.close()
                return {
                    'success': False,
                    'error': 'Invalid warehouse',
                    'message': f'Warehouse ID {data["warehouse_id"]} not found'
                }
            
            try:
                cursor.execute('BEGIN TRANSACTION')
                
                # Insert inventory record
                cursor.execute('''
                    INSERT INTO inventory (product_id, warehouse_id, quantity,
                                         reserved_quantity, reorder_level, max_stock_level)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    data['product_id'],
                    data['warehouse_id'],
                    data['quantity'],
                    data.get('reserved_quantity', 0),
                    data.get('reorder_level', 10),
                    data.get('max_stock_level', 1000)
                ))
                
                inventory_id = cursor.lastrowid
                
                # Record initial stock movement if quantity > 0
                if data['quantity'] > 0:
                    cursor.execute('''
                        INSERT INTO stock_movements (product_id, warehouse_id, movement_type,
                                                   quantity, reference_number, notes, user_id)
                        VALUES (?, ?, 'INITIAL', ?, ?, ?, ?)
                    ''', (
                        data['product_id'],
                        data['warehouse_id'],
                        data['quantity'],
                        f'INIT-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                        'Initial inventory setup',
                        user_id
                    ))
                
                cursor.execute('COMMIT')
                conn.close()
                
                logger.info(f"New inventory record created: ID {inventory_id} by user {user_id}")
                
                return {
                    'success': True,
                    'data': {'id': inventory_id},
                    'message': 'Inventory record created successfully'
                }
                
            except Exception as e:
                cursor.execute('ROLLBACK')
                conn.close()
                raise e
                
        except Exception as e:
            logger.error(f"Error adding inventory: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to create inventory record'
            }
    
    def update_inventory(self, item_id: int, data: Dict, user_id: int) -> Dict:
        """
        Update inventory record.
        
        Args:
            item_id (int): Inventory item ID
            data (dict): Updated inventory data
            user_id (int): User ID performing the action
            
        Returns:
            dict: API response with update result
        """
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Get current inventory data
            cursor.execute('''
                SELECT product_id, warehouse_id, quantity, reserved_quantity,
                       reorder_level, max_stock_level
                FROM inventory
                WHERE id = ?
            ''', (item_id,))
            
            current = cursor.fetchone()
            if not current:
                conn.close()
                return {
                    'success': False,
                    'error': 'Item not found',
                    'message': f'Inventory item with ID {item_id} not found'
                }
            
            current_quantity = current[2]
            
            try:
                cursor.execute('BEGIN TRANSACTION')
                
                # Update inventory record
                update_fields = []
                update_params = []
                
                for field in ['quantity', 'reserved_quantity', 'reorder_level', 'max_stock_level']:
                    if field in data:
                        update_fields.append(f'{field} = ?')
                        update_params.append(data[field])
                
                if update_fields:
                    update_fields.append('last_updated = ?')
                    update_params.append(datetime.now())
                    update_params.append(item_id)
                    
                    cursor.execute(f'''
                        UPDATE inventory
                        SET {', '.join(update_fields)}
                        WHERE id = ?
                    ''', update_params)
                
                # Record stock movement if quantity changed
                if 'quantity' in data and data['quantity'] != current_quantity:
                    quantity_change = data['quantity'] - current_quantity
                    movement_type = 'ADJUSTMENT_IN' if quantity_change > 0 else 'ADJUSTMENT_OUT'
                    
                    cursor.execute('''
                        INSERT INTO stock_movements (product_id, warehouse_id, movement_type,
                                                   quantity, reference_number, notes, user_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        current[0],  # product_id
                        current[1],  # warehouse_id
                        movement_type,
                        abs(quantity_change),
                        f'ADJ-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                        f'Inventory adjustment via API. Change: {quantity_change:+d}',
                        user_id
                    ))
                
                cursor.execute('COMMIT')
                conn.close()
                
                logger.info(f"Inventory item {item_id} updated by user {user_id}")
                
                return {
                    'success': True,
                    'message': 'Inventory record updated successfully'
                }
                
            except Exception as e:
                cursor.execute('ROLLBACK')
                conn.close()
                raise e
                
        except Exception as e:
            logger.error(f"Error updating inventory: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to update inventory record'
            }
    
    def delete_inventory(self, item_id: int, user_id: int) -> Dict:
        """
        Delete inventory record.
        
        Args:
            item_id (int): Inventory item ID
            user_id (int): User ID performing the action
            
        Returns:
            dict: API response with deletion result
        """
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Get inventory data before deletion
            cursor.execute('''
                SELECT product_id, warehouse_id, quantity, p.name, w.name
                FROM inventory i
                JOIN products p ON i.product_id = p.id
                JOIN warehouses w ON i.warehouse_id = w.id
                WHERE i.id = ?
            ''', (item_id,))
            
            inventory_data = cursor.fetchone()
            if not inventory_data:
                conn.close()
                return {
                    'success': False,
                    'error': 'Item not found',
                    'message': f'Inventory item with ID {item_id} not found'
                }
            
            product_id, warehouse_id, quantity, product_name, warehouse_name = inventory_data
            
            try:
                cursor.execute('BEGIN TRANSACTION')
                
                # Record final stock movement
                if quantity > 0:
                    cursor.execute('''
                        INSERT INTO stock_movements (product_id, warehouse_id, movement_type,
                                                   quantity, reference_number, notes, user_id)
                        VALUES (?, ?, 'REMOVED', ?, ?, ?, ?)
                    ''', (
                        product_id,
                        warehouse_id,
                        quantity,
                        f'DEL-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                        f'Inventory record deleted via API',
                        user_id
                    ))
                
                # Delete inventory record
                cursor.execute('DELETE FROM inventory WHERE id = ?', (item_id,))
                
                cursor.execute('COMMIT')
                conn.close()
                
                logger.info(f"Inventory item {item_id} deleted by user {user_id}")
                
                return {
                    'success': True,
                    'message': f'Inventory record deleted: {product_name} at {warehouse_name}'
                }
                
            except Exception as e:
                cursor.execute('ROLLBACK')
                conn.close()
                raise e
                
        except Exception as e:
            logger.error(f"Error deleting inventory: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to delete inventory record'
            }
    
    def get_products(self) -> Dict:
        """Get all products."""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, category, sku, barcode, description, unit_price,
                       cost_price, supplier_id, created_at, updated_at
                FROM products
                ORDER BY name
            ''')
            
            products = []
            for row in cursor.fetchall():
                products.append({
                    'id': row[0],
                    'name': row[1],
                    'category': row[2],
                    'sku': row[3],
                    'barcode': row[4],
                    'description': row[5],
                    'unit_price': row[6],
                    'cost_price': row[7],
                    'supplier_id': row[8],
                    'created_at': row[9],
                    'updated_at': row[10]
                })
            
            conn.close()
            
            return {
                'success': True,
                'data': products,
                'total': len(products),
                'message': f'Retrieved {len(products)} products'
            }
            
        except Exception as e:
            logger.error(f"Error getting products: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to retrieve products'
            }
    
    def get_warehouses(self) -> Dict:
        """Get all warehouses."""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT w.id, w.name, w.location, w.capacity, w.manager_id,
                       u.username as manager_name, w.created_at,
                       COUNT(DISTINCT i.product_id) as total_products,
                       COALESCE(SUM(i.quantity), 0) as total_items
                FROM warehouses w
                LEFT JOIN users u ON w.manager_id = u.id
                LEFT JOIN inventory i ON w.id = i.warehouse_id
                GROUP BY w.id, w.name, w.location, w.capacity, w.manager_id,
                         u.username, w.created_at
                ORDER BY w.name
            ''')
            
            warehouses = []
            for row in cursor.fetchall():
                capacity_utilization = 0
                if row[3] and row[3] > 0:  # capacity exists
                    capacity_utilization = (row[8] / row[3]) * 100
                
                warehouses.append({
                    'id': row[0],
                    'name': row[1],
                    'location': row[2],
                    'capacity': row[3],
                    'capacity_utilization': round(capacity_utilization, 2),
                    'manager_id': row[4],
                    'manager_name': row[5],
                    'created_at': row[6],
                    'total_products': row[7],
                    'total_items': row[8]
                })
            
            conn.close()
            
            return {
                'success': True,
                'data': warehouses,
                'total': len(warehouses),
                'message': f'Retrieved {len(warehouses)} warehouses'
            }
            
        except Exception as e:
            logger.error(f"Error getting warehouses: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to retrieve warehouses'
            }
    
    def get_alerts(self, unread_only: bool = False) -> Dict:
        """Get system alerts."""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            query = '''
                SELECT a.id, a.alert_type, a.message, a.severity, a.is_read,
                       a.created_at, p.name as product_name, w.name as warehouse_name
                FROM alerts a
                LEFT JOIN products p ON a.product_id = p.id
                LEFT JOIN warehouses w ON a.warehouse_id = w.id
                WHERE 1=1
            '''
            
            if unread_only:
                query += ' AND a.is_read = 0'
            
            query += ' ORDER BY a.created_at DESC'
            
            cursor.execute(query)
            
            alerts = []
            for row in cursor.fetchall():
                alerts.append({
                    'id': row[0],
                    'type': row[1],
                    'message': row[2],
                    'severity': row[3],
                    'is_read': bool(row[4]),
                    'created_at': row[5],
                    'product_name': row[6],
                    'warehouse_name': row[7]
                })
            
            conn.close()
            
            return {
                'success': True,
                'data': alerts,
                'total': len(alerts),
                'message': f'Retrieved {len(alerts)} alerts'
            }
            
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to retrieve alerts'
            }
    
    def get_stock_movements(self, product_id: Optional[int] = None,
                           warehouse_id: Optional[int] = None,
                           limit: int = 100) -> Dict:
        """Get stock movement history."""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            query = '''
                SELECT sm.id, sm.product_id, p.name as product_name,
                       sm.warehouse_id, w.name as warehouse_name,
                       sm.movement_type, sm.quantity, sm.reference_number,
                       sm.notes, sm.created_at, u.username
                FROM stock_movements sm
                JOIN products p ON sm.product_id = p.id
                JOIN warehouses w ON sm.warehouse_id = w.id
                JOIN users u ON sm.user_id = u.id
                WHERE 1=1
            '''
            
            params = []
            
            if product_id:
                query += ' AND sm.product_id = ?'
                params.append(product_id)
            
            if warehouse_id:
                query += ' AND sm.warehouse_id = ?'
                params.append(warehouse_id)
            
            query += ' ORDER BY sm.created_at DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            
            movements = []
            for row in cursor.fetchall():
                movements.append({
                    'id': row[0],
                    'product_id': row[1],
                    'product_name': row[2],
                    'warehouse_id': row[3],
                    'warehouse_name': row[4],
                    'movement_type': row[5],
                    'quantity': row[6],
                    'reference_number': row[7],
                    'notes': row[8],
                    'created_at': row[9],
                    'user': row[10]
                })
            
            conn.close()
            
            return {
                'success': True,
                'data': movements,
                'total': len(movements),
                'message': f'Retrieved {len(movements)} stock movements'
            }
            
        except Exception as e:
            logger.error(f"Error getting stock movements: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to retrieve stock movements'
            }
    
    def _get_stock_status(self, quantity: int, reorder_level: int) -> str:
        """Get stock status based on quantity and reorder level."""
        if quantity <= 0:
            return 'out_of_stock'
        elif quantity <= reorder_level:
            return 'low_stock'
        elif quantity <= reorder_level * 2:
            return 'medium_stock'
        else:
            return 'good_stock'
    
    def get_api_stats(self) -> Dict:
        """Get API usage statistics."""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Get basic counts
            cursor.execute('SELECT COUNT(*) FROM products')
            total_products = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM warehouses')
            total_warehouses = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM inventory')
            total_inventory_records = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM stock_movements')
            total_movements = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM alerts WHERE is_read = 0')
            unread_alerts = cursor.fetchone()[0]
            
            # Get recent activity
            cursor.execute('''
                SELECT COUNT(*) FROM stock_movements
                WHERE created_at >= datetime('now', '-24 hours')
            ''')
            movements_last_24h = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'success': True,
                'data': {
                    'total_products': total_products,
                    'total_warehouses': total_warehouses,
                    'total_inventory_records': total_inventory_records,
                    'total_stock_movements': total_movements,
                    'unread_alerts': unread_alerts,
                    'movements_last_24h': movements_last_24h,
                    'api_version': '1.0',
                    'last_updated': datetime.now().isoformat()
                },
                'message': 'API statistics retrieved successfully'
            }
            
        except Exception as e:
            logger.error(f"Error getting API stats: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to retrieve API statistics'
            }