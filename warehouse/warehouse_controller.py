"""
Warehouse Controller for Retail Inventory Tracker

This module handles all warehouse-related operations including
inventory transfers, capacity management, and warehouse analytics.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class WarehouseController:
    """Manages warehouse operations and inventory transfers."""
    
    def __init__(self, database_path='database/inventory.db'):
        """Initialize the warehouse controller."""
        self.database_path = database_path
    
    def get_warehouse_info(self, warehouse_id: int) -> Optional[Dict]:
        """
        Get detailed information about a specific warehouse.
        
        Args:
            warehouse_id (int): Warehouse ID
            
        Returns:
            dict: Warehouse information with inventory statistics
        """
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Get warehouse basic info
            cursor.execute('''
                SELECT id, name, location, capacity, manager_id, created_at
                FROM warehouses
                WHERE id = ?
            ''', (warehouse_id,))
            
            warehouse_data = cursor.fetchone()
            if not warehouse_data:
                conn.close()
                return None
            
            warehouse_id, name, location, capacity, manager_id, created_at = warehouse_data
            
            # Get manager info if exists
            manager_name = None
            if manager_id:
                cursor.execute('SELECT username FROM users WHERE id = ?', (manager_id,))
                manager_result = cursor.fetchone()
                if manager_result:
                    manager_name = manager_result[0]
            
            # Get inventory statistics
            cursor.execute('''
                SELECT 
                    COUNT(DISTINCT i.product_id) as total_products,
                    SUM(i.quantity) as total_items,
                    COUNT(CASE WHEN i.quantity <= i.reorder_level THEN 1 END) as low_stock_products,
                    AVG(i.quantity) as avg_stock_level
                FROM inventory i
                WHERE i.warehouse_id = ?
            ''', (warehouse_id,))
            
            stats = cursor.fetchone()
            total_products, total_items, low_stock_products, avg_stock_level = stats or (0, 0, 0, 0)
            
            # Get top products by quantity
            cursor.execute('''
                SELECT p.name, i.quantity, p.category
                FROM inventory i
                JOIN products p ON i.product_id = p.id
                WHERE i.warehouse_id = ?
                ORDER BY i.quantity DESC
                LIMIT 5
            ''', (warehouse_id,))
            
            top_products = cursor.fetchall()
            
            # Get recent stock movements
            cursor.execute('''
                SELECT sm.movement_type, sm.quantity, p.name, sm.created_at, u.username
                FROM stock_movements sm
                JOIN products p ON sm.product_id = p.id
                JOIN users u ON sm.user_id = u.id
                WHERE sm.warehouse_id = ?
                ORDER BY sm.created_at DESC
                LIMIT 10
            ''', (warehouse_id,))
            
            recent_movements = cursor.fetchall()
            
            conn.close()
            
            # Calculate capacity utilization
            capacity_utilization = 0
            if capacity and capacity > 0:
                capacity_utilization = (total_items / capacity) * 100
            
            return {
                'id': warehouse_id,
                'name': name,
                'location': location,
                'capacity': capacity,
                'capacity_utilization': round(capacity_utilization, 2),
                'manager_id': manager_id,
                'manager_name': manager_name,
                'created_at': created_at,
                'statistics': {
                    'total_products': total_products or 0,
                    'total_items': total_items or 0,
                    'low_stock_products': low_stock_products or 0,
                    'avg_stock_level': round(avg_stock_level or 0, 2)
                },
                'top_products': top_products,
                'recent_movements': recent_movements
            }
            
        except Exception as e:
            logger.error(f"Error getting warehouse info: {e}")
            return None
    
    def get_all_warehouses(self) -> List[Dict]:
        """
        Get information about all warehouses.
        
        Returns:
            list: List of warehouse information dictionaries
        """
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT w.id, w.name, w.location, w.capacity,
                       COUNT(DISTINCT i.product_id) as total_products,
                       COALESCE(SUM(i.quantity), 0) as total_items,
                       u.username as manager_name
                FROM warehouses w
                LEFT JOIN inventory i ON w.id = i.warehouse_id
                LEFT JOIN users u ON w.manager_id = u.id
                GROUP BY w.id, w.name, w.location, w.capacity, u.username
                ORDER BY w.name
            ''')
            
            warehouses = []
            for row in cursor.fetchall():
                warehouse_id, name, location, capacity, total_products, total_items, manager_name = row
                
                capacity_utilization = 0
                if capacity and capacity > 0:
                    capacity_utilization = (total_items / capacity) * 100
                
                warehouses.append({
                    'id': warehouse_id,
                    'name': name,
                    'location': location,
                    'capacity': capacity,
                    'capacity_utilization': round(capacity_utilization, 2),
                    'total_products': total_products or 0,
                    'total_items': total_items or 0,
                    'manager_name': manager_name
                })
            
            conn.close()
            return warehouses
            
        except Exception as e:
            logger.error(f"Error getting all warehouses: {e}")
            return []
    
    def transfer_inventory(self, product_id: int, from_warehouse_id: int, 
                          to_warehouse_id: int, quantity: int, user_id: int,
                          notes: str = None) -> Dict:
        """
        Transfer inventory between warehouses.
        
        Args:
            product_id (int): Product ID to transfer
            from_warehouse_id (int): Source warehouse ID
            to_warehouse_id (int): Destination warehouse ID
            quantity (int): Quantity to transfer
            user_id (int): User performing the transfer
            notes (str): Optional transfer notes
            
        Returns:
            dict: Transfer result with success status and message
        """
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Validate source warehouse has enough inventory
            cursor.execute('''
                SELECT quantity FROM inventory
                WHERE product_id = ? AND warehouse_id = ?
            ''', (product_id, from_warehouse_id))
            
            source_result = cursor.fetchone()
            if not source_result:
                conn.close()
                return {
                    'success': False,
                    'message': 'Product not found in source warehouse'
                }
            
            source_quantity = source_result[0]
            if source_quantity < quantity:
                conn.close()
                return {
                    'success': False,
                    'message': f'Insufficient inventory. Available: {source_quantity}, Requested: {quantity}'
                }
            
            # Check if destination warehouse has inventory record
            cursor.execute('''
                SELECT quantity FROM inventory
                WHERE product_id = ? AND warehouse_id = ?
            ''', (product_id, to_warehouse_id))
            
            dest_result = cursor.fetchone()
            
            try:
                # Start transaction
                cursor.execute('BEGIN TRANSACTION')
                
                # Update source warehouse (subtract quantity)
                new_source_quantity = source_quantity - quantity
                cursor.execute('''
                    UPDATE inventory
                    SET quantity = ?, last_updated = ?
                    WHERE product_id = ? AND warehouse_id = ?
                ''', (new_source_quantity, datetime.now(), product_id, from_warehouse_id))
                
                # Update or create destination warehouse record
                if dest_result:
                    # Update existing record
                    new_dest_quantity = dest_result[0] + quantity
                    cursor.execute('''
                        UPDATE inventory
                        SET quantity = ?, last_updated = ?
                        WHERE product_id = ? AND warehouse_id = ?
                    ''', (new_dest_quantity, datetime.now(), product_id, to_warehouse_id))
                else:
                    # Create new inventory record for destination
                    cursor.execute('''
                        SELECT reorder_level, max_stock_level
                        FROM inventory
                        WHERE product_id = ? AND warehouse_id = ?
                    ''', (product_id, from_warehouse_id))
                    
                    reorder_info = cursor.fetchone()
                    reorder_level = reorder_info[0] if reorder_info else 10
                    max_stock_level = reorder_info[1] if reorder_info else 1000
                    
                    cursor.execute('''
                        INSERT INTO inventory (product_id, warehouse_id, quantity, reorder_level, max_stock_level)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (product_id, to_warehouse_id, quantity, reorder_level, max_stock_level))
                
                # Record stock movements
                transfer_reference = f"TRANSFER-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # Outbound movement from source
                cursor.execute('''
                    INSERT INTO stock_movements (product_id, warehouse_id, movement_type, quantity,
                                               reference_number, notes, user_id)
                    VALUES (?, ?, 'TRANSFER_OUT', ?, ?, ?, ?)
                ''', (product_id, from_warehouse_id, quantity, transfer_reference, 
                     f"Transfer to warehouse {to_warehouse_id}. {notes or ''}", user_id))
                
                # Inbound movement to destination
                cursor.execute('''
                    INSERT INTO stock_movements (product_id, warehouse_id, movement_type, quantity,
                                               reference_number, notes, user_id)
                    VALUES (?, ?, 'TRANSFER_IN', ?, ?, ?, ?)
                ''', (product_id, to_warehouse_id, quantity, transfer_reference,
                     f"Transfer from warehouse {from_warehouse_id}. {notes or ''}", user_id))
                
                # Commit transaction
                cursor.execute('COMMIT')
                conn.close()
                
                logger.info(f"Inventory transfer completed: {quantity} units of product {product_id} "
                           f"from warehouse {from_warehouse_id} to {to_warehouse_id} by user {user_id}")
                
                return {
                    'success': True,
                    'message': f'Successfully transferred {quantity} units',
                    'transfer_reference': transfer_reference
                }
                
            except Exception as e:
                cursor.execute('ROLLBACK')
                conn.close()
                raise e
                
        except Exception as e:
            logger.error(f"Error during inventory transfer: {e}")
            return {
                'success': False,
                'message': f'Transfer failed: {str(e)}'
            }
    
    def adjust_inventory(self, product_id: int, warehouse_id: int, 
                        adjustment_quantity: int, adjustment_type: str,
                        user_id: int, reason: str = None) -> Dict:
        """
        Adjust inventory levels (for corrections, damage, etc.).
        
        Args:
            product_id (int): Product ID
            warehouse_id (int): Warehouse ID
            adjustment_quantity (int): Quantity to adjust (positive or negative)
            adjustment_type (str): Type of adjustment (CORRECTION, DAMAGE, FOUND, etc.)
            user_id (int): User making the adjustment
            reason (str): Reason for adjustment
            
        Returns:
            dict: Adjustment result
        """
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Get current inventory
            cursor.execute('''
                SELECT quantity FROM inventory
                WHERE product_id = ? AND warehouse_id = ?
            ''', (product_id, warehouse_id))
            
            result = cursor.fetchone()
            if not result:
                conn.close()
                return {
                    'success': False,
                    'message': 'Inventory record not found'
                }
            
            current_quantity = result[0]
            new_quantity = current_quantity + adjustment_quantity
            
            # Ensure new quantity is not negative
            if new_quantity < 0:
                conn.close()
                return {
                    'success': False,
                    'message': f'Adjustment would result in negative inventory. Current: {current_quantity}, Adjustment: {adjustment_quantity}'
                }
            
            try:
                cursor.execute('BEGIN TRANSACTION')
                
                # Update inventory
                cursor.execute('''
                    UPDATE inventory
                    SET quantity = ?, last_updated = ?
                    WHERE product_id = ? AND warehouse_id = ?
                ''', (new_quantity, datetime.now(), product_id, warehouse_id))
                
                # Record stock movement
                movement_type = f'ADJUST_{adjustment_type}'
                reference_number = f"ADJ-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                cursor.execute('''
                    INSERT INTO stock_movements (product_id, warehouse_id, movement_type, quantity,
                                               reference_number, notes, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (product_id, warehouse_id, movement_type, abs(adjustment_quantity),
                     reference_number, reason or f'{adjustment_type} adjustment', user_id))
                
                cursor.execute('COMMIT')
                conn.close()
                
                logger.info(f"Inventory adjusted: Product {product_id}, Warehouse {warehouse_id}, "
                           f"Adjustment: {adjustment_quantity}, New total: {new_quantity}")
                
                return {
                    'success': True,
                    'message': f'Inventory adjusted successfully. New quantity: {new_quantity}',
                    'previous_quantity': current_quantity,
                    'new_quantity': new_quantity,
                    'reference_number': reference_number
                }
                
            except Exception as e:
                cursor.execute('ROLLBACK')
                conn.close()
                raise e
                
        except Exception as e:
            logger.error(f"Error adjusting inventory: {e}")
            return {
                'success': False,
                'message': f'Adjustment failed: {str(e)}'
            }
    
    def get_warehouse_capacity_report(self) -> List[Dict]:
        """
        Generate capacity utilization report for all warehouses.
        
        Returns:
            list: Capacity report for all warehouses
        """
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT w.id, w.name, w.location, w.capacity,
                       COALESCE(SUM(i.quantity), 0) as total_items,
                       COUNT(DISTINCT i.product_id) as unique_products,
                       COUNT(CASE WHEN i.quantity <= i.reorder_level THEN 1 END) as low_stock_items
                FROM warehouses w
                LEFT JOIN inventory i ON w.id = i.warehouse_id
                GROUP BY w.id, w.name, w.location, w.capacity
                ORDER BY w.name
            ''')
            
            report = []
            for row in cursor.fetchall():
                warehouse_id, name, location, capacity, total_items, unique_products, low_stock_items = row
                
                utilization_percentage = 0
                available_capacity = capacity or 0
                
                if capacity and capacity > 0:
                    utilization_percentage = (total_items / capacity) * 100
                    available_capacity = capacity - total_items
                
                # Determine capacity status
                if utilization_percentage >= 90:
                    capacity_status = 'CRITICAL'
                elif utilization_percentage >= 75:
                    capacity_status = 'WARNING'
                else:
                    capacity_status = 'NORMAL'
                
                report.append({
                    'warehouse_id': warehouse_id,
                    'warehouse_name': name,
                    'location': location,
                    'capacity': capacity,
                    'total_items': total_items,
                    'unique_products': unique_products,
                    'low_stock_items': low_stock_items,
                    'utilization_percentage': round(utilization_percentage, 2),
                    'available_capacity': max(0, available_capacity),
                    'capacity_status': capacity_status
                })
            
            conn.close()
            return report
            
        except Exception as e:
            logger.error(f"Error generating capacity report: {e}")
            return []
    
    def get_transfer_history(self, warehouse_id: int = None, 
                            days_back: int = 30) -> List[Dict]:
        """
        Get transfer history between warehouses.
        
        Args:
            warehouse_id (int, optional): Specific warehouse to filter by
            days_back (int): Number of days to look back
            
        Returns:
            list: Transfer history records
        """
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            query = '''
                SELECT sm1.product_id, p.name as product_name, sm1.warehouse_id as from_warehouse,
                       sm2.warehouse_id as to_warehouse, sm1.quantity, sm1.reference_number,
                       sm1.created_at, u.username, sm1.notes,
                       w1.name as from_warehouse_name, w2.name as to_warehouse_name
                FROM stock_movements sm1
                JOIN stock_movements sm2 ON sm1.reference_number = sm2.reference_number
                JOIN products p ON sm1.product_id = p.id
                JOIN users u ON sm1.user_id = u.id
                JOIN warehouses w1 ON sm1.warehouse_id = w1.id
                JOIN warehouses w2 ON sm2.warehouse_id = w2.id
                WHERE sm1.movement_type = 'TRANSFER_OUT' 
                  AND sm2.movement_type = 'TRANSFER_IN'
                  AND sm1.created_at >= ?
            '''
            
            params = [cutoff_date]
            
            if warehouse_id:
                query += ' AND (sm1.warehouse_id = ? OR sm2.warehouse_id = ?)'
                params.extend([warehouse_id, warehouse_id])
            
            query += ' ORDER BY sm1.created_at DESC'
            
            cursor.execute(query, params)
            
            transfers = []
            for row in cursor.fetchall():
                (product_id, product_name, from_warehouse, to_warehouse, quantity,
                 reference_number, created_at, username, notes, from_warehouse_name,
                 to_warehouse_name) = row
                
                transfers.append({
                    'product_id': product_id,
                    'product_name': product_name,
                    'from_warehouse_id': from_warehouse,
                    'to_warehouse_id': to_warehouse,
                    'from_warehouse_name': from_warehouse_name,
                    'to_warehouse_name': to_warehouse_name,
                    'quantity': quantity,
                    'reference_number': reference_number,
                    'transfer_date': created_at,
                    'transferred_by': username,
                    'notes': notes
                })
            
            conn.close()
            return transfers
            
        except Exception as e:
            logger.error(f"Error getting transfer history: {e}")
            return []
    
    def optimize_inventory_distribution(self) -> List[Dict]:
        """
        Analyze inventory distribution and suggest optimizations.
        
        Returns:
            list: Optimization suggestions
        """
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Find products with uneven distribution across warehouses
            cursor.execute('''
                SELECT i.product_id, p.name, 
                       GROUP_CONCAT(w.name || ':' || i.quantity) as warehouse_quantities,
                       AVG(i.quantity) as avg_quantity,
                       MAX(i.quantity) - MIN(i.quantity) as quantity_difference,
                       COUNT(w.id) as warehouse_count
                FROM inventory i
                JOIN products p ON i.product_id = p.id
                JOIN warehouses w ON i.warehouse_id = w.id
                GROUP BY i.product_id, p.name
                HAVING COUNT(w.id) > 1 AND (MAX(i.quantity) - MIN(i.quantity)) > avg_quantity * 0.5
                ORDER BY quantity_difference DESC
            ''')
            
            suggestions = []
            for row in cursor.fetchall():
                product_id, product_name, warehouse_quantities, avg_quantity, quantity_difference, warehouse_count = row
                
                # Parse warehouse quantities to find imbalances
                warehouse_data = []
                for wq in warehouse_quantities.split(','):
                    warehouse_name, quantity = wq.split(':')
                    warehouse_data.append({
                        'warehouse_name': warehouse_name,
                        'quantity': int(quantity)
                    })
                
                # Sort by quantity
                warehouse_data.sort(key=lambda x: x['quantity'])
                
                # Suggest transfer from highest to lowest
                highest = warehouse_data[-1]
                lowest = warehouse_data[0]
                
                if highest['quantity'] - lowest['quantity'] > avg_quantity * 0.5:
                    suggested_transfer = int((highest['quantity'] - lowest['quantity']) / 2)
                    
                    suggestions.append({
                        'product_id': product_id,
                        'product_name': product_name,
                        'from_warehouse': highest['warehouse_name'],
                        'to_warehouse': lowest['warehouse_name'],
                        'current_from_quantity': highest['quantity'],
                        'current_to_quantity': lowest['quantity'],
                        'suggested_transfer': suggested_transfer,
                        'efficiency_gain': f"Reduces imbalance by {suggested_transfer} units",
                        'priority': 'HIGH' if quantity_difference > avg_quantity * 2 else 'MEDIUM'
                    })
            
            conn.close()
            return suggestions
            
        except Exception as e:
            logger.error(f"Error optimizing inventory distribution: {e}")
            return []