const express = require('express');

function ordersRouter(models) {
  const router = express.Router();

  router.post('/', async (req, res) => {
    try {
      const { customer, amount, status } = req.body;
      if (!customer || typeof amount !== 'number' || !status) return res.status(400).json({ error: 'Invalid payload' });
      const created = await models.create({ customer, amount, status });
      res.status(201).json(created);
    } catch (err) {
      console.error(err);
      res.status(500).json({ error: 'server error' });
    }
  });

  router.get('/', async (req, res) => {
    try {
      const { page = 1, limit = 10, status, minAmount, maxAmount, startDate, endDate } = req.query;
      
      // Pagination validation and sanitization
      const pageNum = parseInt(page, 10);
      const limitNum = parseInt(limit, 10);
      
      if (isNaN(pageNum) || pageNum < 1) {
        return res.status(400).json({ error: 'Page must be a positive integer' });
      }
      
      if (isNaN(limitNum) || limitNum < 1) {
        return res.status(400).json({ error: 'Limit must be a positive integer' });
      }
      
      // Sanitize limit to prevent DOS attacks (strict max of 100)
      const sanitizedLimit = Math.min(Math.max(1, limitNum), 100);
      
      // Status validation
      const validStatuses = ['pending', 'completed', 'cancelled'];
      if (status && !validStatuses.includes(status)) {
        return res.status(400).json({ error: 'Invalid status. Must be: pending, completed, cancelled' });
      }
      
      // Amount range validation
      const minAmountNum = minAmount !== undefined ? parseFloat(minAmount) : undefined;
      const maxAmountNum = maxAmount !== undefined ? parseFloat(maxAmount) : undefined;
      
      if (minAmount !== undefined && (isNaN(minAmountNum) || minAmountNum < 0)) {
        return res.status(400).json({ error: 'minAmount must be a positive number' });
      }
      
      if (maxAmount !== undefined && (isNaN(maxAmountNum) || maxAmountNum < 0)) {
        return res.status(400).json({ error: 'maxAmount must be a positive number' });
      }
      
      if (minAmountNum !== undefined && maxAmountNum !== undefined && minAmountNum > maxAmountNum) {
        return res.status(400).json({ error: 'minAmount cannot be greater than maxAmount' });
      }
      
      // Date validation
      const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
      if (startDate && !dateRegex.test(startDate)) {
        return res.status(400).json({ error: 'startDate must be in YYYY-MM-DD format' });
      }
      
      if (endDate && !dateRegex.test(endDate)) {
        return res.status(400).json({ error: 'endDate must be in YYYY-MM-DD format' });
      }
      
      if (startDate && endDate && new Date(startDate) > new Date(endDate)) {
        return res.status(400).json({ error: 'startDate cannot be after endDate' });
      }
      
      const q = {
        page: pageNum,
        limit: sanitizedLimit,
        status,
        minAmount: minAmountNum,
        maxAmount: maxAmountNum,
        startDate,
        endDate
      };
      const result = await models.query(q);
      res.json(result);
    } catch (err) {
      console.error(err);
      res.status(500).json({ error: 'server error' });
    }
  });

  return router;
}

module.exports = { ordersRouter };
