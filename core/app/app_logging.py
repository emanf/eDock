import traceback
from datetime import datetime

from core.paths import ensure_app_cache_dir


def sanitize_app_id(app_id):
    if not app_id:
        return "_unknown"
    return str(app_id).strip() or "_unknown"


def resolve_app_id(app_instance=None, app_data=None, app_id=None):
    if app_id:
        return sanitize_app_id(app_id)

    if isinstance(app_data, dict):
        value = app_data.get("id")
        if value:
            return sanitize_app_id(value)

    if app_instance is not None:
        for attr in ("app_id", "id"):
            value = getattr(app_instance, attr, None)
            if value:
                return sanitize_app_id(value)

        manifest = getattr(app_instance, "manifest", None)
        if isinstance(manifest, dict):
            value = manifest.get("id")
            if value:
                return sanitize_app_id(value)

    return "_unknown"


def get_app_log_path(app_id):
    safe_app_id = sanitize_app_id(app_id)
    cache_dir = ensure_app_cache_dir(safe_app_id)
    return cache_dir / "logs" / "log.txt"


def write_app_log(
    message, exc=None, app_instance=None, app_data=None, app_id=None, source="App"
):
    resolved_app_id = resolve_app_id(
        app_instance=app_instance,
        app_data=app_data,
        app_id=app_id,
    )

    log_path = get_app_log_path(resolved_app_id)

    lines = [
        "=" * 80,
        f"time: {datetime.now().isoformat()}",
        f"source: {source}",
        f"app_id: {resolved_app_id}",
        f"message: {message}",
    ]

    if exc is not None:
        lines.append("traceback:")
        lines.append(traceback.format_exc())

    lines.append("")

    try:
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        with open(log_path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception as log_error:
        print(f"[{source}] Failed to write log for '{resolved_app_id}': {log_error}")


def print_and_log(
    message, exc=None, app_instance=None, app_data=None, app_id=None, source="App"
):
    resolved_app_id = resolve_app_id(
        app_instance=app_instance,
        app_data=app_data,
        app_id=app_id,
    )

    print(f"[{source}][{resolved_app_id}] {message}")
    if exc is not None:
        traceback.print_exc()

    write_app_log(
        message=message,
        exc=exc,
        app_instance=app_instance,
        app_data=app_data,
        app_id=resolved_app_id,
        source=source,
    )


def safe_app_call(
    func,
    default=None,
    action_name="unknown",
    app_instance=None,
    app_data=None,
    app_id=None,
    source="App",
):
    try:
        return func()
    except Exception as e:
        print_and_log(
            message=f"App action '{action_name}' failed",
            exc=e,
            app_instance=app_instance,
            app_data=app_data,
            app_id=app_id,
            source=source,
        )
        return default
