.PHONY: up down build migrate makemigrations seed test backup shell logs createsuperuser

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f web

shell:
	docker compose exec web python manage.py shell

migrate:
	docker compose exec web python manage.py migrate

makemigrations:
	docker compose exec web python manage.py makemigrations

seed:
	docker compose exec web python manage.py seed

createsuperuser:
	docker compose exec web python manage.py createsuperuser

test:
	docker compose exec web pytest

backup:
	docker compose exec web python manage.py backup
