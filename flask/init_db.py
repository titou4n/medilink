from app import create_app
import extensions as ext
import logging

logger = logging.getLogger(__name__)

def main():
    app = create_app()

    with app.app_context():
        logger.info("Initializing database...")

        ext._db_manager.init_database()
        ext._roles_permissions_seeders.run()
        ext._accounts_seeder.run()

        logger.info("Database initialization complete.")

if __name__ == "__main__":
    main()