const path = require('path');
const { createApp } = require('./app');

async function seed(){
  const dbFile = process.env.DATABASE_FILE || path.join(__dirname, '..', 'data', 'orders.db');
  const app = createApp(dbFile);
  const models = app.locals.models;
  const statuses = ['pending','paid','cancelled'];
  const sample = [];
  for(let i=1;i<=50;i++){
    sample.push({
      customer: `Customer ${i}`,
      amount: Math.round((Math.random()*500 + 5)*100)/100,
      status: statuses[i % statuses.length],
      created_at: new Date(Date.now() - i*86400000).toISOString()
    });
  }
  await models.seedMany(sample);
  console.log('Seeded 50 orders');
  process.exit(0);
}

seed().catch(e=>{ console.error(e); process.exit(1); });
