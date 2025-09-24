# Retail Chain Inventory Tracker

A comprehensive web-based inventory management system designed for retail chains to track products across multiple warehouses with advanced analytics, AI-powered demand forecasting, and real-time reporting capabilities.

## Features

### 🏪 Core Inventory Management
- **Multi-Warehouse Support**: Manage inventory across multiple warehouse locations
- **Product Catalog**: Complete product management with categories, SKUs, and pricing
- **Stock Tracking**: Real-time inventory levels with automatic low-stock alerts
- **Stock Movements**: Detailed history of all inventory transactions

### 🤖 AI-Powered Analytics
- **Demand Forecasting**: Machine learning predictions for future inventory needs
- **Seasonal Analysis**: Identify and plan for seasonal demand patterns
- **Reorder Optimization**: AI-recommended reorder points and quantities
- **Anomaly Detection**: Automatic detection of unusual stock movements

### 👥 User Management
- **Role-Based Access**: Admin, Manager, and Employee roles with specific permissions
- **Secure Authentication**: Password hashing and session management
- **User Activity Tracking**: Monitor user actions and changes

### 📊 Reporting & Analytics
- **Real-Time Dashboard**: Live inventory status and key metrics
- **Custom Reports**: Generate PDF and CSV reports
- **Visual Analytics**: Charts and graphs for inventory trends
- **Alert System**: Automated notifications for critical inventory events

### 🔗 API Integration
- **RESTful API**: Complete API for external system integration
- **Comprehensive Endpoints**: Full CRUD operations for all resources
- **API Documentation**: Interactive API documentation

## Technology Stack

### Backend
- **Python 3.8+** - Core programming language
- **Flask 2.3+** - Web framework
- **SQLite/PostgreSQL** - Database (SQLite for development, PostgreSQL for production)
- **scikit-learn** - Machine learning for demand forecasting
- **Pandas** - Data processing and analysis

### Frontend
- **HTML5/CSS3** - Modern web standards
- **JavaScript** - Interactive functionality
- **Bootstrap 5** - Responsive UI framework
- **Chart.js** - Data visualization

### Security
- **Flask-Login** - User session management
- **Werkzeug** - Password hashing
- **CSRF Protection** - Cross-site request forgery protection

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)
- Git

### Quick Start

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-username/retail-inventory-tracker.git
   cd retail-inventory-tracker
   ```

2. **Create Virtual Environment**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize Database**
   ```bash
   python setup_database.py
   ```

5. **Run the Application**
   ```bash
   python app.py
   ```

6. **Access the Application**
   Open your web browser and navigate to `http://localhost:5000`

### Default Login Credentials
- **Admin**: Username: `admin`, Password: `admin123`
- **Manager**: Username: `manager`, Password: `manager123`
- **Employee**: Username: `employee`, Password: `employee123`

## Configuration

### Environment Variables
Create a `.env` file in the project root:

```env
# Flask Configuration
FLASK_SECRET_KEY=your-secret-key-here
FLASK_ENV=development
DEBUG=True

# Database Configuration
DATABASE_URL=sqlite:///database/inventory.db
# For PostgreSQL: DATABASE_URL=postgresql://username:password@localhost/inventory_db

# Email Configuration (optional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_USE_TLS=True

# AI Model Configuration
AI_MODEL_UPDATE_INTERVAL=24  # hours
DEMAND_FORECAST_DAYS=30
```

### Production Setup

For production deployment:

1. **Use PostgreSQL Database**
   ```bash
   pip install psycopg2-binary
   ```
   Update the DATABASE_URL in your environment variables.

2. **Use Production Server**
   ```bash
   # Using Gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 app:app

   # Using Waitress (Windows)
   waitress-serve --host=0.0.0.0 --port=8000 app:app
   ```

3. **Configure Reverse Proxy** (Nginx recommended)
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

## Usage

### Dashboard Overview
The main dashboard provides:
- Current inventory summary
- Low stock alerts
- Recent stock movements
- Key performance indicators

### Managing Products
1. Navigate to **Products** section
2. Click **Add Product** to create new products
3. Edit existing products by clicking the edit icon
4. Categories and SKUs help organize your catalog

### Warehouse Operations
1. Access **Warehouse** section for multi-location management
2. Transfer stock between warehouses
3. View warehouse-specific inventory levels
4. Monitor warehouse capacity utilization

### Inventory Tracking
1. **Add Stock**: Record new inventory arrivals
2. **Adjust Stock**: Make corrections and adjustments
3. **Reserve Stock**: Set aside inventory for orders
4. **View History**: Track all stock movements

### AI Predictions
1. Navigate to **Analytics** for AI insights
2. View demand forecasts for individual products
3. Get reorder recommendations
4. Monitor prediction accuracy

### Reports
1. Go to **Reports** section
2. Select date range and filters
3. Generate PDF or CSV exports
4. Schedule automated reports (coming soon)

## API Documentation

### Authentication
All API endpoints require authentication. Use session-based authentication or API keys.

### Base URL
```
http://localhost:5000/api/v1
```

### Endpoints

#### Inventory Management
- `GET /api/v1/inventory` - Get all inventory items
- `GET /api/v1/inventory/{id}` - Get specific inventory item
- `POST /api/v1/inventory` - Create new inventory item
- `PUT /api/v1/inventory/{id}` - Update inventory item
- `DELETE /api/v1/inventory/{id}` - Delete inventory item

#### Products
- `GET /api/v1/products` - Get all products
- `POST /api/v1/products` - Create new product

#### Warehouses
- `GET /api/v1/warehouses` - Get all warehouses

#### Stock Movements
- `GET /api/v1/movements` - Get stock movement history

#### Alerts
- `GET /api/v1/alerts` - Get system alerts

### Example API Usage
```python
import requests

# Get inventory data
response = requests.get('http://localhost:5000/api/v1/inventory')
inventory_data = response.json()

# Add new inventory item
new_item = {
    'product_id': 1,
    'warehouse_id': 1,
    'quantity': 100,
    'reorder_level': 20
}
response = requests.post('http://localhost:5000/api/v1/inventory', json=new_item)
```

## File Structure

```
retail_inventory_tracker/
│
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── setup_database.py              # Database initialization script
├── README.md                       # Project documentation
│
├── auth/                           # Authentication modules
│   ├── __init__.py
│   ├── roles.py                    # Role-based access control
│   └── session_manager.py          # Session management
│
├── api/                            # REST API endpoints
│   ├── __init__.py
│   └── inventory_api.py            # Inventory API implementation
│
├── ai_engine/                      # AI and ML components
│   ├── __init__.py
│   └── predictor.py               # Demand forecasting engine
│
├── warehouse/                      # Warehouse management
│   ├── __init__.py
│   └── warehouse_controller.py     # Warehouse operations
│
├── reports/                        # Reporting system
│   ├── __init__.py
│   ├── exporter.py                # Report generation
│   └── templates/
│       └── report_template.html   # PDF report template
│
├── templates/                      # HTML templates
│   ├── base.html                  # Base template
│   ├── login.html                 # Login page
│   ├── dashboard.html             # Main dashboard
│   ├── inventory.html             # Inventory management
│   ├── alerts.html                # Alerts page
│   ├── warehouse.html             # Warehouse management
│   ├── admin_panel.html           # Admin panel
│   ├── api_docs.html              # API documentation
│   └── logout.html                # Logout page
│
├── static/                         # Static files
│   ├── style.css                  # Main stylesheet
│   └── js/                        # JavaScript files (future)
│
└── database/                       # Database files
    └── inventory.db               # SQLite database (auto-created)
```

## Contributing

We welcome contributions! Please follow these steps:

1. **Fork the Repository**
2. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make Changes** and commit them
4. **Run Tests**
   ```bash
   python -m pytest
   ```
5. **Submit Pull Request**

### Code Style
- Follow PEP 8 for Python code
- Use meaningful variable names
- Add docstrings to functions and classes
- Write unit tests for new features

## Testing

Run the test suite:
```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=.

# Run specific test file
python -m pytest tests/test_inventory.py
```

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Ensure the database directory exists
   - Check file permissions
   - Run `python setup_database.py`

2. **Import Errors**
   - Verify virtual environment is activated
   - Install requirements: `pip install -r requirements.txt`

3. **Port Already in Use**
   - Change the port in `app.py`: `app.run(port=5001)`
   - Or kill the existing process using the port

4. **AI Predictions Not Working**
   - Ensure sufficient historical data exists
   - Check TensorFlow/scikit-learn installation
   - Verify Python version compatibility

### Logs
Application logs are written to `logs/inventory_tracker.log`

## Security Considerations

- **Change Default Passwords**: Update default user passwords immediately
- **Use HTTPS**: Enable SSL/TLS in production
- **Regular Backups**: Implement automated database backups
- **Update Dependencies**: Keep packages up to date
- **Input Validation**: All user inputs are validated and sanitized

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions:
- 📧 Email: support@inventorytracker.com
- 🐛 Bug Reports: Create an issue on GitHub
- 💬 Discussions: Use GitHub Discussions
- 📖 Documentation: Check the Wiki section

## Roadmap

### Version 2.0 (Planned)
- [ ] Mobile app (React Native)
- [ ] Advanced reporting dashboard
- [ ] Integration with popular e-commerce platforms
- [ ] Barcode scanning support
- [ ] Multi-language support
- [ ] Advanced AI models for demand forecasting
- [ ] Real-time notifications via WebSocket
- [ ] Supplier management module
- [ ] Purchase order automation

### Version 2.1 (Future)
- [ ] IoT device integration
- [ ] Blockchain-based supply chain tracking
- [ ] Advanced analytics with BigData support
- [ ] Machine learning model marketplace

## Acknowledgments

- Flask community for the excellent web framework
- scikit-learn team for machine learning capabilities
- Bootstrap team for the responsive UI framework
- Chart.js for beautiful data visualizations

---

**Built with ❤️ for retail inventory management**