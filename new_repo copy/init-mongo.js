// MongoDB initialization script for testing
print("Starting MongoDB initialization...");

// Switch to the test database
db = db.getSiblingDB("testdb");

// Create the sessions collection with indexes
db.createCollection("sessions");

// Create indexes for better performance
db.sessions.createIndex({ user_id: 1 });
db.sessions.createIndex({ user_id: 1, is_active: 1 });
db.sessions.createIndex({ updated_at: 1 });

print("MongoDB initialization completed successfully.");
