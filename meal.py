import argparse
import sys
import json
import os
import shutil
import random
from datetime import datetime, timedelta

BACKUP_SUFFIX = "backup_"
SUGGESTION_SUFFIX = "suggestion_"
ENCODING = "utf-8"

def get_meal_input(args_meal):
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    elif args_meal:
        return " ".join(args_meal)
    else:
        return None

def get_data_file(live, cli_path=None):
    if live:
        if cli_path is None:
            return "./live/meals.json"
        else:
            return os.path.join(os.path.dirname(cli_path), "live", os.path.basename(cli_path) + ".json")
    else:
        if cli_path is None:
            return "./test/meals.json"
        else:
            return os.path.join(os.path.dirname(cli_path), "test", os.path.basename(cli_path) + ".json")
    
def get_suggestion_file(live, cli_path=None):
    if live:
        if cli_path is None:
            return "./live/suggestion.json"
        else:
            return os.path.join(os.path.dirname(cli_path), "live", SUGGESTION_SUFFIX + os.path.basename(cli_path) + ".json")
    else:
        if cli_path is None:
            return "./test/suggestion.json"
        else:
            return os.path.join(os.path.dirname(cli_path), "test", SUGGESTION_SUFFIX + os.path.basename(cli_path) + ".json")    
    
def current_timestamp():
    return datetime.now().strftime("[%Y-%m-%d]")

def valid_date(date):
    if date is None:
        return None
    try:
        return datetime.strptime(date, "%Y-%m-%d").strftime("[%Y-%m-%d]")
    except ValueError:
        print(f"Not a valid date: '{date}'. Format must be YYYY-MM-DD.")
        sys.exit(1)

def load_file(data_file):
    try:
        with open(data_file, "r", encoding=ENCODING) as file:
            return json.load(file)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        print("Corrupted file. Abort loading")
        return None

def save_file(data, data_file):
    directory = os.path.dirname(data_file)
    backup_file = os.path.join(directory, "backup", BACKUP_SUFFIX + os.path.basename(data_file))

    if not os.path.exists(directory):
        os.makedirs(directory)
    if not os.path.exists(os.path.join(directory, "backup")):
        os.makedirs(os.path.join(directory, "backup"))

    try:
        if os.path.exists(data_file):
            shutil.copy2(data_file, backup_file)
    except Exception as e:
        print(f"Warning could not create backup: {e}, {backup_file}")

    try:
        with open(data_file, "w", encoding=ENCODING) as file:
            json.dump(data, file, indent=2)
    except Exception as e:
        print(f"Error saving data: {e}")

def clean_old_meals(meals, days=30):
    cutoff = datetime.now() - timedelta(days=days)
    return [
        meal for meal in meals
        if datetime.strptime(meal["timestamp"], "[%Y-%m-%d]") >= cutoff
    ]

def add_meal(meal, meal_file, suggestion_file, date):
    meals = load_file(meal_file)
    if meals is None:
        meals = []

    meals = clean_old_meals(meals)

 
    entry = {
        "timestamp": current_timestamp() if date == None else date,
        "content": meal
    }
    meals.append(entry)
    save_file(meals, meal_file)
    print(f"Meal added: {entry['content']}")

    suggestions = load_file(suggestion_file)
    if suggestions is None:
        suggestions = []

    # Avoid duplicate suggestions
    if not any(s["content"].lower() == meal.lower() for s in suggestions):
        suggestions.append({"content": meal})
        save_file(suggestions, suggestion_file)

def list_meals(data_file):
    data = load_file(data_file)
    if not data:
        print("No meals found")
    else:
        for i, item in enumerate(data, 1):
            # Support both formats: new (timestamp/content) and old (date/meal)
            timestamp = item.get('timestamp') or item.get('date') or 'unknown date'
            content = item.get('content') or item.get('meal') or 'unknown meal'
            print(f"{i}. {timestamp} - {content}")

def delete_meal(index, data_file):
    data = load_file(data_file)
    if 0 < index <= len(data):
        removed = data.pop(index - 1)
        save_file(data, data_file)
        meal_name = removed.get('content') or removed.get('meal') or 'unknown meal'
        print(f"Deleted meal {index}: {meal_name}")
    else:
        print("Invalid meal number")

def delete_all(data_file):
    save_file([], data_file)
    print("Deleted all meals")

def restore(data_file, suggestion_file):
    data_backup_file = os.path.join(os.path.dirname(data_file), "backup", BACKUP_SUFFIX + os.path.basename(data_file))
    suggestion_backup_file = os.path.join(os.path.dirname(suggestion_file), "backup", BACKUP_SUFFIX + os.path.basename(suggestion_file))
    try:
        with open(data_backup_file, "r", encoding=ENCODING) as file:
            data = json.load(file)
        with open(data_file, "w", encoding=ENCODING) as file:
            json.dump(data, file, indent=2)
        with open(suggestion_backup_file, "r", encoding=ENCODING) as file:
            data = json.load(file)
        with open(suggestion_file, "w", encoding=ENCODING) as file:
            json.dump(data, file, indent=2)        
        print("Successfully restored.")
    except FileNotFoundError:
        print("No file to restore from")
    except json.JSONDecodeError:
        print("Corrupted file. Abort restoring")
    except Exception as e:
        print(f"Error restoring data: {e}")

def suggest_meal(meal_file, suggestion_file):
    recent_meals = load_file(meal_file)
    suggestions = load_file(suggestion_file)

    if suggestions is None or not suggestions:
        print("No suggestions available.")
        return

    recent_cutoff = datetime.now() - timedelta(days=14)

    recent_names = set()
    if recent_meals:
        for meal in recent_meals:
            ts = datetime.strptime(meal["timestamp"], "[%Y-%m-%d]")
            if ts >= recent_cutoff:
                recent_names.add(meal["content"].lower())

    eligible = [m["content"] for m in suggestions if m["content"].lower() not in recent_names]

    if eligible:
        print("Suggested meal:", random.choice(eligible))
    else:
        print("No meal found that hasn't been eaten in the last 2 weeks.")

def add_suggestion(meal, suggestion_file):
    suggestions = load_file(suggestion_file)
    if suggestions is None:
        suggestions = []

    if any(s["content"].lower() == meal.lower() for s in suggestions):
        print(f"Suggestion '{meal}' already exists.")
    else:
        suggestions.append({"content": meal})
        save_file(suggestions, suggestion_file)
        print(f"Added suggestion: {meal}")

def list_suggestions(suggestion_file):
    suggestions = load_file(suggestion_file)
    if not suggestions:
        print("No suggestions found.")
    else:
        for i, s in enumerate(suggestions, 1):
            print(f"{i}. {s.get('content', 'unknown')}")

def main():
    parser = argparse.ArgumentParser(description="Meal Tracker CLI")
    parser.add_argument("--file", "-f", help="Path to meal file")
    parser.add_argument("--date", "-d", help="Date of consumtion")
    parser.add_argument("--test", "-t", action="store_false", help="Test system")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a new meal")
    add_parser.add_argument("meal", nargs="+", help="Meal name")

    add_suggest_parser = subparsers.add_parser("addsuggest", help="Add meal only to suggestions")
    add_suggest_parser.add_argument("meal", nargs="+", help="Meal name")

    subparsers.add_parser("list", help="List all meals")

    delete_parser = subparsers.add_parser("delete", help="Delete a meal by number")
    delete_parser.add_argument("index", type=int, help="Meal number to delete")

    subparsers.add_parser("deleteall", help="Delete all meals")
    subparsers.add_parser("restore", help="Restore from backup")
    subparsers.add_parser("suggest", help="Suggest a meal not eaten in the last 2 weeks")
    subparsers.add_parser("listsuggest", help="List all suggested meals")


    args = parser.parse_args()
    data_file = get_data_file(args.test ,args.file)
    suggestion_file = get_suggestion_file(args.test, args.file)

    if args.command == "add":
        meal = get_meal_input(args.meal)
        date = valid_date(args.date)
        if meal:
            add_meal(meal, data_file, suggestion_file, date)
        else:
            print("No meal content provided.")
    elif args.command == "list":
        list_meals(data_file)
    elif args.command == "delete":
        delete_meal(args.index, data_file)
    elif args.command == "deleteall":
        delete_all(data_file)
    elif args.command == "restore":
        restore(data_file, suggestion_file)
    elif args.command == "suggest":
        suggest_meal(data_file, suggestion_file)
    elif args.command == "addsuggest":
        meal = get_meal_input(args.meal)
        if meal:
            add_suggestion(meal, suggestion_file)
        else:
            print("No meal content provided.")
    elif args.command == "listsuggest":
        list_suggestions(suggestion_file)


if __name__ == "__main__":
    main()
