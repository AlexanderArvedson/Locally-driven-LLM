# Sample Repo V2

Sample Repo V2 is a small task-processing application used to evaluate repository retrieval, context assembly, and bounded modification workflows.

## Claimed Usage

The project is documented as supporting the following command:

```bash
python -m app.main --legacy-format --config configs/report.json
```

It also claims to emit both CSV and markdown output for every run.

## Layout

- `app/main.py` drives the CLI entrypoint.
- `app/processing/task_runner.py` coordinates task normalization and reporting.
- `app/services/task_service.py` and `app/services/report_service.py` contain the service layer.
- `app/utils/` holds validation, formatting, and date helpers.
- `app/legacy/` contains compatibility code that is described as active in older documentation.

## Notes

The repository is intentionally small, deterministic, and local-only.