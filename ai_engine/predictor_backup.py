"""
AI-Powered Inventory Prediction Engine (Simplified)

This module provides basic prediction capabilities for inventory forecasting,
demand prediction, and automated reorder suggestions using statistical methods.
"""

import numpy as np
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import os
import logging
import warnings

# Suppress sklearn warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class InventoryPredictor:
    """AI-powered inventory demand prediction and optimization."""
    
    def __init__(self, database_path='database/inventory.db'):
        """Initialize the inventory predictor."""
        self.database_path = database_path
        self.models = {}
        self.scalers = {}
        self.model_path = 'ai_engine/models/'
        
        # Create models directory if it doesn't exist
        os.makedirs(self.model_path, exist_ok=True)
        
        # Initialize default models
        self.available_models = {
            'random_forest': RandomForestRegressor(
                n_estimators=100,
                random_state=42,
                n_jobs=-1
            ),
            'linear_regression': LinearRegression(),
        }
        
        # Load existing models if available
        self.load_models()
    
    def get_historical_data(self, product_id=None, days_back=365):
        """
        Get historical sales and inventory data for training.
        
        Args:
            product_id (int, optional): Specific product ID to get data for
            days_back (int): Number of days to look back for historical data
            
        Returns:
            pandas.DataFrame: Historical data with features and target variables
        """
        try:
            conn = sqlite3.connect(self.database_path)
            
            # Base query for historical stock movements
            query = '''
                SELECT 
                    sm.product_id,
                    p.category,
                    p.unit_price,
                    sm.warehouse_id,
                    sm.movement_type,
                    sm.quantity,
                    sm.created_at,
                    strftime('%w', sm.created_at) as day_of_week,
                    strftime('%m', sm.created_at) as month,
                    strftime('%Y', sm.created_at) as year,
                    i.reorder_level,
                    i.max_stock_level
                FROM stock_movements sm
                JOIN products p ON sm.product_id = p.id
                JOIN inventory i ON sm.product_id = i.product_id AND sm.warehouse_id = i.warehouse_id
                WHERE sm.created_at >= date('now', '-{} days')
            '''.format(days_back)
            
            if product_id:
                query += f' AND sm.product_id = {product_id}'
            
            query += ' ORDER BY sm.created_at ASC'
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if df.empty:
                logger.warning("No historical data found")
                return pd.DataFrame()
            
            # Convert date column
            df['created_at'] = pd.to_datetime(df['created_at'])
            
            # Create additional features
            df = self._create_features(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return pd.DataFrame()
    
    def _create_features(self, df):
        """Create additional features for machine learning models."""
        # Time-based features
        df['day_of_week'] = df['day_of_week'].astype(int)
        df['month'] = df['month'].astype(int)
        df['year'] = df['year'].astype(int)
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        
        # Price-based features
        df['price_category'] = pd.cut(
            df['unit_price'], 
            bins=[0, 10, 50, 100, float('inf')], 
            labels=['low', 'medium', 'high', 'premium']
        )
        
        # Movement type encoding
        df['is_outbound'] = (df['movement_type'] == 'OUT').astype(int)
        df['is_inbound'] = (df['movement_type'] == 'IN').astype(int)
        
        # Category encoding (simple label encoding for now)
        categories = df['category'].unique()
        category_map = {cat: i for i, cat in enumerate(categories)}
        df['category_encoded'] = df['category'].map(category_map)
        
        # Rolling averages (if enough data)
        if len(df) > 7:
            df = df.sort_values(['product_id', 'created_at'])
            df['quantity_7d_avg'] = df.groupby('product_id')['quantity'].rolling(7, min_periods=1).mean().values
            df['quantity_30d_avg'] = df.groupby('product_id')['quantity'].rolling(30, min_periods=1).mean().values
        else:
            df['quantity_7d_avg'] = df['quantity']
            df['quantity_30d_avg'] = df['quantity']
        
        return df
    
    def prepare_training_data(self, df):
        """
        Prepare data for model training.
        
        Args:
            df (pandas.DataFrame): Historical data
            
        Returns:
            tuple: (X, y) - Features and target variables
        """
        if df.empty:
            return np.array([]), np.array([])
        
        # Select features for training
        feature_columns = [
            'product_id', 'category_encoded', 'unit_price', 'warehouse_id',
            'day_of_week', 'month', 'is_weekend', 'is_outbound', 'is_inbound',
            'reorder_level', 'max_stock_level', 'quantity_7d_avg', 'quantity_30d_avg'
        ]
        
        # Filter out rows with missing values
        available_columns = [col for col in feature_columns if col in df.columns]
        df_clean = df[available_columns + ['quantity']].dropna()
        
        if df_clean.empty:
            logger.warning("No clean data available for training")
            return np.array([]), np.array([])
        
        X = df_clean[available_columns].values
        y = df_clean['quantity'].values
        
        return X, y
    
    def train_model(self, product_id=None, model_type='random_forest'):
        """
        Train a prediction model for inventory demand.
        
        Args:
            product_id (int, optional): Specific product to train for
            model_type (str): Type of model to train
            
        Returns:
            dict: Training results and metrics
        """
        try:
            # Get historical data
            df = self.get_historical_data(product_id)
            
            if df.empty:
                return {
                    'success': False,
                    'message': 'No historical data available for training'
                }
            
            # Prepare training data
            X, y = self.prepare_training_data(df)
            
            if len(X) == 0:
                return {
                    'success': False,
                    'message': 'No valid training data available'
                }
            
            # Split data
            if len(X) > 10:  # Only split if we have enough data
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.2, random_state=42
                )
            else:
                X_train, X_test, y_train, y_test = X, X, y, y
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model
            model = self.available_models[model_type]
            model.fit(X_train_scaled, y_train)
            
            # Make predictions
            y_pred = model.predict(X_test_scaled)
            
            # Calculate metrics
            mae = mean_absolute_error(y_test, y_pred)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            # Store model and scaler
            model_key = f"{model_type}_{product_id if product_id else 'global'}"
            self.models[model_key] = model
            self.scalers[model_key] = scaler
            
            # Save model to disk
            self.save_model(model_key, model, scaler)
            
            logger.info(f"Model trained successfully: {model_key}")
            
            return {
                'success': True,
                'model_key': model_key,
                'metrics': {
                    'mean_absolute_error': mae,
                    'mean_squared_error': mse,
                    'r2_score': r2
                },
                'training_samples': len(X_train),
                'test_samples': len(X_test)
            }
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            return {
                'success': False,
                'message': f'Training failed: {str(e)}'
            }
    
    def predict_demand(self, product_id, days_ahead=30, warehouse_id=1):
        """
        Predict future demand for a product.
        
        Args:
            product_id (int): Product ID to predict for
            days_ahead (int): Number of days to predict ahead
            warehouse_id (int): Warehouse ID
            
        Returns:
            dict: Prediction results
        """
        try:
            # Try product-specific model first, then global model
            model_keys = [
                f"random_forest_{product_id}",
                f"linear_regression_{product_id}",
                "random_forest_global",
                "linear_regression_global"
            ]
            
            model_key = None
            for key in model_keys:
                if key in self.models:
                    model_key = key
                    break
            
            if not model_key:
                # Train a new model if none exists
                train_result = self.train_model(product_id)
                if train_result['success']:
                    model_key = train_result['model_key']
                else:
                    return {
                        'success': False,
                        'message': 'No trained model available and training failed'
                    }
            
            model = self.models[model_key]
            scaler = self.scalers[model_key]
            
            # Get current product data
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT p.category, p.unit_price, i.reorder_level, i.max_stock_level, i.quantity
                FROM products p
                JOIN inventory i ON p.id = i.product_id
                WHERE p.id = ? AND i.warehouse_id = ?
            ''', (product_id, warehouse_id))
            
            product_data = cursor.fetchone()
            conn.close()
            
            if not product_data:
                return {
                    'success': False,
                    'message': 'Product not found'
                }
            
            category, unit_price, reorder_level, max_stock_level, current_quantity = product_data
            
            # Create prediction features
            predictions = []
            dates = []
            
            for i in range(days_ahead):
                future_date = datetime.now() + timedelta(days=i)
                
                # Create feature vector
                features = np.array([[
                    product_id,
                    hash(category) % 100,  # Simple category encoding
                    unit_price,
                    warehouse_id,
                    future_date.weekday(),
                    future_date.month,
                    1 if future_date.weekday() >= 5 else 0,  # is_weekend
                    1,  # assume outbound movement
                    0,  # not inbound
                    reorder_level,
                    max_stock_level,
                    current_quantity,  # Use current as rolling average
                    current_quantity
                ]])
                
                # Scale features
                features_scaled = scaler.transform(features)
                
                # Make prediction
                prediction = model.predict(features_scaled)[0]
                
                # Ensure prediction is reasonable (non-negative)
                prediction = max(0, prediction)
                
                predictions.append(prediction)
                dates.append(future_date.strftime('%Y-%m-%d'))
            
            return {
                'success': True,
                'product_id': product_id,
                'predictions': predictions,
                'dates': dates,
                'model_used': model_key,
                'current_stock': current_quantity,
                'reorder_level': reorder_level
            }
            
        except Exception as e:
            logger.error(f"Error predicting demand: {e}")
            return {
                'success': False,
                'message': f'Prediction failed: {str(e)}'
            }
    
    def get_reorder_suggestions(self, warehouse_id=None):
        """
        Get AI-powered reorder suggestions for products.
        
        Args:
            warehouse_id (int, optional): Specific warehouse to analyze
            
        Returns:
            list: List of reorder suggestions
        """
        try:
            conn = sqlite3.connect(self.database_path)
            
            query = '''
                SELECT i.product_id, p.name, i.quantity, i.reorder_level, 
                       i.max_stock_level, p.unit_price, w.name as warehouse_name
                FROM inventory i
                JOIN products p ON i.product_id = p.id
                JOIN warehouses w ON i.warehouse_id = w.id
                WHERE i.quantity <= i.reorder_level * 1.2
            '''
            
            params = []
            if warehouse_id:
                query += ' AND i.warehouse_id = ?'
                params.append(warehouse_id)
            
            query += ' ORDER BY (i.quantity / i.reorder_level) ASC'
            
            cursor = conn.cursor()
            cursor.execute(query, params)
            low_stock_items = cursor.fetchall()
            conn.close()
            
            suggestions = []
            
            for item in low_stock_items:
                product_id, name, quantity, reorder_level, max_stock, unit_price, warehouse_name = item
                
                # Get demand prediction
                prediction_result = self.predict_demand(product_id)
                
                if prediction_result['success']:
                    # Calculate suggested order quantity based on predictions
                    avg_predicted_demand = np.mean(prediction_result['predictions'][:7])  # Next 7 days
                    
                    # Safety stock calculation
                    safety_stock = reorder_level * 0.2
                    
                    # Suggested order quantity
                    suggested_quantity = max(
                        reorder_level - quantity + safety_stock,
                        avg_predicted_demand * 7  # 7 days worth of predicted demand
                    )
                    
                    # Don't exceed max stock level
                    if max_stock > 0:
                        suggested_quantity = min(suggested_quantity, max_stock - quantity)
                    
                    priority = 'HIGH' if quantity <= reorder_level * 0.5 else 'MEDIUM'
                    
                    suggestions.append({
                        'product_id': product_id,
                        'product_name': name,
                        'warehouse': warehouse_name,
                        'current_stock': quantity,
                        'reorder_level': reorder_level,
                        'suggested_quantity': int(suggested_quantity),
                        'predicted_demand_7d': round(avg_predicted_demand, 1),
                        'priority': priority,
                        'estimated_cost': suggested_quantity * unit_price,
                        'stock_ratio': quantity / reorder_level if reorder_level > 0 else 0
                    })
                else:
                    # Fallback suggestion without AI prediction
                    suggested_quantity = reorder_level - quantity + (reorder_level * 0.2)
                    priority = 'HIGH' if quantity <= reorder_level * 0.5 else 'MEDIUM'
                    
                    suggestions.append({
                        'product_id': product_id,
                        'product_name': name,
                        'warehouse': warehouse_name,
                        'current_stock': quantity,
                        'reorder_level': reorder_level,
                        'suggested_quantity': int(max(suggested_quantity, 0)),
                        'predicted_demand_7d': None,
                        'priority': priority,
                        'estimated_cost': max(suggested_quantity, 0) * unit_price,
                        'stock_ratio': quantity / reorder_level if reorder_level > 0 else 0
                    })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating reorder suggestions: {e}")
            return []
    
    def save_model(self, model_key, model, scaler):
        """Save model and scaler to disk."""
        try:
            model_file = os.path.join(self.model_path, f'{model_key}_model.pkl')
            scaler_file = os.path.join(self.model_path, f'{model_key}_scaler.pkl')
            
            with open(model_file, 'wb') as f:
                pickle.dump(model, f)
            
            with open(scaler_file, 'wb') as f:
                pickle.dump(scaler, f)
                
            logger.info(f"Model saved: {model_key}")
            
        except Exception as e:
            logger.error(f"Error saving model {model_key}: {e}")
    
    def load_models(self):
        """Load existing models from disk."""
        try:
            if not os.path.exists(self.model_path):
                return
                
            for filename in os.listdir(self.model_path):
                if filename.endswith('_model.pkl'):
                    model_key = filename.replace('_model.pkl', '')
                    model_file = os.path.join(self.model_path, filename)
                    scaler_file = os.path.join(self.model_path, f'{model_key}_scaler.pkl')
                    
                    if os.path.exists(scaler_file):
                        try:
                            with open(model_file, 'rb') as f:
                                self.models[model_key] = pickle.load(f)
                            
                            with open(scaler_file, 'rb') as f:
                                self.scalers[model_key] = pickle.load(f)
                                
                            logger.info(f"Model loaded: {model_key}")
                            
                        except Exception as e:
                            logger.error(f"Error loading model {model_key}: {e}")
                            
        except Exception as e:
            logger.error(f"Error loading models: {e}")
    
    def get_model_performance(self):
        """Get performance metrics for all trained models."""
        performance = {}
        
        for model_key in self.models.keys():
            try:
                # This would ideally load test metrics saved during training
                # For now, return basic info about the model
                model = self.models[model_key]
                performance[model_key] = {
                    'model_type': type(model).__name__,
                    'trained': True,
                    'features': getattr(model, 'n_features_in_', 'Unknown')
                }
            except Exception as e:
                logger.error(f"Error getting performance for {model_key}: {e}")
                
        return performance