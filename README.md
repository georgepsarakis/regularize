# Regular Expression Composer

## Motivation

Writing complex regular expressions can prove difficult and error-prone. This library aims to provide a simple interface for constructing patterns, finding matches and performing substitutions.

### Key Features

- Interface for adding / removing flags such as case-insensitive, multiline and multiline _dot_ operator.
- Immutable pattern objects: a new Pattern instance is returned on each method call, allowing patterns to be reused multiple times (see [Examples](#examples)).

## Examples



```python
>>> from regex_composer import pattern, finder

>>> logfile_pattern = pattern()
>>> logfile_pattern = logfile_pattern.\
                      literal('application.').\
                      any_number_between().\
                      quantify(minimum=1).case_insensitive()

>>> uncompressed_logfile = logfile_pattern.literal('.log').end_anchor()
>>> compressed_logfile = logfile_pattern.literal('.log.gz')

>>> print(finder(uncompressed_logfile).match('application.1.log'))
<re.Match object; span=(0, 17), match='application.1.log'>
```

## API

### Pattern Builder

### Finder

### Substitution (Replace) 

## Extending

---