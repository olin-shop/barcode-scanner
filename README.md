# barcode-scanner
A barcode scanner for our shop.

## Backend Overview

This project contains a Python backend (in `src/backend/`) that coordinates requests between the barcode scanner and the Power Automate workflows.

### Environment Variables & Installation
**IMPORTANT:** To run this backend, you must have a `.env` file in the root directory containing the required webhook URLs.

**Ask Shop Instructors for the `.env` file for the barcode scanner before testing and developing.**

After securing the `.env` file, install all backend dependencies using Poetry:
```bash
poetry install
```

### Backend Architecture Overview

The backend uses an asynchronous webhook callback pattern to handle requests to Power Automate. Because Power Automate can take several seconds to process a request, the backend needs a way to "pause" and wait for the response without blocking other requests.

Here is a sequence diagram of how a typical request flows through the backend:

```text
1. User scans barcode → requests.py::get_item()
2. Python generates a unique RequestID (UUID) and creates an asyncio.Future (similar to a Promise in JavaScript).
3. The Future is stored in app_state.pending_requests.
4. Python POSTs the payload (including RequestID) to the Power Automate webhook.
5. Python pauses execution, waiting for the Future to be resolved.
6. Power Automate finishes its workflow and POSTs the result back to endpoints.py::/items with the RequestID.
7. endpoints.py finds the Future in pending_requests using the RequestID and sets the result with the data.
8. requests.py resumes and returns the requested data.
```

This pattern guarantees that even if multiple people are scanning barcodes at the same time, every request will be matched to its correct response.

## Adding Features and Maintaining the Codebase

If you are a new developer or an AI assistant adding features to this codebase, please adhere to the following principles to keep the code clean and maintainable:

1. **Use Type Hints Everywhere**: Every variable, function argument, and return value must have a Python type hint. This allows IDE autocomplete to work flawlessly and drastically reduces cognitive overhead when reading the code.
2. **Keep it Documented**: Ensure that any new functions, routes, or complex logic blocks have descriptive docstrings. Explain *why* the code is doing what it does, not just *what* it is doing.
3. **Handle Global State Carefully**: Any global or mutable state (such as `pending_requests`) should be kept inside `src/backend/app_state.py` or attached directly to the application context. `backend_constants.py` is strictly for immutable variables.
4. **Use Explicit Enums**: Use the `Status` string-enum defined in `backend_types.py` for checking item states rather than loose strings to prevent typos.
5. **Delete Dead Code**: If a file or function is no longer used, delete it. Make sure there is a commit at one point and time keeping it deprecated, and then delete it in the next commit.

## Testing

The codebase is fully tested using `pytest` across Backend, Email, and GUI modules.

### Running the Unit Test Suite
To run all unit tests (Backend, Email, and GUI) without hitting live external webhooks:
```bash
poetry run pytest -m "not integration"
```
Or directly with Python:
```bash
python -m pytest -m "not integration"
```

### Module Specific Testing
- **Backend Tests**: `poetry run pytest tests/backend/`
- **Email Service Tests**: `poetry run pytest tests/email/`
- **GUI & Session Manager Tests**: `poetry run pytest tests/gui/`

### Headless & Cross-Platform Testing (Linux / Raspberry Pi ARM64)
- **Windows & macOS**: GUI and window tests run directly offscreen via window withdrawal.
- **Linux / Raspberry Pi (headless without display)**: Use `xvfb-run` to emulate an X11 server for headless Tkinter window testing:
  ```bash
  xvfb-run poetry run pytest -m "not integration"
  ```
- **ARM64 Linux (Raspberry Pi 3B+)**: CI automatically runs the complete test matrix inside an ARM64 container (`aarch64`) with `xvfb-run`.

### Live Integration Tests
If you want to test against **real** Power Automate flows (requires a valid `.env` file), run:
```bash
poetry run pytest -m integration
```
This suite skips automatically in GitHub Actions or if `.env` webhook URLs are omitted.
