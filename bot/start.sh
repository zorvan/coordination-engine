docker stop coord_bot_db
sleep 2
docker system prune --force --volumes
docker volume prune --force
docker run -d --name coord_bot_db -e POSTGRES_USER=coord_user -e POSTGRES_PASSWORD=coord_pass -e POSTGRES_DB=coord_db -p 5432:5432 --health-cmd="pg_isready -U coord_user -d coord_db"  postgres:15
sleep 5  # Wait for the database to initialize
PGPASSWORD=coord_pass psql -h localhost -U coord_user -d coord_db -f db/schema.sql
#export TELEGRAM_TOKEN="xxxxxxxxxx:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
python3 main.py
