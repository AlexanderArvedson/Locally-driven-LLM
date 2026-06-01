# Project use-cases

## Tested use-cases so far

- Code refactoring/update
- Documentation

## Results

### Code refactoring

Current results are iffy, at one time it initially changed a lot more than was instructed in the task itself, where instead of removing the type hint from a single specified function, it removed all of the ones from the entire file. 

### Documentation

Single test done, decent results so far. It seems to have successfully added docstrings to all the functions in the file, without destroying anything.

For both of the current test cases, the file used was `apps\desktop\python_integration\modules\config_handler\dto_map.py` from the modukey monorepo