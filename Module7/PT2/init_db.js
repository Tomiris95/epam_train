const sqlite3 = require('sqlite3').verbose();
const fs = require('fs');
const path = require('path');

// Connect to the SQLite database
const db = new sqlite3.Database('validation_rules.db', (err) => {
    if (err) {
        console.error('Error opening database ' + err.message);
    } else {
        console.log('Connected to the SQLite database.');
    }
});

// Function to initialize the database with validation rules
function initDatabase() {
    const sqlPath = path.join(__dirname, 'validation_rules.sql');
    return new Promise((resolve, reject) => {
        fs.readFile(sqlPath, 'utf8', (err, sql) => {
            if (err) {
                console.error('Error reading SQL file: ' + err.message);
                return reject(err);
            }
            db.exec(sql, (execErr) => {
                if (execErr) {
                    console.error('Error executing SQL: ' + execErr.message);
                    return reject(execErr);
                }
                console.log('Database initialized with validation rules from validation_rules.sql.');
                resolve();
            });
        });
    });
}

// Function to change default rules in the database
function changeDefaultRules() {
    const updateSql = `UPDATE validation_rules SET regex_pattern = '^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$' WHERE rule_name = 'email_format';`;
    return new Promise((resolve, reject) => {
        db.run(updateSql, function(err) {
            if (err) {
                console.error('Error updating default rules: ' + err.message);
                return reject(err);
            } else {
                console.log('Default rules updated successfully.');
                return resolve();
            }
        });
    });
}

// Initialize the database and change default rules
initDatabase()
    .then(() => changeDefaultRules())
    .catch(err => {
        console.error('Error initializing DB or changing defaults:', err.message);
    })
    .finally(() => {
        db.close((err) => {
            if (err) {
                console.error('Error closing database:', err.message);
            } else {
                console.log('Database connection closed.');
            }
        });
    });
