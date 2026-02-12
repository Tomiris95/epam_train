const { promisify } = require('util');

function createOrderModel(db) {
  const run = (sql, params = []) => new Promise((res, rej) => db.run(sql, params, function(err) { if(err) rej(err); else res(this); }));
  const all = promisify(db.all).bind(db);

  async function create({ customer, amount, status }) {
    const created_at = new Date().toISOString();
    const result = await run(
      `INSERT INTO orders (customer, amount, status, created_at) VALUES (?, ?, ?, ?)`,
      [customer, amount, status, created_at]
    );
    return { id: result.lastID, customer, amount, status, created_at };
  }

  async function query({ page = 1, limit = 10, status, minAmount, maxAmount, startDate, endDate }) {
    const offset = (page - 1) * limit;
    const filters = [];
    const params = [];
    if (status) { filters.push('status = ?'); params.push(status); }
    if (minAmount !== undefined) { filters.push('amount >= ?'); params.push(minAmount); }
    if (maxAmount !== undefined) { filters.push('amount <= ?'); params.push(maxAmount); }
    if (startDate) { filters.push('created_at >= ?'); params.push(new Date(startDate).toISOString()); }
    if (endDate) { filters.push('created_at <= ?'); params.push(new Date(endDate).toISOString()); }

    const where = filters.length ? ('WHERE ' + filters.join(' AND ')) : '';
    const rows = await all(
      `SELECT * FROM orders ${where} ORDER BY created_at DESC LIMIT ? OFFSET ?`,
      params.concat([limit, offset])
    );
    const countRow = await all(
      `SELECT COUNT(*) as count FROM orders ${where}`,
      params
    );
    const total = countRow[0] ? countRow[0].count : 0;
    const totalPages = Math.ceil(total / limit);
    
    return {
      data: rows,
      metadata: {
        pagination: {
          page,
          limit,
          total,
          totalPages,
          hasNext: page < totalPages,
          hasPrevious: page > 1
        },
        filters: {
          status: status || null,
          amountRange: {
            min: minAmount || null,
            max: maxAmount || null
          },
          dateRange: {
            start: startDate || null,
            end: endDate || null
          }
        }
      }
    };
  }

  async function seedMany(items) {
    for (const it of items) {
      await run(`INSERT INTO orders (customer, amount, status, created_at) VALUES (?, ?, ?, ?)`, [it.customer, it.amount, it.status, it.created_at]);
    }
  }

  return { create, query, seedMany };
}

module.exports = { createOrderModel };
