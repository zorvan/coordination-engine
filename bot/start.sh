docker stop coord_bot_db
sleep 2
docker system prune --force --volumes
docker volume prune --force

#export TELEGRAM_TOKEN="xxxxxxxxxx:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
if [ -z "$TELEGRAM_TOKEN" ]; then
  echo "Error: TELEGRAM_TOKEN environment variable is not set."
  exit 1
fi

docker run -d --name coord_bot_db -e POSTGRES_USER=coord_user -e POSTGRES_PASSWORD=coord_pass -e POSTGRES_DB=coord_db -p 5432:5432 --health-cmd="pg_isready -U coord_user -d coord_db"  postgres:15
sleep 5  # Wait for the database to initialize
PGPASSWORD=coord_pass psql -h localhost -U coord_user -d coord_db -f db/schema.sql
python3 main.py 
echo "******* Bot started. Logs are being written to bot.log *******"
