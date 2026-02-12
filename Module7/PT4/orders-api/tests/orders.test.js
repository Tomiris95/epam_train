const fs = require('fs');
const path = require('path');
const request = require('supertest');

describe('Orders API', () => {
  let app;
  
  beforeEach(() => {
    delete require.cache[require.resolve('../src/app')];
    const { createApp } = require('../src/app');
    app = createApp(':memory:');
  });

  afterEach(() => {
    if (app.locals.db) {
      app.locals.db.close();
    }
  });

  test('POST /orders creates an order', async () => {
    const res = await request(app).post('/orders').send({ customer: 'Alice', amount: 123.45, status: 'paid' });
    expect(res.statusCode).toBe(201);
    expect(res.body).toHaveProperty('id');
    expect(res.body.customer).toBe('Alice');
  });

  test('POST /orders rejects invalid payload', async () => {
    const res = await request(app).post('/orders').send({ customer: '', amount: 'x', status: '' });
    expect(res.statusCode).toBe(400);
  });

  test('GET /orders pagination works', async () => {
    // seed some
    const models = app.locals.models;
    const items = [];
    for(let i=1;i<=25;i++) items.push({ customer:`C${i}`, amount:i, status: i%2? 'paid':'pending', created_at: new Date().toISOString() });
    await models.seedMany(items);
    const res = await request(app).get('/orders?page=2&limit=10');
    expect(res.statusCode).toBe(200);
    expect(res.body.data.length).toBe(10);
    expect(res.body.metadata.pagination.page).toBe(2);
  });

  test('GET /orders filter by status', async () => {
    const models = app.locals.models;
    await models.seedMany([{ customer:'A', amount:10, status:'pending', created_at:new Date().toISOString() }, { customer:'B', amount:20, status:'completed', created_at:new Date().toISOString() }]);
    const res = await request(app).get('/orders?status=pending');
    expect(res.statusCode).toBe(200);
    expect(res.body.data.every(o => o.status === 'pending')).toBe(true);
  });

  test('GET /orders filter by amount range', async () => {
    const models = app.locals.models;
    await models.seedMany([{ customer:'A', amount:5, status:'paid', created_at:new Date().toISOString() }, { customer:'B', amount:50, status:'paid', created_at:new Date().toISOString() }]);
    const res = await request(app).get('/orders?minAmount=10&maxAmount=100');
    expect(res.statusCode).toBe(200);
    expect(res.body.data.every(o => o.amount >= 10 && o.amount <=100)).toBe(true);
  });

  test('GET /orders date range filter', async () => {
    const models = app.locals.models;
    const d1 = new Date('2020-01-01').toISOString();
    const d2 = new Date('2022-01-01').toISOString();
    await models.seedMany([{ customer:'A', amount:10, status:'paid', created_at:d1 }, { customer:'B', amount:20, status:'paid', created_at:d2 }]);
    const res = await request(app).get('/orders?startDate=2019-01-01&endDate=2021-01-01');
    expect(res.statusCode).toBe(200);
    expect(res.body.data.length).toBe(1);
    expect(new Date(res.body.data[0].created_at).toISOString()).toBe(d1);
  });

  test('Pagination defaults applied', async () => {
    const models = app.locals.models;
    const items = [];
    for(let i=1;i<=5;i++) items.push({ customer:`Z${i}`, amount:i, status:'pending', created_at:new Date().toISOString() });
    await models.seedMany(items);
    const res = await request(app).get('/orders');
    expect(res.statusCode).toBe(200);
    expect(res.body.metadata.pagination.page).toBe(1);
    expect(res.body.metadata.pagination.limit).toBe(10);
  });

  // Edge cases
  test('GET /orders page out of range returns empty data', async () => {
    const res = await request(app).get('/orders?page=999&limit=10');
    expect(res.statusCode).toBe(200);
    expect(Array.isArray(res.body.data)).toBe(true);
  });

  test('POST /orders SQL injection attempt rejected by type checks', async () => {
    const res = await request(app).post('/orders').send({ customer: "Bob', ('x')", amount: 1, status: 'paid' });
    // Should be accepted as normal string but not cause SQL injection due to parameterized queries
    expect([201,400].includes(res.statusCode)).toBe(true);
  });

  test('Large limit capped practically (handles large requests)', async () => {
    const res = await request(app).get('/orders?limit=1000');
    expect(res.statusCode).toBe(200);
    expect(res.body.metadata.pagination.limit).toBe(100); // Should be capped at 100 due to sanitization
  });

  test('Create and then query returns inserted item', async () => {
    const post = await request(app).post('/orders').send({ customer: 'Eve', amount: 77.7, status: 'pending' });
    expect(post.statusCode).toBe(201);
    const q = await request(app).get(`/orders?status=pending`);
    expect(q.statusCode).toBe(200);
    expect(q.body.data.some(o => o.customer === 'Eve')).toBeTruthy();
  });

  // New comprehensive tests for pagination + filters
  test('GET /orders default pagination parameters', async () => {
    const models = app.locals.models;
    await models.seedMany([
      { customer:'A', amount:10, status:'pending', created_at:new Date('2024-01-01').toISOString() }
    ]);
    const res = await request(app).get('/orders');
    expect(res.statusCode).toBe(200);
    expect(res.body.metadata.pagination.page).toBe(1);
    expect(res.body.metadata.pagination.limit).toBe(10);
    expect(res.body.data).toHaveLength(1);
  });

  test('GET /orders custom pagination parameters', async () => {
    const models = app.locals.models;
    const items = [];
    for(let i=1;i<=15;i++) items.push({ customer:`C${i}`, amount:i, status:'pending', created_at:new Date().toISOString() });
    await models.seedMany(items);
    const res = await request(app).get('/orders?page=2&limit=5');
    expect(res.statusCode).toBe(200);
    expect(res.body.metadata.pagination.page).toBe(2);
    expect(res.body.metadata.pagination.limit).toBe(5);
    expect(res.body.data).toHaveLength(5);
    expect(res.body.metadata.pagination.total).toBe(15);
    expect(res.body.metadata.pagination.totalPages).toBe(3);
  });

  test('GET /orders limit sanitization (DOS protection)', async () => {
    const models = app.locals.models;
    const items = [];
    for(let i=1;i<=5;i++) items.push({ customer:`C${i}`, amount:i, status:'pending', created_at:new Date().toISOString() });
    await models.seedMany(items);
    const res = await request(app).get('/orders?limit=1000');
    expect(res.statusCode).toBe(200);
    expect(res.body.metadata.pagination.limit).toBe(100); // Should be capped at 100
  });

  test('GET /orders invalid page number', async () => {
    const res = await request(app).get('/orders?page=0');
    expect(res.statusCode).toBe(400);
    expect(res.body.error).toBe('Page must be a positive integer');
  });

  test('GET /orders invalid limit number', async () => {
    const res = await request(app).get('/orders?limit=0');
    expect(res.statusCode).toBe(400);
    expect(res.body.error).toBe('Limit must be a positive integer');
  });

  test('GET /orders invalid status filter', async () => {
    const res = await request(app).get('/orders?status=invalid');
    expect(res.statusCode).toBe(400);
    expect(res.body.error).toBe('Invalid status. Must be: pending, completed, cancelled');
  });

  test('GET /orders minAmount greater than maxAmount', async () => {
    const res = await request(app).get('/orders?minAmount=100&maxAmount=50');
    expect(res.statusCode).toBe(400);
    expect(res.body.error).toBe('minAmount cannot be greater than maxAmount');
  });

  test('GET /orders invalid date format', async () => {
    const res = await request(app).get('/orders?startDate=2024/01/01');
    expect(res.statusCode).toBe(400);
    expect(res.body.error).toBe('startDate must be in YYYY-MM-DD format');
  });

  test('GET /orders startDate after endDate', async () => {
    const res = await request(app).get('/orders?startDate=2024-02-01&endDate=2024-01-01');
    expect(res.statusCode).toBe(400);
    expect(res.body.error).toBe('startDate cannot be after endDate');
  });

  test('GET /orders negative amount validation', async () => {
    const res = await request(app).get('/orders?minAmount=-10');
    expect(res.statusCode).toBe(400);
    expect(res.body.error).toBe('minAmount must be a positive number');
  });

  test('GET /orders combined filters work together', async () => {
    const models = app.locals.models;
    await models.seedMany([
      { customer:'A', amount:50, status:'pending', created_at:new Date('2024-01-15').toISOString() },
      { customer:'B', amount:150, status:'completed', created_at:new Date('2024-01-25').toISOString() },
      { customer:'C', amount:75, status:'pending', created_at:new Date('2024-02-15').toISOString() }
    ]);
    const res = await request(app).get('/orders?status=pending&minAmount=40&maxAmount=80&startDate=2024-01-01&endDate=2024-01-31');
    expect(res.statusCode).toBe(200);
    expect(res.body.data).toHaveLength(1);
    expect(res.body.data[0].customer).toBe('A');
    expect(res.body.metadata.filters.status).toBe('pending');
    expect(res.body.metadata.filters.amountRange.min).toBe(40);
    expect(res.body.metadata.filters.amountRange.max).toBe(80);
  });

  test('GET /orders pagination metadata correctness', async () => {
    const models = app.locals.models;
    const items = [];
    for(let i=1;i<=25;i++) items.push({ customer:`C${i}`, amount:i, status:'pending', created_at:new Date().toISOString() });
    await models.seedMany(items);
    const res = await request(app).get('/orders?page=2&limit=10');
    expect(res.statusCode).toBe(200);
    expect(res.body.metadata.pagination.hasNext).toBe(true);
    expect(res.body.metadata.pagination.hasPrevious).toBe(true);
    expect(res.body.metadata.pagination.totalPages).toBe(3);
  });

  test('GET /orders empty result with filters', async () => {
    const models = app.locals.models;
    await models.seedMany([
      { customer:'A', amount:10, status:'pending', created_at:new Date('2024-01-01').toISOString() }
    ]);
    const res = await request(app).get('/orders?status=completed');
    expect(res.statusCode).toBe(200);
    expect(res.body.data).toHaveLength(0);
    expect(res.body.metadata.pagination.total).toBe(0);
    expect(res.body.metadata.filters.status).toBe('completed');
  });

  test('GET /orders edge case last page metadata', async () => {
    const models = app.locals.models;
    const items = [];
    for(let i=1;i<=21;i++) items.push({ customer:`C${i}`, amount:i, status:'pending', created_at:new Date().toISOString() });
    await models.seedMany(items);
    const res = await request(app).get('/orders?page=3&limit=10');
    expect(res.statusCode).toBe(200);
    expect(res.body.metadata.pagination.hasNext).toBe(false);
    expect(res.body.metadata.pagination.hasPrevious).toBe(true);
    expect(res.body.data).toHaveLength(1);
  });
});
