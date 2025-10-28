"""Compatibility monkeypatch for Django template Context __copy__ on Python 3.14+
This module is intentionally imported early (from settings) to apply a safe __copy__
implementation that avoids assigning attributes on a 'super' proxy object which
is incompatible with some CPython 3.14 behavior.
The implementation is defensive and will silently no-op if Django isn't present.
"""

try:
    from django.template import context as dj_context
except Exception:
    dj_context = None


def _safe_copy(self):
    """Return a shallow copy of the context instance in a way that is safe
    across Django and Python versions.
    """
    cls = self.__class__
    # Create a blank instance without calling __init__
    try:
        new = object.__new__(cls)
    except Exception:
        # Fallback: use a plain object if class can't be instantiated this way
        new = {}

    # Copy attributes from __dict__ if available
    if hasattr(self, "__dict__") and isinstance(new, object):
        try:
            new.__dict__.update(self.__dict__.copy())
        except Exception:
            # As a last resort, shallow copy attribute by attribute
            for k, v in list(getattr(self, "__dict__", {}).items()):
                try:
                    setattr(new, k, v)
                except Exception:
                    pass

    # Ensure a safe shallow copy of the 'dicts' attribute if present
    if hasattr(self, "dicts"):
        try:
            new.dicts = [d.copy() if hasattr(d, "copy") else d for d in self.dicts]
        except Exception:
            try:
                new.dicts = list(self.dicts)
            except Exception:
                # ignore if not copyable
                pass

    return new


# Apply monkeypatch if Django is available
if dj_context is not None:
    for name in ("BaseContext", "Context"):
        try:
            cls = getattr(dj_context, name, None)
            if cls is not None:
                # Replace or set a safe __copy__ implementation
                cls.__copy__ = _safe_copy
        except Exception:
            # Do not fail import if patching isn't possible
            pass
