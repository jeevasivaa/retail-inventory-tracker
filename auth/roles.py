"""
Role Management System for Retail Inventory Tracker

This module handles user roles and permissions throughout the application.
Supports admin, manager, and employee roles with different access levels.
"""

import sqlite3
from functools import wraps
from flask import session, redirect, url_for, flash
import logging

logger = logging.getLogger(__name__)

class RoleManager:
    """Manages user roles and permissions."""
    
    # Define role hierarchy and permissions
    ROLES = {
        'admin': {
            'level': 3,
            'permissions': [
                'view_all', 'edit_all', 'delete_all', 'manage_users',
                'manage_warehouses', 'view_reports', 'export_data',
                'manage_api', 'system_settings'
            ]
        },
        'manager': {
            'level': 2,
            'permissions': [
                'view_all', 'edit_inventory', 'add_inventory',
                'view_reports', 'export_data', 'manage_warehouse_assigned'
            ]
        },
        'employee': {
            'level': 1,
            'permissions': [
                'view_inventory', 'update_stock', 'view_alerts'
            ]
        }
    }
    
    def __init__(self):
        """Initialize the role manager."""
        self.database_path = 'database/inventory.db'
    
    def get_user_role(self, user_id):
        """Get the role of a specific user."""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            cursor.execute('SELECT role FROM users WHERE id = ?', (user_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0]
            return None
        except Exception as e:
            logger.error(f"Error getting user role: {e}")
            return None
    
    def has_permission(self, user_id, permission):
        """Check if a user has a specific permission."""
        user_role = self.get_user_role(user_id)
        if not user_role or user_role not in self.ROLES:
            return False
        
        return permission in self.ROLES[user_role]['permissions']
    
    def get_role_level(self, role):
        """Get the numeric level of a role."""
        if role in self.ROLES:
            return self.ROLES[role]['level']
        return 0
    
    def can_access_role(self, user_role, target_role):
        """Check if a user role can access/modify a target role."""
        user_level = self.get_role_level(user_role)
        target_level = self.get_role_level(target_role)
        return user_level >= target_level
    
    def get_available_roles(self, current_user_role):
        """Get roles that the current user can assign to others."""
        current_level = self.get_role_level(current_user_role)
        available = []
        
        for role, info in self.ROLES.items():
            if current_level >= info['level']:
                available.append(role)
        
        return available
    
    def update_user_role(self, user_id, new_role, admin_user_id):
        """Update a user's role (admin only)."""
        try:
            admin_role = self.get_user_role(admin_user_id)
            if not self.has_permission(admin_user_id, 'manage_users'):
                return False, "Insufficient permissions to manage users"
            
            if new_role not in self.ROLES:
                return False, "Invalid role specified"
            
            if not self.can_access_role(admin_role, new_role):
                return False, "Cannot assign a role higher than your own"
            
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
            conn.commit()
            conn.close()
            
            logger.info(f"User {user_id} role updated to {new_role} by admin {admin_user_id}")
            return True, "Role updated successfully"
            
        except Exception as e:
            logger.error(f"Error updating user role: {e}")
            return False, "Database error occurred"

def require_permission(permission):
    """Decorator to require a specific permission for a route."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('login'))
            
            role_manager = RoleManager()
            if not role_manager.has_permission(session['user_id'], permission):
                flash('You do not have permission to access this resource.', 'error')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_role(required_role):
    """Decorator to require a specific role or higher for a route."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('login'))
            
            role_manager = RoleManager()
            user_role = role_manager.get_user_role(session['user_id'])
            
            if not user_role:
                flash('Unable to verify user role.', 'error')
                return redirect(url_for('dashboard'))
            
            user_level = role_manager.get_role_level(user_role)
            required_level = role_manager.get_role_level(required_role)
            
            if user_level < required_level:
                flash(f'Access denied. {required_role.title()} privileges required.', 'error')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_user_permissions(user_id):
    """Get all permissions for a specific user."""
    role_manager = RoleManager()
    user_role = role_manager.get_user_role(user_id)
    
    if user_role and user_role in role_manager.ROLES:
        return role_manager.ROLES[user_role]['permissions']
    return []