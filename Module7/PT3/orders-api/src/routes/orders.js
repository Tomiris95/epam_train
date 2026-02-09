const express = require('express');

function ordersRouter(models){
  const router = express.Router();

  router.post('/', async (req, res) => {
    try{
      const { customer, amount, status } = req.body;
      if(!customer || typeof amount !== 'number' || !status) return res.status(400).json({ error: 'Invalid payload' });
      const created = await models.create({ customer, amount, status });
      res.status(201).json(created);
    }catch(err){
      console.error(err);
      res.status(500).json({ error: 'server error' });
    }
  });

  router.get('/', async (req, res) => {
    try{
      const { page=1, limit=10, status, minAmount, maxAmount, startDate, endDate } = req.query;
      const q = {
        page: parseInt(page,10) || 1,
        limit: parseInt(limit,10) || 10,
        status,
        minAmount: minAmount ? parseFloat(minAmount) : undefined,
        maxAmount: maxAmount ? parseFloat(maxAmount) : undefined,
        startDate,
        endDate
      };
      const result = await models.query(q);
      res.json(result);
    }catch(err){
      console.error(err);
      res.status(500).json({ error: 'server error' });
    }
  });

  return router;
}

module.exports = { ordersRouter };
