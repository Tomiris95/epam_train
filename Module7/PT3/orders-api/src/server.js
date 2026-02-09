const { createApp } = require('./app');
const path = require('path');
const dbFile = process.env.DATABASE_FILE || path.join(__dirname, '..', 'data', 'orders.db');
const app = createApp(dbFile);
const port = process.env.PORT || 3000;
app.listen(port, () => console.log(`Orders API running on http://localhost:${port}`));
