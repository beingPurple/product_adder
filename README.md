# Product Adder - Shopify Catalog Monitor

## Things to fix



## Overview

This application monitors the JDS Wholesale catalog, compares SKUs against a Shopify store's existing products, and provides a streamlined interface for adding new products to the store. It integrates with your existing pricing formulas and SKU handling policies.

## Project Context

This project builds upon the existing `edit_price` system and follows the same patterns for:
- **SKU Cleaning**: Removes hyphens and letters preceding them (e.g., "ABC-LPB004" → "LPB004")
- **Pricing Formulas**: Uses the same pricing logic as the existing system
- **API Integration**: Leverages existing JDS and Shopify authentication

## Architecture

```
product_adder/
├── app.py                 # Main Flask application
├── jds_client.py         # JDS API integration
├── shopify_client.py     # Shopify API integration  
├── pricing_calculator.py # Pricing formulas (ported from edit_price)
├── database.py           # SQLite database models
├── templates/
│   ├── index.html        # Main dashboard
│   ├── product_list.html # Product selection interface
│   └── base.html         # Base template
├── static/
│   ├── css/style.css     # Custom styles
│   └── js/main.js        # Frontend JavaScript
├── requirements.txt      # Python dependencies
├── .env.example         # Environment variables template
└── README.md            # This file
```

## Development Phases

### Phase 1: Foundation Setup (Week 1)

**Goal**: Set up basic project structure and data collection
 **Goal**: Set up basic project structure and data collection

**Tasks**:
1. **Project Setup**
    - Configure environment variables (.env file)
   - Configure environment variables (.env file)
   - Set up SQLite database with initial schema

2. **JDS API Integration** (`jds_client.py`)
   - Port SKU cleaning logic from `edit_price/main.py`:
     ```python
     def clean_sku_for_external_api(sku):
         """Clean SKU by removing hyphen and any letters preceding it"""
         if '-' in sku:
             parts = sku.split('-')
             return parts[-1]
         return sku
     ```
   - Implement function to fetch all available SKUs from JDS
   - Implement batch product details fetching
   - Handle API rate limiting and error responses

3. **Shopify API Integration** (`shopify_client.py`)
   - Port existing Shopify authentication from `edit_price/shopify_auth.py`
   - Implement function to fetch all existing product SKUs
   - Implement function to fetch product details by SKU
   - Handle GraphQL queries for efficient data retrieval

4. **Database Schema** (`database.py`)
   ```sql
   -- JDS Products table
   CREATE TABLE jds_products (
       id INTEGER PRIMARY KEY,
       sku TEXT UNIQUE NOT NULL,
       name TEXT,
       description TEXT,
       case_quantity INTEGER,
       less_than_case_price REAL,
       one_case REAL,
       five_cases REAL,
       ten_cases REAL,
       twenty_cases REAL,
       forty_cases REAL,
       image_url TEXT,
       thumbnail_url TEXT,
       quick_image_url TEXT,
       available_quantity INTEGER,
       local_quantity INTEGER,
       last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );

   -- Shopify Products table
   CREATE TABLE shopify_products (
       id INTEGER PRIMARY KEY,
       sku TEXT UNIQUE NOT NULL,
       product_id TEXT,
       variant_id TEXT,
       current_price REAL,
       product_title TEXT,
       last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

**Deliverables**:
- Working Flask app that can fetch data from both APIs
- Database with proper schema
- Basic logging and error handling

### Phase 2: Core Logic Implementation (Week 2)

**Goal**: Implement SKU comparison and pricing calculation

**Tasks**:
1. **Pricing Calculator** (`pricing_calculator.py`)
   - Port pricing formulas from `edit_price/main.py`:
     ```python
     def calculate_price(formula, x, under5_formula=None):
         import math
         if under5_formula and float(x) < 5:
             return eval(under5_formula, {"x": float(x), "math": math, "__builtins__": {}})
         else:
             return eval(formula, {"x": float(x), "math": math, "__builtins__": {}})
     ```
   - Regular formula: `math.ceil(x * 2.5) - 0.01`
   - Under $5 formula: `x * 3`
   - Implement price calculation for all JDS pricing tiers

2. **SKU Comparison Logic**
   - Implement function to find unmatched products
   - Handle SKU cleaning for comparison
   - Create database views for efficient querying

3. **Data Synchronization**
   - Implement scheduled sync jobs
   - Handle incremental updates
   - Add data validation and error recovery

**Deliverables**:
- Working SKU comparison system
- Accurate pricing calculations
- Data sync functionality

### Phase 3: Web Interface (Week 3)

**Goal**: Create user-friendly interface for product management

**Tasks**:
1. **Main Dashboard** (`templates/index.html`)
   - Display sync status and statistics
   - Show count of unmatched products
   - Quick action buttons

2. **Product List Interface** (`templates/product_list.html`)
   - Display unmatched JDS products in a clean list
   - Show product details: name, description, images, pricing
   - Display calculated Shopify prices
   - Implement bulk selection with checkboxes
   - Add search and filter functionality

3. **Frontend JavaScript** (`static/js/main.js`)
   - Handle bulk selection
   - Implement AJAX for product addition
   - Show progress indicators
   - Handle success/error feedback

4. **Styling** (`static/css/style.css`)
   - Clean, modern interface
- Complete web interface
   - Loading states and animations (but not at the cost of time or performance, so keep it minimal)

**Deliverables**:
- Complete web interface
- Working bulk selection
- Responsive design

### Phase 4: Product Addition Integration (Week 4)

**Goal**: Implement one-click product addition to Shopify

**Tasks**:
1. **Shopify Product Creation**
   - Implement function to create products with variants
   - Handle product images, descriptions, and metadata
   - Set calculated prices on variants
   - Implement proper error handling and retry logic

2. **Bulk Operations**
   - Implement batch product addition
   - Add progress tracking
   - Handle partial failures gracefully

3. **Validation and Feedback**
   - Validate product data before creation
   - Show detailed success/failure messages
   - Implement rollback for failed operations

**Deliverables**:
- Working product addition to Shopify
- Robust error handling
- User feedback system

### Phase 5: Optimization and Monitoring (Week 5)

**Goal**: Polish the application and add monitoring

**Tasks**:
1. **Performance Optimization**
   - Implement caching for frequently accessed data
   - Optimize database queries
   - Add pagination for large product lists

2. **Monitoring and Logging**
   - Enhanced logging throughout the application
   - Error tracking and reporting
   - Performance metrics

3. **Testing and Documentation**
   - Unit tests for core functions
   - Integration tests for API calls
   - Update documentation

**Deliverables**:
- Optimized, production-ready application
- Comprehensive testing
- Complete documentation

## Key Implementation Details

### SKU Handling Policy

The application follows the same SKU cleaning policy as the existing `edit_price` system:

```python
def clean_sku_for_external_api(sku):
    """Clean SKU by removing hyphen and any letters preceding it"""
    if '-' in sku:
        parts = sku.split('-')
        return parts[-1]
    return sku
```

**Examples**:
- "ABC-LPB004" → "LPB004"
- "LTM814" → "LTM814" (no change)
- "TEST-123-ABC" → "ABC"

### Pricing Formula Integration

The pricing system uses the exact same formulas as the existing system:

**Regular Formula** (for prices ≥ $5):
```python
math.ceil(x * 2.5) - 0.01
```

**Under $5 Formula** (for prices < $5):
```python
x * 3
```

Where `x` is the JDS `lessThanCasePrice`.

### JDS API Integration

**Endpoint**: `https://api.jdsapp.com/get-product-details-by-skus`

**Request Format**:
```json
{
    "token": "YOUR_API_TOKEN",
    "skus": ["LPB004", "LWB101", "LTM814"]
}
```

**Response Format**: Array of product objects with pricing tiers, images, and inventory data.

### Shopify API Integration

Uses GraphQL API for efficient data retrieval:

**Fetch All SKUs**:
```graphql
query getProducts($cursor: String) {
  products(first: 250, after: $cursor) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        variants(first: 100) {
          edges {
            node {
              sku
              id
              price
            }
          }
        }
      }
    }
  }
}
```

## Environment Variables

Create a `.env` file with the following variables:

```env
# Shopify Configuration
SHOPIFY_STORE=your-store.myshopify.com
SHOPIFY_API_VERSION=2023-10
SHOPIFY_ACCESS_TOKEN=your_access_token

# JDS API Configuration
EXTERNAL_API_URL=https://api.jdsapp.com/get-product-details-by-skus
EXTERNAL_API_TOKEN=your_jds_token

# Application Configuration
FLASK_ENV=development
DATABASE_URL=sqlite:///product_adder.db
SECRET_KEY=your_secret_key
```

## Dependencies

```txt
Flask==2.3.3
requests==2.31.0
python-dotenv==1.0.0
SQLAlchemy==2.0.21
Flask-SQLAlchemy==3.0.5
```

## Getting Started

1. **Clone and Setup**:
   ```bash
   cd /home/norllr/dev/morganicsPricing/product_adder
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API credentials
   ```

3. **Initialize Database**:
   ```bash
   python -c "from database import init_db; init_db()"
   ```

4. **Run Application**:
   ```bash
   python app.py
   ```

5. **Access Interface**:
   Open `http://localhost:5000` in your browser

## Testing

Run the test suite:
```bash
python -m pytest tests/
```

## Deployment

The application can be deployed using the same Docker setup as the existing `edit_price` system:

1. **Docker Build**:
   ```bash
   docker build -t product-adder .
   ```

2. **Docker Run**:
   ```bash
   docker run -p 5000:5000 --env-file .env product-adder
   ```

## Troubleshooting

### Common Issues

1. **SKU Mismatch**: Ensure SKU cleaning logic matches the existing system
2. **API Rate Limits**: Implement proper rate limiting and retry logic
3. **Pricing Calculation**: Verify formulas match the existing system exactly
4. **Database Issues**: Check SQLite file permissions and schema

### Debug Mode

Enable debug logging by setting:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

- Email notifications for new products
- Advanced filtering and search
- Product category management
- Bulk price updates
- Inventory synchronization
- Automated scheduling

## Support

For questions or issues:
1. Check the existing `edit_price` system for reference patterns
2. Review the JDS API documentation
3. Consult Shopify API documentation
4. Check application logs for detailed error messages

---

**Note**: This application is designed to work alongside the existing `edit_price` system and follows the same patterns and policies. Always test changes in a development environment before deploying to production.
