def solve(x):
    v = x
    v = v - 11
    v = 2 * v + 1
    v = (v * v) % 101
    v = (v + 5) // 3
    return v
