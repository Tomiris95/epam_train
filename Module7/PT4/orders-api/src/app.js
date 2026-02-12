const express = require('express');
const bodyParser = require('express');
const { initDB } = require('./db');
const { createOrderModel } = require('./models/order');
const { ordersRouter } = require('./routes/orders');

function createApp(dbFile) {
  const db = initDB(dbFile);
  const models = createOrderModel(db);
  const app = express();
  app.use(express.json());
  app.use('/orders', ordersRouter(models));
  app.get('/', (req, res) => res.json({ ok: true }));
  // attach models for seed/tests
  app.locals.models = models;
  app.locals.db = db;
  return app;
}

module.exports = { createApp };
