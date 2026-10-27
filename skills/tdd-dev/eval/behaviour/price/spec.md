# Price rounding

`round_price(text)` returns decimal money with exactly two places. Round ties away from zero
(half-up); support negative values and zero. Input is a finite decimal string.
