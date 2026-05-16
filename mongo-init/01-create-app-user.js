const databaseName = process.env.MONGO_APP_DATABASE;
const username = process.env.MONGO_APP_USERNAME;
const password = process.env.MONGO_APP_PASSWORD;

if (!databaseName || !username || !password) {
  throw new Error("Missing Mongo app user environment variables.");
}

db = db.getSiblingDB(databaseName);

db.createUser({
  user: username,
  pwd: password,
  roles: [{ role: "readWrite", db: databaseName }],
});
