# Contributing

Small, focused pull requests are easiest to review. Please explain the operational problem being solved, keep production identifiers out of fixtures and examples, and add or update tests when behavior changes.

Before opening a pull request:

```bash
python3 -m py_compile src/collector.py
python3 -m unittest discover -s tests -v
```
