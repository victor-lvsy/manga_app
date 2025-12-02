"""TODO"""
import json
import sys
from src.db import ComicRepository, DatabaseAccessLayer


def prepare_tags_for_migration():
    """TODO"""
    database_access_layer = DatabaseAccessLayer()
    with database_access_layer.managed_session() as session:
        comic_repository = ComicRepository(session)
        comics_tags = []
        for comic in comic_repository.get_comics():
            comics_tags.append({"comic_id": comic.id, "tags": comic.tags})
        with open("src/db/tags_migration.json", "w", encoding="utf-8") as file:
            json.dump(comics_tags, file, indent=4, ensure_ascii=False)


def migrate_tags():
    """TODO"""
    database_access_layer = DatabaseAccessLayer()
    with database_access_layer.managed_session() as session:
        comic_repository = ComicRepository(session)
        with open("src/db/tags_migration.json", "r", encoding="utf-8") as file:
            comics_tags = json.load(file)
        for comic_tag in comics_tags:
            if comic_repository.get_tag_by_name(comic_tag["name"]) is None:
                comic_repository.create_tag(comic_tag["name"])
                comic_repository.create_comic_tag_link(comic_tag["comic_id"], comic_repository.get_tag_by_name(comic_tag["name"]).id)


def load_tags() -> list[str]:
    """TODO"""
    with open("src/db/tags.json", "r", encoding="utf-8") as file:
        return json.load(file)


def save_tags(tags: list[str]):
    """TODO"""
    with open("src/db/tags.json", "w", encoding="utf-8") as file:
        json.dump(tags, file, indent=4, ensure_ascii=False)


def add_tag(tag: str):
    """TODO"""
    tags = load_tags()
    tags.append(tag)
    save_tags(tags)


def remove_tag(tag: str):
    """TODO"""
    tags = load_tags()
    tags.remove(tag)
    save_tags(tags)


def get_tags() -> list[str]:
    """TODO"""
    return load_tags()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "prepare":
        prepare_tags_for_migration()
    elif len(sys.argv) > 1 and sys.argv[1] == "migrate":
        migrate_tags()
    else:
        print("Usage: python -m src.db.tags [prepare|migrate]")
