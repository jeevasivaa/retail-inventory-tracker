"""
Simplified Inventory Prediction Engine

This module provides basic prediction capabilities for inventory forecasting
using statistical methods without heavy ML dependencies.
"""

import numpy as np
import sqlite3
from datetime import datetime, timedelta
import os
import logging
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger(__name__)

class InventoryPredictor:
    """
    Simplified inventory prediction system using statistical methods.
    """
    
    def __init__(self, database_path='database/inventory.db'):
        """Initialize the predictor with database connection."""
        self.database_path = database_path
        
    def predict_demand(self, product_id: int, warehouse_id: int, days: int = 30) -> Dict:
        """
        Predict demand for a product using simple moving average.
        
        Args:
            product_id (int): Product ID
            warehouse_id (int): Warehouse ID
            days (int): Number of days to predict
            
        Returns:
            dict: Prediction results
        """
        try:
            # Get historical data (list of dict rows)
            historical_data = self._get_historical_movements(product_id, warehouse_id)

            if len(historical_data) < 7:  # Need at least a week of data
                return {
                    'predicted_demand': 10,  # Default fallback
                    'confidence': 0.3,
                    'method': 'default_fallback',
                    'message': 'Insufficient historical data'
                }
            
            # Calculate daily averages for different periods
            daily_movements: List[float] = []
            for row in historical_data:
                if row.get('movement_type') in ['OUT', 'TRANSFER_OUT']:
                    daily_movements.append(row.get('quantity', 0))
            
            if not daily_movements:
                return {
                    'predicted_demand': 5,
                    'confidence': 0.4,
                    'method': 'no_outbound_data',
                    'message': 'No outbound movement data available'
                }
            
            # Simple moving average prediction
            recent_avg = np.mean(daily_movements[-7:]) if len(daily_movements) >= 7 else np.mean(daily_movements)
            overall_avg = np.mean(daily_movements)
            
            # Weight recent data more heavily
            predicted_daily_demand = (recent_avg * 0.7) + (overall_avg * 0.3)
            predicted_total_demand = predicted_daily_demand * days
            
            # Calculate confidence based on data consistency
            std_dev = np.std(daily_movements)
            confidence = max(0.5, 1 - (std_dev / (predicted_daily_demand + 1)))
            
            return {
                'predicted_demand': round(predicted_total_demand, 2),
                'predicted_daily_demand': round(predicted_daily_demand, 2),
                'confidence': round(confidence, 2),
                'method': 'moving_average',
                'historical_points': len(daily_movements),
                'message': f'Prediction based on {len(daily_movements)} historical data points'
            }
            
        except Exception as e:
            logger.error(f"Error in demand prediction: {e}")
            return {
                'predicted_demand': 15,
                'confidence': 0.3,
                'method': 'error_fallback',
                'message': f'Prediction error: {str(e)}'
            }
    
    def get_reorder_recommendation(self, product_id: int, warehouse_id: int) -> Dict:
        """
        Get reorder recommendations for a product.
        
        Args:
            product_id (int): Product ID
            warehouse_id (int): Warehouse ID
            
        Returns:
            dict: Reorder recommendations
        """
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Get current inventory
            cursor.execute('''
                SELECT i.quantity, i.reserved_quantity, i.reorder_level, 
                       i.max_stock_level, p.name as product_name
                FROM inventory i
                JOIN products p ON i.product_id = p.id
                WHERE i.product_id = ? AND i.warehouse_id = ?
            ''', (product_id, warehouse_id))
            
            inventory = cursor.fetchone()
            conn.close()
            
            if not inventory:
                return {
                    'should_reorder': False,
                    'message': 'Product not found in inventory'
                }
            
            current_qty, reserved_qty, reorder_level, max_level, product_name = inventory
            available_qty = current_qty - reserved_qty
            
            # Get demand prediction for next 30 days
            demand_prediction = self.predict_demand(product_id, warehouse_id, 30)
            predicted_demand = demand_prediction['predicted_demand']
            
            # Calculate safety stock (20% of predicted demand)
            safety_stock = predicted_demand * 0.2
            
            # Calculate optimal reorder quantity
            if available_qty <= reorder_level:
                # Calculate how much to order
                target_stock = max_level * 0.8  # Target 80% of max capacity
                recommended_quantity = target_stock - available_qty
                
                return {
                    'should_reorder': True,
                    'recommended_quantity': round(recommended_quantity),
                    'current_stock': current_qty,
                    'available_stock': available_qty,
                    'predicted_demand_30_days': round(predicted_demand),
                    'safety_stock': round(safety_stock),
                    'urgency': 'high' if available_qty <= reorder_level * 0.5 else 'medium',
                    'product_name': product_name,
                    'message': f'Reorder recommended: stock level is {available_qty}, below reorder level of {reorder_level}'
                }
            else:
                days_until_reorder = max(1, (available_qty - reorder_level) / (predicted_demand / 30))
                
                return {
                    'should_reorder': False,
                    'current_stock': current_qty,
                    'available_stock': available_qty,
                    'predicted_demand_30_days': round(predicted_demand),
                    'days_until_reorder': round(days_until_reorder),
                    'product_name': product_name,
                    'message': f'No reorder needed. Estimated {round(days_until_reorder)} days until reorder point.'
                }
                
        except Exception as e:
            logger.error(f"Error in reorder recommendation: {e}")
            return {
                'should_reorder': False,
                'message': f'Error generating recommendation: {str(e)}'
            }
    
    def _get_historical_movements(self, product_id: int, warehouse_id: int, days: int = 90) -> List[Dict[str, Any]]:
        """Get historical stock movements for analysis as a list of dicts.

        This avoids pulling in pandas; consumers expect an iterable of rows
        where each row is a mapping with keys: movement_type, quantity, created_at, reference_number, notes.
        """
        try:
            conn = sqlite3.connect(self.database_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = '''
                SELECT movement_type, quantity, created_at, reference_number, notes
                FROM stock_movements
                WHERE product_id = ? AND warehouse_id = ?
                AND created_at >= datetime('now', '-{} days')
                ORDER BY created_at DESC
            '''.format(days)

            cursor.execute(query, (product_id, warehouse_id))
            rows = cursor.fetchall()
            conn.close()

            result: List[Dict[str, Any]] = [dict(r) for r in rows]
            return result

        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return []
    
    def get_dashboard_summary(self) -> Dict:
        """Get summary data for dashboard display."""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Get products that need reordering
            cursor.execute('''
                SELECT COUNT(*) FROM inventory i
                WHERE i.quantity <= i.reorder_level
            ''')
            reorder_needed = cursor.fetchone()[0]
            
            # Get out of stock items
            cursor.execute('SELECT COUNT(*) FROM inventory WHERE quantity = 0')
            out_of_stock = cursor.fetchone()[0]
            
            # Get total inventory value estimate
            cursor.execute('''
                SELECT COALESCE(SUM(i.quantity * p.unit_price), 0)
                FROM inventory i
                JOIN products p ON i.product_id = p.id
            ''')
            total_value = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'reorder_needed': reorder_needed,
                'out_of_stock': out_of_stock,
                'total_inventory_value': round(total_value, 2),
                'prediction_engine_status': 'Active',
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard summary: {e}")
            return {
                'reorder_needed': 0,
                'out_of_stock': 0,
                'total_inventory_value': 0,
                'prediction_engine_status': 'Error',
                'error': str(e)
            }