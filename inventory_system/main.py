"""Application entry point for the furniture inventory system."""

from cli.interface import InventoryCLI
from database.db import initialize_database
from utils.helpers import seed_sample_data


def main() -> None:
    """Initialize the database, seed sample data, and start the CLI."""
    initialize_database()
    seed_sample_data()
    InventoryCLI().run()


if __name__ == "__main__":
    main()
