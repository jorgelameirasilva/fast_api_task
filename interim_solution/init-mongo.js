// MongoDB initialization script for testing
print("Initializing MongoDB for cosmos service testing...");

// Switch to testdb
db = db.getSiblingDB("testdb");

// Create sessions collection with indexes
db.createCollection("sessions");

// Create indexes for better query performance
db.sessions.createIndex({ user_id: 1 });
db.sessions.createIndex({ created_at: 1 });
db.sessions.createIndex({ updated_at: 1 });
db.sessions.createIndex({ title: "text" });

print("MongoDB initialization completed successfully!");
