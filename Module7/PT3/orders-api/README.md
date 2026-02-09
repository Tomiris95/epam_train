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
- `page` (int, default: 1) - Page number
- `limit` (int, default: 10) - Items per page
- `status` (string, optional) - Filter by status
- `minAmount` (number, optional) - Minimum amount
- `maxAmount` (number, optional) - Maximum amount
- `startDate` (string, optional) - Start date (ISO 8601)
- `endDate` (string, optional) - End date (ISO 8601)

**Example:**
```
GET /orders?page=1&limit=10&status=paid&minAmount=10&maxAmount=100
```

**Response (200):**
```json
{
  "data": [
    { "id": 1, "customer": "Alice", "amount": 123.45, "status": "paid", "created_at": "2026-02-09T12:00:00.000Z" }
  ],
  "page": 1,
  "limit": 10,
  "total": 50
}
```

## Tests

Run test suite with coverage:

```bash
npm test
```

Expected: 11 tests, 72%+ code coverage

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
│   └── orders.test.js  # 11 test cases
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


