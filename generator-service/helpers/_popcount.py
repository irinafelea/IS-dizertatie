def _popcount(x: int) -> int:
    """
    Counts the number of set bits in an integer

    Args:
        x: Integer bitmask

    Returns:
        Number of bits set to 1
    """
    c = 0
    while x:
        x &= x - 1
        c += 1
    return c
