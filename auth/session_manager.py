"""
Session Management System for Retail Inventory Tracker

This module handles user session management, including session security,
timeout handling, and activity tracking.
"""

import sqlite3
import secrets
from datetime import datetime, timedelta
from flask import session, request
import logging

logger = logging.getLogger(__name__)

class SessionManager:
    """Manages user sessions and security."""
    
    def __init__(self):
        """Initialize the session manager."""
        self.database_path = 'database/inventory.db'
        self.session_timeout = timedelta(hours=8)  # 8 hour session timeout
        self.max_concurrent_sessions = 3  # Maximum concurrent sessions per user
    
    def create_session_tables(self):
        """Create session-related database tables."""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # User sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Login attempts table for security
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS login_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip_address TEXT NOT NULL,
                    username TEXT,
                    success BOOLEAN DEFAULT FALSE,
                    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_agent TEXT
                )
            ''')
            
            # User activity log
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT,
                    action TEXT NOT NULL,
                    resource TEXT,
                    ip_address TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Session tables created successfully")
            
        except Exception as e:
            logger.error(f"Error creating session tables: {e}")
    
    def generate_session_token(self):
        """Generate a secure session token."""
        return secrets.token_urlsafe(32)
    
    def create_session(self, user_id, ip_address=None, user_agent=None):
        """Create a new session for a user."""
        try:
            # Clean up old sessions first
            self.cleanup_expired_sessions(user_id)
            
            # Check for maximum concurrent sessions
            if self.get_active_session_count(user_id) >= self.max_concurrent_sessions:
                self.invalidate_oldest_session(user_id)
            
            session_token = self.generate_session_token()
            
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO user_sessions (user_id, session_token, ip_address, user_agent)
                VALUES (?, ?, ?, ?)
            ''', (user_id, session_token, ip_address, user_agent))
            
            conn.commit()
            conn.close()
            
            # Set Flask session
            session['session_token'] = session_token
            session['last_activity'] = datetime.now().isoformat()
            
            logger.info(f"Session created for user {user_id}")
            return session_token
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None
    
    def validate_session(self, user_id, session_token):
        """Validate if a session is still valid."""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT created_at, last_activity, is_active
                FROM user_sessions
                WHERE user_id = ? AND session_token = ?
            ''', (user_id, session_token))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result or not result[2]:  # Session doesn't exist or is inactive
                return False
            
            # Check session timeout
            last_activity = datetime.fromisoformat(result[1])
            if datetime.now() - last_activity > self.session_timeout:
                self.invalidate_session(session_token)
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating session: {e}")
            return False
    
    def update_session_activity(self, session_token):
        """Update the last activity timestamp for a session."""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE user_sessions
                SET last_activity = ?
                WHERE session_token = ?
            ''', (datetime.now(), session_token))
            
            conn.commit()
            conn.close()
            
            # Update Flask session
            session['last_activity'] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"Error updating session activity: {e}")
    
    def invalidate_session(self, session_token):
        """Invalidate a specific session."""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE user_sessions
                SET is_active = FALSE
                WHERE session_token = ?
            ''', (session_token,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Session {session_token[:8]}... invalidated")
            
        except Exception as e:
            logger.error(f"Error invalidating session: {e}")
    
    def invalidate_all_user_sessions(self, user_id):
        """Invalidate all sessions for a specific user."""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE user_sessions
                SET is_active = FALSE
                WHERE user_id = ?
            ''', (user_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"All sessions invalidated for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error invalidating user sessions: {e}")
    
    def cleanup_expired_sessions(self, user_id=None):
        """Clean up expired sessions."""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cutoff_time = datetime.now() - self.session_timeout
            
            if user_id:
                cursor.execute('''
                    UPDATE user_sessions
                    SET is_active = FALSE
                    WHERE user_id = ? AND last_activity < ?
                ''', (user_id, cutoff_time))
            else:
                cursor.execute('''
                    UPDATE user_sessions
                    SET is_active = FALSE
                    WHERE last_activity < ?
                ''', (cutoff_time,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
    
    def get_active_session_count(self, user_id):
        """Get the number of active sessions for a user."""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*)
                FROM user_sessions
                WHERE user_id = ? AND is_active = TRUE
            ''', (user_id,))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count
            
        except Exception as e:
            logger.error(f"Error getting active session count: {e}")
            return 0
    
    def invalidate_oldest_session(self, user_id):
        """Invalidate the oldest active session for a user."""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT session_token
                FROM user_sessions
                WHERE user_id = ? AND is_active = TRUE
                ORDER BY created_at ASC
                LIMIT 1
            ''', (user_id,))
            
            result = cursor.fetchone()
            if result:
                self.invalidate_session(result[0])
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error invalidating oldest session: {e}")
    
    def log_login_attempt(self, ip_address, username=None, success=False, user_agent=None):
        """Log a login attempt for security monitoring."""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO login_attempts (ip_address, username, success, user_agent)
                VALUES (?, ?, ?, ?)
            ''', (ip_address, username, success, user_agent))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error logging login attempt: {e}")
    
    def is_ip_blocked(self, ip_address, max_attempts=5, time_window=timedelta(minutes=15)):
        """Check if an IP address should be blocked due to failed login attempts."""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cutoff_time = datetime.now() - time_window
            
            cursor.execute('''
                SELECT COUNT(*)
                FROM login_attempts
                WHERE ip_address = ? AND success = FALSE AND attempted_at > ?
            ''', (ip_address, cutoff_time))
            
            failed_attempts = cursor.fetchone()[0]
            conn.close()
            
            return failed_attempts >= max_attempts
            
        except Exception as e:
            logger.error(f"Error checking IP block status: {e}")
            return False
    
    def log_user_activity(self, user_id, action, resource=None, session_token=None, ip_address=None):
        """Log user activity for audit purposes."""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO user_activity (user_id, session_token, action, resource, ip_address)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, session_token, action, resource, ip_address))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error logging user activity: {e}")
    
    def get_user_sessions(self, user_id):
        """Get all active sessions for a user."""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT session_token, ip_address, user_agent, created_at, last_activity
                FROM user_sessions
                WHERE user_id = ? AND is_active = TRUE
                ORDER BY last_activity DESC
            ''', (user_id,))
            
            sessions = cursor.fetchall()
            conn.close()
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            return []