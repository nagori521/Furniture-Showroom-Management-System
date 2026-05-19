"""Application configuration for the inventory web app."""

from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "inventory.db"


class Config:
    """Runtime configuration values."""

    SECRET_KEY = "change-this-secret-key"
    DATABASE_PATH = DATABASE_PATH
    LOW_STOCK_THRESHOLD = 5
    SHOP_NAME = "Vishal Bharat Furniture Works"
    SHOP_PHONE = "9998601704"
    SHOP_ADDRESS = "22, Piplaj - Pirana Rd, Calico Mills, Behrampura, Ahmedabad, Gujarat 380022"
