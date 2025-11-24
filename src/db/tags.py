"""TODO"""
import json


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
