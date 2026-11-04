"""Example proposal source, not executed by R3 CI."""
from math import isqrt


def count_primes(limit: int) -> int:
    if limit < 2:
        return 0
    flags = bytearray([True]) * (limit + 1)
    flags[0:2] = b"\x00\x00"
    for divisor in range(2, isqrt(limit) + 1):
        if flags[divisor]:
            first = divisor * divisor
            flags[first:limit + 1:divisor] = b"\x00" * ((limit - first) // divisor + 1)
    return sum(flags)
