This is a task for Ascendion interview process. 

Task: 
Please create a simple application with a Python back end. The back end should offer a RESTful API endpoint which in turn communicates with a database of your choice to persists some data received in the RESTful call. We would like to see automated tests, input sanitisation. Consider error handling and observability. Create a local Git repository for this project. We do not expect perfection but would like to see confidence and good practices.



### Setup

1. Clone the repository:

2. Set up a virtual environment:
```bash
python -m venv venv
source venv/bin/activate 
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Start the PostgreSQL database (using Docker):
```bash
docker-compose up -d db
```

5. Run database migrations:
```bash
alembic upgrade head
```

6. Start the application:
```bash
uvicorn app.main:app --reload
```

Or alternatively use Docker compose 
```bash
docker-compose up -d
```

7. Access the API documentation:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## API Endpoints

- `GET /api/tasks`: List all tasks



## Testing

Run the tests with:
```bash
pytest
```

## Adding db migrations
```bash
alembic revision --autogenerate -m "My new migration"
```


1 - alembic init alembic
2 - alembic revision --autogenerate -m "create init tables"
3 - alembic upgrade head