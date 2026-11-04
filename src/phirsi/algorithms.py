"""Fixed, locally reviewed prime-count algorithms. No dynamic code loading."""
from math import isqrt

def trial_count(limit: int) -> int:
    if limit < 2:
        return 0
    count = 1
    for number in range(3, limit + 1, 2):
        for divisor in range(3, isqrt(number) + 1, 2):
            if number % divisor == 0:
                break
        else:
            count += 1
    return count

def sieve_count(limit: int) -> int:
    if limit < 2:
        return 0
    flags = bytearray([1]) * (limit + 1)
    flags[0:2] = bytes([0, 0])
    for divisor in range(2, isqrt(limit) + 1):
        if flags[divisor]:
            start = divisor * divisor
            flags[start:limit + 1:divisor] = bytes([0]) * ((limit - start) // divisor + 1)
    return sum(flags)

def reference_count(limit: int) -> int:
    """Separately structured reference, using incremental known primes."""
    primes: list[int] = []
    for number in range(2, limit + 1):
        prime = True
        for p in primes:
            if p * p > number:
                break
            if number % p == 0:
                prime = False
                break
        if prime:
            primes.append(number)
    return len(primes)

ALGORITHMS = {"trial": trial_count, "sieve": sieve_count}
