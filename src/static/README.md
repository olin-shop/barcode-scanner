Put image assets here (e.g. `green_corner.png`).

`GUI/gui_constants.py` resolves this folder dynamically via `pathlib`, so it
works no matter what directory the app is launched from:

```python
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
```
