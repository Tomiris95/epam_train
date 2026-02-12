# Orders API

Simple Orders Management REST API with pagination and filtering, built with Express.js and SQLite.

## Installation

```bash
npm install
```

## Seeding (optional)

Populate database with 50 sample orders:

```bash
npm run seed
```

## Running the Server

```bash
npm start
```

Server will start on `http://localhost:3000`

## API Endpoints

### POST /orders
Create a new order.

**Request Body:**
```json
{
  "customer": "string (required)",
  "amount": "number (required)",
  "status": "string (required, e.g., 'pending', 'paid', 'cancelled')"
}
```

**Response (201):**
```json
{
  "id": 1,
  "customer": "Alice",
  "amount": 123.45,
  "status": "paid",
  "created_at": "2026-02-09T12:00:00.000Z"
}
```

### GET /orders
Fetch orders with pagination, filtering, and date range support.

**Query Parameters:**
- `page` (int, default: 1, min: 1) - Page number for pagination
- `limit` (int, default: 10, min: 1, max: 100) - Items per page (DOS protection enforced)
- `status` (string, optional) - Filter by order status. Valid values: `pending`, `completed`, `cancelled`
- `minAmount` (number, optional, min: 0) - Minimum amount filter (inclusive)
- `maxAmount` (number, optional, min: 0) - Maximum amount filter (inclusive)
- `startDate` (string, optional, format: YYYY-MM-DD) - Filter orders created on or after this date
- `endDate` (string, optional, format: YYYY-MM-DD) - Filter orders created on or before this date

**Validation Rules:**
- `page` must be a positive integer
- `limit` must be between 1 and 100 (automatically sanitized if outside range)
- `status` must be one of: `pending`, `completed`, `cancelled`
- `minAmount` and `maxAmount` must be positive numbers, with `minAmount ≤ maxAmount`
- Dates must be in `YYYY-MM-DD` format, with `startDate ≤ endDate`
- Invalid parameters return 400 Bad Request with descriptive error messages

**Example Request:**
```
GET /orders?page=2&limit=5&status=pending&minAmount=50&maxAmount=200&startDate=2024-01-01&endDate=2024-12-31
```

**Response (200):**
```json
{
  "data": [
    {
      "id": 11,
      "customer": "John Doe",
      "amount": 150.00,
      "status": "pending",
      "created_at": "2024-06-15T10:30:00.000Z"
    },
    {
      "id": 12,
      "customer": "Jane Smith", 
      "amount": 75.50,
      "status": "pending",
      "created_at": "2024-06-14T14:20:00.000Z"
    }
  ],
  "metadata": {
    "pagination": {
      "page": 2,
      "limit": 5,
      "total": 47,
      "totalPages": 10,
      "hasNext": true,
      "hasPrevious": true
    },
    "filters": {
      "status": "pending",
      "amountRange": {
        "min": 50,
        "max": 200
      },
      "dateRange": {
        "start": "2024-01-01",
        "end": "2024-12-31"
      }
    }
  }
}
```

**Error Response (400):**
```json
{
  "error": "Page must be a positive integer"
}
```

## Tests

Run test suite with coverage:

```bash
npm test
```

Expected: 25 tests, 76%+ code coverage

## Features

- ✅ **Pagination**: Default page=1, limit=10, max limit=100 with DOS protection
- ✅ **Filtering**: Status, amount range (min/max), date range with strict validation
- ✅ **Metadata**: Standardized response with pagination info and applied filters
- ✅ **Database**: Optimized with indexes for 10k+ records
- ✅ **Validation**: Comprehensive input validation with descriptive error messages
- ✅ **Security**: DOS protection and SQL injection prevention

## Project Structure

```
orders-api/
├── src/
│   ├── app.js          # Express app factory
│   ├── server.js       # Server entry point
│   ├── db.js           # Database initialization
│   ├── seed.js         # Data seeding script
│   ├── models/
│   │   └── order.js    # Order model (CRUD, query)
│   └── routes/
│       └── orders.js   # Order routes
├── tests/
│   └── orders.test.js  # 25 comprehensive test cases
├── package.json
└── jest.config.js
```

## Database

SQLite 3 in-memory or file-based database with `orders` table:
- `id` (INTEGER PRIMARY KEY)
- `customer` (TEXT NOT NULL)
- `amount` (REAL NOT NULL)
- `status` (TEXT NOT NULL)
- `created_at` (TEXT NOT NULL)


