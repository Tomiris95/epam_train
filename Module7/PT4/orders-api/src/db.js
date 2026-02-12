const sqlite3 = require('sqlite3').verbose();
const fs = require('fs');
const path = require('path');

function initDB(dbFile) {
  const dir = path.dirname(dbFile);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  const db = new sqlite3.Database(dbFile);
  db.serialize(() => {
    db.run(`
      CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer TEXT NOT NULL,
        amount REAL NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL
      )
    `);

    // Create indexes for performance with 10k+ records
    db.run(`CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)`);
    db.run(`CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)`);
    db.run(`CREATE INDEX IF NOT EXISTS idx_orders_amount ON orders(amount)`);
    db.run(`CREATE INDEX IF NOT EXISTS idx_orders_status_created_at ON orders(status, created_at)`);
  });
  return db;
}

module.exports = { initDB };
