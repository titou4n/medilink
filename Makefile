.PHONY: help build up down restart logs clean secrets deploy

help:
	@echo "MediLink - Commandes disponibles:"
	@echo "  make build      - Construire les images Docker"
	@echo "  make up         - Démarrer les services"
	@echo "  make down       - Arrêter les services"
	@echo "  make restart    - Redémarrer les services"
	@echo "  make logs       - Afficher les logs"
	@echo "  make clean      - Nettoyer les volumes et images"

build:
	docker-compose build --no-cache

up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

clean:
	docker-compose down -v
	docker system prune -f