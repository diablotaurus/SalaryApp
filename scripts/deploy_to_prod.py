#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ручной деплой SalaryApp: перенос кода из dev-репозитория (current) в production.

Запуск (из корня репозитория или двойным кликом по scripts/deploy_to_prod.bat):
    python scripts/deploy_to_prod.py            # реальный деплой
    python scripts/deploy_to_prod.py --dry-run  # показать план, ничего не меняя
    python scripts/deploy_to_prod.py "D:\\другой\\prod"  # другой каталог цели

Что делает (по шагам):
    1. Проверки безопасности (источник=репо, цель содержит prod.marker).
    2. Бэкап текущего прода в prod/.backup/<версия>_<дата>/.
    3. Снимок prod/bot/.env (чтобы не потерять прод-токен).
    4. Очистка прода (кроме данных и заметок — см. PRESERVE_TOP).
    5. Копирование исходников current -> prod по списку исключений.
    6. Запись очищенной версии (без суффикса "current") в prod/version.txt.
    7. Восстановление prod/bot/.env.
    8. Проверки и итог.

ГАРАНТИИ БЕЗОПАСНОСТИ:
    - Папка db (символическая ссылка на реальную БД) никогда не копируется и не удаляется.
    - prod.marker и bot/.env сохраняются (токен прода не подменяется dev-токеном).
    - Символические ссылки/junction'ы при очистке не удаляются.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import shutil
import sys
import traceback
from datetime import datetime
from pathlib import Path

# Корректный вывод UTF-8 в консоль Windows (для кириллицы и символов-маркеров).
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# ===================== НАСТРОЙКИ ПО УМОЛЧАНИЮ =====================
# Корень репозитория вычисляется относительно расположения скрипта (scripts/..),
# поэтому скрипт работает независимо от того, где лежит репозиторий.
SOURCE_DIR = Path(__file__).resolve().parent.parent
EXCLUDE_FILE = Path(__file__).resolve().parent / "deploy_exclude.txt"
# Локальный (НЕ версионируемый) файл с путём к production: одна строка с путём.
# Добавлен в .gitignore, чтобы личные пути не попадали в репозиторий.
LOCAL_TARGET_FILE = Path(__file__).resolve().parent / "deploy_target.local.txt"

# Каталоги/файлы верхнего уровня, которые НЕ удаляются при очистке прода.
# Это данные и служебные элементы продакшена.
PRESERVE_TOP = {".backup", "db", "prod.marker", "exports", "logs", "nppBackup"}

# Защищаемые секреты: снимаются перед очисткой и возвращаются после копирования.
PROTECTED_RELATIVE = ["bot/.env"]
# =================================================================


def print_header(text: str) -> None:
    print("=" * 60)
    print(f"  {text}")
    print("=" * 60)
    print()


def print_success(text: str) -> None:
    print(f"[OK] {text}")


def print_warning(text: str) -> None:
    print(f"[!] {text}")


def print_error(text: str) -> None:
    print(f"[X] {text}")


def print_info(text: str) -> None:
    print(f"[i] {text}")


def read_exclude_patterns(exclude_file: Path) -> list[str]:
    """Прочитать паттерны исключений из файла (поддерживаются комментарии '#')."""
    patterns: list[str] = []
    if not exclude_file.exists():
        print_warning(f"Файл исключений не найден: {exclude_file}")
        return patterns
    try:
        for line in exclude_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
        print_success(f"Прочитано {len(patterns)} паттернов исключений")
    except Exception as exc:
        print_error(f"Ошибка чтения файла исключений: {exc}")
    return patterns


def should_exclude(path: Path, patterns: list[str], root_path: Path) -> bool:
    """Определить, нужно ли исключить файл/папку (по относительному пути и имени)."""
    try:
        rel_path = path.relative_to(root_path)
        str_path = str(rel_path).replace("\\", "/")
        for pattern in patterns:
            normalized = pattern.replace("\\", "/")
            if fnmatch.fnmatch(str_path, normalized):
                return True
            # Имя файла/папки (для паттернов вида *.db, __pycache__ и т.п.)
            if fnmatch.fnmatch(path.name, normalized):
                return True
        return False
    except Exception:
        return True


def read_clean_version(source_path: Path) -> str:
    """Прочитать версию из version.txt и убрать служебный суффикс 'current'."""
    version_file = source_path / "version.txt"
    if not version_file.exists():
        return "unknown"
    try:
        raw = version_file.read_text(encoding="utf-8").strip()
    except Exception as exc:
        print_error(f"Ошибка чтения version.txt: {exc}")
        return "unknown"
    tokens = [t for t in raw.split() if t.lower() != "current"]
    return " ".join(tokens) if tokens else "unknown"


def read_prod_version(prod_path: Path) -> str:
    version_file = prod_path / "version.txt"
    if version_file.exists():
        try:
            return version_file.read_text(encoding="utf-8").strip() or "unknown"
        except Exception:
            return "unknown"
    return "unknown"


def snapshot_protected(prod_path: Path) -> dict[str, bytes]:
    """Сохранить в память защищаемые файлы (например, bot/.env) перед очисткой."""
    saved: dict[str, bytes] = {}
    for rel in PROTECTED_RELATIVE:
        target = prod_path / rel
        if target.is_file():
            try:
                saved[rel] = target.read_bytes()
                print_success(f"Сохранён защищаемый файл: {rel}")
            except Exception as exc:
                raise RuntimeError(
                    f"Не удалось сохранить защищаемый файл {rel}: {exc}"
                ) from exc
    if not saved:
        print_info("Защищаемые файлы не найдены (нечего сохранять)")
    return saved


def restore_protected(prod_path: Path, saved: dict[str, bytes], dry_run: bool) -> bool:
    """Вернуть защищаемые файлы на место после копирования."""
    for rel, data in saved.items():
        target = prod_path / rel
        if dry_run:
            print_info(f"[dry-run] Восстановил бы: {rel}")
            continue
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            print_success(f"Восстановлен защищаемый файл: {rel}")
        except Exception as exc:
            print_error(f"Ошибка восстановления {rel}: {exc}")
            return False
    return True


def create_backup_before_update(prod_path: Path, dry_run: bool) -> Path | None:
    """Создать резервную копию текущего прода в prod/.backup/<версия>_<дата>/."""
    print_header("Шаг 1. Резервная копия текущего прода")

    version = read_prod_version(prod_path)
    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    backup_root = prod_path / ".backup"
    backup_dir = backup_root / f"{version}_{timestamp}"
    print_info(f"Текущая версия в проде: {version}")
    print_info(f"Каталог резервной копии: {backup_dir}")

    # Что не включаем в бэкап: служебное и данные (db исключаем как симлинк).
    backup_exclude = {".backup", "db", "prod.marker", "__pycache__", "nppBackup"}

    if dry_run:
        print_info("[dry-run] Резервная копия не создаётся")
        return backup_dir

    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        print_error(f"Ошибка создания каталога резервной копии: {exc}")
        return None

    copied = 0
    errors: list[str] = []
    for item in prod_path.iterdir():
        if item.name in backup_exclude or item.is_symlink():
            continue
        try:
            target = backup_dir / item.name
            if item.is_file():
                shutil.copy2(item, target)
                copied += 1
            elif item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
                copied += sum(1 for _ in item.rglob("*") if _.is_file())
        except Exception as exc:
            message = f"Ошибка копирования {item.name}: {exc}"
            errors.append(message)
            print_error(message)

    if errors:
        print_error("Резервная копия неполная. Деплой остановлен.")
        try:
            shutil.rmtree(backup_dir)
        except OSError:
            print_warning(f"Не удалось удалить неполный бэкап: {backup_dir}")
        return None

    info = (
        f"Резервная копия версии: {version}\n"
        f"Дата создания: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
        f"Источник: {prod_path}\n"
    )
    try:
        (backup_dir / "_backup_info.txt").write_text(info, encoding="utf-8")
    except Exception:
        print_error("Не удалось записать сведения о резервной копии")
        try:
            shutil.rmtree(backup_dir)
        except OSError:
            print_warning(f"Не удалось удалить неполный бэкап: {backup_dir}")
        return None

    print_success(f"Резервная копия создана: скопировано файлов ~{copied}")
    return backup_dir


def clean_prod_directory(prod_path: Path, dry_run: bool) -> bool:
    """Очистить прод, сохранив элементы из PRESERVE_TOP и любые симлинки."""
    print_header("Шаг 2. Очистка прода перед копированием")
    deleted_files = deleted_dirs = preserved = 0
    errors: list[str] = []

    for item in prod_path.iterdir():
        # Никогда не удаляем сохраняемые элементы и символические ссылки (в т.ч. db).
        if item.name in PRESERVE_TOP or item.is_symlink():
            print_info(f"Сохранено: {item.name}")
            preserved += 1
            continue

        if dry_run:
            print_info(f"[dry-run] Удалил бы: {item.name}")
            continue

        try:
            if item.is_file():
                item.unlink()
                deleted_files += 1
            elif item.is_dir():
                shutil.rmtree(item)
                deleted_dirs += 1
        except Exception as exc:
            msg = f"Ошибка удаления {item.name}: {exc}"
            errors.append(msg)
            print_error(msg)

    if dry_run:
        print_info("[dry-run] Фактическая очистка не выполнялась")
    else:
        print_success(
            f"Очистка завершена: удалено {deleted_files} файлов и {deleted_dirs} папок, "
            f"сохранено {preserved} элементов"
        )
    return not errors


def copy_with_exclusions(src_dir: Path, dst_dir: Path, patterns: list[str], dry_run: bool) -> tuple[int, int, list[str]]:
    """Рекурсивно скопировать src -> dst, пропуская исключения и защищаемые файлы."""
    copied = skipped = 0
    errors: list[str] = []
    protected_abs = {(dst_dir / rel) for rel in PROTECTED_RELATIVE}

    for root, dirs, files in os.walk(src_dir):
        root_path = Path(root)
        # Не заходим в исключённые каталоги.
        for dir_name in dirs[:]:
            if should_exclude(root_path / dir_name, patterns, src_dir):
                dirs.remove(dir_name)
                skipped += 1

        for file_name in files:
            file_path = root_path / file_name
            if should_exclude(file_path, patterns, src_dir):
                skipped += 1
                continue
            try:
                rel = file_path.relative_to(src_dir)
                target = dst_dir / rel
                # Защищаемые файлы (bot/.env) не перезаписываем dev-версией.
                if target in protected_abs:
                    skipped += 1
                    continue
                if dry_run:
                    copied += 1
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, target)
                copied += 1
            except Exception as exc:
                msg = f"Ошибка копирования {file_name}: {exc}"
                errors.append(msg)
                print_error(msg)

    return copied, skipped, errors


def write_prod_version(prod_path: Path, clean_version: str, dry_run: bool) -> bool:
    """Записать очищенную версию (без 'current') в prod/version.txt."""
    if clean_version == "unknown":
        print_warning("Версия не определена — version.txt прода не изменяется")
        return False
    if dry_run:
        print_info(f"[dry-run] Записал бы в version.txt: {clean_version}")
        return True
    try:
        (prod_path / "version.txt").write_text(clean_version, encoding="utf-8")
        print_success(f"version.txt прода установлен в: {clean_version}")
        return True
    except Exception as exc:
        print_error(f"Ошибка записи version.txt: {exc}")
        return False


def rollback_from_backup(
    prod_path: Path,
    backup_dir: Path,
    saved_protected: dict[str, bytes],
) -> bool:
    """Restore production code from the verified pre-deploy backup."""
    print_header("АВТОМАТИЧЕСКИЙ ОТКАТ")
    if not backup_dir.is_dir():
        print_error(f"Каталог отката не найден: {backup_dir}")
        return False

    if not clean_prod_directory(prod_path, dry_run=False):
        print_error("Не удалось очистить частично обновлённый код перед откатом")
        return False

    errors: list[str] = []
    for item in backup_dir.iterdir():
        if item.name == "_backup_info.txt":
            continue
        try:
            target = prod_path / item.name
            if item.is_file():
                shutil.copy2(item, target)
            elif item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
        except Exception as exc:
            errors.append(f"{item.name}: {exc}")
            print_error(f"Ошибка отката {item.name}: {exc}")

    protected_ok = restore_protected(prod_path, saved_protected, dry_run=False)
    if errors or not protected_ok:
        print_error("Автоматический откат завершился с ошибками")
        return False

    print_success("Предыдущая версия production восстановлена")
    return True


def verify_copy_success(prod_path: Path) -> tuple[int, int]:
    """Проверить, что ключевые файлы на месте."""
    checks = [
        (prod_path / "StartSalary.pyw", "Точка входа desktop"),
        (prod_path / "run_web.py", "Точка входа web"),
        (prod_path / "run_bot.py", "Точка входа Telegram-бота"),
        (prod_path / "desktop" / "app.py", "Главное desktop-приложение"),
        (prod_path / "bot" / "main.py", "Главный модуль Telegram-бота"),
        (prod_path / "core" / "config" / "settings.py", "Конфигурация"),
        (prod_path / "prod.marker", "Маркер production"),
        (prod_path / "requirements.txt", "Зависимости"),
        (prod_path / "bot" / ".env", "Токен бота (bot/.env)"),
    ]
    passed = 0
    print("\nПроверка результатов:")
    print("-" * 40)
    for path, description in checks:
        if path.exists():
            print_success(f"{description}: OK")
            passed += 1
        else:
            print_error(f"{description}: НЕ НАЙДЕН")
    print("-" * 40)
    return passed, len(checks)


def resolve_prod_dir(cli_value: str | None) -> Path | None:
    """
    Определить каталог production без хранения личного пути в репозитории.

    Порядок поиска:
        1. Аргумент командной строки.
        2. Переменная окружения SALARYAPP_PROD_DIR.
        3. Локальный файл scripts/deploy_target.local.txt (одна строка с путём).
    """
    if cli_value:
        return Path(cli_value)
    env_value = os.getenv("SALARYAPP_PROD_DIR")
    if env_value and env_value.strip():
        return Path(env_value.strip())
    if LOCAL_TARGET_FILE.exists():
        text = LOCAL_TARGET_FILE.read_text(encoding="utf-8").strip()
        if text:
            return Path(text)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Деплой SalaryApp из current в production.")
    parser.add_argument("destination", nargs="?", default=None,
                        help="Каталог production. Если не указан — берётся из переменной "
                             "SALARYAPP_PROD_DIR или из файла scripts/deploy_target.local.txt.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Показать план, ничего не меняя.")
    parser.add_argument("--yes", action="store_true",
                        help="Не спрашивать подтверждений (для автоматизации).")
    args = parser.parse_args()

    source_path = SOURCE_DIR
    prod_path = resolve_prod_dir(args.destination)
    if prod_path is None:
        print_error(
            "Не задан каталог production. Укажите его одним из способов:\n"
            "      - аргументом: python scripts/deploy_to_prod.py \"<путь к prod>\"\n"
            "      - переменной окружения SALARYAPP_PROD_DIR\n"
            "      - файлом scripts/deploy_target.local.txt (одна строка с путём)"
        )
        return 1

    backup_dir: Path | None = None
    saved_protected: dict[str, bytes] = {}
    production_modified = False

    try:
        title = "ДЕПЛОЙ PRODUCTION SalaryApp" + (" [DRY-RUN]" if args.dry_run else "")
        print_header(title)
        print_info(f"Источник: {source_path}")
        print_info(f"Цель:     {prod_path}")
        print()

        # --- Проверки безопасности ---
        if not (source_path / "version.txt").exists():
            print_error(f"Источник не похож на репозиторий SalaryApp (нет version.txt): {source_path}")
            return 1
        # Защита: источник должен быть DEV, а не PRODUCTION.
        # prod.marker присутствует только в production-копии и отсутствует в dev.
        if (source_path / "prod.marker").exists():
            print_error(
                "Источник содержит prod.marker — похоже, скрипт запущен из PRODUCTION.\n"
                "      Запускайте деплой из dev-репозитория (current). Остановлено."
            )
            return 1
        # Защита от запуска "из прода": источник и цель не должны совпадать.
        try:
            if source_path.resolve() == prod_path.resolve():
                print_error("Источник и цель совпадают. Запускайте деплой из dev-репозитория, а не из прода.")
                return 1
        except Exception:
            pass
        if not prod_path.exists():
            print_error(f"Каталог production не найден: {prod_path}")
            return 1
        if not (prod_path / "prod.marker").exists():
            print_error(
                "В целевом каталоге нет prod.marker. Это защита от деплоя 'не туда'.\n"
                "      Деплой остановлен."
            )
            return 1

        clean_version = read_clean_version(source_path)
        prod_version = read_prod_version(prod_path)
        patterns = read_exclude_patterns(EXCLUDE_FILE)
        if not patterns:
            print_error("Список исключений пуст или недоступен. Деплой остановлен.")
            return 1
        print_info(f"Версия прода сейчас: {prod_version}")
        print_info(f"Будет установлена:  {clean_version}")
        print()

        if not args.dry_run and not args.yes:
            print("Убедитесь, что приложение SalaryApp закрыто.")
            if input("Продолжить деплой? (y/n): ").strip().lower() != "y":
                print("Деплой отменён.")
                return 1
            print()

        # --- Шаг 1: бэкап ---
        backup_dir = create_backup_before_update(prod_path, args.dry_run)
        if backup_dir is None:
            print_error("Бэкап не создан. Продолжение небезопасно.")
            return 1

        # --- Снимок защищаемых файлов ---
        print()
        saved_protected = snapshot_protected(prod_path)

        # --- Шаг 2: очистка ---
        print()
        clean_ok = clean_prod_directory(prod_path, args.dry_run)
        production_modified = not args.dry_run
        if not clean_ok and not args.dry_run:
            print_error("Очистка завершилась с ошибками. Запускаю откат.")
            rollback_from_backup(prod_path, backup_dir, saved_protected)
            return 1

        # --- Шаг 3: копирование ---
        print()
        print_header("Шаг 3. Копирование current -> prod")
        copied, skipped, errors = copy_with_exclusions(source_path, prod_path, patterns, args.dry_run)
        print_info(f"Скопировано файлов: {copied}")
        print_info(f"Пропущено (исключения): {skipped}")
        if errors:
            print_error(f"Ошибок при копировании: {len(errors)}. Запускаю откат.")
            if not args.dry_run:
                rollback_from_backup(prod_path, backup_dir, saved_protected)
            return 1

        # --- Шаг 4: version.txt ---
        print()
        print_header("Шаг 4. Версия и восстановление секретов")
        if not write_prod_version(prod_path, clean_version, args.dry_run):
            if not args.dry_run:
                rollback_from_backup(prod_path, backup_dir, saved_protected)
            return 1

        # --- Шаг 5: восстановление bot/.env ---
        if not restore_protected(prod_path, saved_protected, args.dry_run):
            if not args.dry_run:
                rollback_from_backup(prod_path, backup_dir, saved_protected)
            return 1

        # --- Итог ---
        print()
        print_header("ИТОГ")
        if args.dry_run:
            print_success("DRY-RUN завершён. Изменения НЕ вносились.")
            print_info("Для реального деплоя запустите без --dry-run.")
            return 0

        passed, total = verify_copy_success(prod_path)
        success = (passed == total and not errors)
        print()
        if success:
            print_success("ДЕПЛОЙ ЗАВЕРШЁН УСПЕШНО!")
            print(f"Резервная копия предыдущей версии — в {prod_path / '.backup'}")
            print("Запустите приложение из прода и проверьте заголовок (РЕАЛЬНАЯ БАЗА ДАННЫХ).")
        else:
            print_warning("ДЕПЛОЙ ЗАВЕРШЁН С ПРЕДУПРЕЖДЕНИЯМИ.")
            print(f"Проверки пройдены: {passed}/{total}; ошибок копирования: {len(errors)}")
            rollback_from_backup(prod_path, backup_dir, saved_protected)
        return 0 if success else 1

    except Exception as exc:
        print_error(f"Критическая ошибка: {exc}")
        traceback.print_exc()
        if production_modified and backup_dir is not None:
            rollback_from_backup(prod_path, backup_dir, saved_protected)
        return 1


if __name__ == "__main__":
    sys.exit(main())
